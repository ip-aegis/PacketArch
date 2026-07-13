# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Host-level CPU/memory stats for the Live Traffic dashboard.

All LOCAL agents (local sensor labs) run directly on the PacketArch host and
share its CPU and RAM — each one's heartbeat reports the same host-wide
figures, so per-agent gauges are the same number repeated. The dashboard
instead shows ONE host gauge for the whole local section, computed here.

Reads the host's /proc directly: the backend container runs without cpu/memory
cgroup limits, so /proc/stat and /proc/meminfo reflect the physical host. The
MemAvailable-based percentage also correctly counts the CV sensors' AF_PACKET
ring buffers (~1 GiB each), which cgroup-based tools like `docker stats` miss.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# (busy_jiffies, total_jiffies) from the previous poll — CPU% is the busy share
# of the delta between dashboard polls. First poll after boot reports 0.0.
_prev_cpu: tuple[float, float] | None = None


def get_host_stats() -> dict | None:
    """Host CPU%, memory% and totals, or None if /proc isn't readable."""
    global _prev_cpu
    try:
        with open("/proc/stat") as f:
            fields = [float(x) for x in f.readline().split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0.0)  # idle + iowait
        total = sum(fields)
        busy = total - idle
        cpu_percent = 0.0
        if _prev_cpu is not None:
            d_total = total - _prev_cpu[1]
            d_busy = busy - _prev_cpu[0]
            if d_total > 0:
                cpu_percent = max(0.0, min(100.0, 100.0 * d_busy / d_total))
        _prev_cpu = (busy, total)

        meminfo: dict[str, float] = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if parts:
                    meminfo[key] = float(parts[0])  # kB
        mem_total = meminfo.get("MemTotal", 0.0)
        mem_avail = meminfo.get("MemAvailable", 0.0)
        if mem_total <= 0:
            return None
        mem_used = mem_total - mem_avail

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(100.0 * mem_used / mem_total, 1),
            "memory_used_gb": round(mem_used / 1048576, 1),
            "memory_total_gb": round(mem_total / 1048576, 1),
            "cores": os.cpu_count() or 0,
        }
    except Exception as e:  # noqa: BLE001 — dashboard must render without host stats
        logger.warning("host stats unavailable: %s", e)
        return None
