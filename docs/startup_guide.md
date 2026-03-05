# 🚀 FJD HRBP 协同系统 - 快速启动与维护指南

本指南供负责人随时查阅，包含了系统访问、日常维护、权限管理及机器人配置等核心信息。

---

## 🔗 核心访问链接

| 模块名称 | 访问地址 |
| :--- | :--- |
| **看板 Web 网址** | [点击进入 (Streamlit 看板)](https://fjd-hrbp-weekly-board.streamlit.app/) |
| **周报填写入口** | [点击跳转 (飞书表单填写)](https://fjdynamics.feishu.cn/share/base/form/shrcnuxUdum6YVhMNLF7dMTdNtb) |
| **飞书多维表 (后台)** | [点击访问 (Bitable 大表)](https://fjdynamics.feishu.cn/base/EPrYb1tWeaQrk7s0hp5c4vKrnlh?table=tblsq8b5JhivRD1x) |

---

## 🔐 系统权限中心

| 角色级别 | 适用场景 | 对应密码 |
| :--- | :--- | :--- |
| **负责人 (Boss)** | 满额权限：审阅全部内容、查看历史、触发 AI 总结 | `Hannah.Wei@FJD` |
| **周会投屏 (Screen)** | 限额权限：仅用于会议室大屏展示周会投屏视图 | `fjd_hrbp_2026` |

> [!IMPORTANT]
> **安全声明**：所有密码均已上云加密。若需更改，请在本地 `configs/config.yaml` 修改后告知 Antigravity 完成 `git push` 同步。

---

## 🛠️ 后台管理指令 (Antigravity 终端调用)

在 Antigravity 终端中，你可以直接运行以下指令查看最新状态：

### 1. 实时填报与系统状态简报
```powershell
python scripts/automation/status_report.py
```
*   **功能**：实时扫描本周填报进度（自动排除 Hannah, Maia, Shimmer）、监控近 10 分钟最新动态、检查 DeepSeek API 状态。

### 2. 强制触发 AI 摘要同步
```powershell
python scripts/automation/run_ai_summarize.py
```
*   **功能**：立即扫描所有最新填报，强制唤醒 AI 生成摘要和议程建议。

---

## 🤖 机器人配置

- **名称**：BP小Q ( cli_a92832259935dbc7 )
- **角色**：系统自动同步员、周报提醒官。
- **维护项**：
    - 已开启飞书多维表 **“编辑者”** 权限。
    - 负责每周三 14:00 发起私信提醒。

---

## 👥 人员逻辑说明

- **自动排除名单**：`Hannah.Wei`, `Maia.Yuan`, `Shimmer.Liu`。
- **离职逻辑**：系统会自动扫描“BP配置中心”表的“在职状态”，标记为“离职”的人员将不再计入应交人数。
- **填报周次**：系统自动按当前系统日期计算所属月度和周次（例如：`26M3W1`）。

---

*最近更新日期：2026-03-05*
