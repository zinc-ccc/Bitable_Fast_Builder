import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def debug():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    
    table_id = ""
    for t in client.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            table_id = t["table_id"]
            
    if table_id:
        records = client.list_records(app_token, table_id)
        for r in records:
            f = r.get("fields", {})
            name = f.get('HRBP') or f.get('姓名')
            uid = f.get('人员ID')
            group = f.get('所属小组')
            print(f"Name: {name} | UID: {uid} | Group: {group}")

if __name__ == "__main__":
    debug()
