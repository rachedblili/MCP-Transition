"""
MCP-Enabled Agent using Official Anthropic MCP Library

Changes from mcp_enabled_agent.py:
- Replaced custom MCPClient with official MCP Python SDK
- Simplified connection and session management
- Reduced codebase by ~100 lines using library abstractions
- Cleaner error handling through library-provided exceptions
- Better protocol compliance through official implementation

This demonstrates the value of using mature libraries vs custom implementations.
The agent functionality remains identical while complexity is significantly reduced.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv

# Official MCP library imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Pydantic AI imports
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import ModelMessage
from prompts import role, goal, instructions, knowledge

# Load environment variables
load_dotenv()


class MCPEnabledAgent:
    def __init__(self, model: str = "gpt-4o-mini", mcp_server_path: str = "mcp_server_stdio.py"):
        """
        Initialize the MCP-enabled Pydantic AI agent using official MCP library.

        Args:
            model: The language model to use
            mcp_server_path: Path to the MCP server script
        """
        self.name = "MCP-Enabled Agent (Official Library)"
        self.mcp_server_path = mcp_server_path
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
            "\nYou have access to tools that will be discovered dynamically from MCP servers."
        ])

    async def start(self) -> None:
        """
        Start the MCP connection and discover available tools.

        This establishes connection to the MCP server using the official library
        and registers discovered tools with the Pydantic AI agent.
        """
        try:
            # Configure server parameters for stdio transport
            server_params = StdioServerParameters(
                command="python",
                args=[self.mcp_server_path],
                env=None  # Use current environment
            )

            # Establish stdio connection to MCP server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport

            # Create MCP session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the MCP session (handshake)
            await self.session.initialize()

            # Discover and register tools
            await self._discover_and_register_tools()

            print(f"✓ MCP Agent ready with {len(self.available_tools)} tools")

        except Exception as e:
            print(f"Failed to start MCP agent: {e}")
            raise

    async def stop(self) -> None:
        """Stop the MCP connection and clean up resources."""
        await self.exit_stack.aclose()
        self.session = None
        print("✓ MCP Agent stopped")

    async def _discover_and_register_tools(self) -> None:
        """
        Discover tools from MCP server and register them with Pydantic AI.

        Using the official library makes tool discovery much simpler -
        we just call session.list_tools() and get a clean response.
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
        to MCP tool execution via the official library.

        Args:
            tool_def: Tool definition from MCP server
        """
        tool_name = tool_def["name"]
        tool_description = tool_def["description"]

        # Create wrapper function for MCP tool execution
        async def mcp_tool_wrapper(ctx: RunContext[str], **kwargs) -> str:
            """
            Wrapper that calls MCP tools through the official library.

            The official library handles all protocol details, error handling,
            and response formatting automatically.
            """
            try:
                if not self.session:
                    return "Error: MCP session not available"

                # Call tool through official MCP library
                result = await self.session.call_tool(tool_name, arguments=kwargs)

                # Extract text content from MCP response
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

        Interface remains identical to previous versions while using
        MCP tools discovered through the official library.

        Args:
            message: User's input message

        Returns:
            Assistant's response
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
        """Async context manager entry - starts MCP connection."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - stops MCP connection."""
        await self.stop()


async def main():
    """
    Example usage demonstrating the MCP-enabled agent with official library.

    The interface and functionality are identical to the custom client version,
    but the implementation is much simpler and more reliable.
    """
    # Install the official MCP library first:
    # pip install mcp

    print("MCP Agent using Official Anthropic Library")
    print("=" * 50)

    async with MCPEnabledAgent() as agent:
        print("MCP-Enabled Agent initialized")

        # Show discovered tools
        tools = await agent.list_available_tools()
        print(f"\nDiscovered {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:60]}...")

        print(f"\nAgent ready. Type 'exit' or 'quit' to end.")
        while True:
            query = input("\nYou: ")
            if query.lower() in ['exit', 'quit']:
                break

            response = await agent.chat(query)
            print(f"Assistant: {response}")


if __name__ == "__main__":
    asyncio.run(main())