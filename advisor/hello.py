"""Sends the chat id to the user on Telegram (never printed to logs)."""
import os, json, urllib.request, urllib.parse
tok = os.environ["TELEGRAM_BOT_TOKEN"]
def call(m, data=None):
    return json.loads(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}", data, timeout=20).read())
ups = call("getUpdates")["result"]
chats = {u["message"]["chat"]["id"] for u in ups if "message" in u}
if not chats: print("No messages found: open the bot in Telegram, press Start, then rerun."); raise SystemExit(1)
for cid in chats:
    call("sendMessage", urllib.parse.urlencode({"chat_id": cid, "text": f"Your chat id: {cid}\nSave it as GitHub secret TELEGRAM_CHAT_ID."}).encode())
print("Sent chat id to Telegram.")
