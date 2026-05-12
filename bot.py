import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_approval_request(title: str, summary: str, draft_id: str, publisher_name: str):
    """
    Sends a message to Discord/Telegram with the blog summary and instructions.
    """
    message = (
        f"🚀 **New AI Blog Draft Ready!**\n\n"
        f"👤 **Publisher:** {publisher_name}\n"
        f"📝 **Title:** {title}\n"
        f"🆔 **Draft ID:** `{draft_id}`\n\n"
        f"📖 **Executive Summary:**\n{summary[:600]}...\n\n"
        f"✅ **To publish, either:**\n"
        f"1. Reply with `PUBLISH BLOG {draft_id} [BANNER_URL]`\n"
        f"2. **Upload an image** with the caption `PUBLISH BLOG {draft_id}`\n"
        f"3. **Reply to an image** with `PUBLISH BLOG {draft_id}`"
    )



    # 1. Send to Discord (Outgoing only)
    if DISCORD_WEBHOOK_URL:
        try:
            with httpx.Client() as client:
                client.post(DISCORD_WEBHOOK_URL, json={"content": message, "username": "GDG Blog Bot"})
        except Exception as e:
            print(f"Discord notify failed: {e}")

    # 2. Send to Telegram (Supports Webhook replies)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            with httpx.Client() as client:
                client.post(url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                })
        except Exception as e:
            print(f"Telegram notify failed: {e}")
