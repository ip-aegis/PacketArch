# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Guards for CV 5.6 network creation through the new UI's CSV import.

CV 5.6 broke classic ``POST /api/3.0/networks/``: the network is created and
assets are attributed to it, but CV never materializes its **asset group** —
and the communications map groups on asset groups, so the network is invisible
there while every other API reports it healthy. Networks are therefore created
through the UI's CSV import, which needs a real UI session.

What is faked here: the CV UI HTTP surface (``httpx.MockTransport``) and the
two client factories in ``cv_centers``. Nothing talks to a real Center, and
nothing touches the database — ``_create_networks`` takes neither a session nor
a scenario precisely so these tests need no Postgres (the provisioning saves
use raw ``jsonb_set``, which the sqlite test DB cannot run).

See ``docs/cyber-vision/API_AUDIT_5.6.md`` §10.
"""
from __future__ import annotations

import csv
import io
from unittest.mock import patch

import httpx
import pytest

from app.services.cv_provisioning_service import (
    DEFAULT_NETWORK_TYPE,
    _create_networks,
    _net_item,
)
from app.services.cyber_vision_ui_service import (
    CSV_COLUMNS,
    CyberVisionUIError,
    CyberVisionUIService,
    build_networks_csv,
)

CSRF = "csrf-token-one"
CSRF_ROTATED = "csrf-token-two"


# --------------------------------------------------------------------------- #
# build_networks_csv
# --------------------------------------------------------------------------- #
def _parse(csv_text: str) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(csv_text)))
    return rows[0], rows[1:]


def test_csv_header_is_cvs_own_column_list():
    header, _ = _parse(build_networks_csv([_net_item("Intake Zone", "10.2.2.0/24")]))
    assert header == list(CSV_COLUMNS)


def test_csv_uses_the_classic_type_vocabulary():
    """The CSV takes ``OT Internal``, not the new-UI API's ``OT`` for the same
    object. Feeding it ``OT`` mistypes the network (audit §2)."""
    _, rows = _parse(build_networks_csv([_net_item("Intake Zone", "10.2.2.0/24")]))
    assert rows[0][CSV_COLUMNS.index("type")] == DEFAULT_NETWORK_TYPE == "OT Internal"


def test_csv_quotes_names_containing_commas_and_em_dashes():
    """Zone labels are ``f"{zone} ({scenario})"`` and scenario names are free
    text, so commas and em dashes are routine. A naive comma join would split
    one network across two columns and silently corrupt the import."""
    name = "External/Internet (Heat & Hot-Water, Phase 2 — Retrofit)"
    text = build_networks_csv([_net_item(name, "10.7.99.0/24")])
    header, rows = _parse(text)
    assert len(rows) == 1 and len(rows[0]) == len(header)
    assert rows[0][CSV_COLUMNS.index("name")] == name
    assert rows[0][CSV_COLUMNS.index("ip_range")] == "10.7.99.0/24"


def test_csv_strips_whitespace_because_cv_does():
    """CV trims ``name`` on import, so an untrimmed name would be recorded
    against a trimmed one and any name-keyed comparison would mismatch."""
    _, rows = _parse(build_networks_csv([_net_item("  Intake Zone  ", "10.2.2.0/24")]))
    assert rows[0][CSV_COLUMNS.index("name")] == "Intake Zone"


def test_net_item_strips_the_name():
    # The scenario /16 umbrella name reaches _net_item unstripped, unlike zone
    # names, which _group_label already strips.
    assert _net_item("  Municipal Water Treatment Plant ", "10.2.0.0/16")["name"] == (
        "Municipal Water Treatment Plant"
    )


def test_csv_extra_columns_become_custom_properties():
    header, rows = _parse(
        build_networks_csv([_net_item("Intake Zone", "10.2.2.0/24")], extra={"Scenario": "Water"})
    )
    assert header == [*CSV_COLUMNS, "Scenario"]
    assert rows[0][-1] == "Water"


# --------------------------------------------------------------------------- #
# _create_networks — the three outcomes
# --------------------------------------------------------------------------- #
class FakeClassic:
    """Stands in for CyberVisionService's network-write surface."""

    def __init__(self):
        self.created: list[list[dict]] = []

    async def create_networks(self, networks):
        self.created.append(networks)
        return True


class FakeUI:
    def __init__(self, result=None, raises=None):
        self._result = result or {}
        self._raises = raises
        self.imported: list[str] = []
        self.closed = False

    async def import_networks_csv(self, csv_text):
        if self._raises:
            raise self._raises
        self.imported.append(csv_text)
        return self._result

    async def close(self):
        self.closed = True


class FakeCenter:
    name = "Test Center"


TO_CREATE = [_net_item("Intake Zone", "10.2.2.0/24"), _net_item("Filter Zone", "10.2.3.0/24")]


async def test_no_ui_credentials_falls_back_to_classic_and_warns():
    classic = FakeClassic()
    with patch("app.services.cv_centers.ui_client", return_value=None):
        warnings = await _create_networks(FakeCenter(), classic, TO_CREATE)

    assert classic.created == [TO_CREATE], "must still create them the old way"
    assert len(warnings) == 1
    assert "will NOT appear on the communications map" in warnings[0]
    assert "10.2.2.0/24" in warnings[0] and "10.2.3.0/24" in warnings[0]


async def test_failed_import_falls_back_to_classic_and_warns():
    classic = FakeClassic()
    ui = FakeUI(raises=CyberVisionUIError("403 CSRF token not found in request"))
    with patch("app.services.cv_centers.ui_client", return_value=ui):
        warnings = await _create_networks(FakeCenter(), classic, TO_CREATE)

    assert classic.created == [TO_CREATE]
    assert ui.closed, "the UI session must be closed even when the import fails"
    assert len(warnings) == 1
    assert "will NOT appear on the communications map" in warnings[0]


async def test_partial_import_warns_but_does_not_fall_back():
    """An ``updated`` row does not repair a bad network, so a classic retry
    would add noise without fixing anything. The assertion that matters is on
    the classic fake's call count, not on the log text."""
    classic = FakeClassic()
    ui = FakeUI(result={"created": 1, "updated": 1, "skipped": 0, "errors": []})
    with patch("app.services.cv_centers.ui_client", return_value=ui):
        warnings = await _create_networks(FakeCenter(), classic, TO_CREATE)

    assert classic.created == [], "a partial import must NOT fall back to the classic API"
    assert len(warnings) == 1
    assert "created only 1 of 2" in warnings[0]
    assert "will NOT appear on the communications map" in warnings[0]
    assert ui.closed


async def test_full_import_creates_nothing_classically_and_warns_nothing():
    classic = FakeClassic()
    ui = FakeUI(result={"created": 2, "updated": 0, "skipped": 0, "errors": []})
    with patch("app.services.cv_centers.ui_client", return_value=ui):
        warnings = await _create_networks(FakeCenter(), classic, TO_CREATE)

    assert classic.created == []
    assert warnings == []
    assert ui.closed
    header, rows = _parse(ui.imported[0])
    assert header == list(CSV_COLUMNS) and len(rows) == 2


# --------------------------------------------------------------------------- #
# The /scv session client's two non-guessable auth mechanics
# --------------------------------------------------------------------------- #
class _ScvStub:
    """A minimal /scv: form-encoded login, CSRF only from check_session."""

    def __init__(self, center_type="standalone", expire_after=None):
        self.center_type = center_type
        self.expire_after = expire_after  # writes to reject with 401 before re-auth
        self.logins: list[dict] = []
        self.login_paths: list[str] = []
        self.write_csrf: list[str | None] = []
        self.csrf = CSRF

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == "/scv/3.0/center-type":
            return httpx.Response(200, json={"center_type": self.center_type})

        if path.endswith("/login"):
            self.login_paths.append(path)
            body = request.content.decode()
            if request.headers.get("content-type", "").startswith("application/json"):
                # What CV actually does with a JSON body — looks like a bad password.
                return httpx.Response(401, json={"message": "INVALID_CREDENTIALS"})
            self.logins.append(dict(httpx.QueryParams(body)))
            # A re-login rotates the CSRF token, because it is bound to the cookie.
            self.csrf = CSRF_ROTATED if len(self.logins) > 1 else CSRF
            return httpx.Response(200, json={"ok": True})

        if path == "/scv/1.0/check_session":
            return httpx.Response(200, json={"ok": True}, headers={"x-csrf-token": self.csrf})

        if path == "/scv/4.0/networks/csv":
            sent = request.headers.get("x-csrf-token")
            self.write_csrf.append(sent)
            if self.expire_after is not None and len(self.write_csrf) <= self.expire_after:
                return httpx.Response(401, text="session expired")
            if sent != self.csrf:
                return httpx.Response(403, text="Forbidden - CSRF token not found in request")
            return httpx.Response(200, json={"created": 1, "updated": 0, "skipped": 0, "errors": []})

        return httpx.Response(404, text="not found")


def _svc(stub: _ScvStub) -> CyberVisionUIService:
    svc = CyberVisionUIService("https://cv.example", "operator", "pw")
    svc._client = httpx.AsyncClient(transport=httpx.MockTransport(stub.handler))
    return svc


async def test_login_is_form_encoded_with_u_and_p_fields():
    """A JSON login body returns 401 INVALID_CREDENTIALS however correct the
    credentials are, which reads exactly like a wrong password."""
    stub = _ScvStub()
    svc = _svc(stub)
    try:
        await svc.import_networks_csv("ip_range,type,name,vlan_id\n")
    finally:
        await svc.close()

    assert stub.logins == [{"u": "operator", "p": "pw"}]
    assert stub.login_paths == ["/scv/1.0/login"]


async def test_csrf_token_comes_from_the_response_header_and_is_echoed():
    stub = _ScvStub()
    svc = _svc(stub)
    try:
        res = await svc.import_networks_csv("ip_range,type,name,vlan_id\n")
    finally:
        await svc.close()

    assert res["created"] == 1
    assert stub.write_csrf == [CSRF], "the write must echo check_session's x-csrf-token"


async def test_a_cvsm_center_logs_in_on_the_other_route():
    stub = _ScvStub(center_type="CVSM")
    svc = _svc(stub)
    try:
        await svc.center_type()
        await svc._login()
    finally:
        await svc.close()

    assert stub.login_paths == ["/scv/4.0/login"]


async def test_reauth_refetches_the_csrf_token_rather_than_reusing_it():
    """The token is bound to the ``_gorilla_csrf`` cookie, so a re-login
    rotates it. Reusing the old one yields a CSRF 403 that looks nothing like
    session expiry — the retry must fetch a fresh token."""
    stub = _ScvStub(expire_after=1)  # first write 401s, forcing one re-auth
    svc = _svc(stub)
    try:
        res = await svc.import_networks_csv("ip_range,type,name,vlan_id\n")
    finally:
        await svc.close()

    assert res["created"] == 1
    assert len(stub.logins) == 2, "expected exactly one re-authentication"
    assert stub.write_csrf == [CSRF, CSRF_ROTATED], "the retry must use the NEW token"


async def test_a_missing_csrf_header_is_a_clear_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/scv/3.0/center-type":
            return httpx.Response(200, json={"center_type": "standalone"})
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(200, json={"ok": True})  # check_session, no header

    svc = CyberVisionUIService("https://cv.example", "operator", "pw")
    svc._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(CyberVisionUIError, match="x-csrf-token"):
            await svc.import_networks_csv("ip_range,type,name,vlan_id\n")
    finally:
        await svc.close()
