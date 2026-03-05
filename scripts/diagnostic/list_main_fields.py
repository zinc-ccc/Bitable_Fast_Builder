import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def list_main_fields():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    fields = client.list_fields(app_token, table_id)
    print(f"Fields in Main Table ({table_id}):")
    for fd in fields:
        if fd['field_name'].startswith("摘要_") or fd['field_name'].startswith("需汇报_"):
            print(f"  - {fd['field_name']} (type: {fd['type']})")

if __name__ == "__main__":
    list_main_fields()
