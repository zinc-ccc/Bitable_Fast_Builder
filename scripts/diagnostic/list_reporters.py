import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def list_recent_reporters():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    records = client.list_records(app_token, table_id, page_size=100)
    print("Found Reporters in Main Table:")
    for r in records:
        f = r["fields"]
        reporter = f.get("汇报人")
        if isinstance(reporter, list): name = reporter[0].get("name", "")
        elif isinstance(reporter, dict): name = reporter.get("name", "")
        else: name = str(reporter)
        
        week = f.get("周索引")
        print(f" - {name} (Week: {week})")

if __name__ == "__main__":
    list_recent_reporters()
