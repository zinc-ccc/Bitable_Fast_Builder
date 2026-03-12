import sys
import os
import yaml
sys.path.insert(0, os.getcwd())
from core.bitable import BitableClient

def check_specific_summaries():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = BitableClient()
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    target_names = ["Lexi.Liu", "Zinc.Zheng"]
    records = client.list_records(app_token, table_id)
    
    # We only care about current week: 26M3W1
    current_week = "26M3W1"
    
    print(f"Checking Summaries for {target_names} in week {current_week}:")
    for r in records:
        f = r["fields"]
        reporter = f.get("汇报人")
        if isinstance(reporter, list): name = reporter[0].get("name", "")
        elif isinstance(reporter, dict): name = reporter.get("name", "")
        else: name = str(reporter)
        
        week = f.get("周索引")
        
        if name in target_names and week == current_week:
            print(f"\n[Record: {name}]")
            # List all summary fields
            for k, v in f.items():
                if k.startswith("摘要_"):
                    print(f"  - {k}: {v[:100] if isinstance(v, str) else v}...")
            # Also check raw content to see if there's something to summarize
            print(f"  - Content Fingerprint: {f.get('内容指纹')}")
            # Identify one raw field for debugging
            raw_agent = f.get("Agent实践与进展")
            print(f"  - Agent Raw: {raw_agent[:50] if isinstance(raw_agent, str) else raw_agent}...")

if __name__ == "__main__":
    check_specific_summaries()
