"""
bitable.py
==========
飞书 Bitable & IM API 封装。
同时支持本地 configs/config.yaml 和 Streamlit Cloud st.secrets 读取凭证。
"""
import os
import json
import yaml
import requests


def _load_lark_config():
    """优先从 Streamlit secrets 读取，回退到本地 config.yaml。"""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "lark" in st.secrets:
            return {
                "app_id":     st.secrets["lark"]["app_id"],
                "app_secret": st.secrets["lark"]["app_secret"],
            }
    except Exception:
        pass

    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return {
        "app_id":     cfg["lark"]["app_id"],
        "app_secret": cfg["lark"]["app_secret"],
    }


class BitableClient:
    def __init__(self, config_path=None):
        """
        config_path: 兼容旧调用（本地脚本传入路径）。
        若不传，自动走 _load_lark_config() 双模式读取。
        """
        if config_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            self.app_id = cfg["lark"]["app_id"]
            self.app_secret = cfg["lark"]["app_secret"]
        else:
            lark = _load_lark_config()
            self.app_id = lark["app_id"]
            self.app_secret = lark["app_secret"]

        self.tenant_access_token = ""

    # ── Token ────────────────────────────────────────
    def get_token(self) -> str:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        res = requests.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret})
        if res.status_code == 200:
            self.tenant_access_token = res.json().get("tenant_access_token", "")
            return self.tenant_access_token
        raise Exception(f"Failed to get token: {res.text}")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    # ── Table operations ─────────────────────────────
    def create_table(self, app_token, table_name):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
        data = requests.post(url, headers=self._headers(), json={"table": {"name": table_name}}).json()
        if data.get("code") == 0:
            return data.get("data", {}).get("table_id")
        if data.get("code") == 1254013:  # duplicate name
            res_list = requests.get(url, headers=self._headers()).json()
            for item in res_list.get("data", {}).get("items", []):
                if item["name"] == table_name:
                    return item["table_id"]
        print(f"[create_table] {data.get('code')} - {data.get('msg')}")
        return None

    def list_tables(self, app_token):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
        data = requests.get(url, headers=self._headers()).json()
        return data.get("data", {}).get("items", [])

    # ── Field operations ─────────────────────────────
    def create_field(self, app_token, table_id, field_name, ui_type, property_obj=None):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        payload = {"field_name": field_name, "type": ui_type}
        if property_obj:
            payload["property"] = property_obj
        data = requests.post(url, headers=self._headers(), json=payload).json()
        if data.get("code") == 0:
            return data.get("data", {}).get("field", {}).get("field_id")
        print(f"[create_field] '{field_name}': {data.get('code')} - {data.get('msg')}")
        if "error" in data:
            print(f"  Details: {json.dumps(data.get('error'))}")
        return None

    def list_fields(self, app_token, table_id):
        url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}"
               f"/tables/{table_id}/fields?page_size=100")
        data = requests.get(url, headers=self._headers()).json()
        return data.get("data", {}).get("items", [])

    # ── Record operations ────────────────────────────
    def list_records(self, app_token, table_id, filter_str="", page_size=500):
        url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}"
               f"/tables/{table_id}/records?page_size={page_size}&display_formula_ref=true")
        if filter_str:
            url += f"&filter={filter_str}"
        data = requests.get(url, headers=self._headers()).json()
        return data.get("data", {}).get("items", [])

    def create_record(self, app_token, table_id, fields):
        url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}"
               f"/tables/{table_id}/records")
        return requests.post(url, headers=self._headers(), json={"fields": fields}).json()

    def update_record(self, app_token, table_id, record_id, fields):
        url = (f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}"
               f"/tables/{table_id}/records/{record_id}")
        return requests.put(url, headers=self._headers(), json={"fields": fields}).json()

    def batch_update_records(self, app_token, table_id, updates: list[dict]) -> int:
        """
        批量更新记录。updates 格式: [{"record_id": ..., "fields": {...}}, ...]
        使用串行循环（飞书批量更新API需要特别权限，此处用循环兼容普通权限）。
        返回成功条数。
        """
        ok = 0
        for item in updates:
            res = self.update_record(app_token, table_id, item["record_id"], item["fields"])
            if res.get("code") == 0:
                ok += 1
            else:
                print(f"  [batch_update] 失败 {item['record_id']}: {res.get('msg')}")
        return ok

    # ── User & Org operations ────────────────────────
    def get_user_info(self, user_id):
        url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}?user_id_type=open_id"
        data = requests.get(url, headers=self._headers()).json()
        if data.get("code") != 0:
            print(f"  [get_user_info] code={data.get('code')} user_id={user_id}")
            return {}
        return data.get("data", {}).get("user", {})

    def get_department_name(self, dept_id):
        url = (f"https://open.feishu.cn/open-apis/contact/v3/departments/{dept_id}"
               f"?department_id_type=open_department_id")
        data = requests.get(url, headers=self._headers()).json()
        if data.get("code") == 0:
            return data.get("data", {}).get("department", {}).get("name", "")
        print(f"  [get_department_name] 失败 dept_id={dept_id}")
        return ""

    def get_bp_user_id(self, app_token: str, t03_table_id: str, bp_name: str) -> str:
        """
        从 T03 配置表中根据 HRBP 姓名查询其飞书 open_id (人员ID)。
        找不到时返回空字符串。
        """
        records = self.list_records(app_token, t03_table_id)
        for rec in records:
            fields = rec.get("fields", {})
            name_val = fields.get("HRBP", "")
            if isinstance(name_val, list):
                name_val = "".join(v.get("text", "") if isinstance(v, dict) else str(v) for v in name_val)
            if bp_name in str(name_val):
                uid = fields.get("人员ID", "")
                if isinstance(uid, list):
                    uid = uid[0] if uid else ""
                return str(uid)
        return ""

    # ── IM operations ────────────────────────────────
    def get_chat_members(self, chat_id):
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members?member_id_type=open_id"
        res = requests.get(url, headers=self._headers())
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
        return []

    def get_chat_name(self, chat_id):
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}"
        data = requests.get(url, headers=self._headers()).json()
        if data.get("code") == 0:
            return data.get("data", {}).get("name", "")
        print(f"  [get_chat_name] 失败 chat_id={chat_id}")
        return ""

    def send_message(self, receive_id: str, receive_id_type: str, content: str) -> dict:
        """发送文本消息给用户 (open_id) 或群 (chat_id)。"""
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content}),
        }
        return requests.post(url, headers=self._headers(), json=payload).json()
