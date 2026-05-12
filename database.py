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

def clean_content(content: str, heading_to_remove: str) -> str:
    """
    Removes the main heading from the content if the AI included it,
    to avoid double-headings in the final markdown.
    """
    if not content:
        return ""
    
    content = content.strip()
    # Remove variations like "# Heading", "## Heading", "**Heading**"
    lines = content.split('\n')
    if lines:
        first_line = lines[0].strip().lower()
        target = heading_to_remove.lower()
        
        # Check if first line is a heading or bold version of the title
        is_redundant = (
            first_line == target or 
            first_line == f"## {target}" or 
            first_line == f"### {target}" or
            first_line == f"**{target}**" or
            first_line.startswith(f"## {target}") or
            first_line.startswith(f"### {target}")
        )
        
        if is_redundant:
            return '\n'.join(lines[1:]).strip()
            
    return content

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
            cleaned = clean_content(content, title)
            md += f"## {title}\n{cleaned}\n\n"
            
    # Implementation Guide
    impl = blog_data.get("implementation_guide", {})
    if impl:
        md += f"## Implementation Guide\n"
        overview = clean_content(impl.get('overview', ''), "Implementation Guide")
        if overview:
            md += f"{overview}\n\n"
            
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
            cleaned = clean_content(content, title)
            md += f"## {title}\n{cleaned}\n\n"
            
    # Key Takeaways
    takeaways = blog_data.get("key_takeaways", [])
    if takeaways:
        md += "## Key Takeaways\n"
        for item in takeaways:
            md += f"- {item}\n"
            
    return md
