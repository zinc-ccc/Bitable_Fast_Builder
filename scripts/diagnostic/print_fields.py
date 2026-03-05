import sys
import json
sys.path.append('.')
from core.bitable import BitableClient

client = BitableClient()
HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
WEEKLY_REPORT_TABLE_ID = "tblsq8b5JhivRD1x"

records = client.list_records(HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID)
print(list(records[0]['fields'].keys()))
