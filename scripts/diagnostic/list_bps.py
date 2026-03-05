import sys
import json
sys.path.append('.')
from core.bitable import BitableClient

def main():
    client = BitableClient()
    HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
    WEEKLY_REPORT_TABLE_ID = "tblsq8b5JhivRD1x"

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
            bp_latest_record[open_id] = name

    print(f"Total Unique BPs: {len(bp_latest_record)}")
    for oid, name in bp_latest_record.items():
        print(f"  - {name} ({oid})")

if __name__ == "__main__":
    main()
