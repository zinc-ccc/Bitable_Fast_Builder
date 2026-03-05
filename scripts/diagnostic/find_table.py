import sys
sys.path.append('.')
from core.bitable import BitableClient

client = BitableClient()
HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
tables = client.list_tables(HECS_APP_TOKEN)
for t in tables:
    if "BP配置中心" in t['name']:
        print("BP_CONFIG_TABLE_ID =", t['table_id'])
