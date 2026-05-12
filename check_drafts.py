import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

try:
    response = supabase.table("blog_drafts").select("*").execute()
    print(f"Drafts found: {len(response.data)}")
    for d in response.data:
        print(f"ID: {d['id']}, Title: {d['title']}")
except Exception as e:
    print(f"Error checking drafts: {e}")
