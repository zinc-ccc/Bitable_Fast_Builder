import lark_oapi as lark
import yaml
import json
import requests
from core.bitable import BitableClient
from core.weekly_summarizer import WeeklySummarizer

from collections import deque

# 加载配置
with open("configs/config.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

bitable_client = BitableClient()
summarizer = WeeklySummarizer()
HECS_APP_TOKEN = "EPrYb1tWeaQrk7s0hp5c4vKrnlh"
WEEKLY_REPORT_TABLE_ID = "tblffLH43wWopBUC"  # HRBP业务周报表

# 事件去重：记录已处理的 message_id，防止重复回复
_processed_message_ids = deque(maxlen=200)

def sync_group_members(chat_id):
    """
    HECS 4.1 核心逻辑：扫描群成员，识别组别填充 T03
    """
    try:
        members = bitable_client.get_chat_members(chat_id)
        if not members: return "未能获取群成员列表，请检查机器人群权限。"
        
        # 找到 T03
        url_tables = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HECS_APP_TOKEN}/tables"
        headers = {"Authorization": f"Bearer {bitable_client.get_token()}"}
        res_tables = requests.get(url_tables, headers=headers)
        data = res_tables.json()
        if data.get("code") != 0:
            return f"获取表格列表失败: {data.get('msg')}"
            
        tables = data.get("data", {}).get("items", [])
        t03_id = next((t['table_id'] for t in tables if "T03" in t['name']), "")
        
        if not t03_id:
            return "未找到 T03 配置中心表格。"

        sync_count = 0
        skip_count = 0
        group_summary = {}

        _no_auth_warned = False
        for m in members:
            user_id = m.get("member_id")
            # 1. 拿用户基本信息
            user_info = bitable_client.get_user_info(user_id)

            # 如果 Contact API 无权限（code=41050），usr_info 为空
            # 则降级使用群成员列表里已有的 name，且无法判断组别，直接跳过
            if not user_info:
                fb_name = m.get("name", user_id)
                if not _no_auth_warned:
                    print(f"  [警告] 无法读取用户资料，请在飞书开放平台将应用的【通讯录权限范围】设为《全员》，并开启 contact:user.base / contact:job_title / contact:department 权限")
                    _no_auth_warned = True
                print(f"  → 跳过（无权限读取资料）: {fb_name}")
                skip_count += 1
                continue

            name = user_info.get("name") or m.get("name", "未知")  # 备用群成员显示名
            job_title = str(user_info.get("job_title", ""))

            # 2. 拿部门 ID 列表，查询每个部门的实际名称
            dept_ids = user_info.get("department_ids", [])
            dept_names = []
            for did in dept_ids:
                d_name = bitable_client.get_department_name(did)
                if d_name:
                    dept_names.append(d_name)
            dept_path = " / ".join(dept_names)  # 拼成如："总经理办公室 / 人力资源 / HRBP组二 / 营销组HRBP"

            # 3. 合并所有可识别字段
            identity_str = dept_path + " " + job_title + " " + name
            print(f"[扫描] {name} | 部门路径: {dept_path or '(无)'} | 职称: {job_title or '(无)'}")

            # 4. 严格识别组别
            group_tag = None
            
            if name == "Hannah.Wei":
                group_tag = "负责人"
            elif "HRBP组三" in identity_str:
                print(f"  → 跳过（属于组三BP，暂时无需录入）: {name}")
                skip_count += 1
                continue
            elif "产研" in identity_str or "研发" in identity_str:
                if "HRBP" in identity_str or "BP" in identity_str:
                    group_tag = "研发组BP"
            elif "营销" in identity_str:
                if "HRBP" in identity_str or "BP" in identity_str:
                    group_tag = "营销组 BP"
            elif "技能评估" in identity_str or "培训" in identity_str:
                group_tag = "培训组"
            elif "HRBP" in identity_str:
                group_tag = "HRBP-待确认"
            
            if group_tag is None:
                print(f"  → 跳过（非目标相关人员）: {name}")
                skip_count += 1
                continue

            fields = {
                "HRBP": name,
                "人员ID": user_id,
                "群聊ID": chat_id,
                "组别": group_tag
            }
            bitable_client.create_record(HECS_APP_TOKEN, t03_id, fields)
            group_summary[group_tag] = group_summary.get(group_tag, 0) + 1
            sync_count += 1
            print(f"  → 写入: {name} → {group_tag} | 群聊ID: {chat_id}")

        # 动态组装回复
        if sync_count == 0:
            return f"群里未识别到需要记录的 BP 人员喔，请确认群成员信息。"
        
        detail_parts = [f"{g} {cnt} 人" for g, cnt in group_summary.items() if cnt > 0]
        detail_str = "、".join(detail_parts)
        
        reply = f"好的！已扫描群成员，共识别 HRBP {sync_count} 人"
        if detail_str:
            reply += f"（{detail_str}）"
        reply += "，已同步到 T03 配置表"
        
        if skip_count > 0:
            reply += f"，其余 {skip_count} 人非目标人员已跳过。"
        else:
            reply += "。"
            
        return reply
    except Exception as e:
        print(f"Sync Logic Error: {e}")
        return f"同步过程中出现错误: {str(e)}"


def summarize_weekly_reports():
    """
    扫描 HRBP 周报表中「没有 AI 核心要点」的记录，
    调用 LLM 生成总结，回写到「AI核心要点」字段。
    """
    try:
        records = bitable_client.list_records(HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID)
        if not records:
            return "周报表暂无记录。"

        pending = [
            r for r in records
            if not r.get("fields", {}).get("AI核心要点", "").strip()
        ]

        if not pending:
            return "所有周报已有 AI 总结，无需补充。"

        ok_count = 0
        fail_count = 0
        for record in pending:
            record_id = record.get("record_id", "")
            fields = record.get("fields", {})
            name = fields.get("汇报人") or record_id
            print(f"  [总结] 处理: {name}")

            summary = summarizer.summarize(fields)
            if summary:
                bitable_client.update_record(
                    HECS_APP_TOKEN, WEEKLY_REPORT_TABLE_ID, record_id,
                    {"AI核心要点": summary}
                )
                ok_count += 1
            else:
                fail_count += 1

        reply = f"已完成 AI 要点补全，成功 {ok_count} 条"
        if fail_count:
            reply += f"，{fail_count} 条调用失败（请检查模型配置）"
        reply += "。"
        return reply
    except Exception as e:
        print(f"Summarize Error: {e}")
        return f"调用 AI 总结时出错: {str(e)}"


def handle_im_message(data: lark.CustomizedEvent):
    """
    处理收到的飞书消息事件 (im.message.receive_v1)
    SDK 调用时，data 是已经反序列化的 CustomizedEvent 对象，
    data.event 是一个字典，包含消息的完整内容。
    """
    global _processed_message_ids
    try:
        event_body = data.event  # dict
        message = event_body.get("message", {})
        message_id = message.get("message_id", "")
        chat_id = message.get("chat_id", "")
        content_str = message.get("content", "{}")
        content = json.loads(content_str)
        text = content.get("text", "").strip()

        if ("@" in text):
            print(f"📩 收到飞书消息: '{text}'  |  ChatID: {chat_id}  |  MsgID: {message_id}")

        # 去重：同一条消息只处理一次（飞书 WebSocket 可能重复投递）
        if message_id and message_id in _processed_message_ids:
            print(f"⚠️  重复事件，已忽略: {message_id}")
            return
        if message_id:
            _processed_message_ids.append(message_id)

        # 指令识别
        if any(k in text for k in ["识别", "同步", "拉取"]):
            print(">>> 触发同步指令，正在执行...")
            resp_text = sync_group_members(chat_id)
            bitable_client.send_message(chat_id, "chat_id", resp_text)
        elif "总结" in text:
            print(">>> 触发 AI 总结指令，正在执行...")
            resp_text = summarize_weekly_reports()
            bitable_client.send_message(chat_id, "chat_id", resp_text)

    except Exception as e:
        print(f"事件处理异常: {e}")


def main():
    print("🚀 HECS 4.1 终端核心启动 (EventDispatcherHandler 模式)...")

    # 使用官方 EventDispatcherHandler，注册 p2 自定义事件处理器
    # encrypt_key 和 verification_token 对 WebSocket 长连接无需校验，传空字符串即可
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_customized_event("im.message.receive_v1", handle_im_message)
        .build()
    )

    ws_client = lark.ws.Client(
        config['lark']['app_id'],
        config['lark']['app_secret'],
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    ws_client.start()

if __name__ == "__main__":
    main()
