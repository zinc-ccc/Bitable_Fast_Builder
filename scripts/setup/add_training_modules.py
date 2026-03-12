
import sys
import os
import yaml

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def add_training_fields():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    client = BitableClient()
    
    new_fields = [
        "摘要_学习系统",
        "摘要_培训AI",
        "摘要_培训赋能",
        "摘要_团队其他"
    ]
    
    print(f"🚀 开始为表 {table_id} 新增培训模块字段...")
    
    for field_name in new_fields:
        res = client.create_field(app_token, table_id, field_name, 1) # 1 is Text
        if res:
            print(f"✅ 成功创建字段: {field_name} (ID: {res})")
        else:
            print(f"❌ 字段 {field_name} 创建失败或已存在")

    # 获取“本周需重点汇报模块”字段信息，尝试更新选项
    target_field_name = "本周需重点汇报模块"
    fields = client.list_fields(app_token, table_id)
    target_field = next((f for f in fields if f['field_name'] == target_field_name), None)
    
    if target_field:
        field_id = target_field['field_id']
        current_options = target_field.get('property', {}).get('options', [])
        current_names = [o['name'] for o in current_options]
        
        new_options_names = ["学习系统", "培训AI", "培训赋能", "团队其他"]
        added_any = False
        
        for name in new_options_names:
            if name not in current_names:
                current_options.append({"name": name})
                added_any = True
        
        if added_any:
            import requests
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
            headers = {
                "Authorization": f"Bearer {client.get_token()}",
                "Content-Type": "application/json; charset=utf-8",
            }
            # 更新多选字段选项
            payload = {
                "field_name": target_field_name,
                "type": 4, # Multi-select
                "property": {"options": current_options}
            }
            res = requests.put(url, headers=headers, json=payload).json()
            if res.get("code") == 0:
                print(f"✅ 成功更新“{target_field_name}”的待选模块选项")
            else:
                print(f"❌ 更新“{target_field_name}”选项失败: {res.get('msg')}")
    else:
        print(f"⚠️ 未找到字段 '{target_field_name}'，请手动更新选项")

if __name__ == "__main__":
    add_training_fields()
