"""Sends the chat id to the user on Telegram (never printed to logs)."""
import os, json, urllib.request, urllib.parse, urllib.error
from advisor.tg import token
tok = token()
print("token found:", bool(tok), "| length:", len(tok))
if not tok:
    print("No valid token in secret TELEGRAM_BOT_TOKEN."); raise SystemExit(1)
def call(m, data=None):
    try:
        return json.loads(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}", data, timeout=20).read())
    except urllib.error.HTTPError as e:
        print(f"Telegram API error on {m}: HTTP {e.code}", "(token is wrong or revoked)" if e.code in (401, 404) else "")
        raise SystemExit(1)
ups = call("getUpdates")["result"]
print("updates received:", len(ups))
chats = {u["message"]["chat"]["id"] for u in ups if "message" in u}
if not chats:
    print("No messages found: open the bot in Telegram, send it any message (e.g. hello), then rerun.")
    raise SystemExit(1)
for cid in chats:
    call("sendMessage", urllib.parse.urlencode({"chat_id": cid, "text": f"Your chat id: {cid}\nSave it as GitHub secret TELEGRAM_CHAT_ID."}).encode())
print("Sent chat id to Telegram.")
