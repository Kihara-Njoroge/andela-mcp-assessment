import pytest

from mcp_client import MCPClient


def test_parse_sse_extracts_json():
    client = MCPClient("http://fake")
    sse = (
        'event: message\ndata: {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}\n\n'
    )
    result = client._parse_sse(sse)
    assert result["jsonrpc"] == "2.0"
    assert "result" in result


def test_parse_sse_raises_on_empty():
    client = MCPClient("http://fake")
    with pytest.raises(ValueError, match="No valid data"):
        client._parse_sse("event: message\n\n")


def test_parse_sse_handles_multiple_data_lines():
    client = MCPClient("http://fake")
    sse = 'data: {"first": true}\ndata: {"second": true}\n'
    result = client._parse_sse(sse)
    assert result["first"] is True


def test_convert_to_openai_tools_basic():
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

    result = client.convert_to_openai_tools(mcp_tools)

    assert len(result) == 1
    func = result[0]
    assert func["type"] == "function"
    assert func["function"]["name"] == "list_products"
    assert func["function"]["description"] == "List all products"
    props = func["function"]["parameters"]["properties"]
    assert "category" in props
    assert "title" not in props["category"]
    assert props["category"]["type"] == "string"


def test_convert_strips_anyof_null():
    client = MCPClient("http://fake")
    mcp_tools = [
        {
            "name": "test_tool",
            "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "optional_field": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    }
                },
                "required": [],
            },
        }
    ]

    result = client.convert_to_openai_tools(mcp_tools)
    props = result[0]["function"]["parameters"]["properties"]
    assert props["optional_field"]["type"] == "string"
    assert "anyOf" not in props["optional_field"]


def test_convert_handles_array_type():
    client = MCPClient("http://fake")
    mcp_tools = [
        {
            "name": "create_order",
            "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                    }
                },
                "required": ["items"],
            },
        }
    ]

    result = client.convert_to_openai_tools(mcp_tools)
    props = result[0]["function"]["parameters"]["properties"]
    assert props["items"]["type"] == "array"
    assert props["items"]["items"] == {"type": "object"}


def test_convert_empty_tools():
    client = MCPClient("http://fake")
    result = client.convert_to_openai_tools([])
    assert result == []


def test_convert_preserves_description():
    client = MCPClient("http://fake")
    mcp_tools = [
        {
            "name": "test",
            "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    }
                },
                "required": [],
            },
        }
    ]

    result = client.convert_to_openai_tools(mcp_tools)
    props = result[0]["function"]["parameters"]["properties"]
    assert props["query"]["description"] == "Search query text"


def test_convert_defaults_missing_type_to_string():
    client = MCPClient("http://fake")
    mcp_tools = [
        {
            "name": "test",
            "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {"unknown_field": {}},
                "required": [],
            },
        }
    ]

    result = client.convert_to_openai_tools(mcp_tools)
    props = result[0]["function"]["parameters"]["properties"]
    assert props["unknown_field"]["type"] == "string"
