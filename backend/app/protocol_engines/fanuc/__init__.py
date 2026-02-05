"""FANUC FOCAS (FANUC Open CNC API Specification) protocol engine.

FOCAS is FANUC's proprietary protocol for CNC machine communication.
Default port: TCP 8193

Supported CNC models (simulated):
- Series 30i-B, 31i-B, 32i-B, 35i
- Series 0i-F, 0i-F Plus
- Power Motion i-A

CNC machine types:
- Machining Center (milling)
- Lathe (turning)
- Punch Press
- Laser
- Wire EDM
- Grinder

Common monitoring data:
- System info (cnc_sysinfo)
- Status (cnc_statinfo) - run/idle/alarm states
- Axis positions (cnc_rdposition)
- Spindle speed/load (cnc_acts2)
- Program info (cnc_rdprognum)
- Feedrate (cnc_actf)
- Alarms (cnc_alarm)
"""

from app.protocol_engines.fanuc.engine import FANUCEngine

__all__ = ["FANUCEngine"]
