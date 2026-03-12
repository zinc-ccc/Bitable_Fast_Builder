
import sys
import os
import yaml
import json
from datetime import datetime
from collections import defaultdict

# Project root
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def _extract_text(val) -> str:
    """统一提取纯文本"""
    if val is None: return ""
    if isinstance(val, bool): return ""
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, str): return val
    if isinstance(val, list):
        parts = []
        for v in val:
            if isinstance(v, dict):
                parts.append(v.get("text", v.get("name", str(v))))
            else:
                parts.append(str(v))
        return "".join(parts)
    if isinstance(val, dict):
        return val.get("text", val.get("name", str(val)))
    return str(val)

def generate_weekly_auto_pushes():
    """
    根据当前时间戳执行对应的自动化推送逻辑。
    1. 周三 16:00: 开启填报通知 (私信)
    2. 周四 11:30: 群动员通知 (@所有人)
    3. 周四 18:00: 精准催办通知 (群内 @未填)
    4. 周四 18:55: 位晴会前引导 (私信)
    5. 周四 19:00: 组长管理同步 (私信 Lexi/Patty)
    """
    now = datetime.now()
    weekday = now.weekday() # 0: Mon, 2: Wed, 3: Thu
    hour = now.hour
    minute = now.minute

    # 加载配置
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    group_chat_id = "oc_b4cf1529dc88822c9f67002bb72d8f52"
    
    client = BitableClient()

    # 获取本周索引
    week_of_month = (now.day - 1) // 7 + 1
    current_week_idx = f"{str(now.year)[-2:]}M{now.month}W{week_of_month}"

    # 获取 BP 配置数据
    tables = client.list_tables(app_token)
    config_id = [t['table_id'] for t in tables if "BP配置" in t.get("name", "")][0]
    bp_records = client.list_records(app_token, config_id)
    
    all_users = [] # List of {name, open_id, group, role}
    for r in bp_records:
        f = r["fields"]
        name = _extract_text(f.get("HRBP"))
        uid = _extract_text(f.get("人员ID"))
        group = _extract_text(f.get("组别"))
        if name and uid:
            all_users.append({"name": name, "uid": uid, "group": group})

    # 获取本周已填报数据
    report_records = client.list_records(app_token, table_id)
    this_week_reports = {} # {reporter_name: fields}
    for r in report_records:
        f = r["fields"]
        if _extract_text(f.get("周索引")) == current_week_idx:
            reporter = _extract_text(f.get("汇报人"))
            this_week_reports[reporter] = f

    # ═══════════════════════════════════════════════
    # 逻辑 1: 周三 16:00 - 开启填报引导 (私信)
    # ═══════════════════════════════════════════════
    if weekday == 2 and hour == 16 and 0 <= minute < 5:
        print("执行: 周三 16:00 开启填报引导...")
        for user in all_users:
            if user["name"] == "Hannah.Wei": continue
            
            if "培训" in user["group"]:
                form_link = "https://fjdynamics.feishu.cn/share/base/form/shrcnCfalOt2jiTFpVc5mzkPYud"
                msg = (f"👋 Hi {user['name']}，培训组周报填报通道已开启。\n"
                       f"🔗 填报入口：{form_link}\n"
                       f"⏰ 截止时间：本周四 18:30。\n"
                       f"💡 提示：内容将展示在周会看板上，请记得勾选“重点模块”以便会上同步。")
            else:
                form_link = "https://fjdynamics.feishu.cn/share/base/form/shrcnuxUdum6YVhMNLF7dMTdNtb"
                msg = (f"👋 Hi {user['name']}，本周周报填报通道已开启。\n"
                       f"🔗 填报入口：{form_link}\n"
                       f"⏰ 截止时间：本周四 18:30。\n"
                       f"💡 提示：现在即可填报，周四截止前均可修改。系统会自动通过 AI 提炼重点，请务必在表单最后勾选重点模块。")
            
            client.send_message(user["uid"], "open_id", msg)

    # ═══════════════════════════════════════════════
    # 逻辑 2: 周四 11:30 - 会前群动员 (@所有人)
    # ═══════════════════════════════════════════════
    if weekday == 3 and hour == 11 and 30 <= minute < 35:
        print("执行: 周四 11:30 会前群动员...")
        msg = ("📢 **【周会预告 & 填报提醒】**\n\n"
               "<at user_id=\"all\">所有人</at>\n"
               "今晚 19:00 准时召开小组周会。请未完成内容填写的同学，记得在 **18:30** 截止前提交。\n\n"
               "🔹 **BP 组填报入口**：https://fjdynamics.feishu.cn/share/base/form/shrcnuxUdum6YVhMNLF7dMTdNtb\n"
               "🔸 **培训组填报入口**：https://fjdynamics.feishu.cn/share/base/form/shrcnCfalOt2jiTFpVc5mzkPYud\n"
               "🔗 **看板预览**：https://fjd-hrbp-weekly-board.streamlit.app/ (密码：fjd_hrbp_03)")
        client.send_message(group_chat_id, "chat_id", msg)

    # ═══════════════════════════════════════════════
    # 逻辑 3: 周四 18:00 - 会前填报提醒 (群内精准 @未填)
    # ═══════════════════════════════════════════════
    if weekday == 3 and hour == 18 and 0 <= minute < 5:
        print("执行: 周四 18:00 精准催办...")
        missing_users = []
        for user in all_users:
            if user["name"] in ["Hannah.Wei"]: continue
            if user["name"] not in this_week_reports:
                missing_users.append(f"<at user_id=\"{user['uid']}\">{user['name']}</at>")
        
        if missing_users:
            mention_str = " ".join(missing_users)
            msg = (f"⏰ **【开会前填报提醒】**\n\n{mention_str}\n"
                   f"各位还没来得及同步的小伙伴，周会将在七点（19:00）准时开始，请务必在 **18:30** 前完成内容同步。\n\n"
                   f"针对勾选为重点填写的模块，内容请尽量充分，以方便会上进行高效讨论，辛苦啦！")
            client.send_message(group_chat_id, "chat_id", msg)

    # ═══════════════════════════════════════════════
    # 逻辑 4: 周四 18:55 - 位晴会前引导 (私信)
    # ═══════════════════════════════════════════════
    if weekday == 3 and hour == 18 and 55 <= minute < 60:
        print("执行: 周四 18:55 位晴会前引导...")
        hannah = next((u for u in all_users if u["name"] == "Hannah.Wei"), None)
        if hannah:
            msg = ("📊 **【周报看板 · 会前就绪】**\n\n"
                   "**位晴** 你好，本周 HR 工作数据已归档完毕。\n"
                   "🔗 **看板直达**：https://fjd-hrbp-weekly-board.streamlit.app/\n"
                   "🔑 **管理密码**：Hannah.Wei@FJD\n\n"
                   "💡 **操作指南**：\n"
                   "* **会前审阅**：请进入【负责人审阅】视图。支持查看各个 BP 的内容原文，并可通过复选框手动追加讨论重点。\n"
                   "* **会上投屏**：请切换至【周会投屏】视图。看板已按模块（招聘、Agent、培训等）动态展示，点击扇区即可快速切换人选，实现“按模块过人、按重点过事”。\n\n"
                   "祝周会高效讨论！")
            client.send_message(hannah["uid"], "open_id", msg)

    # ═══════════════════════════════════════════════
    # 逻辑 5: 周四 19:00 - 组长管理数据同步 (私信)
    # ═══════════════════════════════════════════════
    if weekday == 3 and hour == 19 and 0 <= minute < 5:
        print("执行: 周四 19:00 组长同步...")
        # 组员关系定义
        teams = {
            "Lexi.Liu": ["Daphne.Han"],
            "Patty.Chen": ["Reina.Zhang", "Rita.Zhou"]
        }
        
        module_fields = ["摘要_招聘", "摘要_Agent", "摘要_人员", "摘要_业务", "摘要_领域", "摘要_专项", "摘要_学习系统", "摘要_培训赋能", "摘要_团队其他", "摘要_卡点计划"]

        for leader_name, members in teams.items():
            leader_user = next((u for u in all_users if u["name"] == leader_name), None)
            if not leader_user: continue
            
            leader_status = "✅ 已完成" if leader_name in this_week_reports else "❌ 待完成"
            lines = [f"📋 **【团队周报 · 完整动态同步】**\n", f"* **你的填写状态**：{leader_status}"]
            
            for m_name in members:
                m_status = "✅ 已完成" if m_name in this_week_reports else "❌ 未完成"
                lines.append(f"\n* **{m_name}**：[{m_status}]")
                
                if m_name in this_week_reports:
                    f = this_week_reports[m_name]
                    content_str = ""
                    # 尝试寻找对应的原始内容或摘要
                    for mf in ["招聘进展与HC确认", "Agent实践与进展", "人员情况", "业务部门情况反馈", "目前卡点与下周计划", "摘要_学习系统", "摘要_培训赋能", "摘要_团队其他"]:
                        text = _extract_text(f.get(mf)).strip()
                        if text and text != "暂无" and text != "无":
                            content_str += f"> **{mf}**：{text}\n"
                    
                    if content_str:
                        lines.append(f"{content_str}")
                else:
                    lines.append("> (提醒：请督促其尽快补录)")
            
            msg = "\n".join(lines)
            client.send_message(leader_user["uid"], "open_id", msg)

if __name__ == "__main__":
    generate_weekly_auto_pushes()
