import os, re
def token() -> str:
    """Extract the bot token even if the secret holds extra text around it."""
    m = re.search(r"\d{6,}:[A-Za-z0-9_-]{30,}", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    return m.group(0) if m else ""
def chat_id() -> str:
    m = re.search(r"-?\d+", os.environ.get("TELEGRAM_CHAT_ID", ""))
    return m.group(0) if m else ""
