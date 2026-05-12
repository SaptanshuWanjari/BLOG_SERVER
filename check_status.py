import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

DRAFT_ID = "def3499e-0684-4af3-b2ce-62ea6b6a100a"

def check_status():
    print(f"Checking draft {DRAFT_ID}...")
    draft = supabase.table("blog_drafts").select("*").eq("id", DRAFT_ID).execute()
    if draft.data:
        print(f"Draft still exists: {draft.data[0]['title']}")
    else:
        print("Draft NOT found.")

    print("\nChecking blogs...")
    blogs = supabase.table("blogs").select("*").ilike("title", "%Cache Eviction%").execute()
    if blogs.data:
        for b in blogs.data:
            print(f"Found blog: {b['title']} (ID: {b['id']})")
            print(f"Image URL: {b['image_url']}")
    else:
        print("No matching blog found.")

if __name__ == "__main__":
    check_status()
