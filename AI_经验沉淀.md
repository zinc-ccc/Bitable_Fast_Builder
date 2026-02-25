# AI 工程经验沉淀库

> 这是一个跨项目、持续更新的 AI 辅助开发经验文档。
> 记录真实踩坑和解决方案，配合代码示例，供所有项目复用。
> **维护原则**：遇到坑就记，解决了就补方案，不写废话。

---

## 目录

- [飞书开放平台](#一飞书开放平台)
  - [WebSocket 长连接握手失败](#坑1-websocket-长连接握手失败)
  - [事件重复投递（消息被处理多次）](#坑2-事件重复投递消息被处理多次)
  - [通讯录权限不足导致用户信息读取失败](#坑3-通讯录权限不足导致用户信息读取失败)
- [Git 版本控制](#二git-版本控制)
  - [项目开发过半才初始化 Git](#坑4-项目开发过半才初始化-git)
- [飞书多维表 Bitable API](#三飞书多维表-bitable-api)
  - [字段类型编号对照](#参考字段类型编号对照表)

---

## 一、飞书开放平台

### 坑1: WebSocket 长连接握手失败

**现象**：启动 bot 后 ws 一直连不上，日志显示握手失败或 403。

**根本原因**：飞书 WebSocket 长连接模式下，SDK 用的是 `app_id + app_secret` 直接建立连接，**无需 verification_token 和 encrypt_key**，但如果传了错误的值也可能导致握手失败。

**解决方案**：
- `EventDispatcherHandler.builder("", "")` 中两个参数传空字符串即可，不用填 webhook 里的校验 token
- 确认飞书开放平台后台已开启「长连接」能力（机器人 → 事件订阅 → 选择"使用长连接接收事件"）

```python
# ✅ 正确写法
event_handler = (
    lark.EventDispatcherHandler.builder("", "")  # 长连接模式：两个参数都传空串
    .register_p2_customized_event("im.message.receive_v1", handle_im_message)
    .build()
)

ws_client = lark.ws.Client(
    app_id,
    app_secret,
    event_handler=event_handler,
    log_level=lark.LogLevel.INFO
)
ws_client.start()
```

---

### 坑2: 事件重复投递（消息被处理多次）

**现象**：同一条消息触发了多次回复，或 T03 里写入了重复记录。

**根本原因**：飞书 WebSocket 在网络抖动时可能重复推送同一个事件（相同 `message_id`）。

**解决方案**：用 `deque` 做本地去重缓存，maxlen 控制内存上限。

```python
from collections import deque

_processed_message_ids = deque(maxlen=200)

def handle_im_message(data):
    message_id = data.event.get("message", {}).get("message_id", "")

    # 去重：同一条消息只处理一次
    if message_id and message_id in _processed_message_ids:
        print(f"⚠️ 重复事件，已忽略: {message_id}")
        return
    if message_id:
        _processed_message_ids.append(message_id)

    # ... 正常处理逻辑
```

**注意**：`deque(maxlen=200)` 在 bot 重启后会清空，重启期间若有少量重复可忽略。

---

### 坑3: 通讯录权限不足导致用户信息读取失败

**现象**：调用 `contact/v3/users/{user_id}` 返回 code=41050（无权限），无法读取用户的职称、部门等信息。

**根本原因**：飞书应用默认通讯录权限范围为"仅自己"，导致无法读取其他用户资料。

**解决方案**：
1. 飞书开放平台 → 应用详情 → 权限管理 → 开启以下权限（申请后需管理员审批）：
   - `contact:user.base`（基本信息）
   - `contact:job_title`（职称）
   - `contact:department`（部门）
2. 飞书开放平台 → 开发配置 → 通讯录权限范围 → 改为**"全员"**

**降级处理**（权限未开通时的兜底）：
```python
user_info = bitable_client.get_user_info(user_id)
if not user_info:
    # 降级：用群成员列表里的显示名，跳过组别识别
    print(f"  [警告] 无权限读取用户资料，已跳过: {m.get('name')}")
    skip_count += 1
    continue
```

---

## 二、Git 版本控制

### 坑4: 项目开发过半才初始化 Git

**现象**：项目已有大量代码，但一直没有 git，导致无法回滚、无法追踪变更历史。

**经验教训**：任何项目**第一天就应该 `git init`**，哪怕只有一个 README。

**补救方案**（项目中途初始化 Git）：
```bash
# 1. 初始化仓库（在项目根目录执行）
git init

# 2. 创建 .gitignore（避免把缓存、密钥等提交进去）
# Python 项目最少应包含：
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo ".venv/" >> .gitignore

# 3. 把现有代码作为"初始版本"提交
git add .
git commit -m "chore: initial commit, existing stable state"

# 4. 关联远程仓库（GitHub / Gitea 等）
git remote add origin https://github.com/yourname/yourrepo.git
git push -u origin master
```

**建议的 commit 节点**：
- ✅ 完成某项独立功能之后
- ✅ 修复影响主流程的核心 Bug 之后
- ✅ 大重构**之前**（先存稳定版）
- ✅ 每天结束工作前

---

## 三、飞书多维表 Bitable API

### 参考：字段类型编号对照表

> 在用代码自动创建 Bitable 表字段时，需要指定 `type` 编号。

| type 值 | 字段类型 | 备注 |
|--------|---------|------|
| 1 | 多行文本 (Text) | 长文本用这个 |
| 2 | 数字 (Number) | |
| 3 | 单选 (SingleSelect) | 需在 property.options 里定义选项 |
| 4 | 多选 (MultiSelect) | 需在 property.options 里定义选项 |
| 5 | 日期 (DateTime) | |
| 7 | 复选框 (Checkbox) | |
| 11 | 人员 (User) | |
| 1001 | 创建时间 (CreatedTime) | 只读，无需创建 |
| 1003 | 创建人 (Creator) | 只读，无需创建 |

> ⚠️ 以下字段类型**不支持 API 创建**，只能在飞书界面手动配置：
> - 公式字段（Formula）
> - AI 字段

**创建带选项的单选字段示例**：
```python
client.create_field(app_token, table_id, "组别", 3, property_obj={
    "options": [
        {"name": "研发组BP", "color": 1},
        {"name": "营销组 BP", "color": 3},
        {"name": "培训组", "color": 5},
    ]
})
```

---

*最后更新：2026-02-25 | 维护人：Zinc.Zheng*
