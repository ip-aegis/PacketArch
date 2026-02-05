"""DCS (Distributed Control System) protocol engine.

Supports multiple DCS vendors:
- Emerson DeltaV (UDP 18507)
- Honeywell Experion (CDA protocol over TCP)
- Yokogawa CENTUM VP (Vnet/IP UDP 230)
- Schneider Triconex (TriStation UDP 1502)

Note: ABB 800xA uses MMS (see IEC 61850 engine)
      Siemens PCS7 uses S7comm (see S7 engine)
      GE Mark VI uses proprietary protocols
"""

from app.protocol_engines.dcs.engine import DCSEngine

__all__ = ["DCSEngine"]
