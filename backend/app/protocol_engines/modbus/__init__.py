"""Modbus protocol engine package.

Supports both Modbus TCP and Modbus RTU variants:
- Modbus TCP: MBAP header over TCP/IP (port 502)
- Modbus RTU: CRC-16 framed, supports RTU-over-TCP encapsulation
"""

from app.protocol_engines.modbus.engine import ModbusTcpEngine
from app.protocol_engines.modbus.rtu_engine import ModbusRtuEngine

__all__ = ["ModbusTcpEngine", "ModbusRtuEngine"]
