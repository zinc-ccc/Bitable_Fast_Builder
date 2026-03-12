
import sys
import os
import yaml

sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def verify_ids():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    app_token = cfg["hrbp_dashboard"]["app_token"]
    client = BitableClient()
    
    tables = client.list_tables(app_token)
    config_id = [t['table_id'] for t in tables if "BP配置" in t.get("name", "")][0]
    records = client.list_records(app_token, config_id)
    
    mapping = {}
    for r in records:
        f = r["fields"]
        name = f.get("HRBP")
        uid = f.get("人员ID")
        mapping[name] = uid
    
    target_names = ["Lexi.Chen", "Patty.Chen", "Daphane.Han", "Reina.Li", "Rita.Li", "Maia.Yuan", "Hannah.Wei"]
    print("--- ID Verification ---")
    for name in target_names:
        print(f"{name}: {mapping.get(name, '❌ NOT FOUND')}")

if __name__ == "__main__":
    verify_ids()
