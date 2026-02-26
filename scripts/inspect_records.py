"""一次性检查: 拉取HRBP周报表的字段选项 + 完整记录"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json
from core.bitable import BitableClient

APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
TABLE_ID = "tblsq8b5JhivRD1x"

c = BitableClient()
token = c.get_token()
headers = {"Authorization": f"Bearer {token}"}

# 1. 字段详情（含选项）
fields_resp = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields?page_size=100",
    headers=headers
).json()

print("=== 字段选项 ===")
for f in fields_resp.get("data",{}).get("items",[]):
    fname = f.get("field_name","")
    ftype = f.get("type",0)
    # type 3=单选, 4=多选, 19=关联
    if ftype in (3, 4):
        opts = f.get("property",{}).get("options",[])
        print(f"  [{fname}] (type={ftype}) 选项: {[o['name'] for o in opts]}")
    elif ftype == 7:
        print(f"  [{fname}] (checkbox)")

# 2. 完整记录
print("\n=== 完整记录 ===")
recs_resp = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records?page_size=5",
    headers=headers
).json()
for item in recs_resp.get("data",{}).get("items",[]):
    print(f"\nrecord_id={item['record_id']}")
    for k, v in item.get("fields",{}).items():
        print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:80]}")
