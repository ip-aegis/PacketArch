"""AI-powered help system endpoints.

This module provides AI-powered help for topics like:
- Deployment troubleshooting
- General PacketArch usage
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.exceptions import ExternalServiceError, ValidationError

from app.api.deps import CurrentUser, DBSession
from app.mcp_server.ai_providers import AIProviderFactory
from app.models.settings import SystemSetting

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Help"])


class HelpChatRequest(BaseModel):
    """Request for help chat (non-scenario context)."""

    question: str = Field(..., description="User's help question")
    context: str = Field(
        default="general",
        description="Help context: deployment, general",
    )


class HelpChatResponse(BaseModel):
    """Response from help chat."""

    response: str


# Context-specific system prompts for help
HELP_CONTEXTS = {
    "deployment": """You are a helpful technical assistant specializing in OT traffic deployment and simulation.

Your expertise includes:
- Traffic generation deployment to remote traffic agents
- Network interface selection for traffic injection
- Deployment status monitoring and troubleshooting
- Agent connection and management

When answering questions:
1. Focus on practical troubleshooting steps
2. Explain deployment status codes and their meanings
3. Help diagnose connectivity and configuration issues
4. Provide guidance on agent setup and management
""",
    "general": """You are a helpful technical assistant for PacketArch, an OT Traffic Simulation Platform.

Your expertise includes:
- Scenario creation and management
- Device configuration and protocols
- Traffic generation and deployment
- Traffic agent setup and management
- System administration
""",
}


async def _get_ai_provider(db: DBSession):
    """Get the configured AI provider."""
    from sqlalchemy import select

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "anthropic_api_key")
    )
    setting = result.scalar_one_or_none()

    if not setting or not setting.value:
        raise ValidationError("AI provider not configured. Please set your Anthropic API key in Settings.")

    return AIProviderFactory.create(
        provider_type="anthropic",
        api_key=setting.value,
    )


@router.post("/help", response_model=HelpChatResponse)
async def help_chat(
    request: HelpChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> HelpChatResponse:
    """Answer help questions using AI without scenario context.

    This endpoint provides AI-powered help for topics like
    deployment troubleshooting and general PacketArch usage.

    Args:
        request: Help question and context
        current_user: Authenticated user
        db: Database session

    Returns:
        AI-generated response to the help question
    """
    # Get context-specific system prompt
    system_prompt = HELP_CONTEXTS.get(request.context, HELP_CONTEXTS["general"])

    # Build the prompt - prepend system context to user message
    combined_message = f"""You are a helpful technical assistant. Here is your context and expertise:

{system_prompt}

---

User question: {request.question}

Please provide a helpful, clear answer to the user's question."""

    messages = [
        {"role": "user", "content": combined_message},
    ]

    try:
        provider = await _get_ai_provider(db)

        response = await provider.chat(
            messages=messages,
            max_tokens=4096,
        )

        # Extract text from response
        response_text = ""
        if isinstance(response, dict):
            content = response.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        response_text = block.get("text", "").strip()
                        break
            elif isinstance(content, str):
                response_text = content.strip()
        else:
            response_text = str(response).strip()

        if not response_text:
            response_text = "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        return HelpChatResponse(response=response_text)

    except (ValidationError, ExternalServiceError):
        raise
    except Exception as e:
        logger.error(f"Help chat error: {e}")
        raise ExternalServiceError(service="ai", message="Failed to process help request. Please ensure AI provider is configured.", original_error=e)
