"""
MCP Server that exposes date and web search tools.

This server wraps the date_tool and web_search functions from the cleaned agent
and exposes them through the Model Context Protocol (MCP).
"""

import os
import json
import asyncio
from datetime import date
from typing import Any, Sequence

from dotenv import load_dotenv
from tavily import TavilyClient

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Load environment variables
load_dotenv()

# Initialize Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY environment variable is required")

tavily_client = TavilyClient(api_key=tavily_api_key)

# Create the MCP server
server = Server("example-tools")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool should have a clear name, description, and input schema.
    """
    return [
        types.Tool(
            name="date_tool",
            description=(
                "Get the current date in a human-readable format (Month Day, Year). "
                "Use this tool when you need to know today's date for scheduling, "
                "time-sensitive queries, or providing temporal context. "
                "This tool requires no parameters and always returns the current date."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="web_search",
            description=(
                "Search the web for current information, news, facts, or real-time data. "
                "This tool is best for queries that require up-to-date information that "
                "may not be in your training data. Provide specific, focused queries "
                "for best results. Examples: 'Python 3.12 new features', "
                "'Tesla stock price today', 'weather in Tokyo'. "
                "Returns a JSON array of search results with titles, URLs, and snippets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query. Should be specific and focused. "
                            "Use keywords rather than full sentences for better results."
                        ),
                        "minLength": 1,
                        "maxLength": 200
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """
    Handle tool execution requests.
    """
    if arguments is None:
        arguments = {}

    try:
        if name == "date_tool":
            result = await date_tool()
            return [types.TextContent(type="text", text=result)]

        elif name == "web_search":
            query = arguments.get("query")
            if not query:
                raise ValueError("Query parameter is required for web_search")

            result = await web_search(query)
            return [types.TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


async def date_tool() -> str:
    """
    Get the current date in a human-readable format.

    Returns:
        Current date as "Month Day, Year" (e.g., "January 15, 2024")
    """
    today = date.today()
    return today.strftime("%B %d, %Y")


async def web_search(query: str) -> str:
    """
    Search the web using Tavily and return formatted results as JSON.

    Args:
        query: The search query string

    Returns:
        JSON string containing formatted search results

    Raises:
        Exception: If search fails or API key is invalid
    """
    try:
        search_response = tavily_client.search(query)
        raw_results = search_response.get('results', [])

        # Format results for better readability (matches cleaned_agent.py)
        formatted_results = []
        for result in raw_results:
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0)
            }
            formatted_results.append(formatted_result)

        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        raise Exception(f"Search failed: {str(e)}")


async def main():
    """
    Main function to run the MCP server.
    """
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example-tools",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())