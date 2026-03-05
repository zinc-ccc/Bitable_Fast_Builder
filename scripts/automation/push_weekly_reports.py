import sys
import json
sys.path.append('.')
from core.bitable import BitableClient

def main():
    client = BitableClient()
    HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
    WEEKLY_REPORT_TABLE_ID = "tblsq8b5JhivRD1x"

    records = client.list_records(HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID)
    print(f"Total reports found: {len(records)}")
    
    # Track the latest record per BP
    bp_latest_record = {}

    for rec in records:
        fields = rec.get("fields", {})
        
        # Parse repoter details
        reporter_list = fields.get("汇报人", [])
        if not reporter_list:
            continue
            
        reporter = reporter_list[0] if isinstance(reporter_list, list) else reporter_list
        open_id = reporter.get("id")
        name = reporter.get("name", "BP")
        
        if not open_id:
            continue
            
        # Optional: check submission date if needed, or assume order/latest wins.
        # list_records returns in some order (usually created descending or according to view).
        # We can just check the created_time or assume the last one processed or first one processed is latest.
        # Bitable API usually returns in the order of the default view or created time. 
        # Using the creation timestamp if available, otherwise just use the last one encountered (or first).
        created_time = fields.get("提交时间", 0) 
        if not bp_latest_record.get(open_id) or bp_latest_record[open_id]["time"] < created_time:
            bp_latest_record[open_id] = {
                "time": created_time,
                "fields": fields,
                "name": name,
                "open_id": open_id
            }

    print(f"Unique BPs found: {len(bp_latest_record)}")
    
    for open_id, data in bp_latest_record.items():
        fields = data["fields"]
        name = data["name"]
        
        # Assemble the message
        blocks = []
        blocks.append(f"{name}，你好！这是你2/26提交的周报，可以作为填写本月月报参考。\n")
        
        module_fields = [
            "招聘进展与HC确认", 
            "Agent实践与进展", 
            "人员情况", 
            "业务部门情况反馈", 
            "其他专项工作", 
            "目前卡点与下周计划"
        ]
        
        has_content = False
        for mf in module_fields:
            if mf in fields and fields[mf]:
                val = fields[mf]
                if isinstance(val, list):
                    text_parts = []
                    for item in val:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    val_str = "".join(text_parts).strip()
                else:
                    val_str = str(val).strip()
                    
                if val_str and val_str.lower() != "none" and val_str != "无" and val_str != "暂无" and val_str != "无。":
                    # add padding and structure for readability
                    blocks.append(f"【{mf}】\n{val_str}\n")
                    has_content = True
                    
        if has_content:
            msg_text = "\n".join(blocks).strip()
            print("====================================")
            print(f"Pushing to {name} ({open_id}):")
            print(msg_text[:200] + "...\n")
            
            # Send message via Feishu private message
            res = client.send_message(open_id, "open_id", msg_text)
            if res.get("code") == 0:
                print(f"✅ Message sent to {name}")
            else:
                print(f"❌ Failed to send to {name}: {res}")

if __name__ == "__main__":
    main()
