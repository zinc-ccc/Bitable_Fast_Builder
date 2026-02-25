"""
setup_weekly_report_table.py
============================
自动在飞书多维表中创建「HRBP 业务周报」主表并初始化所有字段。
运行方式：python -m scripts.setup_weekly_report_table

飞书多维表字段类型对照 (type值):
  1  = 多行文本 (Text)
  2  = 数字 (Number)
  3  = 单选 (SingleSelect)
  4  = 多选 (MultiSelect)
  5  = 日期 (DateTime)
  7  = 复选框 (Checkbox)
  11 = 人员 (User)
  1001 = 创建时间 (CreatedTime) — 只读，无需手动创建
  1002 = 修改时间 (ModifiedTime)
  1003 = 创建人 (Creator)

注意：公式字段（汇报周次）、AI字段（要点提炼）、以及视图配置目前不支持 API 创建，
需在飞书界面手动配置，脚本运行后会打印操作指引。
"""

import requests
import yaml
from core.bitable import BitableClient

# ——————————————————————————————
# 目标多维表 App Token（与 T03 同一个 HECS 应用内）
HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
TABLE_NAME = "HRBP业务周报"
# ——————————————————————————————

def setup_weekly_report():
    print("🛠️  开始创建「HRBP 业务周报」主表...")
    client = BitableClient()

    # 1. 创建表格（幂等：已存在则复用）
    table_id = client.create_table(HECS_APP_TOKEN, TABLE_NAME)
    if not table_id:
        print("❌ 创建/获取表格失败，请检查 app_token 和权限。")
        return
    print(f"✅ 表格「{TABLE_NAME}」就绪，Table ID: {table_id}")

    # 2. 字段定义
    # type: 1=文本, 3=单选, 4=多选, 7=复选框, 11=人员
    # 注：第一个字段（标题列）默认已存在，跳过即可；飞书会自动创建名为"标题"的字段
    fields = [
        # —— 基础信息区（BP 填写时隐藏，系统自动填充）——
        {
            "name": "汇报人",
            "type": 11,  # 人员字段，表单设置 "自动收集提交人"
        },
        {
            "name": "所属小组",
            "type": 3,   # 单选，运行后可手动关联 T03 的组别字段
            "property": {
                "options": [
                    {"name": "研发组BP", "color": 1},
                    {"name": "营销组 BP", "color": 3},
                    {"name": "培训组", "color": 5},
                ]
            }
        },

        # —— 业务模块区（BP 填写，表单可见）——
        {"name": "M1 招聘产出与HC确认", "type": 1},
        {
            "name": "📌 招聘关键Case",
            "type": 7,   # 复选框
        },
        {"name": "M2 Agent实践与业务进展", "type": 1},
        {
            "name": "📌 Agent关键Case",
            "type": 7,
        },
        {"name": "M3 人员情况跟进", "type": 1},
        {"name": "M4 业务部门情况", "type": 1},
        {
            "name": "📌 业务关键Case",
            "type": 7,
        },
        {"name": "M5 卡点与下周计划", "type": 1},

        # —— 管理区（管理层使用，表单不可见）——
        {
            "name": "重点讨论模块",
            "type": 4,   # 多选
            "property": {
                "options": [
                    {"name": "招聘", "color": 1},
                    {"name": "Agent", "color": 3},
                    {"name": "人员情况", "color": 5},
                    {"name": "业务部门", "color": 7},
                    {"name": "卡点与计划", "color": 9},
                ]
            }
        },
    ]

    # 3. 逐个创建字段
    print("\n📋 开始创建字段...")
    field_results = {}
    for f in fields:
        fid = client.create_field(
            HECS_APP_TOKEN, table_id,
            f["name"], f["type"],
            property_obj=f.get("property")
        )
        status = "✅" if fid else "⚠️ (可能已存在)"
        print(f"  {status} {f['name']}")
        if fid:
            field_results[f["name"]] = fid

    # 4. 打印后续手动配置指引
    bitable_url = f"https://fjdynamics.feishu.cn/base/{HECS_APP_TOKEN}?table={table_id}"
    print(f"""
✨ 脚本执行完毕！

📊 表格链接: {bitable_url}

⚙️  还需在飞书界面手动完成以下配置（约 30 分钟）：

【字段配置】
  1. 添加「汇报周次」→ 公式字段
     公式：YEAR(CREATED_TIME()) & "-W" & WEEKNUM(CREATED_TIME())

  2. 添加「AI 核心要点」→ AI 字段
     Prompt：阅读该HRBP的5个模块周报内容，提炼出本周最核心的业务动态或风险点，
     输出1句话，严格控制在15-20字，禁止使用"本周"、"完成了"等套话，直接说结论。

【表单配置】
  3. 开启表单，隐藏「汇报人」「所属小组」「汇报周次」「重点讨论模块」「AI核心要点」
  4. 开启「提交后允许修改」
  5. 为每个长文本字段添加填写说明（见下方）

【视图配置】
  6. 新建「会议主持板」(画册视图)，按提交时间升序，封面显示 AI 核心要点
  7. 新建「招聘对齐」「Agent对齐」表格视图（各自筛选仅显示对应模块）
  8. 新建「管理驾驶舱」仪表盘，加提交进度饼图和 Case 分布图

【表单填写说明（各模块）】
  M1 招聘: "本周关键HC进展、画像确认情况，请简述要点"
  M2 Agent: "个人AI工具使用心得 + 向业务团队推广的进展"
  M3 人员: "试用期反馈 + 风险/异常人员情况"
  M4 业务: "业务团队现状、诉求与反馈"
  M5 计划: "本周主要卡点 + 下周核心动作"
  Case勾选: "如本模块有典型案例可供分享，请勾选此项"
""")

if __name__ == "__main__":
    setup_weekly_report()
