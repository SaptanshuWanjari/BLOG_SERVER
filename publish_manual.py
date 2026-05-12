import sys
from database import get_draft, publish_blog, format_blog_to_markdown, delete_draft

def manual_publish(draft_id, banner_url):
    print(f"Fetching draft: {draft_id}")
    draft = get_draft(draft_id)
    if not draft:
        print("Error: Draft not found.")
        return

    print(f"Formatting blog: {draft['title']}")
    markdown = format_blog_to_markdown(draft["content_json"])

    print("Publishing to Supabase...")
    try:
        result = publish_blog(
            writer_id=draft["writer_id"],
            title=draft["title"],
            markdown=markdown,
            image_url=banner_url
        )
        print("Success! Blog published.")
        
        print("Cleaning up draft...")
        delete_draft(draft_id)
        print("Done.")
    except Exception as e:
        print(f"Failed to publish: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python publish_manual.py [draft_id] [banner_url]")
    else:
        manual_publish(sys.argv[1], sys.argv[2])
