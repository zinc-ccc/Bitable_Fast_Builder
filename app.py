"""
HRBP 效能协同中心 - FastAPI 后端 v2
修复：
- 正确读取单选/多选字段的 name 而非 id
- 动态拉取字段选项字典，用于解码 所属小组 等下拉字段
- 写入白名单：只允许写 归档标识 和 AI议程建议
"""
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests as req_lib
from core.bitable import BitableClient
from core.ai_helper import AIHelper

app = FastAPI(title="HRBP Dashboard API v2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 初始化 ---
with open("configs/config.yaml", "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f)

_bitable = BitableClient()
_ai = AIHelper()
APP_TOKEN = _cfg["hrbp_dashboard"]["app_token"]
TABLE_ID  = _cfg["hrbp_dashboard"]["table_id"]

# --- 字段选项缓存（用于解码单选/多选的 option id → name）---
_option_map: dict[str, str] = {}  # {option_id: option_name}

def refresh_option_map():
    global _option_map
    token = _bitable.get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields?page_size=100"
    resp = req_lib.get(url, headers=headers).json()
    for field in resp.get("data", {}).get("items", []):
        for opt in field.get("property", {}).get("options", []):
            if opt.get("id") and opt.get("name"):
                _option_map[opt["id"]] = opt["name"]

refresh_option_map()

# --- 文本提取（兼容所有多维表字段类型）---
def extract_text(val) -> str:
    if val is None: return ""
    if isinstance(val, bool): return val
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, str):
        # 可能是 option id（以opt开头），尝试解码
        return _option_map.get(val, val)
    if isinstance(val, list):
        parts = []
        for v in val:
            if isinstance(v, dict):
                # 富文本段落: {text, type}
                if "text" in v:
                    parts.append(v["text"])
                # 选项对象: {id, name, color}
                elif "name" in v:
                    parts.append(v["name"])
                else:
                    parts.append(str(v))
            elif isinstance(v, str):
                parts.append(_option_map.get(v, v))
            else:
                parts.append(str(v))
        return ", ".join(p for p in parts if p)
    if isinstance(val, dict):
        if "text" in val: return val["text"]
        if "name" in val: return _option_map.get(val.get("id", ""), val["name"])
        return str(val)
    return str(val)

def safe_bool(val) -> bool:
    return bool(val) if val is not None else False

def build_record(r: dict) -> dict:
    f = r.get("fields", {})
    highlights_raw = f.get("本周需重点汇报模块", [])
    if isinstance(highlights_raw, list):
        highlights = [extract_text(h) for h in highlights_raw]
    else:
        highlights = [extract_text(highlights_raw)] if highlights_raw else []

    # 从多选：招聘进展与HC确认, Agent实践与进展, 人员情况, 业务部门情况反馈, 下周计划与卡点
    def is_priority(module_option_name: str) -> bool:
        return any(module_option_name in h for h in highlights)

    return {
        "record_id": r["record_id"],
        "reporter": extract_text(f.get("汇报人", "")),
        "group": extract_text(f.get("所属小组", "")),
        "week": extract_text(f.get("周索引", "")),
        "update_time": f.get("最后更新时间", 0) or 0,
        "highlights": highlights,
        "archived": safe_bool(f.get("归档标识")),
        "ai_agenda": extract_text(f.get("AI议程建议", "")),
        "modules": {
            "招聘": {
                "content": extract_text(f.get("摘要_招聘", "")),
                "raw":     extract_text(f.get("招聘进展与HC确认", "")),
                "priority": safe_bool(f.get("需汇报_招聘")),
                "highlighted": is_priority("招聘"),
            },
            "Agent": {
                "content": extract_text(f.get("摘要_Agent", "")),
                "raw":     extract_text(f.get("Agent实践与进展", "")),
                "priority": safe_bool(f.get("需汇报_Agent")),
                "highlighted": is_priority("Agent"),
            },
            "人员": {
                "content": extract_text(f.get("摘要_人员", "")),
                "raw":     extract_text(f.get("人员情况", "")),
                "priority": safe_bool(f.get("需汇报_人员")),
                "highlighted": is_priority("人员"),
            },
            "业务": {
                "content": extract_text(f.get("摘要_业务", "")),
                "raw":     extract_text(f.get("业务部门情况反馈", "")),
                "priority": safe_bool(f.get("需汇报_业务")),
                "highlighted": is_priority("业务"),
            },
            "专项": {
                "content": extract_text(f.get("摘要_专项", "")),
                "raw":     extract_text(f.get("其他专项工作", "")),
                "priority": False,
                "highlighted": False,
            },
            "计划": {
                "content": extract_text(f.get("摘要_计划", "")),
                "raw":     extract_text(f.get("下周计划与卡点", "")),
                "priority": safe_bool(f.get("需汇报_计划")),
                "highlighted": is_priority("计划"),
            },
        }
    }

# --- API 路由 ---
@app.get("/api/records")
def get_records(week: Optional[str] = None):
    raw = _bitable.list_records(APP_TOKEN, TABLE_ID)
    records = [build_record(r) for r in raw]
    if week:
        records = [r for r in records if r["week"] == week]
    records.sort(key=lambda x: x["update_time"])
    return {"records": records, "total": len(records)}

@app.get("/api/weeks")
def get_weeks():
    raw = _bitable.list_records(APP_TOKEN, TABLE_ID)
    weeks = sorted(
        {build_record(r)["week"] for r in raw if build_record(r)["week"]},
        reverse=True
    )
    return {"weeks": weeks}

@app.post("/api/refresh-fields")
def refresh_fields():
    """重新扫描字段选项（字段更新后调用）"""
    refresh_option_map()
    fields = _bitable.list_fields(APP_TOKEN, TABLE_ID)
    return {"ok": True, "field_count": len(fields)}

class ArchiveRequest(BaseModel):
    record_id: str
    value: bool
    reporter: str

@app.post("/api/archive")
def update_archive(req: ArchiveRequest):
    result = _bitable.update_record(APP_TOKEN, TABLE_ID, req.record_id, {"归档标识": req.value})
    if result.get("code") != 0:
        raise HTTPException(status_code=400, detail=result.get("msg", "更新失败"))
    return {"ok": True, "reporter": req.reporter, "archived": req.value}

class AgendaRequest(BaseModel):
    week: Optional[str] = None

@app.post("/api/generate-agenda")
def generate_agenda(req: AgendaRequest):
    raw = _bitable.list_records(APP_TOKEN, TABLE_ID)
    records = [build_record(r) for r in raw]
    if req.week:
        records = [r for r in records if r["week"] == req.week]
    if not records:
        return {"agenda": "暂无本周数据", "count": 0}

    text = f"汇报周次：{req.week or '全部'}\n\n"
    for r in records:
        text += f"【{r['reporter']}】({r['group']}):\n"
        for mod, data in r["modules"].items():
            if data["content"]:
                prio = " ⭐重点" if data["priority"] else ""
                text += f"  {mod}{prio}: {data['content']}\n"
        text += "\n"

    agenda = _ai.generate_agenda(text)
    ok = 0
    for r in records:
        res = _bitable.update_record(APP_TOKEN, TABLE_ID, r["record_id"], {"AI议程建议": agenda})
        if res.get("code") == 0:
            ok += 1
    return {"agenda": agenda, "count": ok}

# --- 静态文件 ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve():
    return FileResponse("static/index.html")
