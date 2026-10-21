# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Syslog message text and framing.

Framing:
- Cisco IOS / IOS XE: the IOS default line
  ``<PRI>seq: hostname: Mmm dd HH:MM:SS.mmm: %FACILITY-SEVERITY-MNEMONIC: text``
  (facility local7). The mnemonics used are documented in Cisco's IOS system
  message guides: LINEPROTO-5-UPDOWN, LINK-3-UPDOWN, SYS-5-CONFIG_I,
  SEC_LOGIN-5-LOGIN_SUCCESS, SSH-5-SSH2_SESSION.
- Everything else: RFC 5424 (``<PRI>1 TIMESTAMP HOST APP PROCID MSGID SD MSG``)
  with generic, vendor-neutral text. No vendor-specific mnemonics are
  invented for vendors that do not publish theirs.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

# RFC 5424 facilities / severities
LOCAL7, DAEMON, AUTH, KERN = 23, 3, 4, 0
ERR, WARNING, NOTICE, INFO = 3, 4, 5, 6

_CISCO_MESSAGES: list[tuple[int, str, float]] = [
    # (severity, template, weight)
    (5, "%LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/{port}, changed state to {updown}", 3.0),
    (3, "%LINK-3-UPDOWN: Interface GigabitEthernet1/{port}, changed state to {updown}", 2.0),
    (5, "%SYS-5-CONFIG_I: Configured from console by {user} on vty0 ({peer})", 0.5),
    (5, "%SEC_LOGIN-5-LOGIN_SUCCESS: Login Success [user: {user}] [Source: {peer}] [localport: 22] at {clock}", 1.0),
    (5, "%SSH-5-SSH2_SESSION: SSH2 Session request from {peer} (tty = 0) using crypto cipher "
        "'aes128-ctr', hmac 'hmac-sha2-256' Succeeded", 1.0),
]

_GENERIC_MESSAGES: list[tuple[int, int, str, str, float]] = [
    # (facility, severity, app, template, weight)
    (KERN, NOTICE, "kernel", "link {updown} on port {port}", 3.0),
    (DAEMON, INFO, "ntpd", "time synchronized to {peer}", 1.5),
    (AUTH, NOTICE, "httpd", "user {user} logged in from {peer}", 1.0),
    (AUTH, WARNING, "httpd", "login failed for user {user} from {peer}", 0.3),
    (DAEMON, INFO, "config", "configuration saved by {user}", 0.4),
    (DAEMON, INFO, "snmpd", "SNMP request from {peer} for community-authenticated read", 0.8),
]

_USERS = ("admin", "operator", "netops")


def _fill(template: str, peer_ip: str, when: datetime) -> str:
    return template.format(
        port=random.randint(1, 8), updown=random.choice(("up", "up", "down")),
        user=random.choice(_USERS), peer=peer_ip,
        clock=when.strftime("%H:%M:%S UTC %a %b %d %Y"),
    )


def cisco_line(seq: int, hostname: str, when: datetime, peer_ip: str) -> bytes:
    severity, template, _w = random.choices(_CISCO_MESSAGES, [m[2] for m in _CISCO_MESSAGES])[0]
    stamp = when.strftime("%b %d %H:%M:%S.") + f"{when.microsecond // 1000:03d}"
    text = _fill(template, peer_ip, when)
    return f"<{LOCAL7 * 8 + severity}>{seq}: {hostname}: {stamp}: {text}".encode()


def rfc5424_line(hostname: str, when: datetime, peer_ip: str) -> bytes:
    facility, severity, app, template, _w = random.choices(
        _GENERIC_MESSAGES, [m[4] for m in _GENERIC_MESSAGES])[0]
    stamp = when.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    text = _fill(template, peer_ip, when)
    return f"<{facility * 8 + severity}>1 {stamp} {hostname} {app} - - - {text}".encode()


def is_cisco_ios(fingerprint: dict) -> bool:
    descr = str((fingerprint.get("snmp_identity") or {}).get("sys_descr", ""))
    return "Cisco IOS" in descr


def utc(epoch_s: float) -> datetime:
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc)
