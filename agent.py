import os
import logging
import requests
import json
from datetime import datetime
from google.cloud import firestore
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = firestore.Client()
model_name = os.getenv("MODEL", "gemini-2.0-flash")

# MCP Tool 1: Filesystem - Save notes to file
def mcp_filesystem_save(topic: str, content: str) -> dict:
    """MCP Filesystem tool - saves study notes to file"""
    try:
        os.makedirs("/tmp/study_notes", exist_ok=True)
        filename = f"/tmp/study_notes/{topic.replace(' ', '_')}.md"
        with open(filename, 'w') as f:
            f.write(content)
        return {"status": "success", "file": filename, "message": f"Notes saved to {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# MCP Tool 2: Fetch - Web content fetcher
def mcp_fetch_content(url: str) -> dict:
    """MCP Fetch tool - fetches content from web URLs"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        return {"status": "success", "content": response.text[:2000], "url": url}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Tool 3: Wikipedia research
def research_topic(topic: str) -> dict:
    """Research a topic using Wikipedia"""
    try:
        import wikipedia
        results = wikipedia.search(topic, results=3)
        if not results:
            return {"status": "error", "message": "No results found"}
        page = wikipedia.page(results[0])
        summary = wikipedia.summary(topic, sentences=10)
        return {"status": "success", "title": page.title, "summary": summary, "url": page.url}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Tool 4: Save to Firestore
def save_to_firestore(topic: str, notes: str, schedule: str) -> dict:
    """Save study session to Firestore database"""
    try:
        doc_ref = db.collection("study_sessions").document(topic.replace(" ", "_").lower())
        doc_ref.set({
            "topic": topic,
            "notes": notes,
            "schedule": schedule,
            "status": "active",
            "created_at": datetime.now()
        })
        return {"status": "success", "message": f"Saved to Firestore: {topic}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Tool 5: Get saved notes
def get_saved_notes(topic: str) -> dict:
    """Retrieve saved notes from Firestore"""
    try:
        doc_ref = db.collection("study_sessions").document(topic.replace(" ", "_").lower())
        doc = doc_ref.get()
        if doc.exists:
            return {"status": "success", "data": doc.to_dict()}
        return {"status": "not_found", "message": f"No notes found for {topic}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

root_agent = Agent(
    name="study_assistant",
    model=model_name,
    description="AI Study Assistant with MCP tools for research, notes, and scheduling",
    instruction="""You are a friendly Study Assistant with MCP-powered tools.

When a user wants to study a topic:
1. Use research_topic() to get Wikipedia information
2. Create detailed study notes from the research
3. Use mcp_filesystem_save() to save notes as a file (MCP Filesystem tool)
4. Create a 7-day study schedule
5. Use save_to_firestore() to save everything to database
6. For extra research, use mcp_fetch_content() with Wikipedia URL (MCP Fetch tool)
7. Show the user a summary with notes and schedule

Always mention when MCP tools are being used.""",
    tools=[research_topic, mcp_filesystem_save, mcp_fetch_content, save_to_firestore, get_saved_notes]
)
