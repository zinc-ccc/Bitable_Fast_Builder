
import sys
import os
import yaml
import requests

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def final_safe_restore():
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
    
    # 严格按照 BP 原有名称 + 培训组描述 补全
    # 注意：名称必须与底表其他逻辑（如 dashboard 识别）完全一致
    final_names = [
        "招聘进展与HC确认",      # BP
        "Agent实践与进展",        # BP & 培训共用
        "人员情况",               # BP
        "业务部门情况反馈",       # BP
        "其他专项工作",           # BP
        "下周计划与卡点",         # BP & 培训共用
        "学习系统和机制建设",     # 培训特有
        "培训赋能落地",           # 培训特有
        "团队及其他",             # 培训特有
        "暂无"
    ]
    
    # 保持唯一性并转换为选项格式
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
        print("✅ 全量选项列表已彻底同步（BP + 培训）")
        print(f"最终生效选项: {final_names}")
    else:
        print(f"❌ 同步失败: {res.get('msg')}")

if __name__ == "__main__":
    final_safe_restore()
