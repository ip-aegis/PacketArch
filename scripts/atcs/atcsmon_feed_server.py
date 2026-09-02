#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""ATCSMon-compatible feed server — a validation harness for our ATCS codeline.

Cisco Cyber Vision has no rail DPI, so our ATCS engine exists to produce a
spec-conformant corpus a dissector could be trained on. The only *independent*
parser for that codeline is ATCS Monitor (ATCSMon) itself — a closed-source
Windows decoder. This server speaks the ATCSMon "data source" feed protocol so a
real ATCSMon client can connect and try to decode the exact bytes our
``codeline.py`` builds. If ATCSMon renders sensible messages, that independently
corroborates our framing + 31-bit vital CRC.

The one thing the (now-unreachable) atcsmon.com docs never pinned down is whether
the feed carries the codeline as RAW BINARY or ASCII-HEX text, and whether a
length field precedes it. Rather than guess, every uncertain part of the record
is a flag — point a real ATCSMon at this and flip flags until it decodes. That
empirical result is what settles the format (and tells us whether the engine's
shipped encoding needs to change).

Portable by design: depends only on the stdlib plus ``codeline.py`` (itself pure
stdlib). To run on another host (e.g. an ATCSMon/Wine box), copy just this file
and ``backend/app/protocol_engines/atcs/codeline.py`` into the same directory and
run with any Python 3.

Feed protocol (reconstructed from community reverse-engineering; the parts we're
unsure of are flags):

    1. Client opens TCP to the listener port (4802).
    2. Server replies with the UDP data port it assigned, then closes the TCP.
    3. Client sends "Thanks" as a UDP datagram to that port (opens the NAT/return
       path and tells us where to stream).
    4. Server streams one codeline record per UDP datagram; "*KEEPALIVE" when idle.
    5. Client sends "DISCONNECT" before leaving.

Each record: [prefix byte(s)] [optional length] [payload], where payload is the
codeline datagram as binary or ASCII-hex. '#' is the documented ATCS prefix.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import socket
import struct
import threading
import time
from pathlib import Path


def _load_codeline():
    """Load ``codeline.py`` DIRECTLY by file path.

    We deliberately do NOT ``import app.protocol_engines.atcs.codeline`` — that
    would run the package ``__init__`` and drag in every engine (and scapy),
    breaking the pure-stdlib portability that lets this drop onto an ATCSMon box.
    codeline.py is self-contained, so loading the file in isolation is enough.
    """
    here = Path(__file__).resolve().parent
    candidates = [here / "codeline.py"]  # sibling copy (portable deploy, e.g. alpha)
    parents = Path(__file__).resolve().parents
    if len(parents) > 2:  # guard: shallow deploys (e.g. C:\shim) have no parents[2]
        candidates.append(parents[2] / "backend/app/protocol_engines/atcs/codeline.py")
    for f in candidates:
        if f.exists():
            spec = importlib.util.spec_from_file_location("atcs_codeline", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(
        "codeline.py not found — copy it next to this script "
        f"(looked in: {', '.join(str(c) for c in candidates)})"
    )


cl = _load_codeline()


def _log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


# ---------------------------------------------------------------------------
# Frame stream — reuses the engine's codeline builders so this validates the
# exact construction logic the ATCS engine ships.
# ---------------------------------------------------------------------------
def frame_stream(args):
    """Infinite generator of (codeline_bytes, human_label).

    Models a handful of waysides reporting field indications to the office, with
    an occasional office->wayside control. Every frame is vital=True so the
    31-bit K-II CRC (our most spec-confident element) is exercised.
    """
    office = cl.build_atcs_address_7series(
        args.railroad, args.codeline, 0, cl.ATCS_EXT7_INDICATION,
        type_digit=cl.ATCS_TYPE_OFFICE,
    )
    waysides = [
        cl.build_atcs_address_7series(
            args.railroad, args.codeline, serial, cl.ATCS_EXT7_INDICATION,
            type_digit=cl.ATCS_TYPE_WAYSIDE_7,
        )
        for serial in range(1, args.waysides + 1)
    ]
    aspects = [0x00, 0x03, 0x05, 0x08]  # stop / approach / clear-ish, our convention
    if getattr(args, "replay", None):
        # Diagnostic: replay a captured real ATCS frame verbatim to confirm the
        # transport/feed framing is correct against ATCSMon. The corpus hex begins
        # with the RF address-type octet 0x23 — that IS the first frame byte, so it
        # is kept verbatim (with --prefix empty, nothing is prepended).
        # Accept one hex frame, or several separated by ',' / ';' to cycle through
        # (a length sweep — confirm ATCSMon accepts a range of frame sizes).
        specs = [s for s in args.replay.replace(";", ",").split(",") if s.strip()]
        frames = [bytes.fromhex(s.replace(" ", "").replace("\n", "")) for s in specs]
        i = 0
        while True:
            raw = frames[i % len(frames)]
            i += 1
            yield raw, f"replay frame #{i} ({len(raw)}B)"

    for n in itertools.count():
        wayside = waysides[n % len(waysides)]
        if args.control_every and n and n % args.control_every == 0:
            # office -> wayside control
            usr = cl.build_control_usrdata(command=0x01, target=(n % 4), value=0x01)
            frame, fields = cl.build_codeline_frame(
                office, wayside, usr, sseq=n & 0x7F, rseq=(n + 1) & 0x7F,
                vital=args.vital, message_number=n & 0x7F,
            )
            yield _apply_experiments(frame, fields, args), f"control office->{wayside}"
        else:
            # wayside -> office indication
            usr = cl.build_indication_usrdata(
                signal_aspect=aspects[n % len(aspects)],
                switch_normal=(n % 3 != 0),
                occupancy=(n % 2),
            )
            frame, fields = cl.build_codeline_frame(
                wayside, office, usr, sseq=n & 0x7F, rseq=(n + 1) & 0x7F,
                vital=args.vital, message_number=n & 0x7F,
            )
            yield _apply_experiments(frame, fields, args), f"indication {wayside}->office"


def _apply_experiments(frame: bytes, fields: list[dict], args) -> bytes:
    """Diagnostic frame mutations for probing ATCSMon's length expectations.

    ``--no-facility`` drops the 1-octet facility-length field we insert after the
    source address (tests the hypothesis that ATCSMon computes the packet length
    without it, so our frame reads one octet too long). Combine with --no-vital so
    the (now-stale) vital CRC doesn't confound the length check.
    """
    if getattr(args, "no_facility", False):
        fac = next((f for f in fields if f["field"] == "atcs.facility_len"), None)
        if fac is not None:
            off = fac["off"]
            frame = frame[:off] + frame[off + 1:]
    return frame


# ---------------------------------------------------------------------------
# Record framing — the uncertain bits are all flags.
# ---------------------------------------------------------------------------
def encode_record(frame: bytes, args) -> bytes:
    if args.encoding == "binary":
        payload = frame
    elif args.hex_space:
        payload = " ".join(f"{b:02X}" for b in frame).encode("ascii")
    else:
        payload = frame.hex().upper().encode("ascii")

    out = bytearray()
    if args.prefix:
        out += args.prefix.encode("ascii")
    if args.length_mode == "byte":
        out.append(len(payload) & 0xFF)
    elif args.length_mode == "word":
        out += struct.pack(">H", len(payload))
    out += payload
    if args.record_term:
        out += args.record_term.encode("ascii").decode("unicode_escape").encode("latin-1")
    return bytes(out)


def encode_port_reply(udp_port: int, mode: str) -> bytes:
    if mode == "binary":
        return struct.pack(">H", udp_port)
    if mode == "asciicrlf":
        return f"{udp_port}\r\n".encode("ascii")
    return str(udp_port).encode("ascii")


# ---------------------------------------------------------------------------
# Per-client session
# ---------------------------------------------------------------------------
def session(usock: socket.socket, udp_port: int, tcp_peer, args) -> None:
    client_addr = None
    if args.assume_client:
        host, _, port = args.assume_client.partition(":")
        client_addr = (host, int(port))
        _log(f"[udp {udp_port}] assuming client {client_addr} (no handshake wait)")
    disconnected = threading.Event()

    def rx() -> None:
        nonlocal client_addr
        while not disconnected.is_set():
            try:
                data, addr = usock.recvfrom(4096)
            except OSError:
                break
            client_addr = addr
            _log(f"[udp {udp_port}] rx {len(data)}B from {addr}: {data[:40]!r}")
            if b"DISCONNECT" in data:
                _log(f"[udp {udp_port}] client sent DISCONNECT")
                disconnected.set()

    threading.Thread(target=rx, daemon=True).start()

    frames = frame_stream(args)
    sent = 0
    last_tx = time.monotonic()
    waited = 0.0
    while not disconnected.is_set():
        if client_addr is None:
            time.sleep(0.2)
            waited += 0.2
            if waited and waited % 5 < 0.2:
                _log(f"[udp {udp_port}] waiting for client 'Thanks' on UDP {udp_port}...")
            continue

        now = time.monotonic()
        if args.keepalive and now - last_tx >= args.keepalive:
            usock.sendto(b"*KEEPALIVE", client_addr)
            last_tx = now
            _log(f"[udp {udp_port}] tx *KEEPALIVE")

        frame, label = next(frames)
        rec = encode_record(frame, args)
        usock.sendto(rec, client_addr)
        sent += 1
        last_tx = time.monotonic()
        if sent <= 3 or args.verbose:
            _log(f"[udp {udp_port}] tx#{sent} [{label}] {len(rec)}B: {rec[:56].hex()}")
        time.sleep(args.interval)

    try:
        usock.close()
    except OSError:
        pass
    _log(f"[udp {udp_port}] session ended (sent {sent} records)")


# ---------------------------------------------------------------------------
def serve(args) -> None:
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind((args.bind, args.tcp_port))
    tcp.listen(8)
    _log(f"ATCSMon feed server: TCP listener {args.bind}:{args.tcp_port}, "
         f"UDP data ports {args.udp_base}..{args.udp_base + args.udp_span - 1}")
    _log(f"record format: prefix={args.prefix!r} length={args.length_mode} "
         f"encoding={args.encoding}{' (spaced)' if args.hex_space else ''} "
         f"vital={args.vital}")
    _log("point ATCSMon here: add a data source -> this host IP, port "
         f"{args.tcp_port}. Flip --encoding/--length-mode if it won't decode.")

    slots = itertools.count()
    while True:
        conn, peer = tcp.accept()
        _log(f"TCP connect from {peer}")
        slot = next(slots) % args.udp_span
        udp_port = args.udp_base + slot
        usock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        usock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            usock.bind((args.bind, udp_port))
        except OSError as e:
            _log(f"could not bind UDP {udp_port}: {e}; closing")
            conn.close()
            continue
        try:
            conn.sendall(encode_port_reply(udp_port, args.port_reply))
        finally:
            conn.close()
        _log(f"assigned UDP data port {udp_port} to {peer} "
             f"(reply mode={args.port_reply})")
        threading.Thread(target=session, args=(usock, udp_port, peer, args),
                         daemon=True).start()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bind", default="0.0.0.0", help="listen address (default all)")
    p.add_argument("--tcp-port", type=int, default=4802, help="TCP listener port")
    p.add_argument("--udp-base", type=int, default=30000, help="first UDP data port")
    p.add_argument("--udp-span", type=int, default=60, help="how many UDP data ports")
    # --- the uncertain record format: these are the knobs to flip vs ATCSMon ---
    p.add_argument("--encoding", choices=["binary", "hex"], default="binary",
                   help="codeline payload encoding (binary is the leading guess)")
    p.add_argument("--hex-space", action="store_true",
                   help="with --encoding hex, space-separate the octets")
    p.add_argument("--prefix", default="",
                   help="extra record prefix before the frame. Leave EMPTY: the "
                        "frame already begins with its RF address-type octet 0x23 "
                        "(the byte ATCSMon shows as '#'). Setting '#' double-prefixes.")
    p.add_argument("--length-mode", choices=["none", "byte", "word"], default="none",
                   help="length field before the payload")
    p.add_argument("--record-term", default="",
                   help="record terminator, e.g. '\\n' (escapes honored)")
    p.add_argument("--port-reply", choices=["ascii", "asciicrlf", "binary"],
                   default="ascii", help="how the TCP handshake returns the UDP port")
    # --- content ---
    p.add_argument("--interval", type=float, default=1.5, help="seconds between frames")
    p.add_argument("--railroad", type=int, default=125, help="AAR railroad number")
    p.add_argument("--codeline", type=int, default=323, help="codeline/territory number")
    p.add_argument("--waysides", type=int, default=4, help="distinct wayside devices")
    p.add_argument("--control-every", type=int, default=6,
                   help="emit an office->wayside control every N frames (0=off)")
    p.add_argument("--no-vital", dest="vital", action="store_false",
                   help="omit the vital CRC (default: include it)")
    p.add_argument("--no-facility", action="store_true",
                   help="diagnostic: drop the facility-length octet (probe ATCSMon "
                        "packet-length expectations; combine with --no-vital)")
    p.add_argument("--replay", default="",
                   help="diagnostic: replay this hex frame verbatim (a captured real "
                        "ATCS frame) instead of generating codeline; confirms transport")
    p.add_argument("--keepalive", type=float, default=120.0,
                   help="seconds of idle before *KEEPALIVE (0=off)")
    p.add_argument("--assume-client", default="",
                   help="stream to IP:PORT without waiting for a handshake")
    p.add_argument("--verbose", action="store_true", help="log every record sent")
    p.set_defaults(vital=True)
    args = p.parse_args()

    try:
        serve(args)
    except KeyboardInterrupt:
        _log("shutting down")


if __name__ == "__main__":
    main()
