"""
dashboard.py — HRBP 周会智能看板 (V4.1)
=========================================
三视图：老板审阅 | 周会投屏 | 历史数据汇总

V4.1 修订：
  - 字段名来自实际扫描，动态识别，不硬编码
  - 模块为空 → 不渲染，节省视图空间
  - 老板复选框 = 新增汇报模块（合并到 BP 已选，非覆盖）
  - 投屏：显示集合 = BP勾选 ∪ 老板新增
  - AI议程 → 只读展示（由脚本写回，无需看板内点击）
   - 密码保护老板审阅 & 历史数据
   - 动态全局与个体 AI 议程生成
"""

import streamlit as st
import yaml
import os
import plotly.graph_objects as go
from collections import defaultdict
from datetime import datetime
from core.bitable import BitableClient
from core.ai_helper import AIHelper

# ═══════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════
st.set_page_config(
    page_title="HRBP 周会智能看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stAppViewContainer"] { background: #f8f9fa; }
[data-testid="stHeader"] { background: transparent; }

.view-title {
    font-size: 1.6rem; font-weight: 700; color: #1e293b;
    border-left: 5px solid #3b82f6; padding-left: 12px; margin-bottom: 20px;
}
.bp-name { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
.module-hot {
    background: linear-gradient(135deg, #fff1f2, #ffe4e6);
    border-left: 4px solid #ef4444; padding: 12px 16px;
    border-radius: 0 10px 10px 0; margin: 8px 0; color: #1e293b;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.module-boss {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border-left: 4px solid #22c55e; padding: 12px 16px;
    border-radius: 0 10px 10px 0; margin: 8px 0; color: #1e293b;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.module-normal {
    background: #ffffff; border-left: 4px solid #cbd5e1;
    padding: 12px 16px; border-radius: 0 10px 10px 0; margin: 8px 0; color: #334155;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.ai-box {
    background: linear-gradient(135deg, #eff6ff, #dbeafe);
    border: 1px solid #bfdbfe; border-radius: 12px; padding: 16px; color: #1e3a8a;
    margin-top: 8px; font-size: 0.95rem; line-height: 1.6;
    box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}
.agenda-panel {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border: 1px solid #bae6fd; border-radius: 16px; padding: 20px;
    color: #0369a1; margin-bottom: 24px; white-space: pre-wrap;
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.08); font-size: 0.95rem; line-height: 1.6;
}
.order-panel {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 16px 20px; font-size: 0.9rem; color: #475569;
    box-shadow: 0 4px 6px rgba(0,0,0,0.03);
}
.order-item { padding: 8px 0; border-bottom: 1px solid #f1f5f9; color: #0f172a; font-weight: 500;}
.order-item:last-child { border-bottom: none; }

.tag-bp   { background: #ef4444; color: #fff; border-radius: 6px;
            padding: 4px 10px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; }
.tag-boss { background: #22c55e; color: #fff; border-radius: 6px;
            padding: 4px 10px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; }
.tag-normal { background: #e2e8f0; color: #475569; border-radius: 6px;
              padding: 4px 10px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; }
.pw-box {
    background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px;
    padding: 32px; max-width: 400px; margin: 60px auto; text-align: center;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 配置读取（双模式：Streamlit Secrets / 本地 YAML）
# ═══════════════════════════════════════════════
def _get_dashboard_config():
    try:
        if "hrbp_dashboard" in st.secrets:
            return {
                "app_token": st.secrets["hrbp_dashboard"]["app_token"],
                "table_id":  st.secrets["hrbp_dashboard"]["table_id"],
            }
    except Exception:
        pass
    cfg_path = os.path.join(os.path.dirname(__file__), "configs", "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["hrbp_dashboard"]


def _get_boss_password():
    try:
        return st.secrets.get("access", {}).get("boss_password", "")
    except Exception:
        return ""


# ═══════════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════════
@st.cache_resource
def get_clients():
    return BitableClient(), AIHelper()


bitable, ai = get_clients()
_dash = _get_dashboard_config()
APP_TOKEN = _dash["app_token"]
TABLE_ID  = _dash["table_id"]

# BP配置中心 表 ID（动态查找含 "BP配置" 的表名）
@st.cache_data(ttl=600)
def get_bp_config_table_id():
    for t in bitable.list_tables(APP_TOKEN):
        if "BP配置" in t.get("name", ""):
            return t["table_id"]
    return ""


# ═══════════════════════════════════════════════
# 固定字段
# ═══════════════════════════════════════════════
FIELD_REPORTER   = "汇报人"
FIELD_GROUP      = "所属小组"
FIELD_WEEK_IDX   = "周索引"
FIELD_CREATE_TS  = "创建时间"
FIELD_HIGHLIGHTS = "本周需重点汇报模块"
FIELD_AI_AGENDA  = "AI议程建议"


# ═══════════════════════════════════════════════
# 动态字段扫描 & 模块映射
# ═══════════════════════════════════════════════
@st.cache_data(ttl=300)
def scan_modules():
    """
    返回模块列表：[(raw_field, summary_field, checkbox_field_or_None, label), ...]
    完全动态，不硬编码字段名。
    """
    all_fields = bitable.list_fields(APP_TOKEN, TABLE_ID)
    field_by_name = {f["field_name"]: f for f in all_fields}

    # 按照老板要求严格限定顺序
    ORDER = ["招聘", "Agent", "人员", "业务", "专项", "卡点计划"]

    summary_names = [f["field_name"] for f in all_fields if f["field_name"].startswith("摘要_")]
    def get_order_idx(name: str) -> int:
        key = name.replace("摘要_", "")
        try:
            return ORDER.index(key)
        except ValueError:
            return 999
    summary_names = sorted(summary_names, key=get_order_idx)

    raw_text_names = {f["field_name"] for f in all_fields
                      if f.get("type") == 1 and not f["field_name"].startswith("摘要_")}
    checkbox_names = {f["field_name"] for f in all_fields
                      if f["field_name"].startswith("需汇报_")}

    emoji_map = {"招聘": "📋", "Agent": "🤖", "人员": "👥", "业务": "💼", "专项": "📌", "卡点计划": "📅"}

    modules = []
    for sf in summary_names:
        key = sf.replace("摘要_", "")
        # 模糊匹配原始字段
        matched = [n for n in raw_text_names if key in n]
        raw_field = min(matched, key=len) if matched else None
        # 匹配复选框
        cb_field = f"需汇报_{key}" if f"需汇报_{key}" in checkbox_names else None
        emoji = emoji_map.get(key, "📎")
        label = f"{emoji} {key}"
        modules.append((raw_field, sf, cb_field, label))

    return modules


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════
def extract_text(val) -> str:
    if val is None: return ""
    if isinstance(val, bool): return ""
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, str): return val
    
    # Handle display_formula_ref list wrapping
    if isinstance(val, list):
        if len(val) > 0 and isinstance(val[0], dict) and "type" in val[0] and "value_extra" in val[0]:
            # e.g. [{"type": "single_option", "value_extra": {"options": [{"name": "营销组"}]}}]
            opts = val[0]["value_extra"].get("options", [])
            return "".join(opt.get("name", "") for opt in opts)
        
        parts = []
        for v in val:
            if isinstance(v, dict):
                parts.append(v.get("text", v.get("name", str(v))))
            else:
                parts.append(str(v))
        return "".join(parts)
        
    if isinstance(val, dict):
        if "value_extra" in val and "options" in val["value_extra"]:
            opts = val["value_extra"].get("options", [])
            return "".join(opt.get("name", "") for opt in opts)
        if "value" in val:
            return extract_text(val["value"])
        return val.get("text", val.get("name", str(val)))
        
    return str(val)


def get_bp_highlights(fields: dict) -> set:
    """BP 自己勾选的重点模块关键词集合。"""
    raw = fields.get(FIELD_HIGHLIGHTS, [])
    items = raw if isinstance(raw, list) else [raw]
    return {extract_text(h) for h in items if extract_text(h)}


def get_boss_checked(fields: dict, cb_field: str) -> bool:
    """老板是否已勾选该模块。"""
    if not cb_field:
        return False
    return bool(fields.get(cb_field, False))


def is_bp_hot(summary_field: str, bp_highlights: set) -> bool:
    key = summary_field.replace("摘要_", "")
    return any(key in h for h in bp_highlights)


def ts_to_str(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts) / 1000).strftime("%m/%d %H:%M")
    except Exception:
        return str(ts)


def get_display_content(fields: dict, raw_field, summary_field: str) -> str:
    """
    展示优先级：
      1. 摘要字段有内容 → 展示摘要
      2. 摘要为空，原始内容有内容 → 展示原始内容（短内容直写时摘要即原文）
      3. 都为空 → 返回 ""（不渲染该模块）
    """
    summary = extract_text(fields.get(summary_field, "")).strip()
    if summary:
        return summary
    if raw_field:
        raw = extract_text(fields.get(raw_field, "")).strip()
        return raw
    return ""


# ═══════════════════════════════════════════════
# 数据加载与缓存逻辑
# ═══════════════════════════════════════════════
@st.cache_data(ttl=60)
def load_records():
    # 强制使长期运行的 Streamlit 进程热加载最新的 bitable.py，解决 Lookup 字段解析缓存异常
    import sys, importlib
    if 'core.bitable' in sys.modules:
        importlib.reload(sys.modules['core.bitable'])
        global BitableClient, bitable
        from core.bitable import BitableClient
        bitable = BitableClient()
    records = bitable.list_records(APP_TOKEN, TABLE_ID)
    return records if records is not None else []

@st.cache_data(ttl=3600)
def get_global_agenda(records_str: str) -> str:
    ai_helper = AIHelper()
    return ai_helper.summarize_global_agenda(records_str)


def get_week_options(records):
    if not records:
        return []
    weeks = sorted(
        {extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) for r in records
         if r.get("fields") and r["fields"].get(FIELD_WEEK_IDX)},
        reverse=True,
    )
    return weeks


# ═══════════════════════════════════════════════
# 写回操作
# ═══════════════════════════════════════════════
def writeback_boss_module(record_id: str, cb_field: str, new_val: bool,
                          reporter: str, label: str):
    """写回「需汇报_xxx」并向 BP 发飞书私信。"""
    res = bitable.update_record(APP_TOKEN, TABLE_ID, record_id, {cb_field: new_val})
    if res.get("code") == 0:
        if new_val:
            bp_config_id = get_bp_config_table_id()
            if bp_config_id:
                uid = bitable.get_bp_user_id(APP_TOKEN, bp_config_id, reporter)
                if uid:
                    msg = (f"📌 你好 {reporter}！\n"
                           f"负责人在 {label} 模块额外标注了重点，"
                           f"请在周会上重点准备并汇报该模块内容（这是负责人新增，并非重复你已勾选的部分）。")
                    push_res = bitable.send_message(uid, "open_id", msg)
                    if push_res.get("code") == 0:
                        st.toast(f"✅ 已通知 {reporter} 关注「{label}」", icon="📬")
                    else:
                        st.warning(f"⚠️ 飞书推送失败（{push_res.get('msg')}）")
                else:
                    st.warning(f"⚠️ 未在 BP配置中心 找到 {reporter} 的飞书ID")
            else:
                st.warning("⚠️ 未找到 BP配置中心 表")
        else:
            st.toast(f"↩️ 已撤销管理标记: {reporter}—{label}", icon="🔄")
    else:
        st.error(f"写回失败: {res.get('msg')}")
    load_records.clear()


# ═══════════════════════════════════════════════
# 权限校验拦截
# ═══════════════════════════════════════════════
def check_boss_password(key_suffix: str) -> bool:
    boss_pw = _get_boss_password()
    if not boss_pw:
        return True
    if st.session_state.get("boss_authed"):
        return True
    st.markdown('<div class="pw-box">', unsafe_allow_html=True)
    st.markdown("🔐 **系统检测到安全拦截，请输入管理密钥**")
    pw = st.text_input("密钥", type="password", key=f"pw_input_{key_suffix}", label_visibility="collapsed")
    if st.button("效验授权", key=f"pw_btn_{key_suffix}", use_container_width=True):
        if pw == boss_pw:
            st.session_state["boss_authed"] = True
            st.rerun()
        else:
            st.error("密钥验证失败，请重试")
    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ═══════════════════════════════════════════════
# VIEW 1: 负责人审阅
# ═══════════════════════════════════════════════
def render_review_view(records, modules):
    if not check_boss_password("review"):
        return

    st.markdown('<div class="view-title">📊 负责人审阅</div>',
                unsafe_allow_html=True)

    # ── AI 议程（全局汇报）
    individual_agendas = []
    for r in records:
        f = r["fields"]
        reporter  = extract_text(f.get(FIELD_REPORTER, "未知"))
        agenda = extract_text(f.get(FIELD_AI_AGENDA, "")).strip()
        if agenda:
            individual_agendas.append(f"【{reporter}】\n{agenda}")

    if individual_agendas:
        global_input = "\n\n".join(individual_agendas)
        existing_agenda = get_global_agenda(global_input)
        st.markdown(
            f'<div class="agenda-panel">🤖 <b>团队周会全局议程洞察 (AI汇总)</b>\n\n{existing_agenda}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("📭 当周暂无已归档汇报数据，AI 智能总结将在数据沉淀后自动生成。")

    st.markdown("---")

    # ── 分组
    marketing = [r for r in records if "营销" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    rd        = [r for r in records if "研发" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    other     = [r for r in records if r not in marketing and r not in rd]

    tab1, tab2 = st.tabs(["🏪 营销组", "💻 研发组"])

    def render_group_cards(group_records):
        if not group_records:
            st.info("本组暂无汇报记录")
            return

        for rec in group_records:
            f         = rec["fields"]
            rid       = rec["record_id"]
            reporter  = extract_text(f.get(FIELD_REPORTER, "未知"))
            bp_hot    = get_bp_highlights(f)

            with st.container():
                st.markdown(f'<div class="bp-name">👤 {reporter}</div>', unsafe_allow_html=True)

                # 展示个人的 AI 议程
                indiv_agenda = extract_text(f.get(FIELD_AI_AGENDA, "")).strip()
                if indiv_agenda:
                    st.markdown(f'<div style="font-size:0.85rem; color:#64748b; margin-bottom:12px; border-left:3px solid #cbd5e1; padding-left:10px;"><b>✨ 个人工作焦点提炼：</b>{indiv_agenda}</div>', unsafe_allow_html=True)

                # 模块标签行
                tags_html = ""
                for raw_field, sf, cbf, label in modules:
                    content = get_display_content(f, raw_field, sf)
                    if not content:
                        continue  # 无内容 → 不渲染
                    boss_chk = get_boss_checked(f, cbf)
                    bp_hot_flag = is_bp_hot(sf, bp_hot)
                    if boss_chk:
                        tags_html += f'<span class="tag-boss">⭐ {label}</span>'
                    elif bp_hot_flag:
                        tags_html += f'<span class="tag-bp">🔥 {label}</span>'
                    else:
                        tags_html += f'<span class="tag-normal">{label}</span>'
                st.markdown(tags_html, unsafe_allow_html=True)

                # 各模块详情 + 老板额外标记复选框
                for raw_field, sf, cbf, label in modules:
                    content = get_display_content(f, raw_field, sf)
                    if not content:
                        continue  # 空内容 → 不渲染此模块

                    boss_chk    = get_boss_checked(f, cbf)
                    bp_hot_flag = is_bp_hot(sf, bp_hot)

                    src_tags = []
                    div_cls = "module-normal"
                    if boss_chk:
                        src_tags.append("⭐ 负责人标记")
                        div_cls = "module-boss"
                    if bp_hot_flag:
                        src_tags.append("🔥 BP重点聚焦")
                        if not boss_chk:
                            div_cls = "module-hot"
                            
                    flag = " | ".join(src_tags) + " | " if src_tags else ""

                    summary_text = extract_text(f.get(sf, "")).strip()
                    raw_text = extract_text(f.get(raw_field, "")).strip() if raw_field else ""

                    is_ai = bool(summary_text and raw_text and summary_text != raw_text)
                    display_text = summary_text if summary_text else raw_text
                    
                    source_tag = '<span style="font-size:0.75rem;color:#94a3b8;margin-left:8px;">(✨ AI智能总结)</span>' if is_ai else '<span style="font-size:0.75rem;color:#94a3b8;margin-left:8px;">(✍️ HRBP原文)</span>'

                    html_output = f'<b>{label}</b><br>{display_text} {source_tag}'
                    if is_ai:
                        html_output += f'<details style="margin-top:8px;"><summary style="cursor:pointer; color:#64748b; font-size:0.85rem; user-select:none; outline:none;">📝 展开 HRBP 填写原文</summary><div style="margin-top:6px; font-size:0.85rem; color:#475569; white-space:pre-wrap; background:rgba(0,0,0,0.03); padding:10px; border-radius:6px; border-left:2px solid #cbd5e1;">{raw_text}</div></details>'

                    if cbf:
                        col_c, col_cb = st.columns([6, 1])
                    else:
                        col_c = st.container()
                        col_cb = None

                    with col_c:
                        st.markdown(
                            f'<div class="{div_cls}">{flag}{html_output}</div>',
                            unsafe_allow_html=True,
                        )

                    if cbf and col_cb:
                        with col_cb:
                            new_val = st.checkbox(
                                "负责人标记",
                                value=boss_chk,
                                key=f"boss_{rid}_{cbf}",
                                help="⭐ 标记该业务模块为周会重点议题（对BP原决策叠加增强，不发生排斥覆盖）",
                                label_visibility="collapsed",
                            )
                            if new_val != boss_chk:
                                writeback_boss_module(rid, cbf, new_val, reporter, label)
                                st.rerun()

                st.markdown("---")

    with tab1:
        render_group_cards(marketing)
    with tab2:
        render_group_cards(rd)
    if other:
        st.markdown("### 其他")
        render_group_cards(other)


# ═══════════════════════════════════════════════
# VIEW 2: 周会投屏展示
# ═══════════════════════════════════════════════
def render_screen_view(records, modules):
    st.markdown('<div class="view-title">🎯 周会投屏展示</div>',
                unsafe_allow_html=True)

    # ── AI 议程（全局汇报） - 同步投屏展示
    individual_agendas = []
    for r in records:
        f = r["fields"]
        reporter  = extract_text(f.get(FIELD_REPORTER, "未知"))
        agenda = extract_text(f.get(FIELD_AI_AGENDA, "")).strip()
        if agenda:
            individual_agendas.append(f"【{reporter}】\n{agenda}")

    if individual_agendas:
        global_input = "\n\n".join(individual_agendas)
        existing_agenda = get_global_agenda(global_input)
        st.markdown(
            f'<div class="agenda-panel">🤖 <b>团队周会全局议程洞察 (AI汇总)</b>\n\n{existing_agenda}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("📭 当周暂无已归档汇报数据，AI 智能总结将在数据沉淀后自动生成。")

    marketing = [r for r in records if "营销" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    rd        = [r for r in records if "研发" in extract_text(r["fields"].get(FIELD_GROUP, ""))]

    tab1, tab2 = st.tabs(["🏪 营销组", "💻 研发组"])

    def effective_module_recs(group_records, sf, cbf) -> list:
        """
        展示集合 = 修改为：只要有内容就展示出来。
        """
        result = []
        for r in group_records:
            f = r["fields"]
            content = get_display_content(f, None, sf)
            if content:
                result.append(r)
        return result

    def render_module_donuts(group_records, group_name=""):
        if not group_records:
            st.info("本组暂无汇报记录")
            return

        # 汇报顺序（右侧面板）
        ordered = sorted(group_records, key=lambda r: r["fields"].get(FIELD_CREATE_TS, 0) or 0)

        has_any_module = False
        for raw_field, sf, cbf, label in modules:
            if effective_module_recs(group_records, sf, cbf):
                has_any_module = True
                break

        if not has_any_module:
            st.info("本组暂无需重点汇报的模块")
            return

        main_col, order_col = st.columns([5, 1])

        with order_col:
            items_html = ""
            for i, rec in enumerate(ordered, 1):
                reporter = extract_text(rec["fields"].get(FIELD_REPORTER, "未知"))
                ts       = rec["fields"].get(FIELD_CREATE_TS, "")
                ts_str   = ts_to_str(ts) if ts else "—"
                items_html += (
                    f'<div class="order-item">#{i} {reporter}<br>'
                    f'<span style="font-size:0.75rem;color:#6e7681">{ts_str}</span></div>'
                )
            st.markdown(
                f'<div class="order-panel"><b>📋 汇报顺序</b>{items_html}</div>',
                unsafe_allow_html=True,
            )

        with main_col:
            for raw_field, sf, cbf, label in modules:
                priority_recs = effective_module_recs(group_records, sf, cbf)
                if not priority_recs:
                    continue

                st.markdown(f"### {label}")

                bp_names = [extract_text(r["fields"].get(FIELD_REPORTER, "未知"))
                            for r in priority_recs]
                fig = go.Figure(go.Pie(
                    labels=bp_names,
                    values=[1] * len(bp_names),
                    textinfo="label",
                    hovertemplate="<b>%{label}</b><extra></extra>",
                    marker=dict(
                        colors=["#58a6ff", "#79c0ff", "#3d8fd9", "#1f6feb", "#2d8fc9", "#a5d8ff"],
                        line=dict(color="#0d1117", width=2),
                    ),
                ))
                fig.update_layout(
                    showlegend=True,
                    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                    font=dict(color="#334155", family="Inter"),
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=320,
                    legend=dict(bgcolor="#f8f9fa", bordercolor="#e2e8f0",
                                borderwidth=1, font=dict(color="#475569")),
                )
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{label}_{group_name}")

                for rec in priority_recs:
                    reporter = extract_text(rec["fields"].get(FIELD_REPORTER, "未知"))
                    summary_text = extract_text(rec["fields"].get(sf, "")).strip()
                    raw_text = extract_text(rec["fields"].get(raw_field, "")).strip() if raw_field else ""
                    
                    if not summary_text and not raw_text:
                        continue
                        
                    content = summary_text if summary_text else raw_text
                    
                    # 标注来源
                    src_tags = []
                    if get_boss_checked(rec["fields"], cbf):
                        src_tags.append("⭐ 负责人标记")
                    if is_bp_hot(sf, get_bp_highlights(rec["fields"])):
                        src_tags.append("🔥 BP重点聚焦")
                    
                    src = " | ".join(src_tags)
                    src_display = f"  [{src}]" if src else ""

                    is_ai = bool(summary_text and raw_text and summary_text != raw_text)
                    source_tag = '<span style="font-size:0.75rem;color:#94a3b8;margin-left:8px;">(✨ AI智能总结)</span>' if is_ai else '<span style="font-size:0.75rem;color:#94a3b8;margin-left:8px;">(✍️ HRBP原文)</span>'

                    with st.expander(f"👤 {reporter}{src_display}"):
                        st.markdown(f'<div class="ai-box">{content} {source_tag}</div>',
                                    unsafe_allow_html=True)
                        if is_ai:
                            st.markdown(f'<details style="margin-top:8px;"><summary style="cursor:pointer; color:#64748b; font-size:0.85rem; user-select:none; outline:none;">📝 展开 HRBP 填写原文</summary><div style="margin-top:6px; font-size:0.85rem; color:#475569; white-space:pre-wrap; background:#f8f9fa; border:1px solid #e2e8f0; padding:12px; border-radius:6px; border-left:3px solid #cbd5e1;">{raw_text}</div></details>', unsafe_allow_html=True)
                st.markdown("---")

    with tab1:
        render_module_donuts(marketing, "marketing")
    with tab2:
        render_module_donuts(rd, "rd")


# ═══════════════════════════════════════════════
# VIEW 3: 过往数据回溯
# ═══════════════════════════════════════════════
def render_history_view(all_records, modules):
    if not check_boss_password("history"):
        return

    st.markdown('<div class="view-title">📈 过往数据回溯</div>',
                unsafe_allow_html=True)

    week_options = get_week_options(all_records)
    if not week_options:
        st.info("多维表暂无历史记录")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_weeks = st.multiselect(
            "选择月度覆盖周期（目前按周索引模拟）", week_options,
            default=week_options[:2] if len(week_options) >= 2 else week_options,
        )
    with col2:
        group_filter = st.selectbox("组别筛选", ["全部", "营销组", "研发组"])

    tab_a, tab_b = st.tabs(["🤖 AI 智能过往简报", "⏳ 业务模块时光轴"])

    with tab_a:
        st.info("💡 **系统提示**：当前数据累积尚未达到月度标准（暂无全月完整跨度）。\n\n后续完整上线后，大模型将在此处生成强维度的业务提炼摘要。例如：\n- **本月核心业务推进面**\n- **各子模块深度沉淀**\n- **团队人员高光表现**等。")

    with tab_b:
        filtered = [r for r in all_records
                    if extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) in selected_weeks]
        if group_filter != "全部":
            filtered = [r for r in filtered
                        if group_filter[:2] in extract_text(r["fields"].get(FIELD_GROUP, ""))]

        if not filtered:
            st.warning("当前筛选条件下无数据")
            return

        for raw_field, sf, _, label in modules:
            has_data = any(get_display_content(r["fields"], raw_field, sf) for r in filtered)
            if not has_data:
                continue

            with st.expander(f"{label}", expanded=False):
                week_groups = defaultdict(list)
                for r in filtered:
                    week    = extract_text(r["fields"].get(FIELD_WEEK_IDX, "未知周次"))
                    content = get_display_content(r["fields"], raw_field, sf)
                    reporter= extract_text(r["fields"].get(FIELD_REPORTER, ""))
                    if content:
                        week_groups[week].append((reporter, content))

                cols = st.columns(max(min(len(selected_weeks), 3), 1))
                for i, week in enumerate(sorted(week_groups, reverse=True)):
                    with cols[i % len(cols)]:
                        st.markdown(f"**📅 {week}**")
                        for reporter, content in week_groups[week]:
                            st.markdown(
                                f'<div class="module-normal"><b>{reporter}</b><br>'
                                f'<small>{content}</small></div>',
                                unsafe_allow_html=True,
                            )


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════
st.title("📊 HRBP 周会看板")

modules = scan_modules()

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([3, 1, 1, 1])
with ctrl_col1:
    all_records_raw = load_records()
    week_opts = get_week_options(all_records_raw)
    selected_week = st.selectbox(
        "📅 选择当前周次",
        ["全部（含历史）"] + week_opts,
        index=1 if week_opts else 0,
    )
with ctrl_col2:
    if st.button("🔄 同步最新数据"):
        load_records.clear()
        st.rerun()
with ctrl_col3:
    if st.button("🔓 退出管理权限"):
        st.session_state.pop("boss_authed", None)
        st.rerun()
with ctrl_col4:
    st.caption(f"共扫描 {len(all_records_raw)} 条记录")

# 筛选当周，按提交时间升序
if selected_week != "全部（含历史）":
    week_records = [r for r in all_records_raw
                    if extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) == selected_week]
else:
    week_records = all_records_raw

week_records.sort(key=lambda x: x["fields"].get(FIELD_CREATE_TS, 0) or 0)

if not all_records_raw:
    st.info("💡 暂时还没有人填写任何记录，各视图的画板正在等待第一条数据的降临！")

st.divider()

view_tab1, view_tab2, view_tab3 = st.tabs(["📊 负责人审阅", "🎯 周会投屏展示", "📈 过往数据回溯"])

with view_tab1:
    render_review_view(week_records, modules)

with view_tab2:
    render_screen_view(week_records, modules)

with view_tab3:
    render_history_view(all_records_raw, modules)
