import sys
import json
sys.path.append('.')
from core.bitable import BitableClient

def main():
    client = BitableClient()
    HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
    WEEKLY_REPORT_TABLE_ID = "tblsq8b5JhivRD1x"
    BP_CONFIG_TABLE_ID = "tblAfXJhqBC46rYN"

    # Hardcoded IDs based on your instructions
    ADMIN_ID = "ou_2874d7ea6adbab84fa94a8f9c109df84" # Zinc.Zheng
    HANNAH_ID = "ou_d302eccaa2165cd781a2bac438973166" # Hannah.Wei (位晴)

    # Step 1: Read config info to map BPs to their groups
    config_records = client.list_records(HECS_APP_TOKEN, BP_CONFIG_TABLE_ID)
    
    bp_dict = {}
    for rec in config_records:
        fields = rec.get("fields", {})
        open_id = fields.get("人员ID")
        if isinstance(open_id, list): 
             if open_id and isinstance(open_id[0], dict):
                 open_id = open_id[0].get("id", open_id[0].get("text"))
             elif open_id and isinstance(open_id[0], str):
                 open_id = open_id[0]
        elif isinstance(open_id, dict):
            open_id = open_id.get("id", open_id.get("text"))
        else:
            open_id = str(open_id) if open_id else None

        name_val = fields.get("HRBP")
        name = ""
        if isinstance(name_val, list):
             if name_val and isinstance(name_val[0], dict):
                 name = name_val[0].get("name", name_val[0].get("text", ""))
             elif name_val and isinstance(name_val[0], str):
                 name = "".join(name_val)
        else:
            name = str(name_val)
            
        group_val = fields.get("组别", "")
        group = group_val[0].get("text", "") if isinstance(group_val, list) and isinstance(group_val[0], dict) else str(group_val)

        if name and open_id:
             bp_dict[open_id] = {
                 "name": name,
                 "group": group
             }

    # Step 2: Load reports
    records = client.list_records(HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID)
    
    bp_latest_record = {}

    for rec in records:
        fields = rec.get("fields", {})
        reporter_list = fields.get("汇报人", [])
        if not reporter_list: continue
        reporter = reporter_list[0] if isinstance(reporter_list, list) else reporter_list
        open_id = reporter.get("id")
        name = reporter.get("name", "BP")
        
        if not open_id: continue
        created_time = fields.get("提交时间", 0) 
        if not bp_latest_record.get(open_id) or bp_latest_record[open_id]["time"] < created_time:
            bp_latest_record[open_id] = {
                "time": created_time,
                "fields": fields,
                "name": name,
                "open_id": open_id,
            }

    success_bps = []
    failed_bps = []
    skipped_bps = []
    
    group_stats = {"研发组BP": 0, "营销组 BP": 0, "培训组": 0, "其他": 0}

    # Step 3: Loop and send
    for open_id, data in bp_latest_record.items():
        fields = data["fields"]
        name = data["name"]
        
        # 1. Update group stats BEFORE potentially skipping anyone
        group = bp_dict.get(open_id, {}).get("group", "")
        if "研发" in group: group_stats["研发组BP"] += 1
        elif "营销" in group: group_stats["营销组 BP"] += 1
        elif "培训" in group: group_stats["培训组"] += 1
        else: group_stats["其他"] += 1

        # 2. Skip admin from receiving their own report copy via this blast
        if open_id == ADMIN_ID:
            skipped_bps.append(name)
            continue
        
        # 3. Assemble message
        blocks = [f"{name}，你好！这是你2/26提交的周报，可以作为填写本月月报参考。\n"]
        module_fields = ["招聘进展与HC确认", "Agent实践与进展", "人员情况", "业务部门情况反馈", "其他专项工作", "目前卡点与下周计划"]
        has_content = False
        for mf in module_fields:
            if mf in fields and fields[mf]:
                val = fields[mf]
                val_str = ""
                if isinstance(val, list):
                    val_str = "".join([i.get("text", "") if isinstance(i, dict) else str(i) for i in val]).strip()
                else:
                    val_str = str(val).strip()
                if val_str and val_str.lower() != "none" and val_str not in ["无", "暂无", "无。"]:
                    blocks.append(f"【{mf}】\n{val_str}\n")
                    has_content = True
                    
        # 4. Send the message
        if has_content:
            msg_text = "\n".join(blocks).strip()
            # UNCOMMENT IN PRODUCTION TO SEND:
            # res = client.send_message(open_id, "open_id", msg_text)
            # if res.get("code") == 0:
            #     print(f"✅ Success: {name}")
            #     success_bps.append(name)
            # else:
            #     print(f"❌ Failed (Error {res.get('code')}): {name}")
            #     failed_bps.append(name)
            pass

    # Step 4: Notify admin
    # UNCOMMENT IN PRODUCTION TO SEND:
    # admin_msg = f"🔔 【自动化广播回执】管理员好，自动推送操作执行完毕。\n\n"
    # admin_msg += f"✅ 推送成功的人员 ({len(success_bps)}人):\n" + "、".join(success_bps) + "\n\n"
    # admin_msg += f"❌ 推送失败的人员 ({len(failed_bps)}人):\n" + "、".join(failed_bps) + "\n\n"
    # admin_msg += f"⏭️ 已跳过已成功的你本人 ({len(skipped_bps)}人)"
    # client.send_message(ADMIN_ID, "open_id", admin_msg)

    # Step 5: Notify Hannah.Wei
    hannah_msg = f"位晴 你好！2/26 周会一共有 {len(bp_latest_record)} 位 同事填写周报，"
    hannah_msg += f"其中研发组 {group_stats['研发组BP']} 位，营销组 {group_stats['营销组 BP']} 位"
    if group_stats['培训组'] > 0 or group_stats['其他'] > 0:
        hannah_msg += f"（此外还有培训/其他 {group_stats['培训组'] + group_stats['其他']} 位）。\n"
    else:
        hannah_msg += "。\n"
    hannah_msg += f"\n👉 请点击这里查看详细的周会看板: https://fjd-hrbp-weekly-board.streamlit.app/"
    
    # UNCOMMENT IN PRODUCTION TO SEND:
    # client.send_message(HANNAH_ID, "open_id", hannah_msg)
    print(f"[DRY RUN] Would send to Hannah ({HANNAH_ID}):\n{hannah_msg}")

if __name__ == "__main__":
    main()
