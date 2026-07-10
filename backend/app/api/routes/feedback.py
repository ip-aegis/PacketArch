# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""User feedback endpoint — forwards submissions to WebEx via bot token."""

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])

WEBEX_MESSAGES_URL = "https://webexapis.com/v1/messages"


class FeedbackRequest(BaseModel):
    name: str
    email: str
    message: str


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest) -> dict:
    if not settings.webex_bot_token:
        raise HTTPException(status_code=503, detail="Feedback not configured (WEBEX_BOT_TOKEN not set)")

    recipient = settings.webex_recipient_email
    if not recipient:
        raise HTTPException(status_code=503, detail="Feedback not configured (WEBEX_RECIPIENT_EMAIL not set)")

    text = (
        f"**PacketArch Feedback**\n\n"
        f"**From:** {payload.name}  \n"
        f"**Email:** {payload.email}  \n\n"
        f"{payload.message}"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                WEBEX_MESSAGES_URL,
                headers={"Authorization": f"Bearer {settings.webex_bot_token}"},
                json={"toPersonEmail": recipient, "markdown": text},
            )
        if resp.status_code not in (200, 201):
            logger.error("WebEx API error %s: %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="Failed to deliver feedback via WebEx")
    except httpx.RequestError as exc:
        logger.error("WebEx request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach WebEx API")

    return {"status": "sent"}
