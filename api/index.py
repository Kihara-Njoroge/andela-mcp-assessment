"""
FastAPI server for Meridian Electronics Customer Support Chatbot.

Provides a /api/chat endpoint that accepts conversation messages,
routes them through the AI agent, and returns responses.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import ChatAgent

load_dotenv()

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is required")

# --- Global agent instance ---
agent: ChatAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent on startup."""
    global agent
    agent = ChatAgent(openai_api_key=OPENAI_API_KEY)
    # Pre-load MCP tools at startup for faster first response
    try:
        await agent._ensure_tools_loaded()
        print("✅ MCP tools loaded successfully")
    except Exception as e:
        print(f"⚠️  Failed to pre-load MCP tools: {e}")
    yield


app = FastAPI(
    title="Meridian Electronics Support API",
    description="AI-powered customer support chatbot for Meridian Electronics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---
class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


class HealthResponse(BaseModel):
    status: str
    mcp_tools: int


# --- Routes ---
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — also reports MCP tool count."""
    tool_count = 0
    if agent and agent._openai_tools:
        tool_count = len(agent._openai_tools)
    return HealthResponse(status="healthy", mcp_tools=tool_count)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message through the AI agent.

    Expects the full conversation history (messages array).
    Returns the assistant's reply.
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    # Convert Pydantic models to dicts for the agent
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = await agent.chat(messages)
        return ChatResponse(reply=reply)
    except Exception as e:
        print(f"❌ Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
