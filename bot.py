import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_approval_request(title: str, summary: str, draft_id: str, publisher_name: str, default_banner: str = None):
    """
    Sends a message to Discord/Telegram with the blog summary and instructions.
    """
    banner_info = f"\n🖼️ **Default Banner:** {default_banner}" if default_banner else ""
    
    message = (
        f"🚀 **New AI Blog Draft Ready!**\n\n"
        f"👤 **Publisher:** {publisher_name}\n"
        f"📝 **Title:** {title}\n"
        f"🆔 **Draft ID:** `{draft_id}`{banner_info}\n\n"
        f"📖 **Executive Summary:**\n{summary[:600]}...\n\n"
        f"✅ **To publish, either:**\n"
        f"1. Reply with `PUBLISH BLOG {draft_id}` (uses default banner)\n"
        f"2. Reply with `PUBLISH BLOG {draft_id} [BANNER_URL]`\n"
        f"3. **Upload an image** with the caption `PUBLISH BLOG {draft_id}`\n"
        f"4. **Reply to an image** with `PUBLISH BLOG {draft_id}`"
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

def send_publication_confirmation(chat_id: str, title: str, banner_url: str, blog_url: str = None):
    """
    Sends a confirmation message with the banner image to Telegram.
    Falls back to text-only if image sending fails.
    """
    if not TELEGRAM_BOT_TOKEN:
        return

    caption = f"✅ **Blog Published Successfully!**\n\n📝 **Title:** {title}"
    if blog_url:
        caption += f"\n🔗 [Read Blog]({blog_url})"

    try:
        with httpx.Client() as client:
            # Try sending with photo first
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            resp = client.post(photo_url, json={
                "chat_id": chat_id,
                "photo": banner_url,
                "caption": caption,
                "parse_mode": "Markdown"
            })
            
            # If photo fails (e.g. .ico format), fallback to plain message
            if resp.status_code != 200:
                print(f"Telegram sendPhoto failed ({resp.status_code}), falling back to sendMessage")
                msg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                client.post(msg_url, json={
                    "chat_id": chat_id,
                    "text": caption,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                })
    except Exception as e:
        print(f"Telegram confirmation failed: {e}")
