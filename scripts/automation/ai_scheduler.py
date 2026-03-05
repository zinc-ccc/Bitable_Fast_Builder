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
        
        # Target: Thursday (3), 18:00 - 20:00
        is_thursday_window = (weekday == 3 and 18 <= hour < 20)
        
        if is_thursday_window:
            # 18:00 - 19:30: 1 minute interval
            # 19:30 - 20:00: maybe 5 minutes is enough, but user said 6-8 total, especially 6-7:30
            # Let's do 1 min for the whole 6-8 window to be safe and responsive
            interval = 60 
            print(f"[{now.strftime('%H:%M:%S')}] High-frequency window (Thursday 18-20). Running AI summarize...")
        else:
            # Normal time: 30 minutes interval
            interval = 1800
            print(f"[{now.strftime('%H:%M:%S')}] Idle window. Next check in 30 mins.")

        try:
            # Run the summarization script
            # We use subprocess to run it as a separate process to avoid import complexity
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
