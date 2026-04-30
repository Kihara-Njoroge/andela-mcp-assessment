"""
MCP Client for Meridian Electronics Order Server.

Connects to the MCP server via Streamable HTTP transport,
discovers tools dynamically, and provides a clean interface
for the agent to call them.
"""

import json
import httpx
from typing import Any
import os

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL", "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class MCPClient:
    """Stateless MCP client using JSON-RPC over HTTP."""

    def __init__(self, server_url: str = MCP_SERVER_URL):
        self.server_url = server_url
        self._tools: list[dict] | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _rpc_call(self, method: str, params: dict | None = None) -> dict:
        """Make a JSON-RPC call to the MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.server_url,
                json=payload,
                headers=HEADERS,
            )
            response.raise_for_status()

            # Handle SSE responses
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse(response.text)

            return response.json()

    def _parse_sse(self, text: str) -> dict:
        """Parse Server-Sent Events response to extract JSON-RPC result."""
        for line in text.strip().split("\n"):
            if line.startswith("data:"):
                data = line[5:].strip()
                if data:
                    return json.loads(data)
        raise ValueError(f"No valid data found in SSE response: {text}")

    async def initialize(self) -> dict:
        """Initialize the MCP connection."""
        result = await self._rpc_call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "meridian-chatbot", "version": "1.0.0"},
            },
        )
        return result

    async def list_tools(self) -> list[dict]:
        """Discover available tools from the MCP server."""
        if self._tools is not None:
            return self._tools

        result = await self._rpc_call("tools/list")
        self._tools = result.get("result", {}).get("tools", [])
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Call a specific tool on the MCP server.

        Args:
            tool_name: Name of the MCP tool (e.g., 'list_products')
            arguments: Tool arguments as a dictionary

        Returns:
            The tool result as a string
        """
        result = await self._rpc_call(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )

        # Extract the result content
        tool_result = result.get("result", {})

        # Handle different response formats
        if isinstance(tool_result, dict):
            # Check for content array (standard MCP format)
            content = tool_result.get("content", [])
            if content:
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item["text"])
                if texts:
                    return "\n".join(texts)

            # Check for direct result field
            if "result" in tool_result:
                return str(tool_result["result"])

        return json.dumps(tool_result, indent=2)

    def get_openai_tools(self, mcp_tools: list[dict]) -> list[dict]:
        """Convert MCP tool definitions to OpenAI function calling format.

        Args:
            mcp_tools: List of MCP tool definitions

        Returns:
            List of OpenAI-compatible tool definitions
        """
        openai_tools = []
        for tool in mcp_tools:
            schema = tool.get("inputSchema", {})
            # Clean up the schema for OpenAI — remove 'title' fields
            properties = {}
            required = schema.get("required", [])

            for prop_name, prop_def in schema.get("properties", {}).items():
                clean_prop = {}
                # Handle anyOf with null (optional params)
                if "anyOf" in prop_def:
                    types = [t for t in prop_def["anyOf"] if t.get("type") != "null"]
                    if types:
                        clean_prop["type"] = types[0].get("type", "string")
                    else:
                        clean_prop["type"] = "string"
                elif "type" in prop_def:
                    clean_prop["type"] = prop_def["type"]
                else:
                    clean_prop["type"] = "string"

                # Handle array items
                if clean_prop["type"] == "array" and "items" in prop_def:
                    clean_prop["items"] = prop_def["items"]

                if "description" in prop_def:
                    clean_prop["description"] = prop_def["description"]

                properties[prop_name] = clean_prop

            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
            )

        return openai_tools
