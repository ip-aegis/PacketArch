# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""AI assistant routes for scenario composition."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession, RequireAIEnabled
from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY
from app.mcp_server.sanitization.sanitizer import DataSanitizer
from app.mcp_server.server import mcp_server
from app.models.scenario import Scenario
from app.services.ai_session_service import AISessionService
from app.services.ai_scenario_preview_service import AIScenarioPreviewService
from app.services.cve_fingerprint_service import CVEFingerprintService
from app.services.ip_management import IPManagementService
from app.services.fingerprint_cache import get_fingerprint_cache
from app.ai_services.nl_parser import extract_device_counts, format_device_counts_for_prompt, get_device_limit_warning
from app.protocol_engines.identity import generate_mac
from app.services.device_identity_enricher import (
    enrich_device_serial_numbers,
    enrich_device_unique_identifiers,
)

from app.core.constants import MAX_DEVICES_PER_SCENARIO

# Import from extracted service modules
from app.services.ai_chat_service import (
    build_system_prompt,
    build_completion_message,
    detect_convergence,
    execute_tool_call,
    generate_serial_number as _generate_serial_number,
    get_ai_provider as _get_ai_provider,
)
from app.services.ai_mcp_tools import register_mcp_tools as _register_mcp_tools

# Import schemas from extracted module
from app.schemas.ai import (
    AISessionCreateRequest,
    AISessionResponse,
    AIChatRequest,
    AIChatResponse,
    AIToolDefinition,
    AIScenarioGenerateRequest,
    AIScenarioPreviewDevice,
    AIScenarioPreviewFlow,
    AIScenarioPreviewResponse,
    AIScenarioCreateFromPreviewRequest,
    AIScenarioCreateFromPreviewResponse,
    GenerateDescriptionRequest,
    GenerateDescriptionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"],
    dependencies=[RequireAIEnabled],
)

# Backwards compatibility alias
_get_anthropic_provider = _get_ai_provider


@router.post("/sessions", response_model=AISessionResponse)
async def create_ai_session(
    request: AISessionCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AISessionResponse:
    """Create or resume an AI assistant session for a scenario.

    If a session already exists for this user+scenario, returns the existing
    session with its conversation history. Otherwise creates a new session.

    Args:
        request: Request containing scenario_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Session information with conversation history
    """
    # Note: Tools are registered per-chat request with the current db session
    # to ensure the db session is valid for the duration of tool execution.
    # See _register_mcp_tools call in chat_with_ai.

    # Get or create session for this scenario (persists across panel open/close)
    session_data = await AISessionService.get_or_create_session_for_scenario(
        str(current_user.id), request.scenario_id
    )

    return AISessionResponse(
        session_id=session_data["id"],
        created_at=session_data["created_at"],
        scenario_id=session_data.get("scenario_id"),
        messages=session_data.get("messages", []),
    )


@router.delete("/sessions/{session_id}")
async def end_ai_session(
    session_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """End an AI assistant session.

    Args:
        session_id: Session ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    # Validate session exists and belongs to user
    session = await AISessionService.validate_session(session_id, str(current_user.id))
    if session is None:
        raise NotFoundError("AI session", session_id)

    await AISessionService.delete_session(session_id)
    return {"message": "Session ended"}


@router.get("/sessions/scenario/{scenario_id}", response_model=AISessionResponse | None)
async def get_session_for_scenario(
    scenario_id: str,
    current_user: CurrentUser,
) -> AISessionResponse | None:
    """Get existing AI session for a scenario.

    Returns the session with conversation history if it exists,
    or None if no session exists for this user+scenario.

    Args:
        scenario_id: Scenario UUID
        current_user: Authenticated user

    Returns:
        Session information with conversation history, or None
    """
    session_data = await AISessionService.get_session_for_scenario(
        str(current_user.id), scenario_id
    )

    if session_data is None:
        return None

    return AISessionResponse(
        session_id=session_data["id"],
        created_at=session_data["created_at"],
        scenario_id=session_data.get("scenario_id"),
        messages=session_data.get("messages", []),
    )


@router.delete("/sessions/scenario/{scenario_id}")
async def clear_scenario_conversation(
    scenario_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Clear AI conversation for a scenario.

    Deletes the session and its conversation history. A new session
    will be created on the next chat message.

    Args:
        scenario_id: Scenario UUID
        current_user: Authenticated user

    Returns:
        Success message
    """
    deleted = await AISessionService.delete_session_for_scenario(
        str(current_user.id), scenario_id
    )

    if not deleted:
        # Session didn't exist, but that's okay for clearing
        return {"message": "No conversation to clear"}

    return {"message": "Conversation cleared"}


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    request: AIChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIChatResponse:
    """Send a message to the AI assistant.

    Args:
        request: Chat request
        current_user: Authenticated user
        db: Database session

    Returns:
        AI response
    """
    user_id = str(current_user.id)
    scenario_id = request.scenario_id

    # Validate session exists for this user+scenario
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    if session is None:
        raise NotFoundError("AI session")

    # Register MCP tools with the current request's db session
    # This ensures tools have access to a valid db session for commits
    _register_mcp_tools(db, user_id=str(current_user.id))

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == uuid.UUID(request.scenario_id),
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", request.scenario_id)

    # Get AI provider
    provider = await _get_anthropic_provider(db)

    # Sanitize scenario data before sending to AI
    sanitizer = DataSanitizer()
    scenario_context = scenario.definition.copy() if scenario.definition else {}
    sanitized_context = sanitizer.sanitize_scenario(scenario_context)

    # Store sanitizer mapping in session for potential desanitization of AI responses
    sanitizer_mappings = {
        "ip": sanitizer._ip_mapping,
        "mac": sanitizer._mac_mapping,
        "hostname": sanitizer._hostname_mapping,
    }
    await AISessionService.update_session_for_scenario(user_id, scenario_id, sanitizer_mappings=sanitizer_mappings)

    # Append user message to session immediately (before processing)
    # Session stores only clean text messages - tool execution is ephemeral in current_messages
    await AISessionService.append_message_for_scenario(user_id, scenario_id, {"role": "user", "content": request.message})

    # Refresh session data to get updated messages
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    messages = session["messages"].copy()

    # Build enhanced system prompt with domain expertise
    vertical = scenario.vertical or "unspecified"
    device_count = len(sanitized_context.get("devices", {}))
    flow_count = len(sanitized_context.get("flows", {}))

    # Parse user message to extract device counts for better guidance
    user_message = request.message
    parsed_counts = extract_device_counts(user_message)
    device_count_info = format_device_counts_for_prompt(parsed_counts)
    device_limit_warning = get_device_limit_warning(parsed_counts, MAX_DEVICES_PER_SCENARIO)

    system_prompt = build_system_prompt(
        scenario_name=scenario.name,
        vertical=vertical,
        device_count=device_count,
        flow_count=flow_count,
        device_count_info=device_count_info,
        device_limit_warning=device_limit_warning,
        parsed_counts=parsed_counts,
        compact=False,
    )

    system_message = {
        "role": "system",
        "content": system_prompt,
    }

    # Get available tools
    tools_list = []
    for tool_name, tool_info in mcp_server._tools.items():
        tools_list.append({
            "name": tool_name,
            "description": tool_info["description"],
            "input_schema": tool_info["input_schema"],
        })

    # Call AI with tool execution loop
    try:
        current_messages = [system_message] + messages
        all_tool_calls = []
        final_response_text = ""
        max_iterations = 15  # Prevent infinite loops, increased for complex scenarios

        logger.info(f"Starting AI chat. Session messages count: {len(session['messages'])}")
        logger.info(f"Session messages structure: {[(m.get('role'), type(m.get('content')).__name__, str(m.get('content'))[:100] if isinstance(m.get('content'), str) else 'list') for m in session['messages']]}")
        logger.info(f"Messages being sent (count): {len(current_messages)}")
        logger.info(f"Processed messages structure: {[(m.get('role'), type(m.get('content')).__name__) for m in messages]}")

        for iteration in range(max_iterations):
            logger.info(f"AI loop iteration {iteration + 1}/{max_iterations}")
            logger.debug(f"Sending {len(current_messages)} messages to Claude")
            response = await provider.chat(
                messages=current_messages,
                tools=tools_list,
                max_tokens=16384,
            )

            # Log the full response for debugging
            logger.info(f"Claude response stop_reason: {response.get('stop_reason')}")
            logger.info(f"Claude response content blocks: {len(response.get('content', []))}")
            for i, block in enumerate(response.get("content", [])):
                logger.info(f"  Block {i}: type={block.get('type')}, text_len={len(block.get('text', '')) if block.get('type') == 'text' else 'N/A'}")

            # Extract text and tool calls from this response
            response_text = ""
            tool_calls_this_round = []

            for content in response.get("content", []):
                if content["type"] == "text":
                    response_text += content["text"]
                elif content["type"] == "tool_use":
                    tool_calls_this_round.append({
                        "id": content["id"],
                        "name": content["name"],
                        "input": content["input"],
                    })

            final_response_text += response_text
            all_tool_calls.extend(tool_calls_this_round)

            # Check for convergence (stuck loops, oscillating patterns)
            should_stop, stop_reason = detect_convergence(all_tool_calls)
            if should_stop:
                logger.warning(f"Convergence detected: {stop_reason}")
                # Generate a completion message
                tool_names = [tc.get("name", "") for tc in all_tool_calls]
                device_adds = sum(1 for n in tool_names if n == "add_device")
                flow_adds = sum(1 for n in tool_names if n == "add_flow")

                completion_parts = []
                if device_adds > 0:
                    completion_parts.append(f"{device_adds} devices added")
                if flow_adds > 0:
                    completion_parts.append(f"{flow_adds} data flows created")

                if completion_parts:
                    final_response_text = f"Scenario creation completed! {', '.join(completion_parts)}. The scenario is ready for review."
                else:
                    final_response_text = "Operation completed. Please check the Scenario Studio for results."

                await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                    "role": "assistant",
                    "content": final_response_text,
                })
                break

            # If no tool calls, we're done
            if not tool_calls_this_round:
                logger.info(f"No more tool calls. Final response length: {len(final_response_text)}")
                # Append assistant response to session (user message was already added above)
                # Only store the final text response, not tool_use blocks
                await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                    "role": "assistant",
                    "content": final_response_text,  # Use accumulated text from all iterations
                })
                logger.info("Session messages saved to Redis")
                break

            # Execute tool calls and add results
            logger.info(f"Executing {len(tool_calls_this_round)} tool calls")
            current_messages.append({
                "role": "assistant",
                "content": response.get("content", []),
            })

            tool_results = []
            for tool_call in tool_calls_this_round:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                tool_id = tool_call["id"]

                # Execute the tool
                try:
                    if tool_name in mcp_server._tools:
                        handler = mcp_server._tools[tool_name]["handler"]
                        tool_def = mcp_server._tools[tool_name]

                        # Only inject scenario_id for tools that require it
                        # Check if the tool's input_schema has scenario_id as a property
                        input_schema = tool_def.get("input_schema", {})
                        schema_props = input_schema.get("properties", {})

                        if "scenario_id" in schema_props:
                            # Force the correct scenario_id - Claude may send wrong values
                            # (e.g., vertical name like "water_wastewater" instead of UUID)
                            tool_input["scenario_id"] = request.scenario_id
                            logger.info(f"Executing tool: {tool_name} with scenario_id: {request.scenario_id}")
                        else:
                            # Remove scenario_id if Claude sent it but the tool doesn't expect it
                            if "scenario_id" in tool_input:
                                del tool_input["scenario_id"]
                                logger.info(f"Executing tool: {tool_name} (removed unexpected scenario_id)")
                            else:
                                logger.info(f"Executing tool: {tool_name} (no scenario_id required)")

                        result = await handler(**tool_input)
                        result_str = json.dumps(result) if not isinstance(result, str) else result
                        logger.info(f"Tool {tool_name} completed successfully")
                        # Update tool call with result for frontend to extract scenario IDs
                        tool_call["result"] = result_str
                        tool_call["success"] = True
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result_str,
                        })
                    else:
                        tool_call["result"] = f"Error: Unknown tool '{tool_name}'"
                        tool_call["success"] = False
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: Unknown tool '{tool_name}'",
                            "is_error": True,
                        })
                except Exception as tool_error:
                    logger.error(f"Error executing tool {tool_name}: {tool_error}")
                    tool_call["result"] = f"Error: {str(tool_error)}"
                    tool_call["success"] = False
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: {str(tool_error)}",
                        "is_error": True,
                    })

            # Add tool results as a user message
            logger.info(f"Adding {len(tool_results)} tool results")
            # Log size of tool results for debugging
            for tr in tool_results:
                content_len = len(tr.get("content", "")) if isinstance(tr.get("content"), str) else 0
                logger.info(f"  Tool result for {tr.get('tool_use_id', 'unknown')}: {content_len} chars, is_error={tr.get('is_error', False)}")
            current_messages.append({
                "role": "user",
                "content": tool_results,
            })
        else:
            # Hit max iterations - still save the conversation with a helpful message
            logger.warning("AI tool execution hit max iterations")

            # Add a completion message if response is empty or minimal
            if not final_response_text or len(final_response_text.strip()) < 50:
                final_response_text = build_completion_message(all_tool_calls)

            # Append assistant response to session
            await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                "role": "assistant",
                "content": final_response_text,
            })

        return AIChatResponse(
            response=final_response_text,
            tool_calls=all_tool_calls,
            pending_actions=[],
        )

    except Exception as e:
        logger.error(f"Error calling AI: {e}", exc_info=True)
        raise ExternalServiceError(service="ai", message=f"AI request failed: {str(e)}", original_error=e)


@router.post("/chat/stream")
async def chat_with_ai_stream(
    request: AIChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StreamingResponse:
    """Send a message to the AI assistant with SSE streaming response.

    Streams events in real-time:
    - `start`: Conversation started
    - `thinking`: AI is processing
    - `tool_start`: Tool execution beginning (name, input)
    - `tool_complete`: Tool execution finished (name, success, result)
    - `text`: Text chunk from AI response
    - `done`: Conversation complete

    Args:
        request: Chat request
        current_user: Authenticated user
        db: Database session

    Returns:
        Server-Sent Events stream
    """
    user_id = str(current_user.id)
    scenario_id = request.scenario_id

    # Validate session exists for this user+scenario
    session = await AISessionService.get_session_for_scenario(user_id, scenario_id)
    if session is None:
        raise NotFoundError("AI session")

    # Get scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == uuid.UUID(scenario_id),
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    async def event_generator():
        """Generate SSE events for AI chat."""
        try:
            # Emit start event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Processing your request...'})}\n\n"

            # Register MCP tools
            _register_mcp_tools(db, user_id=str(current_user.id))

            # Get AI provider
            provider = await _get_anthropic_provider(db)

            # Sanitize scenario data
            sanitizer = DataSanitizer()
            scenario_context = scenario.definition.copy() if scenario.definition else {}
            sanitized_context = sanitizer.sanitize_scenario(scenario_context)

            # Store sanitizer mapping in Redis
            sanitizer_mappings = {
                "ip": sanitizer._ip_mapping,
                "mac": sanitizer._mac_mapping,
                "hostname": sanitizer._hostname_mapping,
            }
            await AISessionService.update_session_for_scenario(user_id, scenario_id, sanitizer_mappings=sanitizer_mappings)

            # Append user message to Redis
            await AISessionService.append_message_for_scenario(user_id, scenario_id, {"role": "user", "content": request.message})

            # Get updated session with messages
            session_data = await AISessionService.get_session_for_scenario(user_id, scenario_id)
            messages = session_data["messages"].copy()

            # Build system prompt (compact version for streaming)
            vertical = scenario.vertical or "unspecified"
            device_count = len(sanitized_context.get("devices", {}))
            flow_count = len(sanitized_context.get("flows", {}))

            # Parse user message to extract device counts
            parsed_counts = extract_device_counts(request.message)
            device_count_info = format_device_counts_for_prompt(parsed_counts)
            device_limit_warning = get_device_limit_warning(parsed_counts, MAX_DEVICES_PER_SCENARIO)

            system_prompt = build_system_prompt(
                scenario_name=scenario.name,
                vertical=vertical,
                device_count=device_count,
                flow_count=flow_count,
                device_count_info=device_count_info,
                device_limit_warning=device_limit_warning,
                parsed_counts=parsed_counts,
                compact=True,
            )

            system_message = {"role": "system", "content": system_prompt}

            # Get tools
            tools_list = [
                {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "input_schema": tool_info["input_schema"],
                }
                for tool_name, tool_info in mcp_server._tools.items()
            ]

            # Emit thinking event
            yield f"data: {json.dumps({'type': 'thinking', 'message': 'Analyzing your request...'})}\n\n"

            # Tool execution loop
            current_messages = [system_message] + messages
            all_tool_calls = []
            final_response_text = ""
            max_iterations = 15  # Increased for complex scenarios

            for iteration in range(max_iterations):
                yield f"data: {json.dumps({'type': 'thinking', 'iteration': iteration + 1, 'message': f'AI processing (iteration {iteration + 1})...'})}\n\n"

                response = await provider.chat(
                    messages=current_messages,
                    tools=tools_list,
                    max_tokens=16384,
                )

                # Extract text and tool calls
                response_text = ""
                tool_calls_this_round = []

                for content in response.get("content", []):
                    if content["type"] == "text":
                        text_chunk = content["text"]
                        response_text += text_chunk
                        # Stream text chunks
                        if text_chunk:
                            yield f"data: {json.dumps({'type': 'text', 'content': text_chunk})}\n\n"
                    elif content["type"] == "tool_use":
                        tool_calls_this_round.append({
                            "id": content["id"],
                            "name": content["name"],
                            "input": content["input"],
                        })

                final_response_text += response_text
                all_tool_calls.extend(tool_calls_this_round)

                # Check for convergence (stuck loops)
                should_stop, stop_reason = detect_convergence(all_tool_calls)
                if should_stop:
                    logger.warning(f"Convergence detected (streaming): {stop_reason}")
                    # Generate completion message
                    tool_names = [tc.get("name", "") for tc in all_tool_calls]
                    device_adds = sum(1 for n in tool_names if n == "add_device")
                    flow_adds = sum(1 for n in tool_names if n == "add_flow")

                    completion_parts = []
                    if device_adds > 0:
                        completion_parts.append(f"{device_adds} devices added")
                    if flow_adds > 0:
                        completion_parts.append(f"{flow_adds} flows created")

                    if completion_parts:
                        completion_msg = f"Scenario creation completed! {', '.join(completion_parts)}."
                    else:
                        completion_msg = "Operation completed."

                    yield f"data: {json.dumps({'type': 'text', 'content': completion_msg})}\n\n"
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": completion_msg,
                    })
                    break

                # If no tool calls, we're done
                if not tool_calls_this_round:
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": final_response_text,
                    })
                    break

                # Execute tool calls
                current_messages.append({
                    "role": "assistant",
                    "content": response.get("content", []),
                })

                tool_results = []
                for tool_call in tool_calls_this_round:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    tool_id = tool_call["id"]

                    # Emit tool_start event
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': tool_name, 'input': tool_input})}\n\n"

                    try:
                        if tool_name in mcp_server._tools:
                            handler = mcp_server._tools[tool_name]["handler"]
                            tool_def = mcp_server._tools[tool_name]

                            # Handle scenario_id injection
                            input_schema = tool_def.get("input_schema", {})
                            schema_props = input_schema.get("properties", {})

                            if "scenario_id" in schema_props:
                                tool_input["scenario_id"] = request.scenario_id
                            elif "scenario_id" in tool_input:
                                del tool_input["scenario_id"]

                            result = await handler(**tool_input)
                            result_str = json.dumps(result) if not isinstance(result, str) else result

                            # Emit tool_complete event
                            yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': True, 'result_preview': str(result)[:200] if result else None})}\n\n"

                            # Update tool call with result for frontend to extract scenario IDs
                            tool_call["result"] = result_str
                            tool_call["success"] = True

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": result_str,
                            })
                        else:
                            yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': False, 'error': f'Unknown tool: {tool_name}'})}\n\n"
                            tool_call["result"] = f"Error: Unknown tool '{tool_name}'"
                            tool_call["success"] = False
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": f"Error: Unknown tool '{tool_name}'",
                                "is_error": True,
                            })
                    except Exception as tool_error:
                        logger.error(f"Error executing tool {tool_name}: {tool_error}")
                        yield f"data: {json.dumps({'type': 'tool_complete', 'name': tool_name, 'success': False, 'error': str(tool_error)})}\n\n"
                        tool_call["result"] = f"Error: {str(tool_error)}"
                        tool_call["success"] = False
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: {str(tool_error)}",
                            "is_error": True,
                        })

                # Add tool results
                current_messages.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # Hit max iterations
                if final_response_text:
                    await AISessionService.append_message_for_scenario(user_id, scenario_id, {
                        "role": "assistant",
                        "content": final_response_text,
                    })

            # Emit done event with summary
            yield f"data: {json.dumps({'type': 'done', 'response': final_response_text, 'tool_calls': all_tool_calls, 'tool_count': len(all_tool_calls)})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/actions/{action_id}/accept")
async def accept_ai_action(
    action_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> dict[str, Any]:
    """Accept and execute a proposed AI action.

    Args:
        action_id: Action ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Execution result
    """
    action = await AISessionService.get_pending_action(action_id)
    if action is None:
        raise NotFoundError("AI action", action_id)

    # Verify user owns the action
    if action.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    # Execute the action (call the appropriate tool)
    # This is a placeholder - implement actual execution
    result = {"success": True, "action_id": action_id}

    await AISessionService.delete_pending_action(action_id)
    return result


@router.post("/actions/{action_id}/reject")
async def reject_ai_action(
    action_id: str,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Reject a proposed AI action.

    Args:
        action_id: Action ID
        current_user: Authenticated user

    Returns:
        Success message
    """
    action = await AISessionService.get_pending_action(action_id)
    if action is None:
        raise NotFoundError("AI action", action_id)

    # Verify user owns the action
    if action.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    await AISessionService.delete_pending_action(action_id)
    return {"message": "Action rejected"}


@router.get("/tools", response_model=list[AIToolDefinition])
async def list_ai_tools(current_user: CurrentUser) -> list[AIToolDefinition]:
    """List available AI tools.

    Args:
        current_user: Authenticated user

    Returns:
        List of tool definitions
    """
    tools = [
        AIToolDefinition(
            name="list_devices",
            description="List all devices in a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="add_device",
            description="Add a device to a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="update_device",
            description="Update a device in a scenario",
            category="devices",
        ),
        AIToolDefinition(
            name="list_flows",
            description="List all flows in a scenario",
            category="flows",
        ),
        AIToolDefinition(
            name="add_flow",
            description="Add a flow to a scenario",
            category="flows",
        ),
        AIToolDefinition(
            name="suggest_flows",
            description="Suggest flows for a device",
            category="flows",
        ),
        AIToolDefinition(
            name="validate_topology",
            description="Validate scenario topology",
            category="validation",
        ),
        AIToolDefinition(
            name="score_realism",
            description="Score scenario realism",
            category="validation",
        ),
        AIToolDefinition(
            name="auto_assign_addresses",
            description="Auto-assign IP and MAC addresses",
            category="addressing",
        ),
    ]

    return tools


# ==================== AI Scenario Creation Wizard ====================


@router.post("/scenarios/generate-preview", response_model=AIScenarioPreviewResponse)
async def generate_scenario_preview(
    request: AIScenarioGenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIScenarioPreviewResponse:
    """Generate a scenario preview from natural language description.

    This creates a preview without saving to the database. The preview
    is stored in Redis for 30 minutes and can be used to create the
    actual scenario.

    Uses Claude AI for intelligent scenario design with automatic fallback
    to rule-based generation if AI is unavailable.

    Args:
        request: Generation request with name, vertical, description
        current_user: Authenticated user
        db: Database session

    Returns:
        Preview with devices, flows, and summary statistics
    """
    from app.ai_services.ai_scenario_designer import AIScenarioDesigner

    # Use AI-enhanced scenario designer (with rule-based fallback)
    # Use a placeholder range_index for preview - actual IPs will be assigned during create-from-preview
    designer = AIScenarioDesigner(db, range_index=1)

    try:
        result = await designer.design_scenario(
            description=request.description,
            name=request.name,
            duration_ms=request.duration_ms,
            preferred_vendors=request.vendors,
            preferred_protocols=request.protocols,
            vertical=request.vertical,
            total_device_count=request.total_device_count,
            device_counts=request.device_counts,
            include_vulnerable_devices=request.include_vulnerable_devices,
        )
        scenario = result.scenario
        ai_enhanced = result.ai_enhanced
        ai_features = result.ai_features
        design_rationale = result.design_rationale

        if result.fallback_reason:
            logger.info(f"AI fallback: {result.fallback_reason}")
    except Exception as e:
        logger.error(f"Failed to generate scenario preview: {e}", exc_info=True)
        raise ExternalServiceError(service="ai", message=f"Failed to generate scenario: {str(e)}", original_error=e)

    # Enforce device limit
    if len(scenario.devices) > MAX_DEVICES_PER_SCENARIO:
        raise ValidationError(f"Generated scenario exceeds device limit ({len(scenario.devices)} > {MAX_DEVICES_PER_SCENARIO}). Please request fewer devices.")

    # Build preview data
    devices = [
        AIScenarioPreviewDevice(
            device_id=d.device_id,
            name=d.name,
            device_type=d.device_type,
            vendor=d.vendor,
            ip_address=d.ip_address,
            mac_address=d.mac_address,
            zone=d.zone,
            protocols=d.protocols,
            fingerprint_model=d.fingerprint_model,
        )
        for d in scenario.devices
    ]

    # Apply CVE vulnerabilities if requested
    vulnerable_device_count = 0
    cve_ids_used: set[str] = set()

    if request.include_vulnerable_devices:
        import random
        from app.services.cve_data import get_cves_for_vendor

        high_value_types = {"plc", "rtu", "hmi", "scada_server"}

        for device in devices:
            if not device.vendor:
                continue

            vendor_cves = get_cves_for_vendor(device.vendor)
            if not vendor_cves:
                continue

            # 25% base probability, 40% for high-value targets
            prob = 0.40 if device.device_type in high_value_types else 0.25

            if random.random() < prob:
                selected_cve = random.choice(vendor_cves)
                device.cve_ids = [selected_cve["cve_id"]]
                device.is_vulnerable = True
                vulnerable_device_count += 1
                cve_ids_used.add(selected_cve["cve_id"])

    flows = [
        AIScenarioPreviewFlow(
            flow_id=f.flow_id,
            source_device_id=f.source_device_id,
            destination_device_id=f.destination_device_id,
            protocol=f.protocol,
            description=f.description,
        )
        for f in scenario.flows
    ]

    # Extract unique protocols and vendors
    protocols_used = list(set(f.protocol for f in scenario.flows))
    vendors_used = list(set(d.vendor for d in scenario.devices if d.vendor))

    # Store preview in Redis
    preview_data = {
        "name": request.name,
        "vertical": request.vertical,
        "description": request.description,
        "duration_ms": request.duration_ms,
        "devices": [d.model_dump() for d in devices],
        "flows": [f.model_dump() for f in flows],
        "zones": scenario.zones,
        "protocols_used": protocols_used,
        "vendors_used": vendors_used,
        "include_vulnerable_devices": request.include_vulnerable_devices,
    }

    preview_id = await AIScenarioPreviewService.store_preview(
        str(current_user.id), preview_data
    )

    return AIScenarioPreviewResponse(
        preview_id=preview_id,
        name=request.name,
        vertical=request.vertical,
        description=request.description,
        devices=devices,
        flows=flows,
        device_count=len(devices),
        flow_count=len(flows),
        protocols_used=protocols_used,
        vendors_used=vendors_used,
        zones=scenario.zones,
        ai_enhanced=ai_enhanced,
        ai_features=ai_features,
        design_rationale=design_rationale,
        vulnerable_device_count=vulnerable_device_count,
        cve_ids_used=list(cve_ids_used),
    )


@router.post("/scenarios/generate-preview-stream")
async def generate_scenario_preview_stream(
    request: AIScenarioGenerateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StreamingResponse:
    """Generate a scenario preview with real-time SSE progress events.

    Streams phased progress to the client so they see what's happening
    instead of staring at a spinner for minutes.

    SSE Event types:
    - ``phase``: ``{step, total, message}`` — progress update
    - ``done``:  ``{preview: AIScenarioPreviewResponse}`` — complete
    - ``error``: ``{message}`` — failure

    Args:
        request: Generation request with name, vertical, description
        current_user: Authenticated user
        db: Database session

    Returns:
        Server-Sent Events stream
    """
    from app.ai_services.ai_scenario_designer import AIScenarioDesigner

    def _sse(event_type: str, **data: Any) -> str:
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"

    async def event_generator():  # noqa: C901
        try:
            # Phase 1: Initialize
            yield _sse("phase", step=1, total=6, message="Initializing AI scenario designer...")
            designer = AIScenarioDesigner(db, range_index=1)

            try:
                provider = await designer.phase_get_provider()
            except ValueError:
                # Fall back to rule-based generation
                yield _sse("phase", step=2, total=6, message="AI not configured — using rule-based generation...")
                result = designer._fallback_to_rules(
                    description=request.description,
                    name=request.name,
                    duration_ms=request.duration_ms,
                    vertical=request.vertical,
                    preferred_vendors=request.vendors,
                    preferred_protocols=request.protocols,
                    total_device_count=request.total_device_count,
                    device_counts=request.device_counts,
                    reason="AI provider not configured",
                )
                # Skip to finalize with the fallback result
                yield _sse("phase", step=5, total=6, message="Building devices, flows, and zones...")
                # Build preview from fallback result and jump to finalize
                preview_response = await _finalize_preview(
                    request, result, current_user, db
                )
                yield _sse("done", preview=preview_response)
                return

            # Phase 2: Build prompts
            yield _sse("phase", step=2, total=6, message="Building prompts from device fingerprints...")
            system_prompt, user_prompt = designer.phase_build_prompts(
                description=request.description,
                vertical=request.vertical,
                preferred_vendors=request.vendors,
                preferred_protocols=request.protocols,
                total_device_count=request.total_device_count,
                device_counts=request.device_counts,
            )

            # Phase 3: Call AI (the slow part)
            yield _sse("phase", step=3, total=6, message="Waiting for AI response (this may take a minute)...")
            response = await designer.phase_call_ai(
                provider=provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                total_device_count=request.total_device_count,
            )

            # Phase 4: Parse response
            yield _sse("phase", step=4, total=6, message="Parsing AI response...")
            ai_design = designer.phase_parse_response(response)

            # Phase 5: Build scenario
            yield _sse("phase", step=5, total=6, message="Building devices, flows, and zones...")
            result = designer.phase_build_scenario(
                ai_design=ai_design,
                name=request.name,
                description=request.description,
                duration_ms=request.duration_ms,
                vertical=request.vertical,
            )

            # Phase 6: Finalize
            yield _sse("phase", step=6, total=6, message="Finalizing preview...")
            preview_response = await _finalize_preview(
                request, result, current_user, db
            )

            yield _sse("done", preview=preview_response)

        except Exception as e:
            logger.error(f"Streaming preview generation error: {e}", exc_info=True)
            yield _sse("error", message=str(e))

    async def _finalize_preview(
        req: AIScenarioGenerateRequest,
        result: Any,
        user: Any,
        session: Any,
    ) -> dict[str, Any]:
        """Build preview response, apply CVEs, store in Redis."""
        from app.ai_services.device_namer import AIDeviceNamer, DeviceNamingContext
        from app.mcp_server.ai_providers import AIProviderFactory

        scenario = result.scenario

        if len(scenario.devices) > MAX_DEVICES_PER_SCENARIO:
            raise ValidationError(
                f"Generated scenario exceeds device limit "
                f"({len(scenario.devices)} > {MAX_DEVICES_PER_SCENARIO}). "
                "Please request fewer devices."
            )

        # Enrich generic names (e.g. "PLC-001") with process-aware names
        # via AIDeviceNamer — same service used by template creation path.
        try:
            ai_provider = await AIProviderFactory.create(session)
            namer = AIDeviceNamer()
            zone_dict = {
                z.get("name", f"zone_{i}"): z
                for i, z in enumerate(scenario.zones)
            }
            context = DeviceNamingContext(
                vertical=scenario.vertical,
                template_name=req.name or scenario.name,
                template_description=req.description,
                zones=zone_dict,
            )
            device_dicts = [
                {
                    "id": d.device_id,
                    "name": d.name,
                    "type": d.device_type,
                    "vendor": d.vendor or "",
                    "zoneId": d.zone or "",
                    "protocols": d.protocols,
                }
                for d in scenario.devices
            ]
            enhanced = await namer.enhance_device_names(
                device_dicts, context, ai_provider
            )
            # Apply enhanced names back to GeneratedDevice objects
            name_map = {d["id"]: d["name"] for d in enhanced}
            for d in scenario.devices:
                if d.device_id in name_map:
                    d.name = name_map[d.device_id]
            logger.info(f"AI naming enriched {len(name_map)} device names")
        except Exception as e:
            logger.warning(f"AI device naming unavailable, keeping generic names: {e}")

        devices = [
            AIScenarioPreviewDevice(
                device_id=d.device_id,
                name=d.name,
                device_type=d.device_type,
                vendor=d.vendor,
                ip_address=d.ip_address,
                mac_address=d.mac_address,
                zone=d.zone,
                protocols=d.protocols,
                fingerprint_model=d.fingerprint_model,
            )
            for d in scenario.devices
        ]

        # Apply CVE vulnerabilities
        vulnerable_device_count = 0
        cve_ids_used: set[str] = set()

        if req.include_vulnerable_devices:
            import random
            from app.services.cve_data import get_cves_for_vendor

            high_value_types = {"plc", "rtu", "hmi", "scada_server"}
            for device in devices:
                if not device.vendor:
                    continue
                vendor_cves = get_cves_for_vendor(device.vendor)
                if not vendor_cves:
                    continue
                prob = 0.40 if device.device_type in high_value_types else 0.25
                if random.random() < prob:
                    selected_cve = random.choice(vendor_cves)
                    device.cve_ids = [selected_cve["cve_id"]]
                    device.is_vulnerable = True
                    vulnerable_device_count += 1
                    cve_ids_used.add(selected_cve["cve_id"])

        flows = [
            AIScenarioPreviewFlow(
                flow_id=f.flow_id,
                source_device_id=f.source_device_id,
                destination_device_id=f.destination_device_id,
                protocol=f.protocol,
                description=f.description,
            )
            for f in scenario.flows
        ]

        protocols_used = list(set(f.protocol for f in scenario.flows))
        vendors_used = list(set(d.vendor for d in scenario.devices if d.vendor))

        # Store in Redis
        preview_data = {
            "name": req.name,
            "vertical": req.vertical,
            "description": req.description,
            "duration_ms": req.duration_ms,
            "devices": [d.model_dump() for d in devices],
            "flows": [f.model_dump() for f in flows],
            "zones": scenario.zones,
            "conduits": scenario.conduits,
            "protocols_used": protocols_used,
            "vendors_used": vendors_used,
            "include_vulnerable_devices": req.include_vulnerable_devices,
        }

        preview_id = await AIScenarioPreviewService.store_preview(
            str(user.id), preview_data
        )

        return AIScenarioPreviewResponse(
            preview_id=preview_id,
            name=req.name,
            vertical=req.vertical,
            description=req.description,
            devices=devices,
            flows=flows,
            device_count=len(devices),
            flow_count=len(flows),
            protocols_used=protocols_used,
            vendors_used=vendors_used,
            zones=scenario.zones,
            ai_enhanced=result.ai_enhanced,
            ai_features=result.ai_features,
            design_rationale=result.design_rationale,
            vulnerable_device_count=vulnerable_device_count,
            cve_ids_used=list(cve_ids_used),
        ).model_dump()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/scenarios/create-from-preview", response_model=AIScenarioCreateFromPreviewResponse)
async def create_scenario_from_preview(
    request: AIScenarioCreateFromPreviewRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AIScenarioCreateFromPreviewResponse:
    """Create an actual scenario from a validated preview.

    Args:
        request: Request with preview_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Created scenario information
    """
    # Get preview
    preview = await AIScenarioPreviewService.get_preview(
        request.preview_id, str(current_user.id)
    )

    if preview is None:
        raise NotFoundError("AI scenario preview", request.preview_id)

    # Convert preview to database format
    # First, build zones with proper layout and subnet configuration
    zones = {}
    zone_device_map = {}  # device_id -> zone_name mapping
    zone_ip_counters = {}  # zone_name -> next host number for that zone
    preview_zones = preview.get("zones", [])

    # Layout zones in a grid (2 columns)
    zone_width = 450
    zone_height = 350
    zone_margin = 50
    zones_per_row = 2

    for idx, z in enumerate(preview_zones):
        zone_name = z.get("name", f"zone_{idx}")
        zone_id = z.get("id", zone_name.lower().replace(" ", "_"))
        row = idx // zones_per_row
        col = idx % zones_per_row

        zone_x = zone_margin + col * (zone_width + zone_margin)
        zone_y = zone_margin + row * (zone_height + zone_margin)

        # Preserve subnet_offset from preview or assign sequentially
        subnet_offset = z.get("subnet_offset", idx)

        zones[zone_name] = {
            "id": zone_id,
            "name": zone_name.replace("_", " ").title(),
            "type": "network",
            "position": {"x": zone_x, "y": zone_y},
            "dimensions": {"width": zone_width, "height": zone_height},
            "deviceIds": z.get("device_ids", []),
            "subnet_offset": subnet_offset,
            "level": z.get("level"),
            "vlan": z.get("vlan", 100 + idx * 10),
        }

        # Initialize IP counter for this zone (start at .10)
        zone_ip_counters[zone_name] = 10

        # Map devices to their zone
        for device_id in z.get("device_ids", []):
            zone_device_map[device_id] = zone_name

    # Create database scenario first to get ID for IP allocation
    db_scenario = Scenario(
        user_id=current_user.id,
        name=preview["name"],
        description=preview["description"],
        vertical=preview["vertical"],
        total_duration_ms=preview.get("duration_ms", 300000),
        definition={},  # Will be populated below
        version=1,
    )
    db.add(db_scenario)
    await db.flush()  # Get the scenario ID without committing

    # Allocate IP range for this scenario
    try:
        ip_allocation = await IPManagementService.allocate_range(db, db_scenario.id)
        await db.flush()  # Ensure allocation is visible for subsequent get_next_ip calls
        logger.info(f"Allocated IP range {ip_allocation.cidr_range} for scenario {db_scenario.id}")
    except ValueError as e:
        logger.error(f"Failed to allocate IP range: {e}")
        raise ExternalServiceError(service="ip_management", message=f"Failed to allocate IP range: {e}", original_error=e)

    # Build devices with positions inside their zones
    devices = {}
    zone_device_counters = {}  # Track device placement within each zone

    for d in preview.get("devices", []):
        device_id = d["device_id"]
        zone_name = zone_device_map.get(device_id)
        vendor = (d.get("vendor") or "").lower()
        device_type = d.get("device_type", "")
        fingerprint_model = d.get("fingerprint_model")

        # Calculate position inside zone
        if zone_name and zone_name in zones:
            zone = zones[zone_name]
            zone_x = zone["position"]["x"]
            zone_y = zone["position"]["y"]

            # Get device index within this zone
            if zone_name not in zone_device_counters:
                zone_device_counters[zone_name] = 0
            device_idx = zone_device_counters[zone_name]
            zone_device_counters[zone_name] += 1

            # Grid layout inside zone (3 columns, with padding)
            devices_per_row = 3
            device_padding = 30
            device_spacing_x = 130
            device_spacing_y = 100

            row = device_idx // devices_per_row
            col = device_idx % devices_per_row

            device_x = zone_x + device_padding + col * device_spacing_x
            device_y = zone_y + 60 + row * device_spacing_y  # 60px for zone header
        else:
            # Fallback position for devices without zones
            device_x = 100 + (len(devices) % 5) * 150
            device_y = 100 + (len(devices) // 5) * 120

        # Get IP based on zone's /24 subnet
        # Each zone has its own subnet: 10.{range_index}.{subnet_offset}.0/24
        range_index = ip_allocation.range_index
        if zone_name and zone_name in zones:
            zone_config = zones[zone_name]
            subnet_offset = zone_config.get("subnet_offset", 0)
            host_num = zone_ip_counters.get(zone_name, 10)
            zone_ip_counters[zone_name] = host_num + 1
            if host_num > 254:
                host_num = 10  # Wrap around if zone has too many devices

            ip_address = f"10.{range_index}.{subnet_offset}.{host_num}"
            gateway = f"10.{range_index}.{subnet_offset}.1"
            subnet_mask = "255.255.255.0"

            # Update zone's network config
            if "network" not in zone_config:
                zone_config["network"] = {}
            zone_config["network"]["subnet"] = f"10.{range_index}.{subnet_offset}.0/24"
            zone_config["network"]["gateway"] = gateway
            zone_config["network"]["subnet_offset"] = subnet_offset

            logger.debug(f"Assigned IP {ip_address} to device {device_id} in zone {zone_name}")
        else:
            # Fallback for devices without zones - use sequential IP from range
            try:
                ip_info = await IPManagementService.get_next_ip(db, db_scenario.id)
                ip_address = ip_info["ip_address"]
                subnet_mask = ip_info["subnet_mask"]
                gateway = ip_info["gateway"]
                logger.debug(f"Assigned fallback IP {ip_address} to device {device_id} (no zone)")
            except ValueError as e:
                logger.warning(f"IP allocation failed for device {device_id}: {e}. Using fallback.")
                ip_address = d.get("ip_address", "10.0.0.10")
                subnet_mask = "255.255.255.0"
                gateway = "10.0.0.1"

        # Get fingerprint data for deep fingerprinting (lookup BEFORE MAC generation)
        fingerprint_data = None
        cache = get_fingerprint_cache()
        if vendor and fingerprint_model:
            fingerprint_data = cache.get_by_vendor_model(vendor, fingerprint_model)
        elif vendor:
            # Try to get a fingerprint for this vendor
            vendor_fps = cache.get_by_vendor(vendor)
            if vendor_fps:
                # Pick one appropriate for device type if possible
                for fp in vendor_fps:
                    fp_type = fp.get("device_type", "").lower()
                    if fp_type == device_type or not fp_type:
                        fingerprint_data = fp
                        break
                if not fingerprint_data:
                    fingerprint_data = vendor_fps[0]

        # Generate MAC address using fingerprint OUIs when available
        fp_ouis = fingerprint_data.get("oui_prefixes") if fingerprint_data else None
        mac_address = generate_mac(
            vendor=vendor,
            device_type=device_type,
            oui_patterns=fp_ouis if fp_ouis else None,
        )

        # Build network config with deep fingerprint data
        network_config = {
            "macAddress": mac_address,
            "ipAddress": ip_address,
            "subnetMask": subnet_mask,
            "gateway": gateway,
        }

        # Filter protocols to only those supported by the fingerprint
        # This is the CRITICAL validation step that prevents protocol_identity_mismatch
        requested_protocols = d.get("protocols", [])
        validated_protocols = []

        if fingerprint_data:
            for proto in requested_protocols:
                identity_key = PROTOCOL_TO_IDENTITY_KEY.get(proto)
                if identity_key:
                    identity = fingerprint_data.get(identity_key)
                    if identity and isinstance(identity, dict) and len(identity) > 0:
                        validated_protocols.append(proto)
                    else:
                        logger.warning(
                            f"Device '{d['name']}': Removed protocol '{proto}' "
                            f"(no {identity_key} in fingerprint)"
                        )
                else:
                    # Protocol doesn't require identity (http, ssh, etc.)
                    validated_protocols.append(proto)
        else:
            # No fingerprint - device will have no protocols
            if requested_protocols:
                logger.warning(
                    f"Device '{d['name']}': No fingerprint data - removed all protocols {requested_protocols}"
                )

        # Build device with fingerprint data
        device_def = {
            "id": device_id,
            "name": d["name"],
            "type": device_type,
            "protocols": validated_protocols,  # Use validated protocols
            "position": {"x": device_x, "y": device_y},
            "zoneId": zone_name,
            "network": network_config,
            "vendor": d.get("vendor"),
            "fingerprint_model": fingerprint_model,  # CRITICAL: Store fingerprint_model
        }

        # Apply deep fingerprint data if available
        # Use "vendorFingerprint" key — the standard key expected by
        # enrich_device_serial_numbers, enrich_device_unique_identifiers,
        # FingerprintApplicator, and the traffic generator.
        if fingerprint_data:
            device_def["vendorFingerprint"] = {
                "vendor": fingerprint_data.get("vendor"),
                "vendor_family": fingerprint_data.get("vendor_family"),
                "model": fingerprint_data.get("model"),
                "firmware_version": fingerprint_data.get("firmware_version"),
                "serial_number": _generate_serial_number(vendor, fingerprint_data),
            }

            # Protocol-specific identity data (all 7 protocols)
            if fingerprint_data.get("modbus_identity"):
                device_def["vendorFingerprint"]["modbus_identity"] = fingerprint_data["modbus_identity"]
            if fingerprint_data.get("ethernet_ip_identity"):
                device_def["vendorFingerprint"]["ethernet_ip_identity"] = fingerprint_data["ethernet_ip_identity"]
            if fingerprint_data.get("profinet_identity"):
                device_def["vendorFingerprint"]["profinet_identity"] = fingerprint_data["profinet_identity"]
            if fingerprint_data.get("s7_identity"):
                device_def["vendorFingerprint"]["s7_identity"] = fingerprint_data["s7_identity"]
            if fingerprint_data.get("snmp_identity"):
                device_def["vendorFingerprint"]["snmp_identity"] = fingerprint_data["snmp_identity"]
            if fingerprint_data.get("bacnet_identity"):
                device_def["vendorFingerprint"]["bacnet_identity"] = fingerprint_data["bacnet_identity"]
            if fingerprint_data.get("opc_ua_identity"):
                device_def["vendorFingerprint"]["opc_ua_identity"] = fingerprint_data["opc_ua_identity"]

            # TCP stack characteristics
            if fingerprint_data.get("tcp_stack"):
                device_def["vendorFingerprint"]["tcp_stack"] = fingerprint_data["tcp_stack"]

            # Response timing
            if fingerprint_data.get("response_timing"):
                device_def["vendorFingerprint"]["response_timing"] = fingerprint_data["response_timing"]

        # Resolve CVE identity overrides if device has CVE IDs
        cve_ids = d.get("cve_ids", [])
        if cve_ids:
            try:
                variant = await CVEFingerprintService.get_best_variant_for_device(
                    db,
                    vendor=vendor,
                    fingerprint_model=fingerprint_model,
                    cve_ids=cve_ids,
                )
                if variant:
                    device_def["vulnerableVariantId"] = str(variant.id)
                    device_def["vulnerableFirmware"] = variant.firmware_version
                    device_def["cveIds"] = cve_ids
                    # Store identity overrides for traffic generation - CRITICAL for CVE detection
                    device_def["cveIdentityOverrides"] = (
                        CVEFingerprintService.extract_identity_overrides(variant)
                    )
                    logger.info(
                        f"Resolved CVE for AI device {device_id}: {variant.display_name}"
                    )
            except Exception as e:
                logger.warning(f"Failed to resolve CVE for AI device {device_id}: {e}")

        devices[device_id] = device_def

    flows = {}
    for f in preview.get("flows", []):
        flows[f["flow_id"]] = {
            "id": f["flow_id"],
            "name": f["description"],
            "sourceDeviceId": f["source_device_id"],
            "targetDeviceId": f["destination_device_id"],
            "protocol": f["protocol"],
            "timing": {"intervalMs": 1000, "jitterMs": 50},
            "protocolConfig": {},
            "phases": {
                "startup": True,
                "steadyState": True,
                "maintenance": False,
                "shutdown": True,
            },
        }

    # Build conduits from preview or auto-generate from Purdue adjacency
    preview_conduits = preview.get("conduits", {})
    if preview_conduits:
        conduits = preview_conduits
    else:
        # Auto-generate from zone Purdue levels as fallback
        from app.services.conduit_service import generate_default_conduits
        conduits = generate_default_conduits(list(zones.values()))

    # Update scenario definition (scenario was created earlier for IP allocation)
    db_scenario.definition = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
        "conduits": conduits,
        "phases": [],
        "events": [],
    }

    # Set addressing config to track the IP allocation
    db_scenario.addressing_config = {
        "ip_range": ip_allocation.cidr_range,
        "range_index": ip_allocation.range_index,
        "auto_assign_enabled": True,
    }

    # CRITICAL: Ensure all devices have unique serial numbers for each protocol
    # This prevents Cyber Vision from merging devices with identical fingerprints
    for dev_id, dev in devices.items():
        enrich_device_serial_numbers(dev, dev_id, str(db_scenario.id))
        enrich_device_unique_identifiers(dev, dev_id, str(db_scenario.id))

    await db.commit()
    await db.refresh(db_scenario)

    # Delete preview after successful creation
    await AIScenarioPreviewService.delete_preview(request.preview_id)

    logger.info(
        f"Created scenario {db_scenario.id} from preview {request.preview_id} "
        f"with {len(devices)} devices and {len(flows)} flows"
    )

    return AIScenarioCreateFromPreviewResponse(
        success=True,
        scenario_id=str(db_scenario.id),
        name=preview["name"],
        device_count=len(devices),
        flow_count=len(flows),
    )


@router.post("/generate-description", response_model=GenerateDescriptionResponse)
async def generate_scenario_description(
    request: GenerateDescriptionRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> GenerateDescriptionResponse:
    """Generate an AI description for an existing scenario.

    Analyzes the scenario's devices, flows, zones, and configuration
    to produce a meaningful description.

    Args:
        request: Request with scenario_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Generated description and scenario metadata
    """
    # Fetch scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == request.scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise NotFoundError("Scenario", str(request.scenario_id))

    # Extract scenario data
    definition = scenario.definition or {}
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})

    # Build device summary
    device_types = {}
    vendors = set()
    for d in devices.values():
        dtype = d.get("type", "unknown")
        device_types[dtype] = device_types.get(dtype, 0) + 1
        if d.get("vendor"):
            vendors.add(d["vendor"])

    device_summary = ", ".join([f"{count} {dtype}(s)" for dtype, count in device_types.items()])
    if not device_summary:
        device_summary = "No devices"

    # Extract protocols from flows
    protocols = set()
    for f in flows.values():
        if f.get("protocol"):
            protocols.add(f["protocol"])

    # Get zone names
    zone_names = [z.get("name", z.get("id", "unnamed")) for z in zones.values()]

    # Build prompt for AI
    prompt = f"""You are an OT network specialist. Generate a concise 2-3 sentence description for this industrial network simulation scenario.

Scenario Name: {scenario.name}
Industry Vertical: {scenario.vertical or 'Not specified'}
Devices: {device_summary}
Vendors: {', '.join(vendors) if vendors else 'Not specified'}
Protocols: {', '.join(protocols) if protocols else 'None configured'}
Network Zones: {', '.join(zone_names) if zone_names else 'No zones defined'}
Communication Flows: {len(flows)}

Write ONLY the description text. Do not include any preamble, labels, or formatting. Just the plain description sentences."""

    # Get AI provider and generate description
    try:
        provider = await _get_ai_provider(db)
        response = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )

        # Extract text from response
        description = ""
        if isinstance(response, dict):
            content = response.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        description = block.get("text", "").strip()
                        break
            elif isinstance(content, str):
                description = content.strip()
        else:
            description = str(response).strip()

        if not description:
            description = f"A {scenario.vertical or 'industrial'} network simulation scenario with {len(devices)} devices and {len(flows)} communication flows."

    except (ValidationError, NotFoundError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Failed to generate description: {e}")
        # Provide a fallback description
        description = f"A {scenario.vertical or 'industrial'} network simulation scenario featuring {device_summary.lower()} across {len(zones)} network zones with {len(flows)} communication flows."

    return GenerateDescriptionResponse(
        description=description,
        scenario_name=scenario.name,
        device_count=len(devices),
        flow_count=len(flows),
        protocols=list(protocols),
    )


# ---------------------------------------------------------------------------
# Scenario Review / Critique
# ---------------------------------------------------------------------------

from app.schemas.scenario_review import (
    ReviewFinding,
    ScenarioReviewResponse,
    RemediationAction,
    RemediateRequest,
    RemediateResponse,
    RemediationResult,
)

SCENARIO_REVIEW_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "overall_score", "findings"],
    "properties": {
        "summary": {"type": "string"},
        "overall_score": {"type": "integer"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "category",
                    "severity",
                    "title",
                    "description",
                    "suggestion",
                    "affected_device_ids",
                    "affected_flow_ids",
                    "remediation",
                ],
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "topology",
                            "protocols",
                            "timing",
                            "realism",
                            "security",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "warning", "suggestion", "info"],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "affected_device_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "affected_flow_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "remediation": {
                        "anyOf": [
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["action_type", "params_json"],
                                "properties": {
                                    "action_type": {
                                        "type": "string",
                                        "enum": [
                                            "assign_fingerprint",
                                            "repair_protocols",
                                            "update_flow_timing",
                                            "add_flow",
                                            "assign_ips",
                                            "regenerate_macs",
                                            "apply_cve",
                                            "remove_device",
                                            "rename_device",
                                        ],
                                    },
                                    "params_json": {
                                        "type": "string",
                                        "description": "JSON-encoded params object",
                                    },
                                },
                            },
                            {"type": "null"},
                        ],
                    },
                },
            },
        },
    },
}

# Scoring rules, review categories, remediation action schemas, and
# device-naming conventions live in the ``packetarch-scenario-review``,
# ``packetarch-fingerprint-validator``, and ``packetarch-device-naming``
# skills. The per-call system message below is kept minimal so those
# skill bodies remain cache-hits across requests.
_REVIEW_SYSTEM_PROMPT = (
    "You are the PacketArch scenario quality reviewer. Follow the "
    "review workflow and scoring guide from the attached skills. The "
    "user message contains a compact scenario representation plus the "
    "readiness check results — build on them, do not duplicate."
)


def _get_available_fingerprints() -> dict[str, list[str]]:
    """Return vendor → [model, ...] mapping from fingerprint cache."""
    from app.services.fingerprint_cache import get_fingerprint_cache

    cache = get_fingerprint_cache()
    vendor_models: dict[str, list[str]] = {}
    for fp in cache.get_all():
        vendor = fp.get("vendor", "")
        model = fp.get("model", "")
        if vendor and model:
            vendor_models.setdefault(vendor, []).append(model)
    return vendor_models


def _build_review_context(definition: dict) -> dict[str, Any]:
    """Build a compact scenario representation for the AI review prompt."""
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})
    zones = definition.get("zones", {})
    phases = definition.get("phases", [])

    # Build device ID-to-name map for flow resolution
    device_name_map: dict[str, str] = {}
    for did, d in devices.items():
        device_name_map[did] = d.get("name", did)

    compact_devices = []
    for did, d in devices.items():
        fp = d.get("vendorFingerprint") or {}
        network = d.get("network", {})
        ip = network.get("ipAddress") or network.get("ip_address") or ""
        cve_ids = d.get("cve_ids") or []
        compact_devices.append({
            "id": did,
            "name": d.get("name", did),
            "type": d.get("type", "unknown"),
            "vendor": d.get("vendor", ""),
            "protocols": d.get("protocols") or [],
            "zone_id": d.get("zoneId") or d.get("zone_id") or d.get("zone") or "",
            "role": d.get("role", ""),
            "has_fingerprint": bool(fp.get("vendor")),
            "has_ip": bool(ip),
            "mac_prefix": (network.get("macAddress") or network.get("mac_address") or "")[:8],
            "cve_count": len(cve_ids),
        })

    compact_flows = []
    flow_items = list(flows.items())
    truncated = False
    if len(flow_items) > 80:
        flow_items = flow_items[:80]
        truncated = True
    for fid, f in flow_items:
        src_id = f.get("sourceDeviceId") or f.get("source_device_id") or ""
        tgt_id = f.get("targetDeviceId") or f.get("target_device_id") or ""
        config = f.get("config", {})
        compact_flows.append({
            "id": fid,
            "source_name": device_name_map.get(src_id, src_id),
            "target_name": device_name_map.get(tgt_id, tgt_id) if tgt_id else "(external)",
            "protocol": f.get("protocol", ""),
            "poll_interval_ms": config.get("pollIntervalMs") or config.get("poll_interval_ms", 1000),
        })

    # Zone summaries with device counts
    zone_device_counts: dict[str, int] = {}
    for d in devices.values():
        zid = d.get("zoneId") or d.get("zone_id") or d.get("zone") or ""
        if zid:
            zone_device_counts[zid] = zone_device_counts.get(zid, 0) + 1

    compact_zones = []
    for zid, z in zones.items():
        compact_zones.append({
            "id": zid,
            "name": z.get("name", zid),
            "purdue_level": z.get("purdue_level"),
            "device_count": zone_device_counts.get(zid, 0),
        })

    compact_phases = []
    for p in (phases or []):
        compact_phases.append({
            "name": p.get("name") or p.get("displayName", ""),
            "duration_seconds": p.get("duration_seconds", 0),
            "rate_multiplier": p.get("rate_multiplier", 1.0),
        })

    device_count = len(devices)
    flow_count = len(flows)

    # Collect vendors present in this scenario for fingerprint suggestions
    scenario_vendors = {d.get("vendor", "") for d in devices.values() if d.get("vendor")}
    available_fps = _get_available_fingerprints()
    # Include fingerprints for scenario vendors + a few common ones
    relevant_fps: dict[str, list[str]] = {}
    always_include = {"Siemens", "Rockwell Automation", "Schneider Electric", "GE", "Honeywell", "ABB", "Cisco"}
    for vendor in scenario_vendors | always_include:
        if vendor in available_fps:
            relevant_fps[vendor] = available_fps[vendor]

    return {
        "devices": compact_devices,
        "flows": compact_flows,
        "flows_truncated": truncated,
        "zones": compact_zones,
        "phases": compact_phases,
        "stats": {
            "device_count": device_count,
            "flow_count": flow_count,
            "zone_count": len(zones),
            "flow_to_device_ratio": round(flow_count / device_count, 2) if device_count else 0,
        },
        "device_id_map": {v: k for k, v in device_name_map.items()},
        "available_fingerprints": relevant_fps,
    }


@router.post("/scenarios/{scenario_id}/review", response_model=ScenarioReviewResponse)
async def review_scenario(
    scenario_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> ScenarioReviewResponse:
    """AI-powered scenario review returning categorized quality findings.

    Analyzes topology, protocols, timing, realism, and security to provide
    actionable improvement suggestions with an overall quality score.
    """
    from app.api.routes.scenarios import compute_scenario_readiness

    # Fetch scenario
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    definition = scenario.definition or {}
    devices = definition.get("devices", {})

    # Early return for empty scenarios
    if not devices:
        return ScenarioReviewResponse(
            scenario_id=scenario_id,
            summary="This scenario has no devices. Add devices and flows to get a meaningful review.",
            overall_score=0,
            findings=[
                ReviewFinding(
                    category="topology",
                    severity="critical",
                    title="Empty scenario",
                    description="The scenario contains no devices or flows.",
                    suggestion="Add devices from the palette and connect them with protocol flows.",
                )
            ],
            category_counts={"topology": 1},
            severity_counts={"critical": 1},
        )

    # Run existing readiness checks for context
    readiness = compute_scenario_readiness(definition)
    failed_checks = [
        {"name": c.name, "severity": c.severity, "message": c.message}
        for c in readiness.checks
        if not c.passed
    ]

    # Build compact context
    context = _build_review_context(definition)

    user_content = json.dumps(
        {
            "scenario_name": scenario.name,
            "vertical": scenario.vertical or "not specified",
            "readiness_score": readiness.score,
            "readiness_status": readiness.status,
            "failed_readiness_checks": failed_checks,
            **context,
        },
        indent=None,
        default=str,
    )

    messages = [
        {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": f"Review this OT scenario:\n\n{user_content}"},
    ]

    try:
        provider = await _get_ai_provider(db)
        response = await provider.chat(
            messages=messages,
            max_tokens=8192,
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": SCENARIO_REVIEW_JSON_SCHEMA,
                }
            },
            skills=[
                "packetarch-scenario-review",
                "packetarch-fingerprint-validator",
                "packetarch-device-naming",
            ],
        )

        # Extract JSON from structured output
        from app.api.routes.ai_help import _extract_response_text

        raw_text = _extract_response_text(response)
        if not raw_text:
            raise ExternalServiceError(
                service="ai",
                message="AI returned empty response for scenario review.",
            )

        data = json.loads(raw_text)

        # Transform params_json string → params dict in remediation objects
        for f in data.get("findings", []):
            rem = f.get("remediation")
            if rem and "params_json" in rem:
                try:
                    rem["params"] = json.loads(rem.pop("params_json"))
                except (json.JSONDecodeError, TypeError):
                    rem["params"] = {}
                    rem.pop("params_json", None)

        # Compute aggregated counts
        findings = [ReviewFinding(**f) for f in data.get("findings", [])]
        cat_counts: dict[str, int] = {}
        sev_counts: dict[str, int] = {}
        for f in findings:
            cat_counts[f.category] = cat_counts.get(f.category, 0) + 1
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

        score = data.get("overall_score", 50)
        score = max(0, min(100, score))

        return ScenarioReviewResponse(
            scenario_id=scenario_id,
            summary=data.get("summary", "Review completed."),
            overall_score=score,
            findings=findings,
            category_counts=cat_counts,
            severity_counts=sev_counts,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI review response: {e}")
        raise ExternalServiceError(
            service="ai",
            message="Failed to parse AI review response.",
            original_error=e,
        )
    except (ValidationError, NotFoundError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Scenario review error: {e}")
        raise ExternalServiceError(
            service="ai",
            message="Failed to generate scenario review. Please ensure AI provider is configured.",
            original_error=e,
        )


# ---------------------------------------------------------------------------
# Scenario Remediation (deterministic — no AI call)
# ---------------------------------------------------------------------------


@router.post("/scenarios/{scenario_id}/remediate", response_model=RemediateResponse)
async def remediate_scenario(
    scenario_id: str,
    request: RemediateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> RemediateResponse:
    """Execute remediation actions on a scenario.

    Applies deterministic fixes suggested by the AI review.
    No AI call — actions are executed using existing MCP tool functions.
    """
    from app.services.scenario_remediation import execute_actions

    # Verify scenario ownership
    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)

    results = await execute_actions(db, str(scenario.id), request.actions)

    applied = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    # Re-fetch scenario for final version
    await db.refresh(scenario)

    return RemediateResponse(
        scenario_id=scenario_id,
        applied=applied,
        failed=failed,
        results=results,
    )


class SkillInfo(BaseModel):
    """Summary of a registered Claude Agent Skill."""

    name: str
    description: str
    version: str
    tags: list[str]
    tokens_estimate: int


@router.get("/skills", response_model=list[SkillInfo])
async def list_skills(current_user: CurrentUser) -> list[SkillInfo]:
    """List every Claude Agent Skill available to the AI pipeline.

    Returned metadata is what the AnthropicProvider would attach to a
    request — useful for debugging which procedural knowledge Claude
    sees for a given call site.
    """
    from app.ai_services.skills import get_registry

    return [
        SkillInfo(
            name=skill.name,
            description=skill.description,
            version=skill.version,
            tags=list(skill.tags),
            tokens_estimate=skill.tokens_estimate,
        )
        for skill in get_registry().list_skills()
    ]


# Include help router from separate module
from app.api.routes.ai_help import router as help_router
router.include_router(help_router)
