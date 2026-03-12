
import sys
import os
import yaml

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def send_group_notification():
    client = BitableClient()
    group_chat_id = "oc_b4cf1529dc88822c9f67002bb72d8f52" # Found in six_pm_push.py
    
    message = (
        "### 📢【HRBP小组】周会同步 & 填报提醒\n\n"
        "<at user_id=\"all\">所有人</at>\n"
        "今晚周会将在 **19:00** 准时开始，请大家在 **18:30** 前完成本周内容同步。\n"
        "*注：以后每周四 19:00 为固定周会时间（如有变动另行通知）。*\n\n"
        "为了方便大家填报，现提供 BP 组与培训组的专属入口：\n\n"
        "**🔹 HRBP 组填报入口**\n"
        "🔗 https://fjdynamics.feishu.cn/share/base/form/shrcnuxUdum6YVhMNLF7dMTdNtb\n\n"
        "**🔸 培训组填报入口**\n"
        "🔗 https://fjdynamics.feishu.cn/share/base/form/shrcnCfalOt2jiTFpVc5mzkPYud\n\n"
        "---\n\n"
        "**🖥️ 周会看板预览（密码：fjd_hrbp_03）**\n"
        "🔗 https://fjd-hrbp-weekly-board.streamlit.app/\n\n"
        "**💡 填报确认：**\n"
        "请务必在表单中勾选 **“本周需重点汇报模块”**，针对勾选为重点填写的模块，内容请尽量充分。\n\n"
        "稍后周会见！🚀"
    )
    
    print(f"🚀 BP小Q 正在向群组 {group_chat_id} 发送通知...")
    res = client.send_message(group_chat_id, "chat_id", message)
    
    if res.get("code") == 0:
        print("✅ 通知发送成功！")
    else:
        print(f"❌ 通知发送失败: {res.get('msg')}")

if __name__ == "__main__":
    send_group_notification()
