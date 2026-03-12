
import sys
import os
import yaml
import requests

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def cleanup_training_fields():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    client = BitableClient()
    
    # 1. 删除冗余字段 "摘要_培训AI"
    fields = client.list_fields(app_token, table_id)
    target_f = next((f for f in fields if f['field_name'] == "摘要_培训AI"), None)
    
    if target_f:
        field_id = target_f['field_id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
        headers = {"Authorization": f"Bearer {client.get_token()}"}
        res = requests.delete(url, headers=headers).json()
        if res.get("code") == 0:
            print(f"✅ 成功删除冗余字段: 摘要_培训AI")
        else:
            print(f"❌ 删除字段失败: {res.get('msg')}")
    
    # 2. 从“本周需重点汇报模块”中移除“培训AI”选项
    target_field_name = "本周需重点汇报模块"
    target_field = next((f for f in fields if f['field_name'] == target_field_name), None)
    
    if target_field:
        field_id = target_field['field_id']
        current_options = target_field.get('property', {}).get('options', [])
        
        # 过滤掉名为 "培训AI" 的选项
        filtered_options = [o for o in current_options if o['name'] != "培训AI"]
        
        if len(filtered_options) < len(current_options):
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
            headers = {
                "Authorization": f"Bearer {client.get_token()}",
                "Content-Type": "application/json; charset=utf-8",
            }
            payload = {
                "field_name": target_field_name,
                "type": 4, 
                "property": {"options": filtered_options}
            }
            res = requests.put(url, headers=headers, json=payload).json()
            if res.get("code") == 0:
                print(f"✅ 成功从“{target_field_name}”中移除“培训AI”选项")
            else:
                print(f"❌ 移除选项失败: {res.get('msg')}")

if __name__ == "__main__":
    cleanup_training_fields()
