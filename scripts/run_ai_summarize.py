"""
run_ai_summarize.py
===================
扫描 HRBP 周报表，对各模块原始内容自动生成 AI 摘要（15-20字），
写回对应的 摘要_xxx 字段。

字段映射（原始内容 → AI摘要）：
  M1 招聘产出与HC确认  → 摘要_招聘
  M2 Agent实践与业务进展 → 摘要_Agent
  M3 人员情况跟进     → 摘要_人员
  M4 业务部门情况     → 摘要_业务
  M5 卡点与下周计划   → 摘要_计划

运行方式：
  python -m scripts.run_ai_summarize
  或由 run_bot_master.py 通过"生成摘要"指令触发。
"""

import sys
import os

# 支持从项目根目录运行
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from core.bitable import BitableClient
from core.ai_helper import AIHelper

# ── 字段映射 ──────────────────────────────────────────────────────────
# (原始内容字段名, AI摘要写入字段名, 模块显示名)
MODULE_MAP = [
    ("M1 招聘产出与HC确认",    "摘要_招聘",  "招聘"),
    ("M2 Agent实践与业务进展", "摘要_Agent", "Agent"),
    ("M3 人员情况跟进",        "摘要_人员",  "人员"),
    ("M4 业务部门情况",        "摘要_业务",  "业务"),
    ("M5 卡点与下周计划",      "摘要_计划",  "计划"),
]


def _get_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_summarize(app_token: str = None, table_id: str = None, verbose: bool = True) -> str:
    """
    主入口。可直接调用或由机器人触发。
    返回结果摘要文本。
    """
    cfg = _get_config()
    if not app_token:
        app_token = cfg["hrbp_dashboard"]["app_token"]
    if not table_id:
        table_id = cfg["hrbp_dashboard"]["table_id"]

    bitable = BitableClient()
    ai = AIHelper()

    if verbose:
        print(f"🔍 读取多维表记录... app_token={app_token[:8]}...")
    records = bitable.list_records(app_token, table_id)
    if not records:
        return "周报表暂无记录。"

    total_updated = 0
    total_skipped = 0
    updates_needed = []

    for rec in records:
        fields = rec.get("fields", {})
        record_id = rec.get("record_id", "")
        reporter = fields.get("汇报人", record_id)
        if isinstance(reporter, list):
            reporter = "".join(
                v.get("text", "") if isinstance(v, dict) else str(v) for v in reporter
            )

        new_fields = {}
        for raw_field, summary_field, module_name in MODULE_MAP:
            # 跳过：摘要已有内容
            existing_summary = fields.get(summary_field, "")
            if isinstance(existing_summary, list):
                existing_summary = "".join(
                    v.get("text", "") if isinstance(v, dict) else str(v)
                    for v in existing_summary
                )
            if str(existing_summary).strip():
                if verbose:
                    print(f"  ✓ 已有摘要，跳过: {reporter} — {module_name}")
                total_skipped += 1
                continue

            # 读取原始内容
            raw_content = fields.get(raw_field, "")
            if isinstance(raw_content, list):
                raw_content = "".join(
                    v.get("text", "") if isinstance(v, dict) else str(v)
                    for v in raw_content
                )
            raw_content = str(raw_content).strip()

            if not raw_content or len(raw_content) < 8:
                if verbose:
                    print(f"  — 原始内容为空，跳过: {reporter} — {module_name}")
                total_skipped += 1
                continue

            # 调用 AI 生成摘要
            summary = ai.summarize_module(module_name, raw_content)
            if summary:
                new_fields[summary_field] = summary

        if new_fields:
            updates_needed.append({"record_id": record_id, "fields": new_fields})

    if not updates_needed:
        return f"所有模块摘要均已存在或无内容可总结（跳过 {total_skipped} 条）。"

    if verbose:
        print(f"\n📝 准备写回 {len(updates_needed)} 条记录...")
    total_updated = bitable.batch_update_records(app_token, table_id, updates_needed)

    result = f"AI 摘要生成完成：成功写回 {total_updated} 条记录，跳过 {total_skipped} 个字段。"
    if verbose:
        print(f"\n✅ {result}")
    return result


if __name__ == "__main__":
    print(run_summarize(verbose=True))
