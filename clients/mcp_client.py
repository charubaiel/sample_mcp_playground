"""
MCP SSE Client - A Python client for interacting with Model Context Protocol (MCP) endpoints.

This module provides a client for connecting to MCP endpoints using Server-Sent Events (SSE),
listing available tools, and invoking tools with parameters.
"""

from typing import Any, Dict, List
from urllib.parse import urlparse
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import BaseModel


class ToolInvocationResult(BaseModel):
    """Represents the result of a tool invocation.
    
    Attributes:
        content: Result content as a string
        error_code: Error code (0 for success, 1 for error)
    """
    content: str
    error_code: int


class MCPClient:
    """Client for interacting with Model Context Protocol (MCP) endpoints"""
    
    def __init__(self, endpoint: str):
        """Initialize MCP client with endpoint URL
        
        Args:
            endpoint: The MCP endpoint URL (must be http or https)
        """
        if urlparse(endpoint).scheme not in ("http", "https"):
            raise ValueError(f"Endpoint {endpoint} is not a valid HTTP(S) URL")
        self.endpoint = endpoint

    async def list_tools(self) -> List:
        """List available tools from the MCP endpoint
        
        Returns:
            List of ToolDef objects describing available tools
        """
        async with sse_client(self.endpoint) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools_result = await session.list_tools()

        return tools_result

    async def invoke_tool(self, name: str, arguments: Dict[str, Any]) -> ToolInvocationResult:
        """Invoke a specific tool with parameters
        
        Args:
            tool_name: Name of the tool to invoke
            kwargs: Dictionary of parameters to pass to the tool
            
        Returns:
            ToolInvocationResult containing the tool's response
        """
        async with sse_client(self.endpoint) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)

        return ToolInvocationResult(
            content="\n".join([result.model_dump_json() for result in result.content]),
            error_code=1 if result.isError else 0,
        )