import sys
import os
import time
import subprocess
from datetime import datetime

def run_scheduler():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI Summarize Scheduler Started.")
    
    while True:
        now = datetime.now()
        weekday = now.weekday() # 0 is Monday, 3 is Thursday
        hour = now.hour
        minute = now.minute
        
        # 1. 执行周期性推送任务 (周三/周四特定时段)
        try:
            subprocess.run([sys.executable, "scripts/automation/weekly_scheduler_task.py"], capture_output=True, text=True)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Task Scheduler Error: {e}")

        # 2. 执行 AI 总结任务
        # Target: Thursday (3), 18:00 - 20:00
        is_thursday_window = (weekday == 3 and 18 <= hour < 20)
        
        if is_thursday_window:
            interval = 60 
            print(f"[{now.strftime('%H:%M:%S')}] High-frequency window (Thursday 18-20). Running AI summarize...")
        else:
            # Normal time: 4 minutes interval to catch notification windows (Wed 16:00, etc.)
            interval = 240
            print(f"[{now.strftime('%H:%M:%S')}] Idle window. Next check in 4 mins.")

        try:
            result = subprocess.run([sys.executable, "scripts/automation/run_ai_summarize.py"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] AI Summarize Success.")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] AI Summarize Failed Error: {result.stderr}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduler Error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    run_scheduler()
