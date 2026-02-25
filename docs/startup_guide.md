# 项目启动与入口指南

## 1. 入口文件
本项目的核心启动代码位于：
`scripts/run_bot_master.py`

该文件整合了最完善的事件处理逻辑（Raw Event 模式），是官方推荐的生产运行入口。

## 2. 环境准备
在启动之前，请确保已安装必要的依赖：
```bash
pip install -r requirements.txt
```

## 3. 配置检查
请检查 `configs/config.yaml` 文件中的信息是否完整：
*   `app_id` & `app_secret`: 对应的飞书自建应用凭证。
*   应用需具备：`获取群成员`、`读取消息`、`更新多维表` 等必要权限。

## 4. 启动方式

### 标准启动
直接运行主脚本：
```bash
python scripts/run_bot_master.py
```

### 生产启动 (Windows 示例)
若需指定 `PYTHONPATH` 并在后台运行：
```powershell
$env:PYTHONPATH = ".;$env:PYTHONPATH"
python scripts/run_bot_master.py
```

## 5. 验证运行
启动成功后，控制台应输出：
`🚀 HECS 4.1 终端核心启动 (Raw Event 模式)...`

此时，您可以尝试在飞书群中发送包含“同步”、“识别”或“拉取”字样的指令，观察控制台输出。
