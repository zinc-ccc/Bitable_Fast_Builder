import sys
import os
import yaml
import json
from datetime import datetime

# Project root
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def send_six_pm_notifications():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting 6 PM Push...")
    
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    group_chat_id = "oc_b4cf1529dc88822c9f67002bb72d8f52"
    screen_pwd = "fjd_hrbp_2026"
    board_url = "https://fjd-hrbp-weekly-board.streamlit.app/"
    
    bitable = BitableClient()
    
    # 1. 第一条消息：看板介绍 + @所有人
    # 飞书 @all 语法: <at user_id="all">所有人</at>
    msg1 = f"<at user_id=\"all\">所有人</at>\n这是我们的周报协同看板：{board_url} \n输入投屏密码 【{screen_pwd}】 即可在会议室查看周会投屏视图。请开启今天的同步模式吧！"
    
    res1 = bitable.send_message(group_chat_id, "chat_id", msg1)
    print(f"Message 1 Result: {res1}")
    
    # 2. 第二条消息：催办未填人员 (带 @)
    # 获取 BP 配置表映射
    bp_config_id = ""
    for t in bitable.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            bp_config_id = t["table_id"]
            break
            
    if not bp_config_id:
        print("Error: BP Config table not found")
        return

    # 获取在职人员 ID 映射
    bp_records = bitable.list_records(app_token, bp_config_id)
    all_bps_map = {} # {name: open_id}
    EXCLUDE_LIST = ["Hannah.Wei", "Maia", "Shimmer.Liu", "Shimmer"]
    
    for r in bp_records:
        f = r.get("fields", {})
        name_raw = f.get("HRBP") or f.get("姓名")
        status = f.get("在职状态")
        uid = f.get("人员ID")
        
        if not name_raw or status in ["离职", "已离职"]: continue
        
        # Extract Name
        if isinstance(name_raw, list): name_text = name_raw[0].get("text", "")
        elif isinstance(name_raw, dict): name_text = name_raw.get("text", "")
        else: name_text = str(name_raw)
        
        if any(ex in name_text for ex in EXCLUDE_LIST): continue
        
        # Extract UID
        if isinstance(uid, list): uid_text = uid[0] if uid else ""
        else: uid_text = str(uid)
        
        if uid_text:
            all_bps_map[name_text] = uid_text

    # 扫描本周已填
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

    missing_mentions = []
    for name, uid in all_bps_map.items():
        if name not in submitted_names:
            # 飞书 @ 语法: <at user_id="ou_xxx">Name</at>
            missing_mentions.append(f"<at user_id=\"{uid}\">{name}</at>")

    if missing_mentions:
        mention_str = " ".join(missing_mentions)
        msg2 = f"{mention_str} \n各位小伙伴，周会将在七点（19:00）开始，还没来得及同步本周周报内容的同学记得在会前填写一下哦，辛苦啦！"
        res2 = bitable.send_message(group_chat_id, "chat_id", msg2)
        print(f"Message 2 Result: {res2}")
    else:
        print("All BPs have submitted. Sending praise instead.")
        msg2 = "本周周报全员已交齐，大家太棒啦！👏 稍后周会见。"
        bitable.send_message(group_chat_id, "chat_id", msg2)

if __name__ == "__main__":
    send_six_pm_notifications()
