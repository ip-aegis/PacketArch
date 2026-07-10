# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Client for Cisco Cyber Vision's "New UI" API (``/cvapi/v1``).

CV is mid-transition between its classic UI/API (``/api/3.0``, see
``cyber_vision_service.py``) and a new UI with its own API. Both are live at
once on the same CV Center, but the new API uses a SEPARATE token store —
a classic-API token is rejected here (and vice versa) even though the header
name (``x-token-id``) is identical. Confirmed live against a CV 5.5.1 center.

Only the Organization Hierarchy surface is wrapped here (what PacketArch's
provisioning needs); the new API also exposes Assets/CustomProperties/
Vulnerabilities endpoints that aren't consumed yet.
"""

from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_LINK_NEXT_CURSOR_RE = re.compile(r'[?&]cursor=([^&>]+)')


class CyberVisionV1Service:
    """Client for Cyber Vision's new-UI API (``{base_url}/cvapi/v1``)."""

    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = False):
        """Args:
            base_url: CV center URL (same host as the classic API).
            api_token: New-UI API token (separate token store from the classic API).
            verify_ssl: Whether to verify SSL certificates (default False for self-signed).
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                headers={
                    "x-token-id": self.api_token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self, method: str, endpoint: str, params: dict | None = None, json: dict | list | None = None
    ) -> dict | list:
        """Make a request against ``{base_url}/cvapi/v1{endpoint}``."""
        client = await self._get_client()
        url = f"{self.base_url}/cvapi/v1{endpoint}"
        response = await client.request(method, url, params=params, json=json)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    async def _paginated_get(self, endpoint: str, max_page: int = 500) -> list[dict]:
        """GET a cursor-paginated list endpoint, following the ``Link: rel="next"``
        response header (the cursor is NOT in the JSON body — confirmed live)."""
        client = await self._get_client()
        url = f"{self.base_url}/cvapi/v1{endpoint}"
        out: list[dict] = []
        params: dict = {"max": max_page}
        for _ in range(200):  # hard cap — guards against a runaway cursor loop
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json() if response.content else {}
            items = data.get("items", []) if isinstance(data, dict) else []
            out.extend(items)
            if len(items) < max_page:
                break
            link = response.headers.get("link", "")
            match = _LINK_NEXT_CURSOR_RE.search(link) if 'rel="next"' in link else None
            if not match:
                break
            params = {"max": max_page, "cursor": match.group(1)}
        return out

    # ==================== Organization Hierarchy ====================

    async def get_oh_levels(self, max_page: int = 500) -> list[dict]:
        """Fetch every Organization Hierarchy level (cursor-paginated).

        Each item: ``{id, name, description, parentLevelId, hierarchy}``.
        The root ``Global`` level has no ``parentLevelId``.
        """
        return await self._paginated_get("/oh", max_page)

    async def create_oh_levels(self, levels: list[dict]) -> dict:
        """Create one or more hierarchy levels. Each item: ``{name, parentLevelId}``.

        Supports partial success — inspect the returned ``results`` list.
        """
        result = await self._request("POST", "/oh", json={"levels": levels})
        return result if isinstance(result, dict) else {}

    async def rename_oh_level(self, level_id: str, name: str) -> None:
        """Rename an existing hierarchy level."""
        await self._request("PATCH", f"/oh/{level_id}", json={"name": name})

    async def delete_oh_level(self, level_id: str) -> None:
        """Delete a hierarchy level.

        CV rejects this (400) if the level still has child levels or assigned
        networks — callers must delete children first and ensure no networks
        are assigned (see ``assign_networks_to_level``; there is no "unassign"
        call, only reassignment or deleting the underlying network).
        """
        await self._request("DELETE", f"/oh/{level_id}")

    async def assign_networks_to_level(self, level_id: str, network_ids: list[str]) -> None:
        """Assign one or more networks to a hierarchy level.

        Each network belongs to exactly one level at a time — assigning a
        network here moves it away from wherever it was assigned before.
        The list must be non-empty; CV schema-rejects ``{"networks": []}``.
        """
        if not network_ids:
            return
        await self._request("PUT", f"/oh/{level_id}/networks", json={"networks": network_ids})

    # ==================== Networks (read-only here) ====================

    async def get_networks(self, max_page: int = 500) -> list[dict]:
        """Fetch new-UI-API network objects (each carries ``groupId`` = its
        assigned Organization Hierarchy level id, defaulting to Global)."""
        return await self._paginated_get("/networks", max_page)


async def cv_v1_service_from_settings(db) -> CyberVisionV1Service | None:
    """Build a CyberVisionV1Service from stored system settings.

    Reuses the classic API's ``cyber_vision_url`` / ``cyber_vision_verify_ssl``
    (same CV Center serves both APIs) plus the separate ``cyber_vision_new_ui_token``.
    Returns None when the new-UI token isn't configured — this integration is
    additive/optional, unlike the classic API.
    """
    from sqlalchemy import select

    from app.core.encryption import decrypt_value
    from app.models.settings import SystemSetting

    settings: dict[str, str] = {}
    result = await db.execute(
        select(SystemSetting).where(
            SystemSetting.key.in_([
                "cyber_vision_url",
                "cyber_vision_new_ui_token",
                "cyber_vision_verify_ssl",
            ])
        )
    )
    for setting in result.scalars().all():
        if setting.key == "cyber_vision_new_ui_token" and setting.value:
            settings[setting.key] = decrypt_value(setting.value)
        else:
            settings[setting.key] = setting.value

    url = settings.get("cyber_vision_url")
    token = settings.get("cyber_vision_new_ui_token")
    if not url or not token:
        return None
    verify_ssl = (settings.get("cyber_vision_verify_ssl") or "false").lower() == "true"
    return CyberVisionV1Service(url, token, verify_ssl)
