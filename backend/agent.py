"""
AI Agent for Meridian Electronics Customer Support.

Uses OpenAI gpt-4o-mini with function calling to orchestrate
MCP tool calls and provide helpful customer support responses.
"""

import json
from openai import AsyncOpenAI
from mcp_client import MCPClient

SYSTEM_PROMPT = """You are Meridian Support, the AI customer support assistant for **Meridian Electronics** — a company that sells computer products including monitors, keyboards, printers, networking gear, and accessories.

## Your Capabilities
You can help customers with:
1. **Product Browsing** — Search products, browse by category, get detailed product info
2. **Customer Authentication** — Verify customers using their email and 4-digit PIN
3. **Order Placement** — Help authenticated customers place new orders
4. **Order History** — Look up order status and details for authenticated customers

## Rules & Guardrails

### Authentication
- Before placing an order or looking up order history, the customer MUST be authenticated.
- To authenticate, you need their **email address** and **4-digit PIN**.
- Once verified, remember their customer ID for the rest of the conversation.
- If authentication fails, politely ask them to try again or contact support.

### Ordering
- Always confirm the product details and price with the customer before placing an order.
- Use the product's listed price as the unit_price when creating orders.
- After placing an order, provide the order confirmation details.

### General Behavior
- Be friendly, professional, and concise.
- If a customer asks something outside your capabilities, politely let them know and suggest contacting support via phone or email.
- Format responses clearly with bullet points or numbered lists when showing multiple items.
- When showing products, include the SKU, name, price, and stock availability.
- Use currency formatting (e.g., $299.99) for prices.
- Do NOT make up product information — only use data from the tools.
- Do NOT claim to have capabilities you don't have.

### Conversation Style
- Greet new customers warmly and let them know what you can help with.
- Keep responses helpful but not overly long.
- Confirm actions before executing them (especially ordering).
"""


class ChatAgent:
    """OpenAI-powered chat agent with MCP tool integration."""

    def __init__(self, openai_api_key: str):
        self.openai = AsyncOpenAI(api_key=openai_api_key)
        self.mcp = MCPClient()
        self._openai_tools: list[dict] | None = None
        self.model = "gpt-4o-mini"

    async def _ensure_tools_loaded(self) -> list[dict]:
        """Load and cache MCP tools converted to OpenAI format."""
        if self._openai_tools is None:
            await self.mcp.initialize()
            mcp_tools = await self.mcp.list_tools()
            self._openai_tools = self.mcp.get_openai_tools(mcp_tools)
        return self._openai_tools

    async def chat(self, messages: list[dict]) -> str:
        """Process a chat conversation with tool-calling support.

        Args:
            messages: List of conversation messages (role/content dicts).
                      Should NOT include the system message — that's added here.

        Returns:
            The assistant's final text response.
        """
        tools = await self._ensure_tools_loaded()

        # Prepend system prompt
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        # Tool-calling loop: allow the model to call multiple tools sequentially
        max_iterations = 10  # Safety limit
        for _ in range(max_iterations):
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
            )

            choice = response.choices[0]
            message = choice.message

            # If no tool calls, we have our final response
            if not message.tool_calls:
                return (
                    message.content
                    or "I'm sorry, I wasn't able to generate a response."
                )

            # Append the assistant message with tool calls
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

            # Execute each tool call via MCP
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                try:
                    result = await self.mcp.call_tool(func_name, func_args)
                except Exception as e:
                    result = f"Error calling {func_name}: {str(e)}"

                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "I apologize, but I'm having trouble processing your request. Please try again."
