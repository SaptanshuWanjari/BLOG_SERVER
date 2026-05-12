import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for write access
supabase: Client = create_client(url, key)

def get_user_id_by_email(email: str):
    """
    Finds a user by email in the users table.
    """
    response = supabase.table("users").select("id").eq("email", email).execute()
    if response.data:
        return response.data[0]["id"]
    return None

def publish_blog(writer_id: str, title: str, markdown: str, image_url: str):
    """
    Inserts a new blog post into the blogs table.
    """
    data = {
        "writer_id": writer_id,
        "title": title,
        "markdown": markdown,
        "image_url": image_url,
        "likes_count": 0
    }
    response = supabase.table("blogs").insert(data).execute()
    return response.data

def save_draft(writer_id: str, title: str, content_json: dict):
    """
    Saves a generated blog as a draft.
    Note: Requires a 'blog_drafts' table in Supabase.
    """
    data = {
        "writer_id": writer_id,
        "title": title,
        "content_json": content_json
    }
    response = supabase.table("blog_drafts").insert(data).execute()
    return response.data[0] if response.data else None

def get_draft(draft_id: str):
    """
    Retrieves a draft by ID.
    """
    response = supabase.table("blog_drafts").select("*").eq("id", draft_id).execute()
    return response.data[0] if response.data else None

def delete_draft(draft_id: str):
    """
    Deletes a draft after publishing.
    """
    supabase.table("blog_drafts").delete().eq("id", draft_id).execute()

def format_blog_to_markdown(blog_data: dict) -> str:
    """
    Converts structured blog JSON into a single Markdown string.
    """
    md = f"{blog_data.get('executive_summary', '')}\n\n"
    
    sections = [
        ("Background", "background"),
        ("Core Concepts", "core_concepts"),
        ("Architecture Deep Dive", "architecture_deep_dive"),
        ("How It Works", "how_it_works"),
    ]
    
    for title, key in sections:
        content = blog_data.get(key)
        if content:
            md += f"## {title}\n{content}\n\n"
            
    # Implementation Guide
    impl = blog_data.get("implementation_guide", {})
    if impl:
        md += f"## Implementation Guide\n{impl.get('overview', '')}\n\n"
        for example in impl.get("code_examples", []):
            md += f"### {example.get('title', '')}\n"
            md += f"```{example.get('language', 'text')}\n{example.get('code', '')}\n```\n"
            md += f"{example.get('explanation', '')}\n\n"
            
    more_sections = [
        ("Performance and Scalability", "performance_and_scalability"),
        ("Security and Reliability", "security_and_reliability"),
        ("Common Pitfalls", "common_pitfalls"),
        ("Real-World Use Cases", "real_world_use_cases"),
        ("Future Trends", "future_trends"),
    ]
    
    for title, key in more_sections:
        content = blog_data.get(key)
        if content:
            md += f"## {title}\n{content}\n\n"
            
    # Key Takeaways
    takeaways = blog_data.get("key_takeaways", [])
    if takeaways:
        md += "## Key Takeaways\n"
        for item in takeaways:
            md += f"- {item}\n"
            
    return md
