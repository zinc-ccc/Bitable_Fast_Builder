import sys
import os
import yaml
import json
from datetime import datetime

# Project root
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def send_followup_explanation():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending follow-up explanation to group...")
    
    group_chat_id = "oc_b4cf1529dc88822c9f67002bb72d8f52"
    bitable = BitableClient()
    
    msg = "📢 补充说明：由于看板周报采用智能异步抓取模式，后台数据统计可能存在 3-5 分钟的同步延迟。刚刚已经在系统后台成功提交过内容的 BP 同学可以忽略此提醒，稍后看板会自动刷新更新。祝大家开会愉快！"
    
    res = bitable.send_message(group_chat_id, "chat_id", msg)
    print(f"Explanation Message Result: {res}")

if __name__ == "__main__":
    send_followup_explanation()
