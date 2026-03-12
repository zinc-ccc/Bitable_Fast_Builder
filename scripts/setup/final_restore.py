
import sys
import os
import yaml
import requests

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def final_restore_options():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    client = BitableClient()
    
    target_field_name = "本周需重点汇报模块"
    fields = client.list_fields(app_token, table_id)
    target_field = next((f for f in fields if f['field_name'] == target_field_name), None)
    
    if not target_field:
        print("❌ 核心字段未找到")
        return

    field_id = target_field['field_id']
    
    # 按照截图和业务逻辑整理的终极列表
    final_names = [
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
    
    new_options = [{"name": name} for name in final_names]
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
    headers = {
        "Authorization": f"Bearer {client.get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "field_name": target_field_name,
        "type": 4, 
        "property": {"options": new_options}
    }
    
    res = requests.put(url, headers=headers, json=payload).json()
    if res.get("code") == 0:
        print("✅ 终极选项列表已强制恢复！")
        print(f"当前选项: {final_names}")
    else:
        print(f"❌ 恢复失败: {res.get('msg')}")

if __name__ == "__main__":
    final_restore_options()
