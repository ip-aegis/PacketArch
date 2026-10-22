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

Messages never name another host. The engine only knows the device and its
collector, so a message naming a peer (a login source, an NTP server) would
claim activity the rest of the capture does not show.
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
    (5, "%SYS-5-CONFIG_I: Configured from console by {user} on console", 0.5),
]

_GENERIC_MESSAGES: list[tuple[int, int, str, str, float]] = [
    # (facility, severity, app, template, weight)
    (KERN, NOTICE, "kernel", "link {updown} on port {port}", 3.0),
    (DAEMON, INFO, "config", "configuration saved by {user}", 0.4),
]

_USERS = ("admin", "operator", "netops")


def _fill(template: str) -> str:
    return template.format(
        port=random.randint(1, 8), updown=random.choice(("up", "up", "down")),
        user=random.choice(_USERS),
    )


def cisco_line(seq: int, hostname: str, when: datetime) -> bytes:
    severity, template, _w = random.choices(_CISCO_MESSAGES, [m[2] for m in _CISCO_MESSAGES])[0]
    stamp = when.strftime("%b %d %H:%M:%S.") + f"{when.microsecond // 1000:03d}"
    text = _fill(template)
    return f"<{LOCAL7 * 8 + severity}>{seq}: {hostname}: {stamp}: {text}".encode()


def rfc5424_line(hostname: str, when: datetime) -> bytes:
    facility, severity, app, template, _w = random.choices(
        _GENERIC_MESSAGES, [m[4] for m in _GENERIC_MESSAGES])[0]
    stamp = when.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    text = _fill(template)
    return f"<{facility * 8 + severity}>1 {stamp} {hostname} {app} - - - {text}".encode()


def is_cisco_ios(fingerprint: dict) -> bool:
    descr = str((fingerprint.get("snmp_identity") or {}).get("sys_descr", ""))
    return "Cisco IOS" in descr


def utc(epoch_s: float) -> datetime:
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc)
