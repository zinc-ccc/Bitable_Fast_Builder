import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def list_fields():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    
    table_id = ""
    for t in client.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            table_id = t["table_id"]
            
    if table_id:
        fields = client.list_fields(app_token, table_id)
        print(f"Fields in BP配置中心:")
        for fd in fields:
            print(f"  - {fd['field_name']} (type: {fd['type']})")

if __name__ == "__main__":
    list_fields()
