# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Slim, self-contained Mimic persona runtime for off-box (CML) nodes.

Runs a device persona from a fully-RESOLVED spec (identity + point map baked in
by the backend at deploy time), depending only on stdlib + pymodbus — no
device_templates, no fingerprint_applicator, no scapy/numpy, no Docker. This is
what lets a persona run natively on a 512 MB Alpine CML node.

Ships to a node as a small tarball; the node does ``apk add python3 py3-pip``,
``pip install pymodbus``, unpacks this, and runs ``python -m mimic_slim.run``.
"""

from __future__ import annotations
