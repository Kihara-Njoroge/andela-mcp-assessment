# Meridian Electronics Backend

This is the FastAPI backend for the Meridian Electronics Customer Support Chatbot. It provides an API that connects to the Meridian MCP core server and orchestrated responses using the OpenAI (`gpt-4o-mini`) model.

## Setup Instructions

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment and activate it**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Make sure you have a `.env` file in the `backend` directory (copy from `.env.example`) with your keys:
   ```env
   OPENAI_API_KEY=your-openai-api-key
   MCP_SERVER_URL=https://order-mcp-74afyau24q-uc.a.run.app/mcp
   ```

## Running the Server

Run the FastAPI server using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at `http://localhost:8000`. You can check the health endpoint at `http://localhost:8000/api/health` to verify that the MCP tools have been loaded successfully.
