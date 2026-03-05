from core.bitable import BitableClient
import yaml

with open("configs/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# The bot is already updated in config.yaml to 'cli_a92832259935dbc7' (Little Q)
b = BitableClient()
msg = "🔔 【填写提醒】你好！周报填写提交通道已开启。\n📢 请注意：今天晚上七点将准时开始周会，快点准备一下吧！"
res = b.send_message("ou_2a554ef88c79b71726d494e9852faa66", "open_id", msg)
print("Push result:", res)
