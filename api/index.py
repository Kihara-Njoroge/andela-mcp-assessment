import logging
import os
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from agent import ChatAgent

load_dotenv()
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MAX_MESSAGE_LENGTH = 2000
MAX_MESSAGES_PER_REQUEST = 50

agent: ChatAgent | None = None
limiter = Limiter(key_func=get_remote_address)


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

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please wait before sending another message."
        },
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

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant", "system"):
            raise ValueError(
                f"Invalid role: {v}. Must be 'user', 'assistant', or 'system'."
            )
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message content cannot be empty.")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message content exceeds {MAX_MESSAGE_LENGTH} characters."
            )
        return v


class ChatRequest(BaseModel):
    messages: list[Message]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list[Message]) -> list[Message]:
        if not v:
            raise ValueError("Messages array cannot be empty.")
        if len(v) > MAX_MESSAGES_PER_REQUEST:
            raise ValueError(
                f"Too many messages. Maximum is {MAX_MESSAGES_PER_REQUEST}."
            )
        return v


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
@limiter.limit("10/minute")
async def chat(request: ChatRequest, http_request: Request):
    global agent

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    if not agent:
        agent = ChatAgent(openai_api_key=OPENAI_API_KEY)

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
