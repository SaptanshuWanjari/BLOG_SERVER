import logging
import random
import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from prompts import blog_prompt_template

logger = logging.getLogger(__name__)

# Re-defining models for structured output
class CodeExample(BaseModel):
    title: str
    language: str
    code: str
    explanation: str

class ImplementationGuide(BaseModel):
    overview: str
    code_examples: List[CodeExample]

class BlogContent(BaseModel):
    title: str
    executive_summary: str
    background: str
    core_concepts: str
    architecture_deep_dive: str
    how_it_works: str
    implementation_guide: ImplementationGuide
    performance_and_scalability: str
    security_and_reliability: str
    common_pitfalls: str
    real_world_use_cases: str
    future_trends: str
    key_takeaways: List[str]

def generate_blog(groq_api_key: str, topic: str, short_desc: str) -> dict:
    # Using Llama 3.3 70B Versatile (Replacement for deprecated 3.0 series)
    llm = ChatGroq(
        model="llama-3.3-70b-versatile", 
        groq_api_key=groq_api_key,
        temperature=0.3
    )
    structured_llm = llm.with_structured_output(BlogContent)

    chain = blog_prompt_template | structured_llm
    
    response = chain.invoke({"topic": topic, "short_desc": short_desc})
    return response.model_dump()

def get_random_topic(dataset_path: str):
    with open(dataset_path, 'r') as f:
        dataset = json.load(f)
    
    # Flatten all topics from all categories
    all_topics = []
    for category in dataset:
        for topic in category.get("topics", []):
            all_topics.append(topic)
            
    return random.choice(all_topics)

def get_random_member(members_path: str):
    with open(members_path, 'r') as f:
        members = json.load(f)
    return random.choice(members)
