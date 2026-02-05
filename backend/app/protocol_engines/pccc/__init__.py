"""PCCC/DF1 protocol engine for Allen-Bradley/Rockwell PLCs.

PCCC (Programmable Controller Communication Commands) is the application
layer protocol used by Allen-Bradley PLCs for data access and configuration.

DF1 is the data link layer protocol for serial communication.

Supported devices:
- PLC-5 series (legacy)
- SLC-500 series
- MicroLogix series
- ControlLogix/CompactLogix (compatibility mode)

Transport modes:
- PCCC over TCP (port 2222) - Legacy direct TCP
- PCCC over EtherNet/IP (port 44818) - Modern encapsulated
"""

from app.protocol_engines.pccc.engine import PCCCEngine

__all__ = ["PCCCEngine"]
