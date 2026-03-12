"""
诊断脚本：扫描多维表结构
- 列出所有数据表 (tables)
- 对每个表列出所有字段 (fields)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import requests
import yaml
from core.bitable import BitableClient

def list_tables(client, app_token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
    headers = {"Authorization": f"Bearer {client.get_token()}"}
    res = requests.get(url, headers=headers)
    data = res.json()
    if data.get("code") != 0:
        print(f"❌ 获取表列表失败: code={data.get('code')}, msg={data.get('msg')}")
        return []
    return data.get("data", {}).get("items", [])

def main():
    client = BitableClient()
    with open("configs/config.yaml", 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    app_token = cfg['hrbp_dashboard']['app_token']
    print(f"\n🔍 扫描多维表: {app_token}\n{'='*60}")

    tables = list_tables(client, app_token)
    if not tables:
        print("未找到任何数据表，请检查 app_token 是否正确，以及机器人是否有权限。")
        return

    print(f"📋 共找到 {len(tables)} 个数据表:\n")
    for t in tables:
        tname = t.get('name', '')
        tid = t.get('table_id', '')
        print(f"  表名: 【{tname}】  Table ID: {tid}")

        fields = client.list_fields(app_token, tid)
        print(f"  字段数量: {len(fields)}")
        
        summary_fields = [f['field_name'] for f in fields if f['field_name'].startswith('摘要_')]
        ref_fields = [f['field_name'] for f in fields if f['field_name'].startswith('引_')]
        checkbox_fields = [f for f in fields if f.get('type') == 7]  # type 7 = Checkbox in Feishu
        
        if summary_fields:
            print(f"  ✅ 摘要字段 ({len(summary_fields)}): {', '.join(summary_fields)}")
        if ref_fields:
            print(f"  ✅ 引用字段 ({len(ref_fields)}): {', '.join(ref_fields)}")
        if checkbox_fields:
            print(f"  ☑️  复选框字段: {', '.join([f['field_name'] for f in checkbox_fields])}")
            
        print(f"\n  完整字段列表:")
        for f in fields:
            print(f"    - [{f.get('type')}] {f['field_name']}  (ID: {f['field_id']})")
        print()

if __name__ == "__main__":
    main()
