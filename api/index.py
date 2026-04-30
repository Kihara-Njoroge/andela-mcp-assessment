import logging
import os
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import ChatAgent

load_dotenv()
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

agent: ChatAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    if OPENAI_API_KEY:
        agent = ChatAgent(openai_api_key=OPENAI_API_KEY)
        try:
            await agent.ensure_tools_loaded()
            logger.info("MCP tools loaded at startup")
        except Exception as e:
            logger.warning("Failed to pre-load MCP tools: %s", e)
    yield


app = FastAPI(
    title="Meridian Electronics Support API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


class HealthResponse(BaseModel):
    status: str
    mcp_tools: int


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    tool_count = len(agent._openai_tools) if agent and agent._openai_tools else 0
    return HealthResponse(status="healthy", mcp_tools=tool_count)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    if not agent:
        agent = ChatAgent(openai_api_key=OPENAI_API_KEY)

    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = await agent.chat(messages)
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.error("Chat error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)
