"""rename_t03_title_field.py — 将 T03 首行字段改名为「群聊名称」"""
from core.bitable import BitableClient
import requests

c = BitableClient()
token = c.get_token()
app = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 找 T03
tables = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables", headers=headers).json()
t03_id = next(t["table_id"] for t in tables["data"]["items"] if "T03" in t["name"])

# 获取所有字段，找第一个（primary field）
fields = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables/{t03_id}/fields", headers=headers).json()
first_field = fields["data"]["items"][0]
fid = first_field["field_id"]
print(f"当前首行字段名: {first_field['field_name']} | ID: {fid}")

# 改名
r = requests.put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables/{t03_id}/fields/{fid}",
    headers=headers,
    json={"field_name": "群聊名称", "type": 1}
)
result = r.json()
if result.get("code") == 0:
    print("✅ 成功将首行字段改名为「群聊名称」")
else:
    print(f"❌ 失败: {result.get('code')} - {result.get('msg')}")
