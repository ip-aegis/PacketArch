"""AI assistant routes for scenario composition."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
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
from app.services.device_identity_enricher import enrich_device_serial_numbers

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

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

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
                max_tokens=4096,
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
                    max_tokens=4096,
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

        # Generate MAC address using vendor OUI (via centralized identity registry)
        mac_address = generate_mac(vendor=vendor, device_type=device_type)

        # Get fingerprint data for deep fingerprinting
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
            "device_type": device_type,  # Fixed: was 'type', should be 'device_type'
            "protocols": validated_protocols,  # Use validated protocols
            "position": {"x": device_x, "y": device_y},
            "zoneId": zone_name,
            "network": network_config,
            "vendor": d.get("vendor"),
            "fingerprint_model": fingerprint_model,  # CRITICAL: Store fingerprint_model
        }

        # Apply deep fingerprint data if available
        if fingerprint_data:
            device_def["fingerprint"] = {
                "vendor": fingerprint_data.get("vendor"),
                "vendor_family": fingerprint_data.get("vendor_family"),
                "model": fingerprint_data.get("model"),
                "firmware_version": fingerprint_data.get("firmware_version"),
                "serial_number": _generate_serial_number(vendor, fingerprint_data),
            }

            # Protocol-specific identity data (all 7 protocols)
            if fingerprint_data.get("modbus_identity"):
                device_def["fingerprint"]["modbus_identity"] = fingerprint_data["modbus_identity"]
            if fingerprint_data.get("ethernet_ip_identity"):
                device_def["fingerprint"]["ethernet_ip_identity"] = fingerprint_data["ethernet_ip_identity"]
            if fingerprint_data.get("profinet_identity"):
                device_def["fingerprint"]["profinet_identity"] = fingerprint_data["profinet_identity"]
            if fingerprint_data.get("s7_identity"):
                device_def["fingerprint"]["s7_identity"] = fingerprint_data["s7_identity"]
            if fingerprint_data.get("snmp_identity"):
                device_def["fingerprint"]["snmp_identity"] = fingerprint_data["snmp_identity"]
            if fingerprint_data.get("bacnet_identity"):
                device_def["fingerprint"]["bacnet_identity"] = fingerprint_data["bacnet_identity"]
            if fingerprint_data.get("opc_ua_identity"):
                device_def["fingerprint"]["opc_ua_identity"] = fingerprint_data["opc_ua_identity"]

            # TCP stack characteristics
            if fingerprint_data.get("tcp_stack"):
                device_def["fingerprint"]["tcp_stack"] = fingerprint_data["tcp_stack"]

            # Response timing
            if fingerprint_data.get("response_timing"):
                device_def["fingerprint"]["response_timing"] = fingerprint_data["response_timing"]

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

    # Update scenario definition (scenario was created earlier for IP allocation)
    db_scenario.definition = {
        "devices": devices,
        "flows": flows,
        "zones": zones,
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


# Include help router from separate module
from app.api.routes.ai_help import router as help_router
router.include_router(help_router)
