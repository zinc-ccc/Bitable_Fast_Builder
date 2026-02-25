# 主要代码文件介绍

本项目采用清晰的模块化设计，主要分为核心逻辑层 (`core/`) 和 执行脚本层 (`scripts/`)。

## 1. 核心逻辑目录 (`core/`)
*   **`bot.py`**: 封装了飞书机器人的基本交互逻辑，处理消息发送、卡片交互等通用功能。
*   **`bitable.py`**: 飞书多维表（Bitable）的核心操作客户端。封装了获取 Token、创建记录、获取表列表、成员同步等 API 调用。
*   **`analyzer.py`**: 需求分析引擎（开发中/集成中）。负责将用户的自然语言描述转化为结构化的字段定义。
*   **`naming.py`**: 命名规则引擎。确保生成的表名和字段名符合项目预设的规范（如可读性、避免敏感符号等）。

## 2. 脚本目录 (`scripts/`)
*   **`run_bot_master.py`** (**核心入口**): 采用 Raw Event 模式启动的飞书机器人主进程。集成了 HECS 4.1 的成员同步逻辑。
*   **`run_bot_long_conn.py`**: 另一种基于标准事件分发器的长连接启动方式，适用于简单的指令处理。
*   **`create_hecs_tables.py`**: 辅助脚本，用于初始化或批量创建特定的多维表结构。
*   **其他工具脚本**:
    *   `test_conn.py`: API 连接测试。
    *   `fetch_ids.py`: 用于快速获取 App、Table 或 Chat 的 ID。
    *   `diagnose_api.py`: 接口诊断工具。

## 3. 其他重要文件
*   **`configs/config.yaml`**: 全局配置文件，存储 `app_id`、`app_secret` 以及业务参数。
*   **`README.md`**: 项目根目录的快速入门文档，包含了字段设计准则。
*   **`requirements.txt`**: 项目依赖列表。
*   **`prompts/`**: 存储用于 AI 解析的 Prompt 模板。
