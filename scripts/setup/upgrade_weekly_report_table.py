"""
upgrade_weekly_report_table.py
==============================
创建/升级「HRBP业务周报」主表，包含完整字段设计：
- 时间索引：归档标识、周索引
- 身份关联：汇报人、底表关联、所属小组
- 业务模块 M1-M5
- 各模块摘要 S1-S5（bot AI回写）
- 各模块需汇报标记 H1-H5（管理层勾选）
- 综合决策议程建议

运行方式: python -m scripts.upgrade_weekly_report_table
"""
import requests
from core.bitable import BitableClient

HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
TABLE_NAME = "HRBP业务周报"

def upgrade():
    print("🔧 开始创建/升级「HRBP业务周报」表...")
    client = BitableClient()
    token = client.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ── 获取 T03 table_id ──
    tables_res = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables",
        headers=headers
    ).json()
    all_tables = tables_res.get("data", {}).get("items", [])
    t03_id = next((t["table_id"] for t in all_tables if "T03" in t["name"]), None)
    if not t03_id:
        print("❌ 未找到 T03 表")
        return
    print(f"✅ T03 ID: {t03_id}")

    # ── 创建或复用表格 ──
    weekly_id = next((t["table_id"] for t in all_tables if t["name"] == TABLE_NAME), None)
    if weekly_id:
        print(f"✅ 表格「{TABLE_NAME}」已存在，ID: {weekly_id}，追加缺失字段")
    else:
        create_res = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables",
            headers=headers,
            json={"table": {"name": TABLE_NAME}}
        ).json()
        if create_res.get("code") != 0:
            print(f"❌ 建表失败: {create_res.get('msg')}")
            return
        weekly_id = create_res["data"]["table_id"]
        print(f"✅ 表格「{TABLE_NAME}」创建成功，ID: {weekly_id}")

    # ── 获取已有字段 ──
    fields_res = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{weekly_id}/fields",
        headers=headers
    ).json()
    existing = {f["field_name"] for f in fields_res.get("data", {}).get("items", [])}
    print(f"已有字段: {existing or '（空）'}\n")

    # ── 字段定义 ──
    # 注意：飞书字段名不支持方括号 []，使用中文括号（）
    all_fields = [
        # 时间索引
        {"name": "归档标识",         "type": 1,  "note": "API回写: YYYY-MM"},
        {"name": "周索引",           "type": 1,  "note": "API回写: Wxx 如 W09"},
        # 身份
        {"name": "汇报人",           "type": 11, "note": "表单自动收集提交人"},
        {"name": "底表关联",         "type": 21, "note": "关联T03",
         "property": {"table_id": t03_id, "multiple": False}},
        # 模块 M1
        {"name": "M1 招聘产出与HC确认", "type": 1, "note": "BP填写"},
        {"name": "S1（摘要）招聘",    "type": 1,  "note": "AI提炼M1, 15-20字"},
        {"name": "H1 需汇报",        "type": 7,  "note": "管理层勾选触发通知"},
        # 模块 M2
        {"name": "M2 Agent实践与进展", "type": 1, "note": "BP填写"},
        {"name": "S2（摘要）Agent",   "type": 1,  "note": "AI提炼M2, 15-20字"},
        {"name": "H2 需汇报",        "type": 7,  "note": "管理层勾选触发通知"},
        # 模块 M3
        {"name": "M3 人员异常与试用期", "type": 1, "note": "BP填写"},
        {"name": "S3（摘要）人员",    "type": 1,  "note": "AI提炼M3, 15-20字"},
        {"name": "H3 需汇报",        "type": 7,  "note": "管理层勾选触发通知"},
        # 模块 M4
        {"name": "M4 业务部门情况反馈", "type": 1, "note": "BP填写"},
        {"name": "S4（摘要）业务",    "type": 1,  "note": "AI提炼M4, 15-20字"},
        {"name": "H4 需汇报",        "type": 7,  "note": "管理层勾选触发通知"},
        # 模块 M5
        {"name": "M5 下周计划与卡点",  "type": 1, "note": "BP填写"},
        {"name": "S5（摘要）计划",    "type": 1,  "note": "AI提炼M5, 15-20字"},
        {"name": "H5 需汇报",        "type": 7,  "note": "管理层勾选触发通知"},
        # 综合
        {"name": "决策议程建议",      "type": 1,  "note": "AI综合M1-M5输出推荐语"},
    ]

    ok = skip = fail = 0
    for f in all_fields:
        if f["name"] in existing:
            print(f"  ⏭️  已存在: {f['name']}")
            skip += 1
            continue
        payload = {"field_name": f["name"], "type": f["type"]}
        if "property" in f:
            payload["property"] = f["property"]
        res = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{weekly_id}/fields",
            headers=headers, json=payload
        ).json()
        if res.get("code") == 0:
            print(f"  ✅ {f['name']}  ({f['note']})")
            ok += 1
        else:
            print(f"  ❌ 失败: {f['name']} → {res.get('code')} {res.get('msg')}")
            fail += 1

    bitable_url = f"https://fjdynamics.feishu.cn/base/{HECS_APP_TOKEN}?table={weekly_id}"
    print(f"""
✨ 完成！新增 {ok} | 跳过 {skip} | 失败 {fail}

📊 表格链接: {bitable_url}
📌 请更新 run_bot_master.py 中的 WEEKLY_REPORT_TABLE_ID = "{weekly_id}"
""")
    # 自动打印以便复制
    print(f'WEEKLY_REPORT_TABLE_ID = "{weekly_id}"')

if __name__ == "__main__":
    upgrade()
