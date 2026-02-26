"""精确扫描所有数据表和记录数"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from core.bitable import BitableClient

APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"

c = BitableClient()
token = c.get_token()
headers = {"Authorization": f"Bearer {token}"}

# 1. 列出所有表
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables?page_size=50"
resp = requests.get(url, headers=headers).json()
print(f"API code={resp.get('code')} msg={resp.get('msg','')}")
tables = resp.get("data", {}).get("items", [])
print(f"找到 {len(tables)} 个数据表\n")

for t in tables:
    name = t.get("name", "")
    tid = t.get("table_id", "")
    print(f"📋 表名: [{name}]  table_id: {tid}")

    # 查记录数
    r = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{tid}/records?page_size=10", headers=headers).json()
    total = r.get("data", {}).get("total", "?")
    items = r.get("data", {}).get("items", [])
    print(f"   记录数: {total}")
    for item in items:
        f = item.get("fields", {})
        def tx(v):
            if isinstance(v, list): return "".join(x.get("text",x.get("name",str(x))) if isinstance(x,dict) else str(x) for x in v)
            if isinstance(v, dict): return v.get("text", v.get("name", str(v)))
            return str(v) if v else ""
        print(f"    record_id={item['record_id']}  汇报人={tx(f.get('汇报人',''))}  组别={tx(f.get('所属小组',''))}  周索引={tx(f.get('周索引',''))}")
    print()
