"""
Multi-Transport MCP Agent

This agent demonstrates MCP's composability by connecting to multiple servers
simultaneously using different transports:

1. stdio transport → local tools (date, web_search)
2. SSE transport → remote weather service

This shows how MCP enables distributed tool ecosystems where agents can
access both local and remote capabilities through a unified interface.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# Official MCP library imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# Pydantic AI imports
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import ModelMessage
from prompts import role, goal, instructions, knowledge

# Load environment variables
load_dotenv()


class MultiTransportMCPAgent:
    def __init__(
            self,
            model: str = "gpt-4o-mini",
            stdio_server_path: str = "mcp_server_stdio.py",
            sse_server_url: str = "http://localhost:8000/sse"
    ):
        """
        Initialize agent with multiple MCP connections.

        Args:
            model: The language model to use
            stdio_server_path: Path to stdio MCP server
            sse_server_url: URL of SSE MCP server
        """
        self.name = "Multi-Transport MCP Agent"
        self.stdio_server_path = stdio_server_path
        self.sse_server_url = sse_server_url

        # Multiple sessions for different transports
        self.stdio_session: Optional[ClientSession] = None
        self.sse_session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Combined tool registry
        self.available_tools: List[Dict[str, Any]] = []
        self.tool_to_session: Dict[str, ClientSession] = {}

        # Create the base agent
        self.agent = PydanticAgent(
            f'openai:{model}',
            system_prompt=self._build_initial_system_prompt(),
            deps_type=str,
            result_type=str
        )

        # Conversation history
        self.messages: List[ModelMessage] = []

    def _build_initial_system_prompt(self) -> str:
        """Build initial system prompt."""
        return "\n".join([
            role,
            goal,
            instructions,
            knowledge,
            "\nYou have access to tools from multiple sources:",
            "- Local tools via stdio transport (date, web search)",
            "- Remote weather service via SSE transport",
            "All tools are available through a unified interface."
        ])

    async def start(self) -> None:
        """
        Start both MCP connections and discover all available tools.
        """
        try:
            print("🔌 Starting multi-transport MCP connections...")

            # Start stdio connection (local tools)
            await self._start_stdio_connection()

            # Start SSE connection (remote weather service)
            await self._start_sse_connection()

            # Discover and register all tools from both servers
            await self._discover_all_tools()

            print(f"✅ Multi-transport agent ready with {len(self.available_tools)} tools")

            # Show tool distribution
            stdio_tools = [t for t, s in self.tool_to_session.items() if s == self.stdio_session]
            sse_tools = [t for t, s in self.tool_to_session.items() if s == self.sse_session]
            print(f"   📍 Local (stdio): {stdio_tools}")
            print(f"   🌐 Remote (SSE): {sse_tools}")

        except Exception as e:
            print(f"❌ Failed to start multi-transport agent: {e}")
            raise

    async def _start_stdio_connection(self) -> None:
        """Start stdio MCP connection for local tools."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.stdio_server_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport

        self.stdio_session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.stdio_session.initialize()
        print("✓ stdio connection established (local tools)")

    async def _start_sse_connection(self) -> None:
        """Start SSE MCP connection for remote weather service."""
        sse_transport = await self.exit_stack.enter_async_context(
            sse_client(self.sse_server_url)
        )
        read_stream, write_stream = sse_transport

        self.sse_session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.sse_session.initialize()
        print("✓ SSE connection established (remote weather service)")

    async def _discover_all_tools(self) -> None:
        """
        Discover tools from all connected servers and register them.
        """
        # Discover stdio tools
        if self.stdio_session:
            stdio_tools = await self.stdio_session.list_tools()
            for tool in stdio_tools.tools:
                tool_def = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                    "source": "stdio"
                }
                self.available_tools.append(tool_def)
                self.tool_to_session[tool.name] = self.stdio_session
                self._register_mcp_tool(tool_def)

        # Discover SSE tools
        if self.sse_session:
            sse_tools = await self.sse_session.list_tools()
            for tool in sse_tools.tools:
                tool_def = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                    "source": "sse"
                }
                self.available_tools.append(tool_def)
                self.tool_to_session[tool.name] = self.sse_session
                self._register_mcp_tool(tool_def)

        # Update system prompt with all discovered tools
        self._update_system_prompt()

    def _register_mcp_tool(self, tool_def: Dict[str, Any]) -> None:
        """
        Register a tool from any MCP server with the Pydantic AI agent.
        """
        tool_name = tool_def["name"]
        tool_description = tool_def["description"]

        async def mcp_tool_wrapper(ctx: RunContext[str], **kwargs) -> str:
            """
            Universal wrapper that routes tool calls to the correct MCP session.
            """
            try:
                # Find which session handles this tool
                session = self.tool_to_session.get(tool_name)
                if not session:
                    return f"Error: No session found for tool {tool_name}"

                # Execute tool on the appropriate session
                result = await session.call_tool(tool_name, arguments=kwargs)

                # Extract text content
                if result.content and len(result.content) > 0:
                    first_content = result.content[0]
                    if hasattr(first_content, 'text'):
                        return first_content.text
                    else:
                        return str(first_content)

                return "No content returned from tool"

            except Exception as e:
                return f"Tool execution failed: {e}"

        # Set function metadata
        mcp_tool_wrapper.__name__ = tool_name
        mcp_tool_wrapper.__doc__ = tool_description

        # Register with Pydantic AI
        self.agent.tool(mcp_tool_wrapper)

    def _update_system_prompt(self) -> None:
        """
        Update system prompt with all discovered tools from all servers.
        """
        if not self.available_tools:
            return

        # Group tools by source
        stdio_tools = [t for t in self.available_tools if t["source"] == "stdio"]
        sse_tools = [t for t in self.available_tools if t["source"] == "sse"]

        tool_descriptions = []

        if stdio_tools:
            tool_descriptions.append("\nLocal tools (stdio):")
            for tool in stdio_tools:
                tool_descriptions.append(f"- {tool['name']}: {tool['description']}")

        if sse_tools:
            tool_descriptions.append("\nRemote tools (SSE):")
            for tool in sse_tools:
                tool_descriptions.append(f"- {tool['name']}: {tool['description']}")

        updated_prompt = self._build_initial_system_prompt() + "\n".join(tool_descriptions)

        # Recreate agent with updated prompt
        model = self.agent.model
        self.agent = PydanticAgent(
            model,
            system_prompt=updated_prompt,
            deps_type=str,
            result_type=str
        )

        # Re-register all tools
        for tool_def in self.available_tools:
            self._register_mcp_tool(tool_def)

    async def stop(self) -> None:
        """Stop all MCP connections."""
        await self.exit_stack.aclose()
        self.stdio_session = None
        self.sse_session = None
        print("✅ All MCP connections stopped")

    async def chat(self, message: str) -> str:
        """
        Send a message and get a response using all available tools.
        """
        if not self.stdio_session and not self.sse_session:
            raise RuntimeError("No MCP connections available. Call start() first.")

        try:
            result = await self.agent.run(
                message,
                message_history=self.messages
            )

            self.messages.extend(result.new_messages())
            return result.output

        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I encountered an error processing your request."

    def clear_chat(self) -> bool:
        """Reset conversation context."""
        try:
            self.messages = []
            return True
        except Exception as e:
            print(f"Error clearing chat: {e}")
            return False

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools from all servers."""
        return self.available_tools.copy()

    # Context manager support
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


async def test_servers_available() -> bool:
    """Test if both servers are accessible."""
    print("🔍 Checking server availability...")

    # Test SSE server
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/sse", timeout=2) as response:
                if response.status == 200:
                    print("✅ SSE weather server is running")
                else:
                    print(f"⚠️  SSE server responded with status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to SSE server: {e}")
        print("💡 Start with: python mcp_server_sse.py")
        return False

    print("✅ stdio server will be started automatically")
    return True


async def main():
    """
    Demonstrate multi-transport MCP agent with local and remote tools.
    """
    print("🚀 Multi-Transport MCP Agent Demo")
    print("=" * 50)

    # Check server availability
    if not await test_servers_available():
        return

    async with MultiTransportMCPAgent() as agent:
        # Show all discovered tools
        tools = await agent.list_available_tools()
        print(f"\n🔧 Total tools available: {len(tools)}")

        for tool in tools:
            source_icon = "📍" if tool["source"] == "stdio" else "🌐"
            print(f"   {source_icon} {tool['name']}: {tool['description']}")

        print(f"\n💬 Agent ready! You can use both local and remote tools.")
        print("   Examples:")
        print("   - 'What's today's date?' (local stdio tool)")
        print("   - 'Search for MCP tutorial' (local stdio tool)")
        print("   - 'Weather in Tokyo?' (remote SSE tool)")
        print("   - 'Weather forecast for London' (remote SSE tool)")
        print("   Type 'exit' or 'quit' to end.\n")

        while True:
            try:
                query = input("You: ")
                if query.lower() in ['exit', 'quit']:
                    break

                if not query.strip():
                    continue

                print("Assistant: ", end="", flush=True)
                response = await agent.chat(query)
                print(response)
                print()

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())