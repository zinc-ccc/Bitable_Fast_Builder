import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def test_prio_update():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    # 找一条最近的记录
    records = client.list_records(app_token, table_id, page_size=5)
    if not records:
        print("No records found.")
        return
        
    rec = records[0]
    rid = rec["record_id"]
    reporter = rec["fields"].get("汇报人", "Unknown")
    
    # 尝试更新 "需汇报_招聘" (假设这个字段存在且是 type 7)
    field_to_test = "需汇报_招聘"
    current_val = rec["fields"].get(field_to_test, False)
    new_val = not current_val
    
    print(f"Testing update for {reporter} ({rid}): {field_to_test} -> {new_val}")
    res = client.update_record(app_token, table_id, rid, {field_to_test: new_val})
    
    if res.get("code") == 0:
        print("✅ Update Success!")
        # 还原
        client.update_record(app_token, table_id, rid, {field_to_test: current_val})
    else:
        print(f"❌ Update Failed: {res.get('code')} - {res.get('msg')}")
        if "Forbidden" in res.get("msg", ""):
            print("Detected Forbidden error locally.")

if __name__ == "__main__":
    test_prio_update()
