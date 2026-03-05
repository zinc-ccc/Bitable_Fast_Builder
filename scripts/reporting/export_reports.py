import sys
sys.path.append('.')
from core.bitable import BitableClient

client = BitableClient()
HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
WEEKLY_REPORT_TABLE_ID = "tblsq8b5JhivRD1x"

records = client.list_records(HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID)
print(f"Total records: {len(records)}")
if len(records) > 0:
    for rec in records:
        print("========")
        print("Record ID:", rec.get("record_id"))
        fields = rec.get("fields", {})
        print("汇报人:", fields.get("汇报人"))
        print("创建时间:", fields.get("提交时间", fields.get("创建时间")))
        # print part of the contents
        for key, val in fields.items():
            if "内容" in key or "进展" in key or "AI" in key or "情况" in key or "计划" in key:
                print(f"{key}: {str(val)[:100]}...")
