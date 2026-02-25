import requests
import json
import yaml
import os

class BitableClient:
    def __init__(self, config_path="configs/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.app_id = self.config['lark']['app_id']
        self.app_secret = self.config['lark']['app_secret']
        self.tenant_access_token = ""

    def get_token(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            self.tenant_access_token = res.json().get("tenant_access_token")
            return self.tenant_access_token
        else:
            raise Exception(f"Failed to get token: {res.text}")

    def create_table(self, app_token, table_name):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"table": {"name": table_name}}
        res = requests.post(url, headers=headers, json=payload)
        data = res.json()
        
        if res.status_code == 200:
            if data.get("code") == 0:
                return data.get("data", {}).get("table_id")
            elif data.get("code") == 1254013: # TableNameDuplicated
                print(f"Table '{table_name}' already exists. Fetching ID...")
                # Fetch table list
                res_list = requests.get(url, headers=headers)
                list_data = res_list.json()
                for item in list_data.get("data", {}).get("items", []):
                    if item['name'] == table_name:
                        return item['table_id']
            else:
                print(f"Error creating table '{table_name}': {data.get('code')} - {data.get('msg')}")
        else:
            print(f"HTTP Error {res.status_code} creating table '{table_name}': {res.text}")
        return None

    def create_field(self, app_token, table_id, field_name, ui_type, description="", property_obj=None):
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "field_name": field_name,
            "type": ui_type
        }
        if property_obj:
            payload["property"] = property_obj
            
        res = requests.post(url, headers=headers, json=payload)
        data = res.json()
        if res.status_code == 200:
            if data.get("code") == 0:
                return data.get("data", {}).get("field", {}).get("field_id")
            else:
                # Log detailed error
                print(f"Error creating field '{field_name}' (Type {ui_type}): {data.get('code')} - {data.get('msg')}")
                if "error" in data:
                    print(f"  Details: {json.dumps(data.get('error'))}")
        else:
            print(f"HTTP Error {res.status_code} creating field '{field_name}': {res.text}")
        return None

    def get_user_info(self, user_id):
        """
        获取用户信息
        API: GET /open-apis/contact/v3/users/{user_id}?user_id_type=open_id
        返回字段包含: name, job_title, department_ids 等
        注意: department_name 不是标准字段，需另外查询部门名称
        """
        url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}?user_id_type=open_id"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get("code") != 0:
            print(f"  [get_user_info] 失败 code={data.get('code')} msg={data.get('msg')} user_id={user_id}")
            return {}
        user = data.get("data", {}).get("user", {})
        return user

    def get_department_name(self, dept_id):
        """
        通过部门 ID 获取部门名称
        API: GET /open-apis/contact/v3/departments/{department_id}?department_id_type=open_department_id
        注意: department_ids 中存的是 open_department_id （od- 开头）
        """
        url = f"https://open.feishu.cn/open-apis/contact/v3/departments/{dept_id}?department_id_type=open_department_id"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        res = requests.get(url, headers=headers)
        data = res.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("department", {}).get("name", "")
        print(f"  [get_department_name] 失败 dept_id={dept_id} code={data.get('code')} msg={data.get('msg')}")
        return ""

    def update_record(self, app_token, table_id, record_id, fields):
        """
        更新多维表记录
        API: PUT /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}
        """
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"fields": fields}
        res = requests.put(url, headers=headers, json=payload)
        return res.json()

    def list_records(self, app_token, table_id, filter_str=""):
        """
        列出多维表记录
        """
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        if filter_str:
            url += f"?filter={filter_str}"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        res = requests.get(url, headers=headers)
        return res.json().get("data", {}).get("items", [])

    def create_record(self, app_token, table_id, fields):
        """
        新增多维表记录
        """
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {"fields": fields}
        res = requests.post(url, headers=headers, json=payload)
        return res.json()

    def get_chat_members(self, chat_id):
        """
        获取群成员列表
        API: GET /open-apis/im/v1/chats/:chat_id/members?member_id_type=open_id
        """
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members?member_id_type=open_id"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("data", {}).get("items", [])
        return []

    def send_message(self, receive_id, receive_id_type, content):
        """
        发送消息给用户或群
        """
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
        res = requests.post(url, headers=headers, json=payload)
        return res.json()
