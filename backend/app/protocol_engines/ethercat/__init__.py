"""EtherCAT protocol engine for Beckhoff motion control systems.

EtherCAT (Ethernet for Control Automation Technology) is a high-performance
real-time industrial Ethernet protocol developed by Beckhoff.

Key features:
- Layer 2 protocol (EtherType 0x88A4)
- Processing on the fly for sub-microsecond cycle times
- Daisy chain topology with automatic addressing
- Distributed Clocks (DC) for synchronized outputs
- Mailbox protocols (CoE, EoE, FoE, SoE)

Typical applications:
- Motion control (servo drives, stepper motors)
- CNC machines
- Packaging machines
- Robotics
- Semiconductor manufacturing
"""

from app.protocol_engines.ethercat.engine import EtherCATEngine

__all__ = ["EtherCATEngine"]
