"""MCP protocol types and schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | list[Any] | None = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None
    result: Any | None = None
    error: JSONRPCError | None = None


class MCPCapabilities(BaseModel):
    """MCP server capabilities."""

    tools: bool = True
    resources: bool = True
    prompts: bool = False
    sampling: bool = False


class MCPServerInfo(BaseModel):
    """MCP server information."""

    name: str = "PacketArch MCP Server"
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"


class MCPInitializeResult(BaseModel):
    """Result of MCP initialize."""

    server_info: MCPServerInfo
    capabilities: MCPCapabilities


class ToolInputSchema(BaseModel):
    """JSON Schema for tool input."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    input_schema: ToolInputSchema


class ToolResult(BaseModel):
    """Result of a tool execution."""

    content: list[dict[str, Any]]
    is_error: bool = False


class ResourceContents(BaseModel):
    """Contents of a resource."""

    uri: str
    mime_type: str = "application/json"
    text: str | None = None


class ResourceDefinition(BaseModel):
    """MCP resource definition."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str = "application/json"
