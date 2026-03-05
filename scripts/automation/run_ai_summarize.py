"""
run_ai_summarize.py  (V4.1)
============================
动态扫描 HRBP 周报表字段，对各模块生成 AI 摘要并写回。
触发后同时生成 AI议程建议（基于原始内容，不依赖摘要）。

原则：
  - BP 填写的原始内容字段：绝对只读，不得修改
  - 系统只写入：摘要_xxx、AI议程建议、汇报标识_系统自动
  - 每条记录：摘要已存在 → 跳过（不重复调用）
  - 原始内容为空 → 跳过（不写任何内容）
  - 原始内容 < 10字 → 直接写入原始内容，不调用 AI
  - 原始内容 ≥ 10字 → 调用 DeepSeek 生成 15-20 字摘要

命名合规检查：字段名含全角符号/括号/连字符会打印警告。

运行：
  python -m scripts.run_ai_summarize
  或由 run_bot_master.py "生成摘要" 指令触发
"""

import sys
import os
import re
import time
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import yaml
from core.bitable import BitableClient
from core.ai_helper import AIHelper

# ── 字段名合规检查 ──────────────────────────────────────
_BAD_CHARS = re.compile(r'[（）【】《》\u201c\u201d\u2018\u2019\u2014、。，！？：；·()\[\]]')

def _check_field_name(name: str):
    if _BAD_CHARS.search(name):
        print(f"  ⚠️  [字段命名警告] '{name}' 含不规范符号，可能导致 API 识别问题，建议改为纯中文或「半角:_」格式")


def _get_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _extract_text(val) -> str:
    """统一从飞书字段值中提取纯文本。"""
    if val is None:
        return ""
    if isinstance(val, bool):
        return ""
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts = []
        for v in val:
            if isinstance(v, dict):
                parts.append(v.get("text", v.get("name", str(v))))
            else:
                parts.append(str(v))
        return "".join(parts)
    if isinstance(val, dict):
        return val.get("text", val.get("name", str(val)))
    return str(val)


# ── 动态字段映射构建 ────────────────────────────────────
def build_module_map(all_fields: list, verbose: bool = True) -> list:
    """
    从字段列表中动态构建模块映射。
    返回: [(raw_field_name, summary_field_name, display_name), ...]

    逻辑：
      - 找到所有 摘要_xxx 字段
      - 对每个 摘要_xxx，在原始字段中寻找名称包含 xxx 的文本字段（type=1）
      - 如果找不到，打印警告
    """
    summary_fields = {f["field_name"]: f for f in all_fields if f["field_name"].startswith("摘要_")}
    raw_text_fields = {f["field_name"]: f for f in all_fields if f.get("type") == 1 and not f["field_name"].startswith("摘要_")}

    # 检查所有字段命名合规性
    for f in all_fields:
        _check_field_name(f["field_name"])

    module_map = []
    for summary_name in sorted(summary_fields.keys()):
        key = summary_name.replace("摘要_", "")  # e.g. "招聘", "Agent", "人员"
        # 模糊匹配：原始字段名包含 key
        matched = [fname for fname in raw_text_fields if key in fname and not fname.startswith("摘要_")]
        if not matched:
            if verbose:
                print(f"  ⚠️  [字段映射] 未找到对应 '{summary_name}' 的原始内容字段（含 '{key}' 的文本字段不存在）")
            continue
        # 若多个匹配取最短名（最精确）
        raw_name = min(matched, key=len)
        module_map.append((raw_name, summary_name, key))
        if verbose:
            print(f"  ✅ 字段映射: {raw_name!r:25s} → {summary_name!r}")

    return module_map


def _compute_content_hash(module_texts: dict) -> str:
    """
    对一条记录的所有原始内容进行哈希，用于检测 BP 是否编辑过内容。
    最终输出是一个定长 8 位字符串，写入小表内的「内容指纹」字段。
    """
    combined = "|".join(f"{k}:{v}" for k, v in sorted(module_texts.items()))
    return hashlib.md5(combined.encode("utf-8")).hexdigest()[:8]


# ── 主函数 ──────────────────────────────────────────────
def run_summarize(app_token: str = None, table_id: str = None, verbose: bool = True,
                  force: bool = False) -> str:
    """
    扫描、摘要、生成议程。
    force=True 时强制重新生成所有已有摘要。
    """
    cfg = _get_config()
    if not app_token:
        app_token = cfg["hrbp_dashboard"]["app_token"]
    if not table_id:
        table_id = cfg["hrbp_dashboard"]["table_id"]

    bitable = BitableClient()
    ai = AIHelper()

    # 1. 扫描字段，动态构建映射
    if verbose:
        print("\n🔍 扫描字段结构...")
    all_fields = bitable.list_fields(app_token, table_id)
    module_map = build_module_map(all_fields, verbose)
    if not module_map:
        return "未能构建任何字段映射，请检查多维表字段命名。"

    # 2. 读取记录
    if verbose:
        print(f"\n📋 读取周报记录...")
    records = bitable.list_records(app_token, table_id)
    if not records:
        return "周报表暂无记录。"

    if verbose:
        print(f"  共 {len(records)} 条记录，开始处理...\n")

    updates_needed = []           # [{record_id, fields}]
    agenda_source_parts = []      # 用于生成议程的原始内容聚合
    total_skipped = 0
    total_short  = 0
    total_ai     = 0

    for rec in records:
        fields     = rec.get("fields", {})
        record_id  = rec.get("record_id", "")
        reporter   = _extract_text(fields.get("汇报人", record_id))
        new_fields = {}

        # 每 BP 的全部原始内容（供议程使用）
        bp_raw_parts = []

        # 收集所有模块的原始内容，用于内容哈希计算
        raw_content_map = {}
        for raw_field, summary_field, module_name in module_map:
            raw_content_map[raw_field] = _extract_text(fields.get(raw_field, "")).strip()

        # 计算当前内容的哈希指纹并与表中已存的对比
        current_hash = _compute_content_hash(raw_content_map)
        stored_hash  = _extract_text(fields.get("内容指纹", "")).strip()
        content_changed = (current_hash != stored_hash)
        if content_changed:
            new_fields["内容指纹"] = current_hash  # 更新存储的哈希字段

        # 自动计算 周索引 和 汇报标识
        create_ts = fields.get("创建时间")
        if create_ts:
            dt = datetime.fromtimestamp(int(create_ts) / 1000)
            week_of_month = (dt.day - 1) // 7 + 1
            
            calc_week_idx = f"{str(dt.year)[-2:]}M{dt.month}W{week_of_month}"
            calc_report_tag = f"{dt.year}年{dt.month}月第{week_of_month}周"
            
            curr_week_idx = _extract_text(fields.get("周索引", "")).strip()
            curr_report_tag = _extract_text(fields.get("汇报标识_系统自动", "")).strip()
            
            if curr_week_idx != calc_week_idx:
                new_fields["周索引"] = calc_week_idx
            if curr_report_tag != calc_report_tag:
                new_fields["汇报标识_系统自动"] = f"{reporter}-{calc_report_tag}" # 加上汇报人，确保标识清晰

        for raw_field, summary_field, module_name in module_map:
            raw_content = raw_content_map[raw_field]

            # 聚合原始内容给议程
            if raw_content:
                bp_raw_parts.append(f"「{module_name}」{raw_content}")

            # 内容指纹未变且已有摘要 → 跳过（不消耗 token）
            existing_summary = _extract_text(fields.get(summary_field, "")).strip()
            if existing_summary and not content_changed and not force:
                total_skipped += 1
                if verbose:
                    print(f"  ✓ 内容未变，跳过: {reporter} — {module_name}")
                continue

            # 原始内容为空 → 不写任何东西
            if not raw_content:
                if verbose:
                    print(f"  — 原始内容为空，跳过: {reporter} — {module_name}")
                continue

            # 原始内容 < 10字 → 直接写入原始内容，不调用 AI
            if len(raw_content) < 10:
                new_fields[summary_field] = raw_content
                total_short += 1
                if verbose:
                    print(f"  📝 内容极短，直接写入: {reporter} — {module_name}: {raw_content!r}")
                continue

            # 调用 AI 生成摘要（内容已变或摘要为空）
            if verbose:
                print(f"  🤖 内容已变，重新生成摘要: {reporter} — {module_name}")
            summary = ai.summarize_module(module_name, raw_content, verbose)
            if summary:
                new_fields[summary_field] = summary
                total_ai += 1

        # 聚合议程内容并生成个体议程
        if bp_raw_parts:
            highlights_raw = _extract_text(fields.get("本周需重点汇报模块", ""))
            bp_content_for_ai = f"「BP勾选重点：{highlights_raw or '未勾选'}」\n" + "\n".join(bp_raw_parts)

            existing_agenda = _extract_text(fields.get("AI议程建议", "")).strip()
            # 内容发生变化或尚无议程时，重新生成
            if not existing_agenda or content_changed or force:
                agenda = ai.generate_individual_agenda(bp_content_for_ai)
                if agenda:
                    new_fields["AI议程建议"] = agenda
                    if verbose:
                        print(f"  🤖 已提炼个体议程: {reporter}")
            elif verbose:
                print(f"  ✓ 议程未变，跳过: {reporter}")

        if new_fields:
            updates_needed.append({"record_id": record_id, "fields": new_fields})

    # 3. 写回摘要与议程
    ok_count = 0
    if updates_needed:
        if verbose:
            print(f"\n📝 写回 {len(updates_needed)} 条记录的摘要/议程字段...")
        ok_count = bitable.batch_update_records(app_token, table_id, updates_needed)

    # 4. 汇总结果
    result_parts = []
    if ok_count:
        result_parts.append(f"智能内容写回 {ok_count} 条记录")
    if total_ai:
        result_parts.append(f"AI生成 {total_ai} 个模块")
    if total_short:
        result_parts.append(f"短内容直写 {total_short} 个")
    if total_skipped:
        result_parts.append(f"跳过已有摘要 {total_skipped} 个")

    result = "、".join(result_parts) + "。" if result_parts else "所有摘要均已处理或无需更新。"
    if verbose:
        print(f"\n✅ {result}")
    return result


if __name__ == "__main__":
    print(run_summarize(verbose=True))
