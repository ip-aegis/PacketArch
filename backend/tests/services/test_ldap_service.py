"""Unit tests for the LDAP authentication service.

The tests exercise the public surface of :mod:`app.services.ldap_service`
without touching a real directory — we patch ``ldap3.Connection`` at the
import site inside the service module so all bind/search behaviour is under
our control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services import ldap_service


def _make_config(**overrides: Any) -> ldap_service.LdapConfig:
    base = dict(
        enabled=True,
        server_url="ldap://dc.example.com",
        use_ssl=False,
        start_tls=False,
        verify_ssl=True,
        bind_dn="CN=svc,DC=example,DC=com",
        bind_password="svcpw",
        search_base="DC=example,DC=com",
        user_search_filter="(&(objectClass=user)(sAMAccountName={username}))",
        email_attribute="mail",
        display_name_attribute="displayName",
    )
    base.update(overrides)
    return ldap_service.LdapConfig(**base)


@dataclass
class _FakeAttr:
    value: Any


@dataclass
class _FakeEntry:
    entry_dn: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> _FakeAttr:
        return _FakeAttr(self.attrs.get(key))


class _FakeConnection:
    """Stand-in for ``ldap3.Connection`` with programmable behaviour.

    Each call to ``Connection(...)`` returns a new instance; the class-level
    ``script`` controls the outcome of the service bind vs. the user bind.
    """

    # (bind_succeeds, user_dn or None, entries)
    script: list[tuple[bool, list[_FakeEntry]]] = []
    instances: list["_FakeConnection"] = []

    def __init__(self, server, user=None, password=None, **_kwargs):
        self.server = server
        self.user = user
        self.password = password
        self.entries: list[_FakeEntry] = []
        self.result: dict[str, Any] = {"description": "success"}
        self._bound = False
        self.unbound = False
        _FakeConnection.instances.append(self)

    def bind(self) -> bool:
        if not _FakeConnection.script:
            # Default: bind succeeds so we don't need to program every call.
            self._bound = True
            return True
        ok, entries = _FakeConnection.script.pop(0)
        self._bound = ok
        if not ok:
            self.result = {"description": "invalidCredentials"}
        self._pending_entries = entries
        return ok

    def start_tls(self) -> None:  # noqa: D401 — matches ldap3 API
        return None

    def search(self, search_base, search_filter, **_kwargs) -> bool:
        self.last_search_base = search_base
        self.last_search_filter = search_filter
        self.entries = getattr(self, "_pending_entries", [])
        return True

    def unbind(self) -> None:
        self.unbound = True

    @classmethod
    def reset(cls) -> None:
        cls.script = []
        cls.instances = []


# ---------------------------------------------------------------------------
# is_enabled / empty-password guard
# ---------------------------------------------------------------------------


def test_is_enabled_requires_all_core_fields() -> None:
    config = _make_config()
    assert ldap_service.is_enabled(config) is True

    assert ldap_service.is_enabled(_make_config(enabled=False)) is False
    assert ldap_service.is_enabled(_make_config(server_url="")) is False
    assert ldap_service.is_enabled(_make_config(bind_dn="")) is False
    assert ldap_service.is_enabled(_make_config(bind_password="")) is False
    assert ldap_service.is_enabled(_make_config(search_base="")) is False


def test_authenticate_rejects_empty_password_without_touching_ldap() -> None:
    config = _make_config()
    with patch.object(ldap_service, "Connection") as conn_cls:
        result = ldap_service.authenticate(config, "alice", "")
    assert result.success is False
    assert result.reason == "empty_password"
    conn_cls.assert_not_called()


def test_authenticate_rejects_bad_filter_template() -> None:
    config = _make_config(user_search_filter="(&(objectClass=user)(cn=alice))")
    with patch.object(ldap_service, "Connection") as conn_cls:
        result = ldap_service.authenticate(config, "alice", "hunter2")
    assert result.success is False
    assert result.reason == "bad_filter"
    conn_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Search + rebind happy path
# ---------------------------------------------------------------------------


def test_authenticate_success_populates_user_info() -> None:
    config = _make_config()
    entry = _FakeEntry(
        entry_dn="CN=Alice,OU=Users,DC=example,DC=com",
        attrs={"mail": "alice@example.com", "displayName": "Alice Example"},
    )
    _FakeConnection.reset()
    # service bind succeeds with entries, user bind succeeds with no entries
    _FakeConnection.script = [(True, [entry]), (True, [])]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        result = ldap_service.authenticate(config, "alice", "hunter2")

    assert result.success is True
    assert result.user is not None
    assert result.user.dn == "CN=Alice,OU=Users,DC=example,DC=com"
    assert result.user.username == "alice"
    assert result.user.email == "alice@example.com"
    assert result.user.display_name == "Alice Example"

    # Two Connection instances: service bind + user bind.
    assert len(_FakeConnection.instances) == 2
    svc, user_conn = _FakeConnection.instances
    # Service bind used the configured service DN and password.
    assert svc.user == config.bind_dn
    assert svc.password == config.bind_password
    # User rebind used the resolved DN, not the raw username.
    assert user_conn.user == entry.entry_dn
    assert user_conn.password == "hunter2"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_authenticate_not_found_when_search_returns_no_entries() -> None:
    config = _make_config()
    _FakeConnection.reset()
    _FakeConnection.script = [(True, [])]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        result = ldap_service.authenticate(config, "ghost", "whatever")

    assert result.success is False
    assert result.reason == "not_found"
    # Only the service bind should have happened.
    assert len(_FakeConnection.instances) == 1


def test_authenticate_ambiguous_when_multiple_matches() -> None:
    config = _make_config()
    entries = [
        _FakeEntry(entry_dn="CN=Alice1,DC=example,DC=com"),
        _FakeEntry(entry_dn="CN=Alice2,DC=example,DC=com"),
    ]
    _FakeConnection.reset()
    _FakeConnection.script = [(True, entries)]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        result = ldap_service.authenticate(config, "alice", "pw")

    assert result.success is False
    assert result.reason == "ambiguous"


def test_authenticate_invalid_credentials_on_user_bind_failure() -> None:
    config = _make_config()
    entry = _FakeEntry(entry_dn="CN=Alice,DC=example,DC=com")
    _FakeConnection.reset()
    _FakeConnection.script = [(True, [entry]), (False, [])]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        result = ldap_service.authenticate(config, "alice", "wrong")

    assert result.success is False
    assert result.reason == "invalid_credentials"


def test_authenticate_service_bind_failure() -> None:
    config = _make_config()
    _FakeConnection.reset()
    _FakeConnection.script = [(False, [])]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        result = ldap_service.authenticate(config, "alice", "pw")

    assert result.success is False
    assert result.reason == "service_bind_failed"


def test_authenticate_server_error_is_reported() -> None:
    config = _make_config()

    def _boom(*_args, **_kwargs):
        from ldap3.core.exceptions import LDAPSocketOpenError

        raise LDAPSocketOpenError("cannot reach server")

    with patch.object(ldap_service, "Connection", side_effect=_boom):
        result = ldap_service.authenticate(config, "alice", "pw")

    assert result.success is False
    assert result.reason == "server_error"


# ---------------------------------------------------------------------------
# Filter escaping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected_fragment",
    [
        ("a*b", r"a\2ab"),  # '*' becomes \2a
        ("a(b", r"a\28b"),  # '(' becomes \28
        ("a)b", r"a\29b"),
        ("a\\b", r"a\5cb"),  # '\' becomes \5c
        ("a\x00b", r"a\00b"),  # NUL becomes \00
    ],
)
def test_filter_escaping_neutralises_metacharacters(raw: str, expected_fragment: str) -> None:
    formatted = ldap_service._format_filter(
        "(&(objectClass=user)(sAMAccountName={username}))", raw
    )
    assert expected_fragment in formatted
    # The raw metacharacter should not appear unescaped next to 'sAMAccountName='.
    # (Except in NUL case, which would never survive as a raw char anyway.)
    assert "(sAMAccountName=" + raw + ")" not in formatted


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


def test_test_connection_requires_minimum_config() -> None:
    cfg = _make_config(server_url="")
    assert ldap_service.test_connection(cfg).success is False

    cfg = _make_config(bind_dn="")
    assert ldap_service.test_connection(cfg).success is False

    cfg = _make_config(bind_password="")
    assert ldap_service.test_connection(cfg).success is False


def test_test_connection_success() -> None:
    config = _make_config()
    _FakeConnection.reset()
    _FakeConnection.script = [(True, [])]

    with patch.object(ldap_service, "Connection", _FakeConnection):
        with patch.object(ldap_service, "_build_server") as build_server:
            # server.info is informational only — make sure it doesn't blow up.
            fake_server = MagicMock()
            fake_server.info = None
            build_server.return_value = fake_server
            result = ldap_service.test_connection(config)

    assert result.success is True
    assert "successful" in result.message.lower()
