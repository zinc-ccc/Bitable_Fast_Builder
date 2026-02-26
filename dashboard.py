"""
dashboard.py — HRBP 周会智能看板 (V4.0)
========================================
三视图：老板审阅 | 周会投屏 | 历史数据汇总

新特性：
  - 双模式凭证（Streamlit Secrets / 本地 config.yaml）
  - 老板审阅：按模块勾选，同步多维表 + 飞书私信推送给 BP
  - 周会投屏：优先级判断（老板勾选 > BP勾选），右下角汇报顺序面板
  - 密码保护：老板审阅 & 历史数据需密码，周会投屏公开
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

[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stHeader"] { background: transparent; }

.view-title {
    font-size: 1.5rem; font-weight: 700; color: #e6edf3;
    border-left: 4px solid #58a6ff; padding-left: 12px; margin-bottom: 16px;
}
.bp-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 12px;
}
.bp-name { font-size: 1.05rem; font-weight: 600; color: #e6edf3; margin-bottom: 8px; }
.module-hot {
    background: linear-gradient(90deg, #3d1a1a, #1a1a2e);
    border-left: 3px solid #f85149; padding: 8px 12px;
    border-radius: 0 8px 8px 0; margin: 6px 0; color: #e6edf3;
}
.module-normal {
    background: #21262d; border-left: 3px solid #30363d;
    padding: 8px 12px; border-radius: 0 8px 8px 0; margin: 6px 0; color: #c9d1d9;
}
.ai-box {
    background: linear-gradient(135deg, #0d2137, #0d3740);
    border: 1px solid #1f6feb; border-radius: 10px; padding: 14px; color: #79c0ff;
    margin-top: 8px; font-size: 0.9rem; line-height: 1.6;
}
.agenda-panel {
    background: linear-gradient(135deg, #12121f, #1a1a3a);
    border: 1px solid #3d52a0; border-radius: 14px; padding: 18px;
    color: #a0b4e8; margin-bottom: 20px;
}
.order-panel {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 12px 16px; font-size: 0.85rem; color: #8b949e;
}
.order-item { padding: 4px 0; border-bottom: 1px solid #21262d; color: #c9d1d9; }
.tag-hot { background: #f85149; color: #fff; border-radius: 4px;
           padding: 2px 8px; font-size: 0.78rem; margin-right: 6px; }
.tag-normal { background: #30363d; color: #8b949e; border-radius: 4px;
              padding: 2px 8px; font-size: 0.78rem; margin-right: 6px; }
.group-header {
    font-size: 1.2rem; font-weight: 700; color: #58a6ff;
    border-bottom: 2px solid #21262d; padding-bottom: 8px; margin-bottom: 16px;
}
.pw-box {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 32px; max-width: 400px; margin: 60px auto; text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# 配置读取（双模式）
# ═══════════════════════════════════════════════
def _get_dashboard_config():
    """优先 Streamlit secrets，回退本地 config.yaml。"""
    try:
        if "hrbp_dashboard" in st.secrets:
            return {
                "app_token": st.secrets["hrbp_dashboard"]["app_token"],
                "table_id":  st.secrets["hrbp_dashboard"]["table_id"],
            }
    except Exception:
        pass
    cfg_path = os.path.join(os.path.dirname(__file__), "configs", "config.yaml")
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return cfg["hrbp_dashboard"]


def _get_boss_password():
    try:
        return st.secrets.get("access", {}).get("boss_password", "")
    except Exception:
        return ""


# ── T03 表 ID（动态查找含"T03"的表名）
@st.cache_data(ttl=600)
def get_t03_table_id(app_token):
    tables = bitable.list_tables(app_token)
    for t in tables:
        if "T03" in t.get("name", ""):
            return t["table_id"]
    return ""


# ═══════════════════════════════════════════════
# 初始化客户端
# ═══════════════════════════════════════════════
@st.cache_resource
def get_clients():
    return BitableClient(), AIHelper()


bitable, ai = get_clients()
dash_cfg = _get_dashboard_config()
APP_TOKEN = dash_cfg["app_token"]
TABLE_ID  = dash_cfg["table_id"]


# ═══════════════════════════════════════════════
# 字段常量
# ═══════════════════════════════════════════════
FIELD_REPORTER   = "汇报人"
FIELD_GROUP      = "所属小组"
FIELD_WEEK_IDX   = "周索引"
FIELD_UPDATE_TS  = "最后更新时间"
FIELD_HIGHLIGHTS = "本周需重点汇报模块"
FIELD_AI_AGENDA  = "AI议程建议"
FIELD_ARCHIVE    = "归档标识"

# (AI摘要字段, 老板勾选字段, 显示标签)
MODULES = [
    ("摘要_招聘",  "需汇报_招聘",  "📋 招聘进展"),
    ("摘要_Agent", "需汇报_Agent", "🤖 Agent实践"),
    ("摘要_人员",  "需汇报_人员",  "👥 人员情况"),
    ("摘要_业务",  "需汇报_业务",  "💼 业务情况"),
    ("摘要_专项",  None,           "📌 专项工作"),
    ("摘要_计划",  "需汇报_计划",  "📅 下周计划"),
]


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════
def extract_text(val) -> str:
    if val is None: return ""
    if isinstance(val, bool): return str(val)
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, str): return val
    if isinstance(val, list):
        parts = []
        for v in val:
            if isinstance(v, dict): parts.append(v.get("text", v.get("name", str(v))))
            else: parts.append(str(v))
        return "".join(parts)
    if isinstance(val, dict): return val.get("text", val.get("name", str(val)))
    return str(val)


def get_highlights(fields: dict) -> list:
    raw = fields.get(FIELD_HIGHLIGHTS, [])
    if isinstance(raw, list): return [extract_text(h) for h in raw]
    return [extract_text(raw)] if raw else []


def is_module_hot_by_bp(summary_field: str, highlights: list) -> bool:
    key = summary_field.replace("摘要_", "")
    return any(key in h for h in highlights)


def boss_has_any_selection(fields: dict) -> bool:
    """老板是否对该条记录做过任何模块勾选。"""
    for _, cbf, _ in MODULES:
        if cbf and fields.get(cbf, False):
            return True
    return False


def ts_to_str(ts) -> str:
    """毫秒时间戳 → 可读字符串。"""
    try:
        dt = datetime.fromtimestamp(int(ts) / 1000)
        return dt.strftime("%m/%d %H:%M")
    except Exception:
        return str(ts)


# ═══════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════
@st.cache_data(ttl=60)
def load_records():
    return bitable.list_records(APP_TOKEN, TABLE_ID)


def get_week_options(records):
    weeks = sorted(
        {extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) for r in records
         if r["fields"].get(FIELD_WEEK_IDX)},
        reverse=True,
    )
    return weeks


# ═══════════════════════════════════════════════
# 写回操作
# ═══════════════════════════════════════════════
def writeback_boss_module(record_id: str, cbf: str, new_val: bool,
                          reporter: str, label: str):
    """
    写回单个「需汇报_xxx」字段，并向该 BP 发送飞书私信通知。
    """
    res = bitable.update_record(APP_TOKEN, TABLE_ID, record_id, {cbf: new_val})
    if res.get("code") == 0:
        if new_val:
            # 查询 BP 的 open_id 并发私信
            t03_id = get_t03_table_id(APP_TOKEN)
            if t03_id:
                uid = bitable.get_bp_user_id(APP_TOKEN, t03_id, reporter)
                if uid:
                    msg = (f"📌 你好 {reporter}！负责人已将你的【{label}】模块标记为本周重点汇报，"
                           f"请在周会上重点准备并汇报该部分内容。")
                    push_res = bitable.send_message(uid, "open_id", msg)
                    if push_res.get("code") == 0:
                        st.toast(f"✅ 已通知 {reporter} 准备「{label}」", icon="📬")
                    else:
                        st.warning(f"⚠️ 飞书推送失败（{push_res.get('msg')}），请检查机器人权限")
                else:
                    st.warning(f"⚠️ 未在 T03 找到 {reporter} 的飞书ID，无法推送")
            else:
                st.warning("⚠️ 未找到 T03 配置表，无法推送通知")
        else:
            st.toast(f"↩️ 已取消勾选: {reporter}—{label}", icon="🔄")
    else:
        st.error(f"写回失败: {res.get('msg')}")
    load_records.clear()


def writeback_ai_agenda(record_ids: list, agenda_text: str) -> int:
    ok = 0
    for rid in record_ids:
        res = bitable.update_record(APP_TOKEN, TABLE_ID, rid, {FIELD_AI_AGENDA: agenda_text})
        if res.get("code") == 0:
            ok += 1
    return ok


# ═══════════════════════════════════════════════
# 密码保护装饰器
# ═══════════════════════════════════════════════
def check_boss_password() -> bool:
    """
    返回 True = 已通过验证。
    若未设置密码则直接放行。
    """
    boss_pw = _get_boss_password()
    if not boss_pw:
        return True  # 未配置密码时不拦截

    if st.session_state.get("boss_authed"):
        return True

    st.markdown('<div class="pw-box">', unsafe_allow_html=True)
    st.markdown("🔐 **请输入管理密码**")
    pw_input = st.text_input("密码", type="password", key="pw_input", label_visibility="collapsed")
    if st.button("确认", use_container_width=True):
        if pw_input == boss_pw:
            st.session_state["boss_authed"] = True
            st.rerun()
        else:
            st.error("密码错误")
    st.markdown("</div>", unsafe_allow_html=True)
    return False


# ═══════════════════════════════════════════════
# VIEW 1: 老板审阅
# ═══════════════════════════════════════════════
def render_review_view(records):
    if not check_boss_password():
        return

    st.markdown('<div class="view-title">📋 老板审阅视图 — 本周各 BP 汇报详情</div>',
                unsafe_allow_html=True)

    # ── AI 议程建议区块
    col_a1, col_a2 = st.columns([4, 1])
    with col_a1:
        existing_agenda = extract_text(records[0]["fields"].get(FIELD_AI_AGENDA, "")) if records else ""
        if existing_agenda:
            st.markdown(
                f'<div class="agenda-panel">🤖 <b>本周 AI 汇报议程建议</b><br><br>{existing_agenda}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("📭 本周尚未生成 AI 议程建议，请点击右侧按钮生成。")
    with col_a2:
        if st.button("✨ 生成 AI 议程", use_container_width=True):
            full_text = "\n\n".join([
                f"【{extract_text(r['fields'].get(FIELD_REPORTER, '未知'))}】:\n" +
                "\n".join([f"  {label}: {extract_text(r['fields'].get(sf, ''))}"
                           for sf, _, label in MODULES if r["fields"].get(sf)])
                for r in records
            ])
            with st.spinner("DeepSeek 生成中..."):
                agenda = ai.generate_agenda(full_text)
            count = writeback_ai_agenda([r["record_id"] for r in records], agenda)
            st.success(f"✅ 已同步至多维表 ({count} 条)")
            load_records.clear()
            st.rerun()

    st.markdown("---")

    # ── 分组渲染
    marketing = [r for r in records if "营销" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    rd        = [r for r in records if "研发" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    other     = [r for r in records if r not in marketing and r not in rd]

    tab1, tab2 = st.tabs(["🏪 营销组", "💻 研发组"])

    def render_group_cards(group_records):
        if not group_records:
            st.info("本组暂无汇报记录")
            return
        for rec in group_records:
            f = rec["fields"]
            rid = rec["record_id"]
            reporter = extract_text(f.get(FIELD_REPORTER, "未知"))
            highlights = get_highlights(f)
            boss_has_sel = boss_has_any_selection(f)

            with st.container():
                st.markdown(f'<div class="bp-name">👤 {reporter}</div>', unsafe_allow_html=True)

                # 模块标签（显示哪些有内容）
                tags_html = ""
                for sf, cbf, label in MODULES:
                    content = extract_text(f.get(sf, ""))
                    if not content:
                        continue
                    # 显示：老板已勾选 > BP勾选 > 无标记
                    if cbf and bool(f.get(cbf, False)):
                        cls = "tag-hot"
                    elif not boss_has_sel and is_module_hot_by_bp(sf, highlights):
                        cls = "tag-hot"
                    else:
                        cls = "tag-normal"
                    tags_html += f'<span class="{cls}">{label}</span>'
                st.markdown(tags_html, unsafe_allow_html=True)

                # 各模块内容 + 老板勾选框
                for sf, cbf, label in MODULES:
                    content = extract_text(f.get(sf, ""))
                    if not content:
                        continue

                    # 优先级：老板勾选 > BP勾选
                    if cbf:
                        boss_checked = bool(f.get(cbf, False))
                        col_content, col_cb = st.columns([5, 1])
                    else:
                        boss_checked = False
                        col_content, col_cb = st.columns([6, 0.01])

                    hot = boss_checked or (not boss_has_sel and is_module_hot_by_bp(sf, highlights))
                    div_cls = "module-hot" if hot else "module-normal"
                    flag = "🔥 " if hot else ""

                    with col_content:
                        st.markdown(
                            f'<div class="{div_cls}">{flag}<b>{label}</b><br>{content}</div>',
                            unsafe_allow_html=True,
                        )

                    if cbf:
                        with col_cb:
                            new_val = st.checkbox(
                                "老板标记",
                                value=boss_checked,
                                key=f"boss_{rid}_{cbf}",
                                help="勾选后将同步至多维表并向 BP 发送飞书提醒",
                                label_visibility="collapsed",
                            )
                            if new_val != boss_checked:
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
# VIEW 2: 周会投屏
# ═══════════════════════════════════════════════
def render_screen_view(records):
    st.markdown('<div class="view-title">🖥️ 周会投屏视图 — 按模块汇总</div>',
                unsafe_allow_html=True)

    marketing = [r for r in records if "营销" in extract_text(r["fields"].get(FIELD_GROUP, ""))]
    rd        = [r for r in records if "研发" in extract_text(r["fields"].get(FIELD_GROUP, ""))]

    tab1, tab2 = st.tabs(["🏪 营销组", "💻 研发组"])

    def effective_modules(group_records: list) -> list:
        """
        决定哪些模块在投屏中展示。
        优先级规则：
          - 若任意 BP 记录中老板勾选了某模块 → 该模块展示
          - 若本组所有记录老板均未勾选 → 以 BP 自己勾选的「本周需重点汇报模块」为准
        """
        boss_any = any(boss_has_any_selection(r["fields"]) for r in group_records)
        active_modules = []
        for sf, cbf, label in MODULES:
            if cbf:
                if boss_any:
                    if any(bool(r["fields"].get(cbf, False)) for r in group_records):
                        active_modules.append((sf, cbf, label))
                else:
                    highlights_all = []
                    for r in group_records:
                        highlights_all.extend(get_highlights(r["fields"]))
                    key = sf.replace("摘要_", "")
                    if any(key in h for h in highlights_all):
                        active_modules.append((sf, cbf, label))
            else:
                # 专项：有内容就显示
                if any(extract_text(r["fields"].get(sf, "")) for r in group_records):
                    active_modules.append((sf, cbf, label))
        return active_modules

    def render_module_donuts(group_records: list):
        if not group_records:
            st.info("本组暂无汇报记录")
            return

        active = effective_modules(group_records)
        if not active:
            st.info("本组暂无需重点汇报的模块")
            return

        # 右侧汇报顺序面板
        ordered = sorted(
            group_records,
            key=lambda r: r["fields"].get(FIELD_UPDATE_TS, 0) or 0,
        )

        main_col, order_col = st.columns([5, 1])
        with order_col:
            st.markdown('<div class="order-panel"><b>📋 汇报顺序</b>', unsafe_allow_html=True)
            for i, rec in enumerate(ordered, 1):
                reporter = extract_text(rec["fields"].get(FIELD_REPORTER, "未知"))
                ts = rec["fields"].get(FIELD_UPDATE_TS, "")
                ts_str = ts_to_str(ts) if ts else "—"
                st.markdown(
                    f'<div class="order-item">#{i} {reporter}<br>'
                    f'<span style="font-size:0.75rem;color:#6e7681">{ts_str}</span></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with main_col:
            for sf, cbf, label in active:
                priority_recs = [r for r in group_records
                                 if extract_text(r["fields"].get(sf, ""))]
                if not priority_recs:
                    continue

                st.markdown(f"### {label}")

                bp_names = [extract_text(r["fields"].get(FIELD_REPORTER, "未知")) for r in priority_recs]
                values   = [1] * len(priority_recs)

                fig = go.Figure(go.Pie(
                    labels=bp_names,
                    values=values,
                    hole=0.55,
                    textinfo="label",
                    hovertemplate="<b>%{label}</b><extra></extra>",
                    marker=dict(
                        colors=["#58a6ff", "#79c0ff", "#3d8fd9", "#1f6feb", "#2d8fc9", "#a5d8ff"],
                        line=dict(color="#0d1117", width=2),
                    ),
                ))
                fig.update_layout(
                    showlegend=True,
                    paper_bgcolor="#161b22",
                    plot_bgcolor="#161b22",
                    font=dict(color="#c9d1d9", family="Inter"),
                    annotations=[dict(
                        text=label.split(" ", 1)[-1],
                        x=0.5, y=0.5, font_size=14, showarrow=False, font_color="#e6edf3"
                    )],
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=320,
                    legend=dict(bgcolor="#21262d", bordercolor="#30363d",
                                borderwidth=1, font=dict(color="#c9d1d9")),
                )
                st.plotly_chart(fig, use_container_width=True)

                for rec in priority_recs:
                    reporter = extract_text(rec["fields"].get(FIELD_REPORTER, "未知"))
                    content  = extract_text(rec["fields"].get(sf, ""))
                    with st.expander(f"👤 {reporter} 的 {label}"):
                        st.markdown(f'<div class="ai-box">{content}</div>', unsafe_allow_html=True)

                st.markdown("---")

    with tab1:
        render_module_donuts(marketing)
    with tab2:
        render_module_donuts(rd)


# ═══════════════════════════════════════════════
# VIEW 3: 历史数据汇总
# ═══════════════════════════════════════════════
def render_history_view(all_records):
    if not check_boss_password():
        return

    st.markdown('<div class="view-title">📚 历史数据汇总 — 按周/月回溯</div>',
                unsafe_allow_html=True)

    week_options = get_week_options(all_records)
    if not week_options:
        st.info("多维表暂无填写「周索引」的历史记录")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_weeks = st.multiselect(
            "选择周次（可多选对比）",
            week_options,
            default=week_options[:2] if len(week_options) >= 2 else week_options,
        )
    with col2:
        group_filter = st.selectbox("组别筛选", ["全部", "营销组", "研发组"])

    filtered = [r for r in all_records
                if extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) in selected_weeks]
    if group_filter != "全部":
        filtered = [r for r in filtered
                    if group_filter[:2] in extract_text(r["fields"].get(FIELD_GROUP, ""))]

    if not filtered:
        st.warning("当前筛选条件下无数据")
        return

    for sf, _, label in MODULES:
        has_data = any(extract_text(r["fields"].get(sf, "")) for r in filtered)
        if not has_data:
            continue

        with st.expander(f"{label}", expanded=False):
            week_groups = defaultdict(list)
            for r in filtered:
                week = extract_text(r["fields"].get(FIELD_WEEK_IDX, "未知周次"))
                content  = extract_text(r["fields"].get(sf, ""))
                reporter = extract_text(r["fields"].get(FIELD_REPORTER, ""))
                if content:
                    week_groups[week].append((reporter, content))

            cols = st.columns(min(len(selected_weeks), 3))
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
# 主入口 & 全局控制栏
# ═══════════════════════════════════════════════
st.title("📊 HRBP 周会智能看板")

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([3, 1, 1, 1])
with ctrl_col1:
    all_records_raw = load_records()
    week_opts = get_week_options(all_records_raw)
    selected_week = st.selectbox(
        "📅 当前周次",
        ["全部（含历史）"] + week_opts,
        index=1 if week_opts else 0,
    )
with ctrl_col2:
    if st.button("🔄 刷新数据"):
        load_records.clear()
        st.rerun()
with ctrl_col3:
    if st.button("🔓 退出管理"):
        st.session_state.pop("boss_authed", None)
        st.rerun()
with ctrl_col4:
    st.caption(f"共 {len(all_records_raw)} 条记录")

# 筛选当周记录并按提交时间排序
if selected_week != "全部（含历史）":
    week_records = [
        r for r in all_records_raw
        if extract_text(r["fields"].get(FIELD_WEEK_IDX, "")) == selected_week
    ]
else:
    week_records = all_records_raw

week_records.sort(key=lambda x: x["fields"].get(FIELD_UPDATE_TS, 0) or 0)

st.divider()

# 三视图 Tab
view_tab1, view_tab2, view_tab3 = st.tabs(["📋 老板审阅", "🖥️ 周会投屏", "📚 历史数据"])

with view_tab1:
    render_review_view(week_records)

with view_tab2:
    render_screen_view(week_records)

with view_tab3:
    render_history_view(all_records_raw)
