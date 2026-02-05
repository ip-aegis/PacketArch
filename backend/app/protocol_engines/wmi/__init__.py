"""WMI (Windows Management Instrumentation) protocol engine.

WMI is used for Windows device discovery and management over DCOM/RPC.

Protocol stack:
- WMI queries (SELECT * FROM Win32_*)
- DCOM/ORPC (Object RPC)
- DCE/RPC (Distributed Computing Environment RPC)
- TCP (ports 135 + dynamic)

Key features:
- RPC endpoint mapper (port 135)
- Dynamic port allocation (49152-65535)
- NTLMSSP authentication
- WQL (WMI Query Language) support

Common discovery queries:
- Win32_ComputerSystem: Hardware and system info
- Win32_OperatingSystem: OS version and details
- Win32_NetworkAdapterConfiguration: Network settings
- Win32_BIOS: BIOS/firmware information
"""

from app.protocol_engines.wmi.engine import WMIEngine

__all__ = ["WMIEngine"]
