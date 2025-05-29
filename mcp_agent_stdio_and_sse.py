"""
MCP-Enabled Agent using SSE (Server-Sent Events) transport

This agent connects to HTTP-based MCP servers instead of subprocess-based ones.
Key differences from stdio agents:
- Connects to HTTP URLs instead of launching subprocesses
- Can connect to remote servers (not just local scripts)
- Uses SSE transport for real-time communication
- Better suited for production deployments

This demonstrates how MCP agents can work with different transport layers
while maintaining the same tool discovery and execution patterns.
"""

import os
import asyncio
import json
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# Official MCP library imports for SSE
from mcp import ClientSession
from mcp.client.sse import sse_client

# Pydantic AI imports
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import ModelMessage
from prompts import role, goal, instructions, knowledge

# Load environment variables
load_dotenv()


class SSEMCPAgent:
    def __init__(self, model: str = "gpt-4o-mini", server_url: str = "http://localhost:8000/sse"):
        """
        Initialize the SSE-based MCP agent.

        Args:
            model: The language model to use
            server_url: URL of the SSE MCP server
        """
        self.name = "SSE MCP-Enabled Agent"
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[Dict[str, Any]] = []

        # Create the base agent without hardcoded tools
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
            "\nYou have access to tools that will be discovered dynamically from MCP servers.",
            "When you receive structured JSON data from tools, interpret and present it naturally in conversation."
        ])

    async def start(self) -> None:
        """
        Start the SSE MCP connection and discover available tools.

        This connects to an HTTP-based MCP server instead of launching
        a subprocess like the stdio transport does.
        """
        try:
            print(f"🔗 Connecting to SSE MCP server at {self.server_url}")

            # Establish SSE connection to MCP server
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(self.server_url)
            )
            read_stream, write_stream = sse_transport

            # Create MCP session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the MCP session (handshake)
            await self.session.initialize()

            # Discover and register tools
            await self._discover_and_register_tools()

            print(f"✅ SSE MCP Agent ready with {len(self.available_tools)} tools")

        except Exception as e:
            print(f"❌ Failed to start SSE MCP agent: {e}")
            print(f"💡 Make sure the SSE server is running at {self.server_url}")
            raise

    async def stop(self) -> None:
        """Stop the SSE MCP connection and clean up resources."""
        await self.exit_stack.aclose()
        self.session = None
        print("✅ SSE MCP Agent stopped")

    async def _discover_and_register_tools(self) -> None:
        """
        Discover tools from SSE MCP server and register them with Pydantic AI.

        The tool discovery process is identical to stdio transport -
        the transport layer is abstracted away by the MCP library.
        """
        if not self.session:
            raise RuntimeError("MCP session not initialized")

        # Discover tools using official MCP library
        tools_response = await self.session.list_tools()

        # Convert MCP tool definitions to our internal format
        self.available_tools = []
        for tool in tools_response.tools:
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            self.available_tools.append(tool_def)

            # Register each tool with Pydantic AI
            self._register_mcp_tool(tool_def)

        # Update system prompt with discovered tools
        self._update_system_prompt()

    def _register_mcp_tool(self, tool_def: Dict[str, Any]) -> None:
        """
        Register a single MCP tool with the Pydantic AI agent.

        Creates a wrapper function that bridges Pydantic AI tool calls
        to SSE MCP tool execution.

        Args:
            tool_def: Tool definition from MCP server
        """
        tool_name = tool_def["name"]
        tool_description = tool_def["description"]

        # Create wrapper function for MCP tool execution
        async def mcp_tool_wrapper(ctx: RunContext[str], **kwargs) -> str:
            """
            Wrapper that calls MCP tools through SSE transport.

            The tool execution is identical to stdio transport - the MCP library
            abstracts away the transport differences.
            """
            try:
                if not self.session:
                    return "Error: MCP session not available"

                # Call tool through SSE MCP connection
                result = await self.session.call_tool(tool_name, arguments=kwargs)

                # Extract content from MCP response
                if result.content and len(result.content) > 0:
                    first_content = result.content[0]
                    if hasattr(first_content, 'text'):
                        return first_content.text
                    else:
                        return str(first_content)

                return "No content returned from tool"

            except Exception as e:
                return f"Tool execution failed: {e}"

        # Set function metadata for Pydantic AI
        mcp_tool_wrapper.__name__ = tool_name
        mcp_tool_wrapper.__doc__ = tool_description

        # Register with Pydantic AI agent
        self.agent.tool(mcp_tool_wrapper)

    def _update_system_prompt(self) -> None:
        """
        Update system prompt with discovered tool descriptions.

        Rebuilds the agent with enhanced system prompt since Pydantic AI
        doesn't allow direct system prompt modification.
        """
        if not self.available_tools:
            return

        # Build tool descriptions
        tool_descriptions = []
        for tool in self.available_tools:
            tool_descriptions.append(f"- {tool['name']}: {tool['description']}")

        tools_section = f"\n\nAvailable tools:\n" + "\n".join(tool_descriptions)
        updated_prompt = self._build_initial_system_prompt() + tools_section

        # Recreate agent with updated prompt
        model = self.agent.model
        self.agent = PydanticAgent(
            model,
            system_prompt=updated_prompt,
            deps_type=str,
            result_type=str
        )

        # Re-register all tools with new agent
        for tool_def in self.available_tools:
            self._register_mcp_tool(tool_def)

    async def chat(self, message: str) -> str:
        """
        Send a message and get a response.

        The chat interface is identical regardless of transport type.
        The agent will use SSE-based weather tools transparently.

        Args:
            message: User's input message

        Returns:
            Assistant's response with naturally formatted tool data
        """
        if not self.session:
            raise RuntimeError("Agent not started. Call start() first.")

        try:
            result = await self.agent.run(
                message,
                message_history=self.messages
            )

            # Maintain conversation history
            self.messages.extend(result.new_messages())
            return result.output

        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I encountered an error processing your request."

    def clear_chat(self) -> bool:
        """Reset the conversation context."""
        try:
            self.messages = []
            return True
        except Exception as e:
            print(f"Error clearing chat: {e}")
            return False

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of currently available tools."""
        return self.available_tools.copy()

    # Context manager support for automatic start/stop
    async def __aenter__(self):
        """Async context manager entry - starts SSE MCP connection."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - stops SSE MCP connection."""
        await self.stop()


async def test_weather_server():
    """
    Test function to verify the SSE weather server is running and accessible.
    """
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/sse", timeout=2) as response:
                if response.status == 200:
                    print("✅ SSE weather server is running")
                    return True
                else:
                    print(f"⚠️  SSE server responded with status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to SSE server: {e}")
        print("💡 Start the server with: python mcp_server_sse.py")
        return False


async def main():
    """
    Example usage demonstrating the SSE MCP agent with weather tools.

    This shows how agents can connect to HTTP-based MCP servers
    for more flexible deployment scenarios.
    """
    print("🌤️  SSE MCP Agent with Weather Tools")
    print("=" * 50)

    # Check if the SSE server is running
    server_running = await test_weather_server()
    if not server_running:
        print("\n🚀 Please start the SSE server first:")
        print("   python mcp_server_sse.py")
        return

    print("\n🔌 Connecting to weather MCP server...")

    async with SSEMCPAgent() as agent:
        print("✅ SSE MCP Agent initialized")

        # Show discovered tools
        tools = await agent.list_available_tools()
        print(f"\n🔧 Discovered {len(tools)} weather tools:")
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")

        print(f"\n💬 Agent ready! Try asking about weather in different cities.")
        print("   Examples: 'What's the weather in Tokyo?', 'Forecast for London'")
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
                print()  # Add spacing

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())