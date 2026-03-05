"""list_fields.py — 列出指定表格的所有字段"""
from core.bitable import BitableClient
import requests

c = BitableClient()
token = c.get_token()
app = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
table_id = "tblsq8b5JhivRD1x"
headers = {"Authorization": f"Bearer {token}"}

type_map = {
    1: "多行文本", 2: "数字", 3: "单选", 4: "多选", 5: "日期",
    7: "复选框", 11: "人员", 13: "电话", 15: "超链接",
    17: "查找引用", 18: "公式", 19: "双向关联", 20: "公式",
    21: "单向关联", 22: "双向关联", 1001: "创建时间",
    1002: "最后更新时间", 1003: "创建人", 1004: "修改人"
}

r = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables/{table_id}/fields",
    headers=headers
).json()

items = r.get("data", {}).get("items", [])
print(f"共 {len(items)} 个字段：\n")
for i, f in enumerate(items, 1):
    t = type_map.get(f["type"], f"类型{f['type']}")
    print(f"  {i:02d}. {f['field_name']}  [{t}]")
