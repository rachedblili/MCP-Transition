"""
MCP-Enabled Agent that discovers and uses tools through Model Context Protocol.

Changes from improved_agent.py:
- Hardcoded @agent.tool decorators removed
- MCP client integration added for dynamic tool discovery
- Tools are discovered at runtime from MCP server
- Tool execution happens through MCP protocol
- Agent becomes server-agnostic (can work with any MCP server)

This demonstrates the core value of MCP: separating tool implementation
from tool usage, enabling dynamic and extensible agent architectures.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import ModelMessage
from prompts import role, goal, instructions, knowledge
from mcp_client_stdio import MCPClient, MCPError

# Load environment variables
load_dotenv()


class MCPEnabledAgent:
    def __init__(self, model: str = "gpt-4o-mini", mcp_server_path: str = "mcp_server_stdio.py"):
        """
        Initialize the MCP-enabled Pydantic AI agent.

        Args:
            model: The language model to use
            mcp_server_path: Path to the MCP server script
        """
        self.name = "MCP-Enabled Agent"
        self.mcp_server_path = mcp_server_path
        self.mcp_client: Optional[MCPClient] = None
        self.available_tools: List[Dict[str, Any]] = []

        # Create the base agent without any hardcoded tools
        self.agent = PydanticAgent(
            f'openai:{model}',
            system_prompt=self._build_system_prompt(),
            deps_type=str,
            result_type=str
        )

        # We'll register MCP tools dynamically after discovering them

        # Conversation history
        self.messages: List[ModelMessage] = []

    def _build_system_prompt(self) -> str:
        """
        Build system prompt with placeholder for tools.
        """
        base_prompt = "\n".join([
            role,
            goal,
            instructions,
            knowledge,
            "\nYou have access to tools that will be discovered dynamically."
        ])

        return base_prompt

    async def start(self) -> None:
        """
        Start the MCP connection and discover available tools.

        This must be called before using the agent to establish
        the MCP connection and register discovered tools.
        """
        try:
            # Initialize MCP client
            self.mcp_client = MCPClient(self.mcp_server_path)
            await self.mcp_client.start()

            # Discover available tools
            await self._discover_and_register_tools()

            print(f"✓ MCP Agent ready with {len(self.available_tools)} tools")

        except MCPError as e:
            print(f"Failed to start MCP agent: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop the MCP connection and clean up resources.
        """
        if self.mcp_client:
            await self.mcp_client.stop()
            self.mcp_client = None
            print("✓ MCP Agent stopped")

    async def _discover_and_register_tools(self) -> None:
        """
        Discover tools from MCP server and register them with the Pydantic AI agent.

        This is the key integration point where MCP discovery meets
        Pydantic AI tool registration.
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized")

        # Discover tools from MCP server
        self.available_tools = await self.mcp_client.list_tools()

        # Register each discovered tool with the Pydantic AI agent
        for tool_def in self.available_tools:
            self._register_mcp_tool(tool_def)

        # Update system prompt with tool descriptions
        self._update_system_prompt()

    def _register_mcp_tool(self, tool_def: Dict[str, Any]) -> None:
        """
        Register a single MCP tool with the Pydantic AI agent.

        This creates a bridge between MCP tool definitions and
        Pydantic AI's tool system.

        Args:
            tool_def: Tool definition from MCP server
        """
        tool_name = tool_def["name"]
        tool_description = tool_def["description"]
        input_schema = tool_def.get("inputSchema", {})

        # Create a wrapper function that calls the MCP tool
        async def mcp_tool_wrapper(ctx: RunContext[str], **kwargs) -> str:
            """
            Wrapper function that bridges Pydantic AI tool calls to MCP tool execution.
            """
            try:
                # Call the tool through MCP
                result = await self.mcp_client.call_tool(tool_name, kwargs)
                return result
            except MCPError as e:
                return f"Tool execution failed: {e}"

        # Set the wrapper function's metadata for Pydantic AI
        mcp_tool_wrapper.__name__ = tool_name
        mcp_tool_wrapper.__doc__ = tool_description

        # Register the wrapper as a tool with the Pydantic AI agent
        # Note: This is a simplified registration - in practice, you might need
        # to convert the JSON schema to Pydantic AI's expected format
        self.agent.tool(mcp_tool_wrapper)

    def _update_system_prompt(self) -> None:
        """
        Update the system prompt to include descriptions of discovered tools.

        This helps the AI understand what tools are available and how to use them.
        Note: We rebuild the agent with updated system prompt since Pydantic AI
        doesn't allow direct system prompt modification after creation.
        """
        if not self.available_tools:
            return

        tool_descriptions = []
        for tool in self.available_tools:
            tool_descriptions.append(f"- {tool['name']}: {tool['description']}")

        tools_section = f"\n\nAvailable tools:\n" + "\n".join(tool_descriptions)

        # Build new system prompt with tool descriptions
        updated_prompt = self._build_system_prompt() + tools_section

        # Create new agent with updated system prompt
        # (Pydantic AI doesn't allow modifying system prompt after creation)
        model = self.agent.model  # Get current model
        self.agent = PydanticAgent(
            model,
            system_prompt=updated_prompt,
            deps_type=str,
            result_type=str
        )

        # Re-register all tools with the new agent
        for tool_def in self.available_tools:
            self._register_mcp_tool(tool_def)

    async def chat(self, message: str) -> str:
        """
        Send a message and get a response.

        This method maintains the same interface as the cleaned agent,
        but now uses MCP-discovered tools instead of hardcoded ones.

        Args:
            message: User's input message

        Returns:
            Assistant's response
        """
        if not self.mcp_client:
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
        """
        Reset the conversation context.

        Returns:
            True if reset was successful
        """
        try:
            self.messages = []
            return True
        except Exception as e:
            print(f"Error clearing chat: {e}")
            return False

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of currently available tools.

        Returns:
            List of tool definitions from MCP server
        """
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
    Example usage demonstrating the MCP-enabled agent.

    This shows how the agent interface remains the same while
    the underlying tool system becomes dynamic and extensible.
    """
    # Use context manager to handle MCP connection lifecycle
    async with MCPEnabledAgent() as agent:
        print("MCP-Enabled Agent initialized")

        # Show discovered tools
        tools = await agent.list_available_tools()
        print(f"\nDiscovered {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")

        print("\nAgent ready. Type 'exit' or 'quit' to end.")
        while True:
            query = input("\nYou: ")
            if query.lower() in ['exit', 'quit']:
                break

            response = await agent.chat(query)
            print(f"Assistant: {response}")


if __name__ == "__main__":
    asyncio.run(main())