"""
Generic MCP Client for stdio transport

This is a reusable MCP (Model Context Protocol) client that can connect to any
MCP server using stdio transport. The client handles:

1. Server lifecycle management (start/stop subprocess)
2. MCP protocol initialization and handshake
3. Tool discovery (finding what tools the server offers)
4. Tool execution (calling tools with parameters)
5. Proper JSON-RPC 2.0 message handling

Key MCP Concepts Demonstrated:
- Transport Layer: stdio pipes between client and server subprocess
- Protocol Layer: JSON-RPC 2.0 messages following MCP specification
- Tool Discovery: Dynamic discovery of available tools and their schemas
- Tool Execution: Stateless tool calls with structured parameters and responses

This client can be used as a library component in larger applications or
as a standalone tool for testing MCP servers.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import subprocess


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    pass


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""
    pass


class MCPProtocolError(MCPError):
    """Raised when MCP protocol communication fails."""
    pass


class MCPToolError(MCPError):
    """Raised when tool execution fails."""
    pass


class MCPClient:
    """
    Generic MCP client for stdio transport.

    This client can connect to any MCP server that supports stdio transport.
    It handles the full MCP lifecycle from initialization to tool execution.

    Example usage:
        async with MCPClient("path/to/server.py") as client:
            tools = await client.list_tools()
            result = await client.call_tool("tool_name", {"param": "value"})
    """

    def __init__(self, server_script_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize MCP client.

        Args:
            server_script_path: Path to the MCP server script to run
            logger: Optional logger for debugging (creates default if None)
        """
        self.server_script_path = server_script_path
        self.process: Optional[subprocess.Popen] = None
        self.message_id = 0
        self.logger = logger or self._create_default_logger()

    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger for the client."""
        logger = logging.getLogger(f"MCPClient.{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def __aenter__(self):
        """Async context manager entry - starts the server."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - stops the server."""
        await self.stop()

    async def start(self) -> None:
        """
        Start the MCP server subprocess and initialize the session.

        This creates a subprocess running the server script and establishes
        the MCP protocol connection with proper handshake.

        Raises:
            MCPConnectionError: If server startup or initialization fails
        """
        try:
            # Start the server process with stdio pipes
            # The server will communicate via JSON-RPC 2.0 over stdin/stdout
            self.process = subprocess.Popen(
                [sys.executable, self.server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered I/O for real-time communication
            )

            self.logger.info(f"Started MCP server: {self.server_script_path}")

            # Perform MCP protocol handshake
            await self._initialize_session()

        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise MCPConnectionError(f"Failed to start server: {e}") from e

    async def stop(self) -> None:
        """
        Stop the MCP server subprocess gracefully.

        Attempts graceful termination first, then forces kill if necessary.
        """
        if self.process:
            self.process.terminate()

            # Give the process time to terminate gracefully
            await asyncio.sleep(0.1)

            # Force kill if still running
            if self.process.poll() is None:
                self.process.kill()

            self.process = None
            self.logger.info("Stopped MCP server")

    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 message to the server and receive response.

        This is the core communication method that handles the JSON-RPC protocol.
        All MCP communication flows through this method.

        Args:
            message: JSON-RPC message dictionary

        Returns:
            Response dictionary from server

        Raises:
            MCPProtocolError: If communication fails or response is invalid
        """
        if not self.process:
            raise MCPConnectionError("Server not started")

        # Add unique message ID for JSON-RPC 2.0 protocol
        message["id"] = self.message_id
        self.message_id += 1

        # Serialize and send message
        message_json = json.dumps(message) + "\n"
        self.logger.debug(f"→ Sending: {message_json.strip()}")

        try:
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
        except Exception as e:
            raise MCPProtocolError(f"Failed to send message: {e}") from e

        # Read response line
        try:
            response_line = self.process.stdout.readline()
            if not response_line:
                raise MCPProtocolError("No response from server")

            self.logger.debug(f"← Received: {response_line.strip()}")

        except Exception as e:
            raise MCPProtocolError(f"Failed to read response: {e}") from e

        # Parse JSON response
        try:
            response = json.loads(response_line)
            return response
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response: {e}") from e

    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification (no response expected).

        Notifications are one-way messages that don't expect a response.
        Used for lifecycle events like "initialized".

        Args:
            method: Notification method name
            params: Optional parameters dictionary
        """
        message = {
            "jsonrpc": "2.0",
            "method": method
        }

        if params:
            message["params"] = params

        message_json = json.dumps(message) + "\n"
        self.logger.debug(f"→ Notification: {message_json.strip()}")

        try:
            self.process.stdin.write(message_json)
            self.process.stdin.flush()
        except Exception as e:
            raise MCPProtocolError(f"Failed to send notification: {e}") from e

    async def _initialize_session(self) -> None:
        """
        Initialize the MCP session with proper handshake.

        MCP requires a specific initialization sequence:
        1. Send "initialize" request with client capabilities
        2. Receive server capabilities in response
        3. Send "notifications/initialized" to complete handshake

        This establishes the protocol version and capabilities on both sides.

        Raises:
            MCPProtocolError: If initialization handshake fails
        """
        # Step 1: Send initialize request
        # This tells the server what protocol version we support and our capabilities
        init_message = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",  # MCP protocol version
                "capabilities": {
                    "tools": {}  # We support tool calling
                },
                "clientInfo": {
                    "name": "generic-mcp-client",
                    "version": "0.1.0"
                }
            }
        }

        response = await self._send_message(init_message)

        # Check for initialization errors
        if "error" in response:
            raise MCPProtocolError(f"Initialization failed: {response['error']}")

        self.logger.info("✓ MCP session initialized")

        # Step 2: Send initialized notification
        # This completes the handshake and tells the server we're ready
        await self._send_notification("notifications/initialized")

        self.logger.info("✓ MCP handshake complete")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools from the server.

        This is the MCP tool discovery mechanism. The server returns a list
        of all tools it provides, including their names, descriptions, and
        input schemas. This allows dynamic discovery of server capabilities.

        Returns:
            List of tool definition dictionaries, each containing:
            - name: Tool identifier
            - description: Human-readable description
            - inputSchema: JSON schema for tool parameters

        Raises:
            MCPToolError: If tool discovery fails
        """
        message = {
            "jsonrpc": "2.0",
            "method": "tools/list"
        }

        response = await self._send_message(message)

        if "error" in response:
            raise MCPToolError(f"Failed to list tools: {response['error']}")

        tools = response.get("result", {}).get("tools", [])
        self.logger.info(f"✓ Discovered {len(tools)} tools")

        return tools

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a tool on the server.

        This sends a tool execution request to the server with the specified
        parameters. The server validates the parameters against the tool's
        schema and executes the tool function.

        Args:
            name: Tool name (must match a tool from list_tools())
            arguments: Tool parameters dictionary (must match tool's inputSchema)

        Returns:
            Tool execution result as string

        Raises:
            MCPToolError: If tool execution fails
        """
        if arguments is None:
            arguments = {}

        message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }

        response = await self._send_message(message)

        if "error" in response:
            raise MCPToolError(f"Tool '{name}' execution failed: {response['error']}")

        # Extract text content from MCP response format
        # MCP tool responses contain a "content" array with typed content blocks
        result = response.get("result", {})
        content = result.get("content", [])

        if content and len(content) > 0 and content[0].get("type") == "text":
            return content[0].get("text", "")

        return "No content returned"


# Demo usage (can be removed when using as library)
async def demo_mcp_client():
    """
    Demonstrate the generic MCP client functionality.

    This shows how to use the client to connect to an MCP server,
    discover tools, and execute them. Remove this when using as a library.
    """
    # Configure logging to see the MCP protocol messages
    logging.basicConfig(level=logging.DEBUG)

    async with MCPClient("mcp_server_stdio.py") as client:
        try:
            # Discover available tools
            print("\n=== TOOL DISCOVERY ===")
            tools = await client.list_tools()

            for tool in tools:
                print(f"\nTool: {tool['name']}")
                print(f"Description: {tool['description']}")
                print(f"Parameters: {json.dumps(tool.get('inputSchema', {}), indent=2)}")

            # Test each discovered tool
            print("\n=== TOOL EXECUTION ===")

            # Test date tool (no parameters)
            if any(tool['name'] == 'date_tool' for tool in tools):
                print(f"\nTesting date_tool:")
                date_result = await client.call_tool("date_tool")
                print(f"Result: {date_result}")

            # Test web search (with parameters)
            if any(tool['name'] == 'web_search' for tool in tools):
                print(f"\nTesting web_search:")
                search_result = await client.call_tool("web_search", {
                    "query": "Model Context Protocol tutorial"
                })
                print(f"Result preview: {search_result[:200]}...")

        except MCPError as e:
            print(f"MCP Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(demo_mcp_client())