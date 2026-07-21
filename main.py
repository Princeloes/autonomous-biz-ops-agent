import os
import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from config import settings
from core.agent import AutonomousAgentSystem, AgentState
from core.memory import MemoryManager
from tools.email_tool import _load_mailbox, _save_mailbox
from tools.calendar_tool import _load_calendar, _save_calendar

app = FastAPI(title="Autonomous Business Operations Agent API")

# Initialize the Agent System and Memory
agent_system = AutonomousAgentSystem()
memory_manager = MemoryManager()

# Mount static files folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Data models
class RunRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "default_user"

class MemoryRequest(BaseModel):
    text: str
    user_id: Optional[str] = "default_user"

# API Routes
@app.get("/api/config")
async def get_config():
    return {
        "model_name": settings.OPENAI_MODEL_NAME,
        "is_mock_mode": settings.is_mock_mode,
        "langfuse_configured": bool(settings.LANGFUSE_PUBLIC_KEY),
        "mem0_configured": bool(settings.MEM0_API_KEY)
    }

@app.post("/api/run")
async def run_agent(request: RunRequest):
    """Runs the agent and streams the progress via Server-Sent Events (SSE)."""
    async def event_generator():
        # Initialize state
        state = {
            "messages": [("user", request.prompt)],
            "plan": [],
            "current_step": 0,
            "user_id": request.user_id,
            "execution_logs": [f"Initializing execution for user '{request.user_id}'..."]
        }
        
        try:
            # We run the LangGraph async stream
            async for output in agent_system.app.astream(state):
                # output is a dict like {'node_name': {state_keys: values}}
                node_name = list(output.keys())[0]
                node_output = output[node_name]
                
                # Extract relevant updates
                plan = node_output.get("plan", [])
                current_step = node_output.get("current_step", 0)
                logs = node_output.get("execution_logs", [])
                messages = node_output.get("messages", [])
                
                new_logs = logs[len(state["execution_logs"]):] if logs else []
                state["execution_logs"] = logs
                if plan:
                    state["plan"] = plan
                state["current_step"] = current_step
                
                yield f"data: {json.dumps({'node': node_name, 'plan': plan, 'current_step': current_step, 'logs': new_logs})}\n\n"
                await asyncio.sleep(0.5) # Smooth streaming flow
                
            # Yield final completion event
            yield f"data: {json.dumps({'status': 'completed', 'message': 'Agent execution successfully completed.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Error during execution: {str(e)}'})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/memories")
async def get_memories(user_id: str = "default_user"):
    return memory_manager.get_all_memories(user_id)

@app.post("/api/memories")
async def add_memory(request: MemoryRequest):
    mem_id = memory_manager.add_memory(request.user_id, request.text)
    return {"status": "success", "id": mem_id}

@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    memory_manager.delete_memory(memory_id)
    return {"status": "success"}

@app.get("/api/mailbox")
async def get_mailbox():
    return _load_mailbox()

@app.get("/api/calendar")
async def get_calendar():
    return _load_calendar()

@app.get("/api/reports")
async def get_reports():
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    if not os.path.exists(reports_dir):
        return []
    reports = []
    for filename in os.listdir(reports_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(reports_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            reports.append({
                "filename": filename,
                "path": filepath,
                "content": content
            })
    return reports

# SPA Fallback (Must be mounted last)
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

# Mount remaining static files at /static
app.mount("/static", StaticFiles(directory=static_dir), name="static")
