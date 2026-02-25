"""check_tables.py — 列出当前 app 下所有表格 ID"""
from core.bitable import BitableClient
import requests

c = BitableClient()
token = c.get_token()
app = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
headers = {"Authorization": f"Bearer {token}"}
r = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables", headers=headers).json()
for t in r.get("data", {}).get("items", []):
    print(f"{t['name']} -> {t['table_id']}")
