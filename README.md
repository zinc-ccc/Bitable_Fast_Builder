# HRBP 效能协同中心（Bitable Fast Builder）

## 项目概述
本项目已从最初的“飞书多维表格快捷搭建工具”演变为**完整的 HRBP 效能协同系统**。涵盖了数据收集（多维表）、后台自动化处理、AI摘要提炼、以及前后端一体的周会投屏看板功能。

为了防止代码库随着功能膨胀而导致理解和维护成本上升，我们将核心功能进行了模块化拆分，分为**主 Web 服务** 和 **辅助运维能力集**。

---

## 一、系统架构与模块划分

### 1. 通用后端服务模块 (Web Service)
此模块直接服务于业务看板演示、审阅等前台需求。

- `app.py`: FastAPI 后端主程序。提供拉取数据请求、数据拼装、身份校验等核心借口。
- `static/index.html`: 前端界面（单文件 HTML/JS + Tailwind）。实现投屏及阅览、历史数据回溯功能。
- `core/`: 核心通用库（如 `bitable.py` 多维表接口操作、`ai_helper.py` DeepSeek 摘要提炼封装）。
- `configs/config.yaml`: 配置文件（包含应用 token，飞书秘钥、大模型配置、权限密码配置）。

### 2. 自动化辅助与运维脚本 (Scripts)
这些代码主要是围绕着飞书多维表的定期运营和突发状态修正而存在的脚本集，拆分在具体的 `scripts/` 各个子目录下：

- **自动化组 (`scripts/automation/`)** 
  （定期执行或事件驱动的核心辅助操作）
  - `run_bot_master.py`: 机器人指令系统主程序（支持与飞书机器人长连接聊天）。
  - `run_ai_summarize.py`: 手动或定时对多维表明细数据执行 AI 摘要填充。
  - `push_weekly_reports.py`: 为群组或个人群发周报搜集催办和汇报内容推送（通过服务机器人）。
  - `selective_push_reports.py`: 选择性推送处理。
  
- **构建组 (`scripts/setup/`)** 
  （只在系统初创、表结构升级时需要调用的“开荒”代码）
  - `setup_weekly_report_table.py` / `upgrade_weekly_report_table.py`: 一键在飞书中建表、加字段、设置规则的基础工具。
  - `fix_table_headers.py`, `patch_weekly_report_table.py` 等单次业务修正操作。
  
- **监控与排障组 (`scripts/diagnostic/`)**
  （排查飞书表结构、Token异常、查数据结构使用）
  - `diagnose_tables.py`: 检查表的字段丢失情况或异常。
  - `scan_bitable_structure.py`: 把远程多维表的所有结构打印出来并核对。
  - `list_bps.py`, `inspect_records.py` 等获取简单配置或数据视图使用。

- **环境变量与报表组 (`scripts/env/`, `scripts/reporting/`)**
  辅助的测试等清理脚本以及偶尔可能用一次的数据导出脚本。

- **归档组 (`archive/`)**
  - 早期的 `dashboard.py`（Streamlit 版本等旧有实现）。留作参考，通常无需运行。

---

## 二、部署与日常操作手册

### 1. 环境准备与配置修改
配置全部汇总在 `configs/config.yaml`。里面包含 `lark` 小程序校验 (确保 App ID 及 Secret 无误)、`openai` 密钥、以及 `auth` (前端密码)。
前端密码说明：
- `boss_pwd`: 最高权限（审阅、投屏、历史数据回溯可全部访问操作）。
- `screen_pwd`: 只读和投屏展示使用。限制只展示投屏视图。

### 2. 启动与运行主看板
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
启动后访问局域网 IP / 公网机器域名 即可进入密码验证界面。

### 3. 日常维护指引
- **机器人发信/催办**：可以使用 `python scripts/automation/push_weekly_reports.py` 手动调用或在操作系统定时任务中加入。
- **飞书结构字段添加后报错了怎么办？**：
  如果多维表格被 HRBP 改乱，或者字段对不上，可以先运行：
  `python scripts/diagnostic/diagnose_tables.py`，查看差异。
  然后让 Web 后端重新扫码一次字段（点击前端页面的扫字段或请求 `/api/refresh-fields`）。
  
### 4. 关于@所有人的说明
飞书机器人如果在群内没有具体的 `@所有用户` 权限操作能力或者格式被限制，所有消息已降级并统一为了稳健的文字推送 (`"大家记得填周报!"`)，如必须要求通知触达全体，可通过群管手动补充。

如果有新应用接入或新场景（如员工面谈库），请参照“工具脚本+基础库”的范式去编写 `setup_xxx.py` 初始化表结构，而不要都挤在根目录下，防止项目爆炸。
