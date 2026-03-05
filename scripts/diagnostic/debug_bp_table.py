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
            print(f"Found table: {t['name']} ({table_id})")
            
    if table_id:
        records = client.list_records(app_token, table_id)
        for r in records:
            f = r.get("fields", {})
            name = f.get('HRBP') or f.get('姓名')
            status = f.get('在职状态')
            print(f"Name: {name} | Status: {status}")

if __name__ == "__main__":
    debug()
