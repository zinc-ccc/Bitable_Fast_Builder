import sys
import os
import yaml
import json
from datetime import datetime
from collections import defaultdict

# Project root
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def send_boss_premeeting_push():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Boss Pre-meeting Push...")
    
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    hannah_uid = "ou_d302eccaa2165cd781a2bac438973166"
    board_url = "https://fjd-hrbp-weekly-board.streamlit.app/"
    boss_pwd = "Hannah.Wei@FJD"
    
    bitable = BitableClient()
    
    # 1. 获取在职 BP 分组信息
    bp_config_id = ""
    for t in bitable.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            bp_config_id = t["table_id"]
            break
            
    group_map = defaultdict(list) # {group_name: [name1, name2, ...]}
    EXCLUDE_LIST = ["Hannah.Wei", "Maia", "Shimmer.Liu", "Shimmer"]
    
    bp_records = bitable.list_records(app_token, bp_config_id)
    for r in bp_records:
        f = r.get("fields", {})
        name_raw = f.get("HRBP") or f.get("姓名")
        group_raw = f.get("所属小组") or "其他"
        status = f.get("在职状态")
        
        if not name_raw or status in ["离职", "已离职"]: continue
        
        # Extract Name
        if isinstance(name_raw, list): name_text = name_raw[0].get("text", "")
        elif isinstance(name_raw, dict): name_text = name_raw.get("text", "")
        else: name_text = str(name_raw)
        
        if any(ex in name_text for ex in EXCLUDE_LIST): continue
        
        # Extract Group
        if isinstance(group_raw, list): g_text = group_raw[0].get("text", group_raw[0].get("name", "其他"))
        elif isinstance(group_raw, dict): g_text = group_raw.get("text", group_raw.get("name", "其他"))
        else: g_text = str(group_raw)
        
        group_map[g_text].append(name_text)

    # 2. 扫描本周已填
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

    # 3. 统计各组情况
    stats_lines = []
    for group_name, members in group_map.items():
        done = [m for m in members if m in submitted_names]
        not_done = [m for m in members if m not in submitted_names]
        line = f"• {group_name}: 提交 {len(done)}/{len(members)}"
        if not_done:
            line += f"（未交：{', '.join(not_done)}）"
        stats_lines.append(line)

    # 4. 组装消息
    stats_content = "\n".join(stats_lines)
    msg = (
        f"👋 Hannah 您好，周会将在 18:55 准时开启前置看板审阅。\n\n"
        f"📊 【本周填报进度统计】\n{stats_content}\n\n"
        f"🔗 看板链接：{board_url}\n"
        f"🔐 管理员密码：{boss_pwd}\n\n"
        f"💡 【今日重点讨论议题提醒】\n"
        f"1. 上周一例竞业 Case，复盘分享，节点意识。\n"
        f"2. Antigravity 跑的招聘进度——关注几例已达成节点。\n"
        f"3. Agent 提效的资源协同与各组进展。\n\n"
        f"请点击链接查看详情，祝周会高效！"
    )
    
    res = bitable.send_message(hannah_uid, "open_id", msg)
    print(f"Boss Push Result: {res}")

if __name__ == "__main__":
    send_boss_premeeting_push()
