import sys
import os
import yaml
import json
from datetime import datetime
from collections import defaultdict

# Project root
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def preview_boss_push():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    board_url = "https://fjd-hrbp-weekly-board.streamlit.app/"
    boss_pwd = "Hannah.Wei@FJD"
    
    bitable = BitableClient()
    
    bp_config_id = ""
    for t in bitable.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            bp_config_id = t["table_id"]
            break
            
    group_map = defaultdict(list)
    EXCLUDE_LIST = ["Hannah.Wei", "Maia", "Shimmer.Liu", "Shimmer"]
    
    bp_records = bitable.list_records(app_token, bp_config_id)
    for r in bp_records:
        f = r.get("fields", {})
        name_raw = f.get("HRBP") or f.get("姓名")
        group_raw = f.get("组别") or "其他"
        status = f.get("在职状态")
        if not name_raw or status in ["离职", "已离职"]: continue
        if isinstance(name_raw, list): name_text = name_raw[0].get("text", "")
        elif isinstance(name_raw, dict): name_text = name_raw.get("text", "")
        else: name_text = str(name_raw)
        if any(ex in name_text for ex in EXCLUDE_LIST): continue
        if isinstance(group_raw, list): g_text = group_raw[0].get("text", group_raw[0].get("name", "其他"))
        elif isinstance(group_raw, dict): g_text = group_raw.get("text", group_raw.get("name", "其他"))
        else: g_text = str(group_raw)
        group_map[g_text].append(name_text)

    dt = datetime.now()
    week_of_month = (dt.day - 1) // 7 + 1
    current_week_idx = f"{str(dt.year)[-2:]}M{dt.month}W{week_of_month}"
    
    report_records = bitable.list_records(app_token, table_id)
    submitted_names = set()
    for r in report_records:
        f = r.get("fields", {})
        if f.get("周索引") == current_week_idx:
            reporter = f.get("汇报人")
            if isinstance(reporter, list): r_name = reporter[0].get("name", "")
            elif isinstance(reporter, dict): r_name = reporter.get("name", "")
            else: r_name = str(reporter)
            submitted_names.add(r_name)

    stats_lines = []
    for group_name in sorted(group_map.keys()):
        members = group_map[group_name]
        done = [m for m in members if m in submitted_names]
        not_done = [m for m in members if m not in submitted_names]
        line = f"• {group_name}: 提交 {len(done)}/{len(members)}"
        if not_done:
            line += f"\n  （未填：{', '.join(not_done)}）"
        stats_lines.append(line)

    stats_content = "\n".join(stats_lines)
    msg = (
        f"👋 位晴您好，系统已为您准备好本周周会的看板数据，请通过指引进行审阅。\n\n"
        f"📊 【本周填报进度统计】\n{stats_content}\n"
        f"（数据统计截止 18:55，由于异步抓取，如有 3-5 分钟延迟属正常情况）\n\n"
        f"🔗 看板链接：{board_url}\n"
        f"🔐 管理员密码：{boss_pwd}\n\n"
        f"💡 【今日重点讨论议题提醒】\n"
        f"1. 上周一例竞业 case，复盘分享，节点意识。\n"
        f"2. Antigravity 跑的招聘——关注几个已达成节点。\n"
        f"3. Agent 提效的资源协同与各组进展。\n\n"
        f"提示：本推送目前为自动触发，暂不支持对话交互功能，期待未来的迭代更新。如有疑问请随时联系 Zinc。\n\n"
        f"祝周会高效！"
    )
    
    print("\n" + "--- 消息预览 (正式外发版) ---" + "\n")
    print(msg)
    print("\n" + "--- 预览结束 ---" + "\n")

if __name__ == "__main__":
    preview_boss_push()
