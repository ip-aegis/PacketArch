# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""HTTP + SSE transport for MCP server."""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, DBSession, RequireAIEnabled
from app.mcp_server.schemas.mcp_types import JSONRPCRequest, JSONRPCResponse
from app.mcp_server.server import mcp_server

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp",
    tags=["MCP"],
    dependencies=[RequireAIEnabled],
)

# In-memory session storage
# In production, this should use Redis or similar
sessions: dict[str, dict[str, Any]] = {}


class MCPMessageRequest(BaseModel):
    """Request to send an MCP message."""

    session_id: str | None = None
    request: JSONRPCRequest


class MCPMessageResponse(BaseModel):
    """Response from MCP message."""

    session_id: str
    response: JSONRPCResponse


@router.post("/message", response_model=MCPMessageResponse)
async def send_mcp_message(
    message: MCPMessageRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> MCPMessageResponse:
    """Send a message to the MCP server and get a response.

    Args:
        message: MCP message request
        current_user: Authenticated user
        db: Database session

    Returns:
        MCP response
    """
    # Create or get session
    session_id = message.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "user_id": str(current_user.id),
            "created_at": asyncio.get_event_loop().time(),
            "events": [],
        }

    # Process request
    response = await mcp_server.handle_request(message.request)

    return MCPMessageResponse(
        session_id=session_id,
        response=response,
    )


@router.get("/events/{session_id}")
async def stream_mcp_events(
    session_id: str,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Stream server-initiated events via SSE.

    Args:
        session_id: Session ID
        current_user: Authenticated user

    Returns:
        SSE stream
    """
    # Validate session
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session = sessions[session_id]

    # Verify session belongs to user
    if session["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    async def event_generator():
        """Generate SSE events."""
        try:
            # Send initial connection event
            yield f"data: {{'type': 'connected', 'session_id': '{session_id}'}}\n\n"

            # Keep connection alive and send any pending events
            while True:
                # In a real implementation, this would pull from a queue
                # For now, just keep the connection alive with heartbeats
                await asyncio.sleep(30)
                yield "data: {'type': 'heartbeat'}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for session {session_id}")
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/sessions/{session_id}")
async def end_mcp_session(
    session_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """End an MCP session.

    Args:
        session_id: Session ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session = sessions[session_id]

    # Verify session belongs to user
    if session["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to end this session",
        )

    # Remove session
    del sessions[session_id]

    return {"message": "Session ended successfully"}
