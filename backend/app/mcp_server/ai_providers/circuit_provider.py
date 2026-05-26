# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Cisco CIRCUIT AI provider implementation.

CIRCUIT is Cisco's internal LLM gateway (chat-ai.cisco.com). It speaks
the Azure OpenAI chat-completions REST shape, but:

* Authentication is OAuth2 client_credentials against
  ``https://id.cisco.com/oauth2/default/v1/token``; the returned JWT
  is passed as ``api-key:`` (NOT ``Authorization: Bearer``) on each
  chat call. Token TTL is 3600 s.
* The chat endpoint embeds the model name in the URL path:
  ``https://chat-ai.cisco.com/openai/deployments/<model>/chat/completions``.
* Each request body must carry a ``user`` field that is a JSON-encoded
  string containing the caller's ``appkey``. The appkey identifies the
  Cisco application under which usage is billed; without it the gateway
  rejects the call.

Models served (subject to per-appkey entitlements): gpt-4.1, gpt-4o,
gpt-4o-mini, o3, o4-mini, gemini-2.5-pro, gemini-2.5-flash, gpt-5
family. See the CIRCUIT portal for the canonical list.
"""

import json
import logging
import time
from typing import Any, AsyncIterator

import httpx

from app.ai_services.skills import SkillNotFoundError, get_registry
from app.ai_services.usage_recorder import AIUsageContext, record_call
from app.mcp_server.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)

CIRCUIT_TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"
CIRCUIT_API_BASE = "https://chat-ai.cisco.com"

# Token-refresh safety margin. Refresh slightly before expiry so a
# request that takes a few seconds doesn't race the JWT's exp claim.
_TOKEN_REFRESH_MARGIN_S = 60.0


def _prepend_skills_as_system(
    messages: list[dict[str, Any]],
    skills: list[str] | None,
) -> list[dict[str, Any]]:
    """Return a copy of ``messages`` with skill bodies inlined at the front.

    Mirrors :func:`openai_provider._prepend_skills_as_system` — CIRCUIT
    has no native skill/cache-block primitive, so bodies are inlined
    into a single leading system message.
    """
    if not skills:
        return messages
    registry = get_registry()
    bodies: list[str] = []
    for name in skills:
        try:
            bodies.append(registry.get(name).body)
        except SkillNotFoundError:
            logger.warning(
                "Skill '%s' not registered; continuing without it", name,
            )
    if not bodies:
        return messages
    skill_block = {"role": "system", "content": "\n\n---\n\n".join(bodies)}
    return [skill_block, *messages]


class CircuitProvider(AIProvider):
    """Cisco CIRCUIT (chat-ai.cisco.com) provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        app_key: str,
        model: str = "gpt-4.1",
        timeout_s: float = 120.0,
    ) -> None:
        """Initialise CIRCUIT provider.

        Args:
            client_id: Okta client_id issued with the CIRCUIT appkey.
            client_secret: Okta client_secret (treat as a password).
            app_key: CIRCUIT appkey (``egai-...``) — identifies the
                Cisco application charged for the request.
            model: Deployment / model name (e.g. ``gpt-4.1``).
            timeout_s: Per-request timeout. CIRCUIT can take ~30 s on
                reasoning models; 120 s leaves headroom.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._app_key = app_key
        self.model = model
        self._timeout_s = timeout_s
        self._client = httpx.AsyncClient(timeout=timeout_s)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # OAuth2 token cache
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        """Return a valid bearer token, refreshing via OAuth2 if needed."""
        now = time.monotonic()
        if self._token and now < self._token_expires_at - _TOKEN_REFRESH_MARGIN_S:
            return self._token

        logger.info("Acquiring CIRCUIT OAuth2 access token via Okta")
        resp = await self._client.post(
            CIRCUIT_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if resp.status_code != 200:
            # Don't surface client_secret in logs even on error.
            raise RuntimeError(
                "CIRCUIT OAuth2 token request failed: "
                f"HTTP {resp.status_code} {resp.text[:200]}"
            )
        body = resp.json()
        token = body.get("access_token")
        ttl = float(body.get("expires_in", 3600))
        if not token:
            raise RuntimeError("CIRCUIT OAuth2 response missing access_token")
        self._token = token
        self._token_expires_at = now + ttl
        return token

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
        skills: list[str] | None = None,
        tracking: AIUsageContext | None = None,
    ) -> dict[str, Any]:
        if tools:
            # CIRCUIT exposes the Azure OpenAI surface so tool/function
            # calling does exist, but call sites that need tools should
            # use the OpenAI provider directly until we've tested
            # function-calling against the CIRCUIT gateway.
            logger.debug(
                "CIRCUIT.chat called with %d tools — tools are forwarded "
                "as-is in OpenAI tool-calling format; verify against your "
                "appkey if you rely on this.", len(tools),
            )

        messages = _prepend_skills_as_system(messages, skills)
        openai_messages = self._convert_messages(messages)

        body: dict[str, Any] = {
            "messages": openai_messages,
            "user": json.dumps({"appkey": self._app_key}),
            "max_tokens": max_tokens,
            # The CIRCUIT examples include a stop sentinel for
            # continuous conversation. Including it is harmless when
            # absent from the prompt.
            "stop": ["<|im_end|>"],
        }
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = self._convert_tools(tools)
            body["tool_choice"] = "auto"
        if output_config and output_config.get("format", {}).get("type") == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "scenario_design",
                    "schema": output_config["format"]["schema"],
                    "strict": True,
                },
            }

        token = await self._get_token()
        url = f"{CIRCUIT_API_BASE}/openai/deployments/{self.model}/chat/completions"
        t0 = time.monotonic()
        try:
            resp = await self._client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "api-key": token,
                },
                content=json.dumps(body),
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"CIRCUIT chat call failed: HTTP {resp.status_code} "
                    f"{resp.text[:500]}"
                )
            formatted = self._format_response(resp.json())
            await record_call(
                provider="circuit",
                model=self.model,
                usage=formatted.get("usage"),
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
            )
            return formatted
        except httpx.HTTPError as e:
            await record_call(
                provider="circuit",
                model=self.model,
                usage=None,
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
                error=str(e),
            )
            logger.error("CIRCUIT chat HTTP error: %s", e)
            raise
        except Exception as e:
            await record_call(
                provider="circuit",
                model=self.model,
                usage=None,
                latency_ms=int((time.monotonic() - t0) * 1000),
                tracking=tracking,
                error=str(e),
            )
            raise

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16384,
        temperature: float | None = None,
        output_config: dict[str, Any] | None = None,
        skills: list[str] | None = None,
        tracking: AIUsageContext | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        # CIRCUIT's gateway accepts stream=true on the same endpoint
        # and returns Server-Sent Events. Until a call site needs
        # streaming we fall back to the non-stream path and yield one
        # synthetic chunk — same posture as the OpenAI provider when a
        # caller passes tools but the model can't stream them.
        result = await self.chat(
            messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            output_config=output_config,
            skills=skills,
            tracking=tracking,
        )
        for chunk in result.get("content", []):
            if chunk.get("type") == "text":
                yield {
                    "type": "stream_delta",
                    "content": chunk.get("text", ""),
                    "finish_reason": None,
                }
        yield {
            "type": "stream_delta",
            "content": "",
            "finish_reason": result.get("stop_reason"),
        }

    # ------------------------------------------------------------------
    # Conversion helpers (mirror OpenAI provider's shapes)
    # ------------------------------------------------------------------

    def _convert_tools(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in mcp_tools
        ]

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                out.append({"role": "system", "content": content})
            elif role == "user":
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "tool_result":
                            out.append({
                                "role": "tool",
                                "tool_call_id": item.get("tool_use_id"),
                                "content": item.get("content", ""),
                            })
                else:
                    out.append({"role": "user", "content": content})
            elif role == "assistant":
                if isinstance(content, list):
                    text = ""
                    calls: list[dict[str, Any]] = []
                    for item in content:
                        if item.get("type") == "text":
                            text += item.get("text", "")
                        elif item.get("type") == "tool_use":
                            tc: dict[str, Any] = {
                                "id": item.get("id"),
                                "type": "function",
                                "function": {
                                    "name": item.get("name"),
                                    "arguments": json.dumps(item.get("input", {})),
                                },
                            }
                            # Vertex AI / Gemini-via-CIRCUIT returns a
                            # ``thought_signature`` per tool_call when
                            # thinking is enabled and REQUIRES it back
                            # verbatim on subsequent turns or the gateway
                            # rejects the call (HTTP 400 INVALID_ARGUMENT).
                            # Round-trip it if we captured one earlier.
                            sig = item.get("_circuit_thought_signature")
                            if sig is not None:
                                tc["thought_signature"] = sig
                            calls.append(tc)
                    m: dict[str, Any] = {"role": "assistant"}
                    if text:
                        m["content"] = text
                    if calls:
                        m["tool_calls"] = calls
                    out.append(m)
                else:
                    out.append({"role": "assistant", "content": content})
        return out

    def _format_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message", {}) or {}
        usage = payload.get("usage", {}) or {}
        formatted: dict[str, Any] = {
            "id": payload.get("id", ""),
            "role": "assistant",
            "content": [],
            "model": payload.get("model", self.model),
            "stop_reason": choice.get("finish_reason"),
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        }
        text = message.get("content")
        if text:
            formatted["content"].append({"type": "text", "text": text})
        for tc in message.get("tool_calls") or []:
            try:
                args = json.loads(tc.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            block: dict[str, Any] = {
                "type": "tool_use",
                "id": tc.get("id"),
                "name": tc.get("function", {}).get("name"),
                "input": args,
            }
            # Preserve Gemini's ``thought_signature`` if present so it
            # can be echoed back on the next request — Vertex AI rejects
            # follow-up turns that include the tool_call without it.
            sig = tc.get("thought_signature")
            if sig is not None:
                block["_circuit_thought_signature"] = sig
            formatted["content"].append(block)
        return formatted
