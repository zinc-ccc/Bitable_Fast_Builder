"""
rebuild_weekly_report_v3.py
===========================
按照 HRBP周会搭建规则.md V3.0_Final 标准，从零重建主表：
1. 将 T03-BP底表 重命名为 BP配置中心
2. 删除旧的 HRBP业务周报 表
3. 新建 HRBP周报 表
4. 按规则创建 22 个字段

字段命名规范：下划线连接，禁止括号/横杠/点号，半角英文符号

运行方式: python -m scripts.rebuild_weekly_report_v3
"""
import requests
from core.bitable import BitableClient

HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
NEW_TABLE_NAME  = "HRBP周报"
BASE_TABLE_NAME = "BP配置中心"

def rebuild():
    print("📋 读取规则: HRBP周会搭建规则.md V3.0_Final")
    client = BitableClient()
    token = client.get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ── 获取当前所有表格 ──
    tables = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables",
        headers=headers
    ).json().get("data", {}).get("items", [])
    print("当前表格：" + " | ".join(f"{t['name']}" for t in tables))

    t03 = next((t for t in tables if "T03" in t["name"] or "底表" in t["name"]), None)
    old_weekly = next((t for t in tables if "HRBP" in t["name"] and "周报" in t["name"]), None)
    blank = next((t for t in tables if t["name"] == "数据表"), None)

    # ── Step 1: 重命名底表为 BP配置中心 ──
    if t03 and t03["name"] != BASE_TABLE_NAME:
        r = requests.patch(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{t03['table_id']}",
            headers=headers, json={"name": BASE_TABLE_NAME}
        ).json()
        print(f"✅ 底表重命名: {t03['name']} → {BASE_TABLE_NAME}" if r.get("code") == 0
              else f"❌ 底表重命名失败: {r.get('msg')}")
        base_table_id = t03["table_id"]
    else:
        base_table_id = t03["table_id"] if t03 else None
        print(f"✅ 底表已是: {BASE_TABLE_NAME} ({base_table_id})")

    # ── Step 2: 删除旧周报表 + 空白表 ──
    ids_to_delete = []
    if old_weekly:
        ids_to_delete.append(old_weekly["table_id"])
    if blank:
        ids_to_delete.append(blank["table_id"])
    if ids_to_delete:
        r = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/batch_delete",
            headers=headers,
            json={"table_ids": ids_to_delete}
        )
        try:
            result = r.json()
            if result.get("code") == 0:
                print(f"✅ 已删除旧表: {[t for t in [old_weekly, blank] if t]}")
            else:
                print(f"❌ 删除失败: {result.get('msg')}")
        except Exception:
            if r.status_code in (200, 204):
                print("✅ 旧表已删除")
            else:
                print(f"❌ 删除请求失败 HTTP {r.status_code}")

    # ── Step 4: 新建 HRBP周报 表 ──
    r = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables",
        headers=headers, json={"table": {"name": NEW_TABLE_NAME}}
    ).json()
    if r.get("code") != 0:
        print(f"❌ 建表失败: {r.get('msg')}")
        return
    weekly_id = r["data"]["table_id"]
    print(f"✅ 新表创建成功: {NEW_TABLE_NAME} -> {weekly_id}")

    # ── Step 5: 创建 22 个标准字段 ──
    # 注: 飞书不支持 API 创建「查找引用」类型字段(所属小组)，需手动配置
    # 注: 创建日期(填写日期) type 1001 为系统只读字段，由系统自动生成，无需 API 创建
    fields = [
        # 序号2-3: 时间索引
        {"field_name": "归档标识",             "type": 1},   # 文本, API写入 YYYY_MM
        {"field_name": "周索引",               "type": 1},   # 文本, API写入 Wxx
        # 序号4-5: 身份
        {"field_name": "汇报人",               "type": 11},  # 人员, 表单自动采集
        {"field_name": "底表关联",             "type": 21,   # 单向关联 BP配置中心
         "property": {"table_id": base_table_id, "multiple": False}},
        # 序号7-9: 模块 M1 招聘
        {"field_name": "招聘产出与HC确认",     "type": 1},
        {"field_name": "摘要_招聘",            "type": 1},
        {"field_name": "需汇报_招聘",          "type": 7},
        # 序号10-12: 模块 M2 Agent
        {"field_name": "Agent实践与进展",      "type": 1},
        {"field_name": "摘要_Agent",           "type": 1},
        {"field_name": "需汇报_Agent",         "type": 7},
        # 序号13-15: 模块 M3 人员
        {"field_name": "人员异常与试用期",     "type": 1},
        {"field_name": "摘要_人员",            "type": 1},
        {"field_name": "需汇报_人员",          "type": 7},
        # 序号16-18: 模块 M4 业务
        {"field_name": "业务部门情况反馈",     "type": 1},
        {"field_name": "摘要_业务",            "type": 1},
        {"field_name": "需汇报_业务",          "type": 7},
        # 序号19-21: 模块 M5 计划
        {"field_name": "下周计划与卡点",       "type": 1},
        {"field_name": "摘要_计划",            "type": 1},
        {"field_name": "需汇报_计划",          "type": 7},
        # 序号22: 综合
        {"field_name": "议程建议",             "type": 1},
    ]

    ok = fail = 0
    for f in fields:
        payload = {"field_name": f["field_name"], "type": f["type"]}
        if "property" in f:
            payload["property"] = f["property"]
        res = requests.post(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{weekly_id}/fields",
            headers=headers, json=payload
        ).json()
        if res.get("code") == 0:
            print(f"  ✅ {f['field_name']}")
            ok += 1
        else:
            print(f"  ❌ {f['field_name']} → {res.get('code')} {res.get('msg')}")
            fail += 1

    # 首行字段改名
    fields_res = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{weekly_id}/fields",
        headers=headers
    ).json()
    first = fields_res["data"]["items"][0]
    r = requests.put(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables/{weekly_id}/fields/{first['field_id']}",
        headers=headers, json={"field_name": "填写日期", "type": 1}
    ).json()
    print(f"  ✅ 首行字段改名为「填写日期」" if r.get("code") == 0 else f"  ❌ 首行改名失败")

    bitable_url = f"https://fjdynamics.feishu.cn/base/{HECS_APP_TOKEN}?table={weekly_id}"
    print(f"""
✨ 完成！新增 {ok} | 失败 {fail}
📊 {NEW_TABLE_NAME}: {bitable_url}
📌 请更新常量: WEEKLY_REPORT_TABLE_ID = "{weekly_id}"

⚠️  以下需手动配置（API 不支持）：
  1. 「所属小组」→ 新建查找引用字段，引用「底表关联」的「组别」
  2. 「填写日期」→ 将类型改为创建日期（系统字段），表单隐藏
  3. 配置记录级权限：HRBP_Team 只能看自己的记录
  4. 配置 3 个视图（规则文档第四节）
  5. 配置自动化流：需汇报字段被 Hannah 勾选 → 私聊 BP
""")
    print(f'WEEKLY_REPORT_TABLE_ID = "{weekly_id}"')

if __name__ == "__main__":
    rebuild()
