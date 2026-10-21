# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Ambient DNS (RFC 1035) query/response frames between scenario hosts and
the site's DNS server."""

from __future__ import annotations

from scapy.layers.dns import DNS, DNSQR, DNSRR, DNSRRSRV
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether


def build_dns_query(src_mac: str, src_ip: str, dst_mac: str, dst_ip: str, src_port: int,
                    txid: int, qname: str, qtype: str = "A", ttl: int = 128) -> bytes:
    return bytes(
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / UDP(sport=src_port, dport=53)
        / DNS(id=txid, rd=1, qd=DNSQR(qname=qname, qtype=qtype))
    )


def build_dns_a_response(src_mac: str, src_ip: str, dst_mac: str, dst_ip: str, dst_port: int,
                         txid: int, qname: str, address: str, ttl: int = 128) -> bytes:
    return bytes(
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / UDP(sport=53, dport=dst_port)
        / DNS(id=txid, qr=1, aa=1, rd=1, ra=1, qd=DNSQR(qname=qname, qtype="A"),
              an=DNSRR(rrname=qname, type="A", ttl=1200, rdata=address))
    )


def build_dns_srv_response(src_mac: str, src_ip: str, dst_mac: str, dst_ip: str, dst_port: int,
                           txid: int, qname: str, target: str, address: str, port: int,
                           ttl: int = 128) -> bytes:
    return bytes(
        Ether(src=src_mac, dst=dst_mac)
        / IP(src=src_ip, dst=dst_ip, ttl=ttl)
        / UDP(sport=53, dport=dst_port)
        / DNS(id=txid, qr=1, aa=1, rd=1, ra=1, qd=DNSQR(qname=qname, qtype="SRV"),
              an=DNSRRSRV(rrname=qname, ttl=600, priority=0, weight=100, port=port, target=target),
              ar=DNSRR(rrname=target, type="A", ttl=3600, rdata=address))
    )
