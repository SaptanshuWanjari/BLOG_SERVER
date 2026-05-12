import os
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from generator import get_random_topic, get_random_member, generate_blog
from database import get_user_id_by_email, save_draft, get_draft, publish_blog, format_blog_to_markdown, delete_draft
from bot import send_approval_request
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GDG AI Blog Automation")

from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset" / "content.topic.json"
MEMBERS_PATH = BASE_DIR / "dataset" / "members.json"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")



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
        
        user_id = get_user_id_by_email(member["email"])
        if not user_id:
            logger.error(f"User {member['email']} not found in database.")
            return

        draft = save_draft(user_id, blog_content["title"], blog_content)
        
        if draft:
            send_approval_request(
                title=blog_content["title"],
                summary=blog_content["executive_summary"],
                draft_id=draft["id"]
            )
            logger.info(f"Draft saved and notification sent. Draft ID: {draft['id']}")
            
    except Exception as e:
        logger.error(f"Error in process_blog_generation: {e}", exc_info=True)

@app.post("/publish")
def publish_to_site(req: PublishRequest):
    return execute_publish(req.draft_id, req.banner_url)

def execute_publish(draft_id: str, banner_url: str):
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    markdown = format_blog_to_markdown(draft["content_json"])
    
    try:
        result = publish_blog(
            writer_id=draft["writer_id"],
            title=draft["title"],
            markdown=markdown,
            image_url=banner_url
        )
        delete_draft(draft_id)
        return {"message": "Blog published successfully!", "data": result}
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Listens for replies in Telegram to publish blogs.
    Expected pattern: PUBLISH BLOG [DraftID] [BannerURL]
    """
    data = await request.json()
    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"].strip()
        if text.upper().startswith("PUBLISH BLOG"):
            parts = text.split()
            if len(parts) >= 4:
                draft_id = parts[2]
                banner_url = parts[3]
                logger.info(f"Telegram trigger: Publishing draft {draft_id}")
                try:
                    execute_publish(draft_id, banner_url)
                    return {"status": "success"}
                except Exception as e:
                    logger.error(f"Webhook publish failed: {e}")
    return {"status": "ignored"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
