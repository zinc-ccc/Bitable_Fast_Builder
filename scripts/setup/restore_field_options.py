
import sys
import os
import yaml
import requests

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def restore_options():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    client = BitableClient()
    
    target_field_name = "本周需重点汇报模块"
    fields = client.list_fields(app_token, table_id)
    target_field = next((f for f in fields if f['field_name'] == target_field_name), None)
    
    if not target_field:
        print("❌ Error: Field not found")
        return

    field_id = target_field['field_id']
    
    # 完整的选项列表（合并 BP 和 培训组）
    required_options = [
        "招聘进展与HC确认",
        "Agent实践与进展",
        "人员情况",
        "业务部门情况反馈",
        "其他专项工作",
        "下周计划与卡点",
        "暂无",
        "学习系统",
        "培训赋能",
        "团队其他"
    ]
    
    # 构建新的选项列表，保留已有的（如果存在），缺失的补全
    current_options = target_field.get('property', {}).get('options', [])
    current_names = {o['name']: o for o in current_options}
    
    final_options = []
    for name in required_options:
        if name in current_names:
            final_options.append(current_names[name])
        else:
            final_options.append({"name": name})
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
    headers = {
        "Authorization": f"Bearer {client.get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "field_name": target_field_name,
        "type": 4, # Multi-select
        "property": {"options": final_options}
    }
    
    res = requests.put(url, headers=headers, json=payload).json()
    if res.get("code") == 0:
        print(f"✅ 成功恢复并补全“{target_field_name}”的所有选项")
        print(f"当前选项列表: {[o['name'] for o in final_options]}")
    else:
        print(f"❌ 恢复失败: {res.get('msg')}")

if __name__ == "__main__":
    restore_options()
