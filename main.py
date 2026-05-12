import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel

from bot import send_approval_request, send_publication_confirmation
from database import (
    delete_draft,
    format_blog_to_markdown,
    get_draft,
    get_user_id_by_email,
    publish_blog,
    save_draft,
)
from generator import generate_blog, get_random_member, get_random_topic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GDG AI Blog Automation")

# Configuration
BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset" / "content.topic.json"
MEMBERS_PATH = BASE_DIR / "dataset" / "members.json"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBSITE_URL = os.environ.get("WEBSITE_URL")  # Need this to hit the upload API

# Global Fallback Banner (for when dataset or user doesn't provide one)
DEFAULT_BANNER_URL = "https://res.cloudinary.com/dlvkywzol/image/upload/v1778603998/GDG_BLOG_COVERS/file_ndivzj.ico"


class PublishRequest(BaseModel):
    draft_id: str
    banner_url: str


@app.get("/")
def read_root():
    return {"status": "online", "message": "GDG AI Blog Automation Service"}


@app.get("/trigger")
def trigger_generation(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_blog_generation)
    return {"message": "Blog generation started in background."}


def process_blog_generation():
    try:
        logger.info("Background task started")
        topic_item = get_random_topic(DATASET_PATH)
        member = get_random_member(MEMBERS_PATH)

        topic_name = topic_item.get("topic")
        short_desc = " ".join(topic_item.get("content", []))

        logger.info(f"Generating blog for topic: {topic_name} by {member['name']}")
        blog_content = generate_blog(GROQ_API_KEY, topic_name, short_desc)

        # Ensure the title is EXACTLY the topic name from the dataset
        blog_content["title"] = topic_name

        # Add default image from dataset if available

        blog_content["banner_url"] = topic_item.get("image")

        user_id = get_user_id_by_email(member["email"])
        if not user_id:
            logger.error(f"User {member['email']} not found in database.")
            return

        draft = save_draft(user_id, blog_content["title"], blog_content)

        if draft:
            send_approval_request(
                title=blog_content["title"],
                summary=blog_content["executive_summary"],
                draft_id=draft["id"],
                publisher_name=member["name"],
                default_banner=blog_content["banner_url"],
            )
            logger.info(f"Draft saved and notification sent. Draft ID: {draft['id']}")

    except Exception as e:
        logger.error(f"Error in process_blog_generation: {e}", exc_info=True)


@app.post("/publish")
def publish_to_site(req: PublishRequest):
    return execute_publish(req.draft_id, req.banner_url)


def execute_publish(draft_id: str, banner_url: str = None):
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Priority: 1. Manual Link, 2. Draft's saved banner, 3. Global Default
    final_banner_url = banner_url or draft["content_json"].get("banner_url") or DEFAULT_BANNER_URL

    logger.info(f"Publishing draft {draft_id} with banner: {final_banner_url}")

    markdown = format_blog_to_markdown(draft["content_json"])

    try:
        result = publish_blog(
            writer_id=draft["writer_id"],
            title=draft["title"],
            markdown=markdown,
            image_url=final_banner_url,
        )
        delete_draft(draft_id)
        return {"message": "Blog published successfully!", "data": result}
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def upload_to_cloudinary(file_content: bytes, filename: str):
    """
    Uploads a file to the website's Cloudinary API route.
    """
    if not WEBSITE_URL:
        logger.error("WEBSITE_URL not set in environment")
        return None

    upload_api_url = f"{WEBSITE_URL.rstrip('/')}/api/upload"

    async with httpx.AsyncClient() as client:
        files = {"file": (filename, file_content, "image/jpeg")}
        data = {"folder": "BLOG_BANNERS"}
        try:
            response = await client.post(
                upload_api_url, files=files, data=data, timeout=30.0
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("url") or result.get("secure_url")
            else:
                logger.error(
                    f"Upload API failed with status {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"Error uploading to Cloudinary API: {e}")
    return None


async def download_telegram_file(file_id: str):
    """
    Downloads a file from Telegram servers.
    """
    async with httpx.AsyncClient() as client:
        # Get file path
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return None

        file_path = resp.json()["result"]["file_path"]

        # Download file
        download_url = (
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        )
        file_resp = await client.get(download_url)
        if file_resp.status_code == 200:
            return file_resp.content
    return None


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Listens for replies in Telegram to publish blogs.
    Supports text commands and photo uploads with captions.
    """
    data = await request.json()
    message = data.get("message")
    if not message:
        return {"status": "ignored"}

    text = message.get("text", "")
    caption = message.get("caption", "")
    photo = message.get("photo")
    reply_to = message.get("reply_to_message")

    # Command can be in text or caption
    cmd_text = (text if text else caption).strip()

    logger.info(
        f"Webhook received: text='{text}', caption='{caption}', has_photo={bool(photo)}, has_reply={bool(reply_to)}"
    )

    if cmd_text.upper().startswith("PUBLISH BLOG"):
        parts = cmd_text.split()
        if len(parts) >= 3:
            draft_id = parts[2]
            banner_url = parts[3] if len(parts) >= 4 else None
            chat_id = message["chat"]["id"]

            # If no photo in current message, check if it's a reply to a message with a photo
            if not photo and reply_to:
                photo = reply_to.get("photo")
                if photo:
                    logger.info(
                        f"Using photo from replied-to message for draft {draft_id}"
                    )

            # Case 1: Photo available (in message or reply) but no URL provided
            if photo and not banner_url:
                logger.info(f"Telegram trigger: Photo detected for draft {draft_id}")
                # Get largest photo
                file_id = photo[-1]["file_id"]
                file_content = await download_telegram_file(file_id)
                if file_content:
                    banner_url = await upload_to_cloudinary(
                        file_content, f"banner_{draft_id}.jpg"
                    )

            # Case 2: Link provided in command, photo upload successful, OR default available in draft
            if banner_url or not photo:
                logger.info(f"Telegram trigger: Attempting to publish draft {draft_id}")
                try:
                    # execute_publish will handle the fallback to draft's default banner
                    result = execute_publish(draft_id, banner_url)

                    # Get title and used banner from the draft (before it was deleted) or result
                    # Since execute_publish deletes the draft, we can get info from result or just pass what we have
                    draft_title = "Blog Post"  # Fallback
                    if result and "data" in result and len(result["data"]) > 0:
                        draft_title = result["data"][0].get("title", draft_title)
                        final_banner = result["data"][0].get("image_url", banner_url)
                    else:
                        final_banner = banner_url

                    send_publication_confirmation(chat_id, draft_title, final_banner)
                    return {"status": "success"}
                except Exception as e:
                    logger.error(f"Webhook publish failed: {e}")
            else:
                logger.error(
                    f"No banner URL found for draft {draft_id} and no photo available."
                )

    return {"status": "ignored"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
