"""MCP Server core implementation."""

import logging
from typing import Any, Callable

from app.mcp_server.schemas.mcp_types import (
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPCapabilities,
    MCPInitializeResult,
    MCPServerInfo,
    ResourceContents,
    ResourceDefinition,
    ToolDefinition,
    ToolResult,
)

logger = logging.getLogger(__name__)


# Error codes from JSON-RPC 2.0 spec
class ErrorCode:
    """JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MCPServer:
    """MCP server with tool and resource registry."""

    def __init__(self) -> None:
        """Initialize MCP server."""
        self._tools: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._initialized = False

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable,
    ) -> None:
        """Register a tool with the MCP server.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool input
            handler: Async function to handle tool execution
        """
        self._tools[name] = {
            "description": description,
            "input_schema": input_schema,
            "handler": handler,
        }
        logger.info(f"Registered tool: {name}")

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str | None,
        mime_type: str,
        handler: Callable,
    ) -> None:
        """Register a resource with the MCP server.

        Args:
            uri: Resource URI
            name: Resource name
            description: Resource description
            mime_type: MIME type of resource content
            handler: Async function to retrieve resource content
        """
        self._resources[uri] = {
            "name": name,
            "description": description,
            "mime_type": mime_type,
            "handler": handler,
        }
        logger.info(f"Registered resource: {uri}")

    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle an MCP JSON-RPC request.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        try:
            method = request.method

            if method == "initialize":
                result = await self._handle_initialize(request.params or {})
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(request.params or {})
            elif method == "resources/list":
                result = await self._handle_list_resources()
            elif method == "resources/read":
                result = await self._handle_read_resource(request.params or {})
            else:
                return JSONRPCResponse(
                    id=request.id,
                    error=JSONRPCError(
                        code=ErrorCode.METHOD_NOT_FOUND,
                        message=f"Method not found: {method}",
                    ),
                )

            return JSONRPCResponse(id=request.id, result=result)

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(e),
                ),
            )

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        self._initialized = True
        result = MCPInitializeResult(
            server_info=MCPServerInfo(),
            capabilities=MCPCapabilities(),
        )
        return result.model_dump()

    async def _handle_list_tools(self) -> dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for name, tool_info in self._tools.items():
            tool_def = ToolDefinition(
                name=name,
                description=tool_info["description"],
                input_schema=tool_info["input_schema"],
            )
            tools.append(tool_def.model_dump())

        return {"tools": tools}

    async def _handle_call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Missing tool name")

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_info = self._tools[tool_name]
        handler = tool_info["handler"]

        try:
            # Call the tool handler
            result = await handler(**arguments)

            # Format as ToolResult
            tool_result = ToolResult(
                content=[{"type": "text", "text": str(result)}],
                is_error=False,
            )
            return tool_result.model_dump()

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            tool_result = ToolResult(
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                is_error=True,
            )
            return tool_result.model_dump()

    async def _handle_list_resources(self) -> dict[str, Any]:
        """Handle resources/list request."""
        resources = []
        for uri, resource_info in self._resources.items():
            resource_def = ResourceDefinition(
                uri=uri,
                name=resource_info["name"],
                description=resource_info["description"],
                mime_type=resource_info["mime_type"],
            )
            resources.append(resource_def.model_dump())

        return {"resources": resources}

    async def _handle_read_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")

        if not uri:
            raise ValueError("Missing resource URI")

        if uri not in self._resources:
            raise ValueError(f"Unknown resource: {uri}")

        resource_info = self._resources[uri]
        handler = resource_info["handler"]

        try:
            # Call the resource handler
            content = await handler()

            # Format as ResourceContents
            resource_contents = ResourceContents(
                uri=uri,
                mime_type=resource_info["mime_type"],
                text=content,
            )
            return {"contents": [resource_contents.model_dump()]}

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise


# Global MCP server instance
mcp_server = MCPServer()
