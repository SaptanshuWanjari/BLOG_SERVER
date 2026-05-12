import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Direct image link for CAP Theorem from your dataset
VALID_IMAGE_URL = "https://substackcdn.com/image/fetch/$s_!WfFu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bcceca2-48a3-4c21-ac72-9179ef8474e5_1200x750.jpeg"

def fix_blog_image():
    # Find the blog by title
    title = "Navigating the CAP Theorem: A Deep Dive into Distributed System Design"
    response = supabase.table("blogs").select("id").eq("title", title).execute()
    
    if response.data:
        blog_id = response.data[0]["id"]
        print(f"Found blog ID: {blog_id}. Updating image...")
        
        update_res = supabase.table("blogs").update({"image_url": VALID_IMAGE_URL}).eq("id", blog_id).execute()
        print("Success! Image updated.")
    else:
        print("Blog not found.")

if __name__ == "__main__":
    fix_blog_image()
