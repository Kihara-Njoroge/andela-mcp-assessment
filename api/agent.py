import json

from openai import AsyncOpenAI

from mcp_client import MCPClient

SYSTEM_PROMPT = """You are Meridian Support, the AI customer support assistant for Meridian Electronics — a company that sells computer products including monitors, keyboards, printers, networking gear, and accessories.

## Capabilities
1. Product Browsing — Search products, browse by category, get detailed product info
2. Customer Authentication — Verify customers using their email and 4-digit PIN
3. Order Placement — Help authenticated customers place new orders
4. Order History — Look up order status and details for authenticated customers

## Authentication Rules
- Customers MUST authenticate before placing orders or viewing order history.
- Authentication requires an email address and 4-digit PIN.
- Remember the customer ID for the rest of the conversation once verified.
- On failure, ask the customer to retry or contact support.

## Ordering Rules
- Confirm product details and price before placing an order.
- Use the product's listed price as the unit_price.
- Provide order confirmation details after placement.

## General Rules
- Be friendly, professional, and concise.
- Decline requests outside your capabilities and suggest contacting support.
- Format product listings with SKU, name, price, and stock availability.
- Use currency formatting (e.g., $299.99).
- Never fabricate product data or claim capabilities you lack.
- Confirm destructive actions before executing them.
"""

MAX_TOOL_ITERATIONS = 10


class ChatAgent:
    def __init__(self, openai_api_key: str):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.mcp = MCPClient()
        self._openai_tools: list[dict] | None = None
        self.model = "gpt-4o-mini"

    async def ensure_tools_loaded(self) -> list[dict]:
        if self._openai_tools is None:
            await self.mcp.initialize()
            mcp_tools = await self.mcp.list_tools()
            self._openai_tools = self.mcp.convert_to_openai_tools(mcp_tools)
        return self._openai_tools

    async def chat(self, messages: list[dict]) -> str:
        tools = await self.ensure_tools_loaded()
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return (
                    message.content
                    or "I'm sorry, I wasn't able to generate a response."
                )

            full_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                try:
                    result = await self.mcp.call_tool(tc.function.name, args)
                except Exception as e:
                    result = f"Error calling {tc.function.name}: {e}"

                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        return "I apologize, but I'm having trouble processing your request. Please try again."
