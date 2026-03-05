import sys
import os
import yaml
from datetime import datetime

# 设置包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.bitable import BitableClient

def run_attendance_check():
    """扫描今日/本周填报情况，识别未填人员，并排除特定名单"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "config.yaml")
    
    # 兼容流处理（如果不在 streamlit 环境下）
    try:
        import streamlit as st
        # 如果是 streamlit 环境，读 secrets
        if hasattr(st, "secrets") and "hrbp_dashboard" in st.secrets:
             app_token = st.secrets["hrbp_dashboard"]["app_token"]
             table_id = st.secrets["hrbp_dashboard"]["table_id"]
        else:
             with open(config_path, "r", encoding="utf-8") as f:
                  cfg = yaml.safe_load(f)
             app_token = cfg["hrbp_dashboard"]["app_token"]
             table_id = cfg["hrbp_dashboard"]["table_id"]
    except:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        app_token = cfg["hrbp_dashboard"]["app_token"]
        table_id = cfg["hrbp_dashboard"]["table_id"]
    
    bitable = BitableClient()
    
    # 1. 查找 BP 配置表（T03）
    bp_config_table_id = ""
    for t in bitable.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            bp_config_table_id = t["table_id"]
            break
    
    if not bp_config_table_id:
        print("❌ 未找到 BP配置中心 表")
        return

    # 2. 从 BP配置表 加载所有在职人员
    bp_records = bitable.list_records(app_token, bp_config_table_id)
    all_bps = {} # {name: open_id}
    
    # 排除名单
    EXCLUDE_LIST = ["Hannah.Wei", "Maia", "Shimmer.Liu", "Shimmer"]
    
    for r in bp_records:
        f = r.get("fields", {})
        # 兼容不同命名
        name_raw = f.get("HRBP") or f.get("姓名") or f.get("汇报人")
        status = f.get("在职状态")
        
        if not name_raw: continue
        
        # 提取姓名文字
        if isinstance(name_raw, list):
            name_text = name_raw[0].get("text", name_raw[0].get("name", ""))
        elif isinstance(name_raw, dict):
            name_text = name_raw.get("text", name_raw.get("name", ""))
        else:
            name_text = str(name_raw)
            
        if any(ex in name_text for ex in EXCLUDE_LIST):
            continue
            
        # 仅统计在职人员（如果没有状态字段则默认为在职）
        if status in ["在职", "试用期", None]:
             all_bps[name_text] = r.get("record_id")

    # 3. 扫描主表（周报表），看谁在本周（或当次）填了
    dt = datetime.now()
    week_of_month = (dt.day - 1) // 7 + 1
    current_week_idx = f"{str(dt.year)[-2:]}M{dt.month}W{week_of_month}"
    
    report_records = bitable.list_records(app_token, table_id)
    submitted_bps = set()
    
    for r in report_records:
        f = r.get("fields", {})
        week_idx = f.get("周索引")
        reporter = f.get("汇报人")
        
        if week_idx != current_week_idx: continue
        
        # 提取汇报人名称
        if isinstance(reporter, list):
            r_name = reporter[0].get("name", "")
        elif isinstance(reporter, dict):
            r_name = reporter.get("name", "")
        else:
            r_name = str(reporter)
            
        submitted_bps.add(r_name)

    # 4. 统计结果
    missing = [name for name in all_bps if name not in submitted_bps]
    
    print(f"\n📅 当前周期: {current_week_idx}")
    print(f"👥 应交人数: {len(all_bps)} (已排除 {', '.join(EXCLUDE_LIST)})")
    print(f"✅ 已交人数: {len(submitted_bps)}")
    print(f"🛑 未交人数: {len(missing)}")
    if missing:
        print(f"⚠️ 未填名单: {', '.join(missing)}")
    
    return missing

if __name__ == "__main__":
    run_attendance_check()
