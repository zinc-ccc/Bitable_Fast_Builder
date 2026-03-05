import requests
import json
import yaml
from core.bitable import BitableClient

def setup_t3():
    print("🛠️ 开始在新应用中创建 T03 配置表...")
    client = BitableClient()
    app_token = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
    table_name = "T03-BP配置中心"
    
    # 1. 创建表格
    table_id = client.create_table(app_token, table_name)
    if not table_id:
        print("❌ 创建表格失败")
        return
    print(f"✅ 表格 '{table_name}' 创建成功，ID: {table_id}")

    # 2. 创建字段 (飞书多维表 API 的字段类型: 1-文本, 3-单选)
    fields = [
        {"name": "HRBP", "type": 1},
        {"name": "人员ID", "type": 1},
        {"name": "群聊ID", "type": 1},
        {"name": "组别", "type": 3, "property": {
            "options": [
                {"name": "研发组BP"},
                {"name": "营销组 BP"},
                {"name": "培训组"},
                {"name": "负责人"},
                {"name": "HRBP-待确认"}
            ]
        }}
    ]

    for f in fields:
        res = client.create_field(app_token, table_id, f["name"], f["type"], property_obj=f.get("property"))
        if res:
            print(f"  - 字段 '{f['name']}' 创建成功")
        else:
            print(f"  - 字段 '{f['name']}' 可能已存在或创建失败")

    print("\n🚀 T03 配置表搭建完成！")
    print(f"链接: https://fjdynamics.feishu.cn/base/{app_token}?table={table_id}")

if __name__ == "__main__":
    setup_t3()
