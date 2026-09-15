# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Client for Cyber Vision's private UI API (``/scv/*``).

**This is not a published API.** ``/scv`` is what CV's own web UI talks to: it
appears in no OpenAPI document Cisco serves, and it may change in any CV
release. It is wrapped here because CV 5.6 leaves us no alternative.

Why it exists
-------------
CV 5.6 moved network creation into the new UI. A network created through the
*classic* ``POST /api/3.0/networks/`` is not registered correctly: it lists on
both APIs and assets are attributed to it, but CV never creates the network's
**asset group** — and the new UI's communications map groups on asset groups,
so the network is invisible there. Cisco has confirmed the classic route is
being deprecated with no API replacement planned for some time; the supported
automation path is the new UI's **CSV import**, which lives here.

Two auth mechanics that are not guessable
-----------------------------------------
1. **The login body is form-encoded, with fields ``u`` and ``p``.** Sending
   JSON returns ``401 INVALID_CREDENTIALS`` no matter how correct the
   credentials are — which reads exactly like a wrong password.
2. **Writes need a gorilla/csrf token.** CV's backend is Go.
   ``GET /scv/1.0/check_session`` sets the ``_gorilla_csrf`` cookie *and*
   returns the matching token in the ``x-csrf-token`` **response header**;
   every write must echo that value in the ``x-csrf-token`` **request**
   header. The cookie value on its own is not the token. Without the header:
   ``403 Forbidden - CSRF token not found in request``.

The token is bound to the cookie, so it must never be reused across a
re-login: a rotated cookie plus a held-over token yields the same CSRF 403,
which looks nothing like session expiry. ``_reset_session`` drops both
together, and that is the only way the pair is ever cleared.

Audited against CV 5.6. See ``docs/cyber-vision/API_AUDIT_5.6.md`` §10 and
``docs/cyber-vision/CV-5.6-Communications-Map-Remediation.md``.
"""

from __future__ import annotations

import csv
import io
import logging

import httpx

logger = logging.getLogger(__name__)

# CV rejects a login body that isn't form-encoded, and the fields are one letter.
_LOGIN_USER_FIELD = "u"
_LOGIN_PASS_FIELD = "p"

# CSV template columns, from CV's own GET /scv/4.0/networks/csv/sample. The
# first four are required; any further column becomes a network custom
# property. ``type`` takes the CLASSIC vocabulary ("OT Internal" /
# "IT Internal" / "External") — NOT the new-UI API's reading of the same field,
# which reports "OT" for the same object. Feeding it "OT" mistypes the network.
CSV_COLUMNS = ("ip_range", "type", "name", "vlan_id")


class CyberVisionUIError(Exception):
    """A /scv call failed in a way the caller may want to fall back from."""


class CyberVisionUIService:
    """Session-authenticated client for CV's private UI API (``{base_url}/scv``).

    One instance holds one CV UI session: the session cookie, the
    ``_gorilla_csrf`` cookie and the CSRF token all live in a single
    ``httpx.AsyncClient``, so the instance must be reused across the calls of
    an operation and closed afterwards (the ``try/finally: await svc.close()``
    convention the other CV clients use).
    """

    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False):
        """Args:
            base_url: CV center URL (same host as both API surfaces).
            username: CV UI username (a real UI account, not an API token).
            password: CV UI password.
            verify_ssl: Whether to verify SSL certificates (default False for self-signed).
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None
        self._csrf: str | None = None
        self._center_type: str | None = None

    # --- Plumbing -----------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        """The one client per session — it owns the cookie jar."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=60.0,  # a CSV import of a whole scenario is not instant
                follow_redirects=False,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self._csrf = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _reset_session(self) -> None:
        """Drop the session AND the CSRF token together.

        They are a pair: the token is bound to the ``_gorilla_csrf`` cookie, so
        keeping one without the other guarantees a CSRF 403 on the next write.
        """
        self._csrf = None
        if self._client and not self._client.is_closed:
            self._client.cookies.clear()

    # --- Auth ---------------------------------------------------------------

    async def center_type(self) -> str:
        """``standalone`` or ``CVSM`` — decides the login route. Unauthenticated."""
        if self._center_type is None:
            client = await self._get_client()
            resp = await client.get(self._url("/scv/3.0/center-type"))
            resp.raise_for_status()
            try:
                self._center_type = str((resp.json() or {}).get("center_type") or "standalone")
            except ValueError:
                self._center_type = "standalone"
        return self._center_type

    async def _login(self) -> None:
        """Log in and capture the CSRF token. Raises CyberVisionUIError."""
        client = await self._get_client()
        ctype = await self.center_type()
        # A CVSM (multi-center) deployment logs in on a different path.
        path = "/scv/4.0/login" if ctype.upper() == "CVSM" else "/scv/1.0/login"
        resp = await client.post(
            self._url(path),
            # Form-encoded, NOT json — see the module docstring.
            data={_LOGIN_USER_FIELD: self.username, _LOGIN_PASS_FIELD: self.password},
        )
        if resp.is_error:
            raise CyberVisionUIError(
                f"CV UI login failed for '{self.username}' at {path}: "
                f"HTTP {resp.status_code} {(resp.text or '').strip()[:200]}"
            )
        await self._refresh_csrf()

    async def _refresh_csrf(self) -> None:
        """Read the CSRF token out of check_session's RESPONSE HEADER."""
        client = await self._get_client()
        resp = await client.get(self._url("/scv/1.0/check_session"))
        if resp.is_error:
            raise CyberVisionUIError(
                f"CV UI check_session failed: HTTP {resp.status_code}"
            )
        # The _gorilla_csrf COOKIE is not the token; the header is.
        token = resp.headers.get("x-csrf-token")
        if not token:
            raise CyberVisionUIError(
                "CV UI check_session returned no x-csrf-token header — cannot write"
            )
        self._csrf = token

    async def _ensure_session(self) -> None:
        if not self._csrf:
            await self._login()

    @staticmethod
    def _is_csrf_failure(resp: httpx.Response) -> bool:
        return resp.status_code == 403 and "csrf" in (resp.text or "").lower()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        files: dict | None = None,
        _retry: bool = True,
    ):
        """An authenticated /scv request, re-authenticating once if needed.

        Retries on 401 (session gone) and on a CSRF 403, because both mean the
        session/token pair is stale rather than the request being wrong.
        """
        await self._ensure_session()
        client = await self._get_client()
        headers = {"x-csrf-token": self._csrf or ""}
        resp = await client.request(
            method, self._url(path), params=params, json=json, files=files, headers=headers
        )

        if (resp.status_code == 401 or self._is_csrf_failure(resp)) and _retry:
            logger.debug("CV UI %s %s -> %s, re-authenticating once", method, path, resp.status_code)
            self._reset_session()
            return await self._request(
                method, path, params=params, json=json, files=files, _retry=False
            )

        if resp.is_error:
            raise CyberVisionUIError(
                f"CV UI {method} {path}: HTTP {resp.status_code} "
                f"{(resp.text or '').strip()[:300]}"
            )
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # --- Reads --------------------------------------------------------------

    async def list_asset_groups(self) -> list[dict]:
        """Asset groups, the health check for the CV 5.6 network defect.

        CV materializes one asset group per properly-registered network, and
        the communications map groups on asset groups — so a network missing
        from this list cannot appear on the map, however healthy it looks on
        every other API.

        Items look like::

            {"groupId": "...", "name": "Intake Zone", "type": "network",
             "groupOrigin": "system", "interfaceCount": 8}

        ``interfaceCount`` is informational only: a scenario's /16 umbrella
        legitimately reports 0 because CV attributes assets to the more
        specific /24s. Absence from this list is the fault, not a zero count.
        """
        data = await self._request(
            "GET", "/scv/4.0/asset-group", params={"type": "all", "hasParent": "false"}
        )
        if isinstance(data, list):
            return data
        return (data or {}).get("items", []) or []

    async def get_csv_sample(self) -> str:
        """CV's own network CSV template — the authoritative column list."""
        data = await self._request("GET", "/scv/4.0/networks/csv/sample")
        return data if isinstance(data, str) else str(data)

    async def network_details(self, network_id: str) -> dict:
        """One network, including ``orgHierarchy`` and ``totalAssetsCount``."""
        data = await self._request("GET", f"/scv/4.0/network/{network_id}/details")
        return data if isinstance(data, dict) else {}

    # --- Writes -------------------------------------------------------------

    async def import_networks_csv(self, csv_text: str) -> dict:
        """Create networks through the new UI's CSV import.

        Returns CV's ``{"created": N, "updated": N, "skipped": N,
        "errors": [...]}``.

        **Check ``created``, never the overall success.** The import upserts by
        ``ip_range``: a row for a range CV already knows takes the *update*
        path, which returns ``updated: 1`` and repairs nothing — only a
        *create* materializes the asset group. That is why a partial import is
        not retried against the classic API.
        """
        body = csv_text.encode("utf-8")
        data = await self._request(
            "POST",
            "/scv/4.0/networks/csv",
            files={"file": ("networks.csv", body, "text/csv")},
        )
        return data if isinstance(data, dict) else {}

    async def delete_networks(self, network_ids: list[str]) -> bool:
        """Delete networks by id. No-op (and no request) for an empty list."""
        ids = [str(i) for i in network_ids if i]
        if not ids:
            return False
        await self._request("DELETE", "/scv/4.0/networks", json={"idList": ids})
        return True

    # --- Convenience --------------------------------------------------------

    async def test_connection(self) -> tuple[bool, str]:
        """``(ok, message)``; never raises. Reads only."""
        try:
            ctype = await self.center_type()
            await self._login()
            groups = await self.list_asset_groups()
            return True, f"Connected to a {ctype} Center ({len(groups)} asset groups)"
        except CyberVisionUIError as e:
            return False, str(e)
        except httpx.HTTPError as e:
            return False, f"Could not reach the Cyber Vision UI API: {e}"
        except Exception as e:  # noqa: BLE001 — a probe must never raise
            return False, f"Unexpected error talking to the Cyber Vision UI API: {e}"


def build_networks_csv(items: list[dict], *, extra: dict[str, str] | None = None) -> str:
    """Render classic network payload dicts as CV's network-import CSV.

    Takes the SAME ``_net_item``-shaped dicts the classic writer posts
    (``name`` / ``ipRange`` / ``type`` / ``vlanId``), which is what mechanically
    guarantees ``type`` carries PacketArch's intent in CV's classic vocabulary
    and can never be a value round-tripped out of the new-UI API (which reports
    ``OT`` for the same object that classic reports as ``OT Internal``).

    ``extra`` adds columns beyond the required four; CV turns any such column
    into a network custom property.

    Uses ``csv.writer`` rather than joining on commas because these names
    genuinely contain commas and em dashes — a zone label is
    ``f"{zone} ({scenario})"`` and scenario names are free text.
    """
    extra = extra or {}
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([*CSV_COLUMNS, *extra.keys()])
    for item in items:
        vlan = item.get("vlanId")
        writer.writerow(
            [
                item.get("ipRange") or "",
                item.get("type") or "",
                # CV trims whitespace in name; strip here so what we record
                # matches what CV stores and any name-keyed compare holds.
                (item.get("name") or "").strip(),
                "" if vlan is None else str(vlan),
                *extra.values(),
            ]
        )
    return buf.getvalue()
