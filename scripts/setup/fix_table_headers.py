"""
fix_table_headers.py
====================
修复两个表格的问题：
1. 将 T03-BP配置中心 重命名为 T03-BP底表
2. 将 HRBP业务周报 首行字段「多行文本」重命名为「汇报标题」

运行方式：python -m scripts.fix_table_headers
"""
import requests
from core.bitable import BitableClient

HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"

def fix():
    client = BitableClient()
    token = client.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 获取所有表格
    tables_res = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables",
        headers=headers
    ).json()
    tables = tables_res.get("data", {}).get("items", [])
    print("当前所有表格：")
    for t in tables:
        print(f"  {t['name']} -> {t['table_id']}")

    t03 = next((t for t in tables if "T03" in t["name"]), None)
    weekly = next((t for t in tables if t["name"] == "HRBP业务周报"), None)

    # ── 1. 重命名 T03-BP配置中心 → T03-BP底表 ──
    if t03:
        r = requests.patch(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{t03['table_id']}",
            headers=headers,
            json={"name": "T03-BP底表"}
        ).json()
        if r.get("code") == 0:
            print(f"\n✅ T03 表重命名成功: {t03['name']} → T03-BP底表")
        else:
            print(f"\n❌ T03 重命名失败: code={r.get('code')} msg={r.get('msg')}")
    else:
        print("\n⚠️  未找到 T03 表")

    # ── 2. 重命名 HRBP业务周报 首行字段 ──
    if weekly:
        tid = weekly["table_id"]
        fields_res = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{tid}/fields",
            headers=headers
        ).json()
        first = fields_res.get("data", {}).get("items", [])[0]
        print(f"\n周报表首行字段：「{first['field_name']}」 ID: {first['field_id']}")

        r2 = requests.put(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{tid}/fields/{first['field_id']}",
            headers=headers,
            json={"field_name": "汇报标题", "type": 1}
        ).json()
        if r2.get("code") == 0:
            print(f"✅ 首行字段重命名成功: 「{first['field_name']}」→「汇报标题」")
        else:
            print(f"❌ 首行字段重命名失败: code={r2.get('code')} msg={r2.get('msg')}")
    else:
        print("\n⚠️  未找到 HRBP业务周报 表")

if __name__ == "__main__":
    fix()
