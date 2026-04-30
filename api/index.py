try:
    import os
    from contextlib import asynccontextmanager
    from dotenv import load_dotenv
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    from agent import ChatAgent

    load_dotenv()

    # --- Configuration ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # --- Global agent instance ---
    agent: ChatAgent | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize the agent on startup for local dev/long-running processes."""
        global agent
        if OPENAI_API_KEY:
            agent = ChatAgent(openai_api_key=OPENAI_API_KEY)
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
        tool_count = 0
        if agent and agent._openai_tools:
            tool_count = len(agent._openai_tools)
        return HealthResponse(status="healthy", mcp_tools=tool_count)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        global agent
        
        if not OPENAI_API_KEY:
            raise HTTPException(
                status_code=500, 
                detail="OPENAI_API_KEY missing from Vercel Environment Variables. Please add it in project settings and redeploy."
            )

        if not agent:
            # Lazy initialization
            agent = ChatAgent(openai_api_key=OPENAI_API_KEY)

        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages array cannot be empty")

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        try:
            reply = await agent.chat(messages)
            return ChatResponse(reply=reply)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Chat error:\n{error_trace}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred: {str(e)}\n\nTraceback:\n{error_trace}",
            )

except Exception as e:
    import traceback
    from fastapi import FastAPI, HTTPException
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse

    err_msg = traceback.format_exc()

    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catchall(request: Request, path: str):
        return JSONResponse(
            status_code=500,
            content={"detail": f"Vercel Module Import Crash:\n\n{err_msg}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)
