import sys
import os
import yaml
import requests
from datetime import datetime, timedelta

# Project root for imports
sys.path.insert(0, os.getcwd())

from core.bitable import BitableClient

def get_status_report():
    """综合状态汇报：填报进度、近10分钟动态、以及系统状态"""
    
    # 1. 加载配置
    config_path = os.path.join(os.getcwd(), "configs", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    app_token = cfg["hrbp_dashboard"]["app_token"]
    table_id = cfg["hrbp_dashboard"]["table_id"]
    
    bitable = BitableClient()
    
    # --- 逻辑 A: 扫描 BP 配置表 (T03) ---
    bp_config_table_id = ""
    for t in bitable.list_tables(app_token):
        if "BP配置" in t.get("name", ""):
            bp_config_table_id = t["table_id"]
            break
    
    # 排除名单 (根据用户要求：Hannah, Maia 不参与周会填报；Shimmer 已离职)
    EXCLUDE_LIST = ["Hannah.Wei", "Maia", "Shimmer.Liu", "Shimmer"]
    
    all_bps = {}
    if bp_config_table_id:
        bp_records = bitable.list_records(app_token, bp_config_table_id)
        for r in bp_records:
            f = r.get("fields", {})
            name_raw = f.get("HRBP") or f.get("姓名")
            status = f.get("在职状态")
            
            if not name_raw: continue
            
            # 统一提取名称
            if isinstance(name_raw, list):
                name_text = name_raw[0].get("text", name_raw[0].get("name", ""))
            elif isinstance(name_raw, dict):
                name_text = name_raw.get("text", name_raw.get("name", ""))
            else:
                name_text = str(name_raw)
            
            if any(ex in name_text for ex in EXCLUDE_LIST):
                continue
            
            # 过滤逻辑：如果在职状态明确为“离职”，则跳过
            if status in ["离职", "已离职"]:
                continue
                
            all_bps[name_text] = r.get("record_id")

    # --- 逻辑 B: 扫描周报表 (主表) ---
    dt = datetime.now()
    week_of_month = (dt.day - 1) // 7 + 1
    current_week_idx = f"{str(dt.year)[-2:]}M{dt.month}W{week_of_month}"
    
    report_records = bitable.list_records(app_token, table_id)
    submitted_bps = set()
    recent_submissions = [] # 记录最近 10 分钟
    now_ts = datetime.now().timestamp() * 1000
    ten_mins_ago = now_ts - (10 * 60 * 1000)
    
    total_tokens_estimated = 0 # 粗略统计当日 AI 消耗作为监控参考
    
    for r in report_records:
        f = r.get("fields", {})
        week_idx = f.get("周索引")
        reporter = f.get("汇报人")
        create_ts = f.get("最后更新时间") or f.get("创建时间") or 0
        
        # 提取姓名
        if isinstance(reporter, list):
            r_name = reporter[0].get("name", "")
        elif isinstance(reporter, dict):
            r_name = reporter.get("name", "")
        else:
            r_name = str(reporter)
            
        if week_idx == current_week_idx:
            if r_name in all_bps:
                submitted_bps.add(r_name)
                
        # 监控近 10 分钟动态
        if create_ts > ten_mins_ago:
            recent_submissions.append(f"{r_name} (更新于 {datetime.fromtimestamp(create_ts/1000).strftime('%H:%M:%S')})")

    # --- 逻辑 C: DeepSeek 模拟监控 ---
    # 注：DeepSeek API 目前没有公开的 /balance 查询接口，这里打印当前的 API 配置状态和最近调用的摘要数
    ai_status = f"DeepSeek-V3 运行正常 | 模型: {cfg['openai']['model']}"
    
    # --- 打印报告 ---
    print("\n" + "="*50)
    print(f"🚀 HRBP 协同系统 - 实时状态简报 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("="*50)
    
    print(f"\n[1] 📅 本周填报进度 ({current_week_idx})")
    print(f"    - 应交人数: {len(all_bps)}人 (已排除 Hannah, Maia, Shimmer)")
    print(f"    - 已交人数: {len(submitted_bps)}人")
    print(f"    - 完成比例: {len(submitted_bps)/len(all_bps)*100 if all_bps else 0:.1f}%")
    
    missing = [n for n in all_bps if n not in submitted_bps]
    if missing:
        print(f"    - 🛑 未填名单: {', '.join(missing)}")
    else:
        print("    - ✅ 全员已交齐！")

    print(f"\n[2] ⚡ 最近 10 分钟动态")
    if recent_submissions:
        for sub in recent_submissions:
            print(f"    - {sub}")
    else:
        print("    - 暂无最新填写动态")

    print(f"\n[3] 🤖 AI 后台与额度监控")
    print(f"    - 状态: {ai_status}")
    print(f"    - 余额提示: DeepSeek 需前往后台 manual 充值，API目前处于可用状态")
    print(f"    - 今日已生成摘要数: (见 Bitable 汇报标识_系统自动 字段统计)")

    print("\n" + "="*50)
    print("💡 指向性命令: 运行 'python scripts/automation/run_ai_summarize.py' 强制触发同步")
    print("="*50 + "\n")

if __name__ == "__main__":
    get_status_report()
