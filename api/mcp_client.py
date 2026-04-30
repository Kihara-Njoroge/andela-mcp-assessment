import json
import os
from typing import Any

import httpx

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL", "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
)

RPC_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class MCPClient:
    """Stateless MCP client using JSON-RPC over Streamable HTTP."""

    def __init__(self, server_url: str = MCP_SERVER_URL):
        self.server_url = server_url
        self._tools: list[dict] | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _rpc_call(self, method: str, params: dict | None = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.server_url, json=payload, headers=RPC_HEADERS
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse(response.text)
            return response.json()

    def _parse_sse(self, text: str) -> dict:
        for line in text.strip().split("\n"):
            if line.startswith("data:"):
                data = line[5:].strip()
                if data:
                    return json.loads(data)
        raise ValueError(f"No valid data in SSE response: {text[:200]}")

    async def initialize(self) -> dict:
        return await self._rpc_call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "meridian-chatbot", "version": "1.0.0"},
            },
        )

    async def list_tools(self) -> list[dict]:
        if self._tools is not None:
            return self._tools
        result = await self._rpc_call("tools/list")
        self._tools = result.get("result", {}).get("tools", [])
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        result = await self._rpc_call(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )
        tool_result = result.get("result", {})

        if isinstance(tool_result, dict):
            content = tool_result.get("content", [])
            if content:
                texts = [
                    item["text"]
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)

            if "result" in tool_result:
                return str(tool_result["result"])

        return json.dumps(tool_result, indent=2)

    def convert_to_openai_tools(self, mcp_tools: list[dict]) -> list[dict]:
        openai_tools = []
        for tool in mcp_tools:
            schema = tool.get("inputSchema", {})
            properties = {}
            required = schema.get("required", [])

            for prop_name, prop_def in schema.get("properties", {}).items():
                clean_prop: dict[str, Any] = {}

                if "anyOf" in prop_def:
                    non_null = [t for t in prop_def["anyOf"] if t.get("type") != "null"]
                    clean_prop["type"] = (
                        non_null[0].get("type", "string") if non_null else "string"
                    )
                else:
                    clean_prop["type"] = prop_def.get("type", "string")

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
