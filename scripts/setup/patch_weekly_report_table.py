"""
patch_weekly_report_table.py
============================
补丁脚本：在已存在的「HRBP业务周报」表中，
补全缺失的字段（📌 C3、📌 C5、AI核心要点）。

运行方式：python -m scripts.patch_weekly_report_table
"""

from core.bitable import BitableClient

HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
WEEKLY_REPORT_TABLE_ID = "tblffLH43wWopBUC"  # HRBP业务周报表

def patch():
    print("🔧 开始补全「HRBP业务周报」缺失字段...")
    client = BitableClient()

    missing_fields = [
        # M3 后面补一个 Case 复选框
        {
            "name": "📌 人员关键Case",
            "type": 7,   # 复选框
            "note": "M3 人员情况跟进的 Case 标注"
        },
        # M5 后面补一个 Case 复选框
        {
            "name": "📌 计划关键Case",
            "type": 7,
            "note": "M5 卡点与下周计划的 Case 标注"
        },
        # AI 核心要点（普通文本字段，由 bot 回写）
        {
            "name": "AI核心要点",
            "type": 1,   # 多行文本
            "note": "由机器人调用 LLM 后自动填充，15-20字总结"
        },
    ]

    for f in missing_fields:
        fid = client.create_field(
            HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID,
            f["name"], f["type"]
        )
        if fid:
            print(f"  ✅ 已添加：{f['name']}（{f['note']}）")
        else:
            print(f"  ⚠️  {f['name']} 可能已存在或创建失败")

    print("""
✨ 字段补全完成！

⚠️  以下字段无法通过 API 创建，需在飞书界面手动处理：
  1. 「汇报周次」→ 公式字段（如尚未创建）
     公式：YEAR(CREATED_TIME()) & "-W" & WEEKNUM(CREATED_TIME())

  2. 表单里，请手动调整字段顺序，确保 📌 Case 复选框紧贴在对应模块下方
     建议顺序：M1 → 📌招聘Case → M2 → 📌AgentCase → M3 → 📌人员Case
               → M4 → 📌业务Case → M5 → 📌计划Case

  3. 表单内为每个 📌 复选框加说明文字：
     "如本模块有典型案例可供分享，请勾选此项"

  4. 目视整理 5 个看板视图（API 暂不支持）
""")
    print(f"📊 表格链接: https://fjdynamics.feishu.cn/base/{HECS_APP_TOKEN}?table={WEEKLY_REPORT_TABLE_ID}")

if __name__ == "__main__":
    patch()
