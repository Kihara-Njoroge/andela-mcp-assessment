from mcp_client import MCPClient


def test_parse_sse():
    client = MCPClient("http://fake")
    dummy_sse = (
        'event: message\ndata: {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}\n\n'
    )
    result = client._parse_sse(dummy_sse)
    assert result["jsonrpc"] == "2.0"
    assert "result" in result


def test_convert_to_openai_tools():
    client = MCPClient("http://fake")

    mcp_tools = [
        {
            "name": "list_products",
            "description": "List all products",
            "inputSchema": {
                "type": "object",
                "properties": {"category": {"title": "Category", "type": "string"}},
                "required": ["category"],
            },
        }
    ]

    openai_tools = client.convert_to_openai_tools(mcp_tools)

    assert len(openai_tools) == 1
    assert openai_tools[0]["type"] == "function"
    assert openai_tools[0]["function"]["name"] == "list_products"
    properties = openai_tools[0]["function"]["parameters"]["properties"]
    assert "category" in properties
    assert "title" not in properties["category"]
