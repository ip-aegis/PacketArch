"""Distribution and Logistics industry scenario templates.

Primary Vendors: KUKA, MiR (AGVs), Rockwell, Siemens (conveyors), Cognex (vision), Impinj/Zebra (RFID)
Protocol Focus: EtherNet/IP (Rockwell conveyors, AGVs), PROFINET (KUKA/Siemens), Modbus TCP (sensors, MiR)

Enhanced templates with:
- AGV fleet management and mobile robot traffic
- Conveyor and sortation system automation
- RFID tracking and barcode scanning workflows
- Cold chain temperature monitoring (refrigerated variant)
- 30-50 devices per template following Purdue model
"""

from typing import Any


DISTRIBUTION_LOGISTICS_TEMPLATES: dict[str, dict[str, Any]] = {
    # ============================================================
    # TEMPLATE 1: FULFILLMENT CENTER (45 devices)
    # E-commerce fulfillment with AGVs, conveyors, pick-to-light
    # ============================================================
    "fulfillment_center": {
        "name": "Fulfillment Center",
        "description": "E-commerce fulfillment center with goods-to-person AGV system, conveyor sortation, "
                       "and pick-to-light stations. Features KUKA and MiR mobile robots for inventory transport, "
                       "Rockwell conveyor automation, Cognex vision QC, and SICK barcode scanning. "
                       "45 devices across WMS core, fleet management, conveyor, AGV, and pick zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "devices": [
            # ============================================================
            # WMS CORE ZONE (Level 3) - 4 devices
            # Warehouse Management System servers and core infrastructure
            # ============================================================
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "wms_core",
             "name": "WCS_Primary_Server", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Warehouse Control System"},
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "wms_core",
             "name": "WCS_Backup_Server", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Warehouse Control System"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wms_core",
             "name": "WMS_Core_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Core Network Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "wms_core",
             "name": "WMS_Core_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Core Network Switch"},

            # ============================================================
            # FLEET MANAGEMENT ZONE (Level 2) - 3 devices
            # AGV fleet controllers and coordination
            # ============================================================
            {"type": "fleet_manager", "vendor": "kuka", "count": 1, "zone": "fleet_mgmt",
             "name": "KUKA_Fleet_Manager", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KUKA.FleetManager",
             "role": "AGV Fleet Controller",
             "cve_ids": ["CVE-2022-30310"]},
            {"type": "fleet_manager", "vendor": "mir", "count": 1, "zone": "fleet_mgmt",
             "name": "MiR_Fleet_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "MiR Fleet",
             "role": "AMR Fleet Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "fleet_mgmt",
             "name": "Fleet_Network_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # CONVEYOR ZONE (Level 2) - 10 devices
            # Conveyor PLCs, VFDs, and sortation controllers
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Main_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0003, "timeout_rate": 0.0001},
             "role": "Conveyor Master Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Inbound_Conveyor_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L83E",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Outbound_Conveyor_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L83E",
             "role": "Conveyor Zone Controller"},
            {"type": "sortation_controller", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Sortation_Master_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Sortation Controller"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Main_Takeaway_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Merge_Line_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Accumulation_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Divert_Gate_VFD", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Variable Frequency Drive"},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Safety_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Safety Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "conveyor_zone",
             "name": "Conveyor_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # AGV ZONE (Level 1) - 14 devices
            # Individual AGV/AMR units
            # ============================================================
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_01", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_02", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_03", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_04", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 1500",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_05", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_06", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_07", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "agv", "vendor": "kuka", "count": 1, "zone": "agv_zone",
             "name": "AGV_KUKA_08", "protocols": ["profinet", "ethernet_ip"],
             "fingerprint_model": "KMP 600",
             "role": "Automated Guided Vehicle"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_01", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_02", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_03", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_04", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_05", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "agv_zone",
             "name": "AMR_MiR_06", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR250",
             "role": "Autonomous Mobile Robot"},

            # ============================================================
            # PICK ZONE (Level 1) - 14 devices
            # Pick-to-light, barcode scanners, vision systems
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_Master_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1769-L33ER",
             "role": "Pick Station Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_1_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_2_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_3_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_4_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_5_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "pick_zone",
             "name": "Pick_Station_6_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Pick-to-Light I/O"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Inbound_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Inbound_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Outbound_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "pick_zone",
             "name": "Outbound_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Fixed Barcode Scanner"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "pick_zone",
             "name": "QC_Vision_Station_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Quality Control Vision",
             "cve_ids": ["CVE-2023-4707", "CVE-2023-4708"]},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "pick_zone",
             "name": "QC_Vision_Station_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Quality Control Vision"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "pick_zone",
             "name": "Pick_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Industrial Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "wms_core",
             "name": "Warehouse_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             "cve_ids": ["CVE-2022-1523", "CVE-2022-1524", "CVE-2023-22846"]},
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "wms_core",
             "name": "WMS_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             "cve_ids": ["CVE-2019-0708"]},
        ],
        "flows": [
            # ============================================================
            # FLEET MANAGEMENT FLOWS
            # ============================================================
            # KUKA Fleet Manager to KUKA AGVs - PROFINET cyclic (8ms) - native KUKA protocol
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_01",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_02",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_03",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_04",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_05",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_06",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_07",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "KUKA_Fleet_Manager", "target": "AGV_KUKA_08",
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # MiR Fleet Controller to MiR AMRs - mission commands (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_01",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_02",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_03",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_04",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_05",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "MiR_Fleet_Controller", "target": "AMR_MiR_06",
             "jitter_ms": 30, "jitter_type": "gaussian"},

            # ============================================================
            # CONVEYOR ZONE FLOWS
            # ============================================================
            # Main Conveyor PLC to VFDs - cyclic I/O (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Conveyor_Main_PLC", "target": "Main_Takeaway_VFD",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Conveyor_Main_PLC", "target": "Merge_Line_VFD",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Conveyor_Main_PLC", "target": "Accumulation_VFD",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Sortation PLC to Divert VFD
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sortation_Master_PLC", "target": "Divert_Gate_VFD",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Inter-PLC communication - zone coordination (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Main_PLC", "target": "Inbound_Conveyor_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Main_PLC", "target": "Outbound_Conveyor_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Main_PLC", "target": "Sortation_Master_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Safety PLC to conveyor PLCs - safety interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Conveyor_Main_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Inbound_Conveyor_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Outbound_Conveyor_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Sortation_Master_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # Safety PLC to VFDs - E-stop interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Main_Takeaway_VFD",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Merge_Line_VFD",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Accumulation_VFD",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Conveyor_Safety_PLC", "target": "Divert_Gate_VFD",
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # PICK ZONE FLOWS
            # ============================================================
            # Pick Station PLC to I/O modules - pick-to-light (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_1_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_2_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_3_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_4_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_5_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Pick_Station_Master_PLC", "target": "Pick_Station_6_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Pick PLC to barcode scanners (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Pick_Station_Master_PLC", "target": "Inbound_Scanner_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Pick_Station_Master_PLC", "target": "Inbound_Scanner_2",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Pick_Station_Master_PLC", "target": "Outbound_Scanner_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Pick_Station_Master_PLC", "target": "Outbound_Scanner_2",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Vision systems to Pick PLC - QC results (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source": "QC_Vision_Station_1", "target": "Pick_Station_Master_PLC",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source": "QC_Vision_Station_2", "target": "Pick_Station_Master_PLC",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # ============================================================
            # WCS/SCADA FLOWS (Level 3 to Level 2)
            # ============================================================
            # Primary WCS to all conveyor PLCs (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "WCS_Primary_Server", "target": "Conveyor_Main_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "WCS_Primary_Server", "target": "Inbound_Conveyor_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "WCS_Primary_Server", "target": "Outbound_Conveyor_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "WCS_Primary_Server", "target": "Sortation_Master_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "WCS_Primary_Server", "target": "Pick_Station_Master_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # WCS to Fleet Managers (500ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 500,
             "source": "WCS_Primary_Server", "target": "KUKA_Fleet_Manager",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "WCS_Primary_Server", "target": "MiR_Fleet_Controller",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # WCS to Safety PLC status (1s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source": "WCS_Primary_Server", "target": "Conveyor_Safety_PLC",
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # WCS to Vision Systems (1s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source": "WCS_Primary_Server", "target": "QC_Vision_Station_1",
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source": "WCS_Primary_Server", "target": "QC_Vision_Station_2",
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # Backup WCS heartbeat to primary (5s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 5000,
             "source": "WCS_Backup_Server", "target": "WCS_Primary_Server",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            # WCS monitoring all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "WCS_Primary_Server", "target": "WMS_Core_Switch_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "WCS_Primary_Server", "target": "WMS_Core_Switch_2"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "WCS_Primary_Server", "target": "Fleet_Network_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "WCS_Primary_Server", "target": "Conveyor_Zone_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "WCS_Primary_Server", "target": "Pick_Zone_Switch"},

            # ============================================================
            # EWON REMOTE ACCESS - Talk2M Cloud Communication (30s heartbeat)
            # Uses actual Talk2M public IPs for Cyber Vision external detection
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source": "Warehouse_Remote_Gateway", "target": "talk2m_cloud",
             "external_ip": "13.56.142.1", "external_port": 443,
             "description": "eWON Talk2M VPN heartbeat",
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # eWON Modbus polling to conveyor PLCs (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Warehouse_Remote_Gateway", "target": "Conveyor_Main_PLC",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # JUMP SERVER - External RDP Access (simulated admin sessions)
            # ============================================================
            {"protocol": "rdp", "pattern": "external", "interval_ms": 60000,
             "source": "WMS_Jump_Server", "target": "external_admin",
             "external_ip": "203.0.113.50", "external_port": 3389,
             "description": "Remote admin RDP session",
             "jitter_ms": 15000, "jitter_type": "uniform"},

            # Jump server SNMP monitoring
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "WMS_Jump_Server", "target": "WMS_Core_Switch_1"},
        ],
        "zones": [
            {"id": "wms_core", "name": "WMS Core", "level": 3,
             "subnet_offset": 0, "vlan": 100, "security_level": "high"},
            {"id": "fleet_mgmt", "name": "Fleet Management", "level": 2,
             "subnet_offset": 1, "vlan": 110, "security_level": "high"},
            {"id": "conveyor_zone", "name": "Conveyor Network", "level": 2,
             "subnet_offset": 2, "vlan": 120, "security_level": "standard"},
            {"id": "agv_zone", "name": "AGV Network", "level": 1,
             "subnet_offset": 3, "vlan": 130, "security_level": "standard"},
            {"id": "pick_zone", "name": "Pick Stations", "level": 1,
             "subnet_offset": 4, "vlan": 140, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "jitter_spike", "agv_position_lag"],
            "protocol": ["ethernet_ip_error", "modbus_exception"],
            "sequence": ["duplicate", "out_of_order", "scan_retry"],
            "payload": ["barcode_read_error", "vision_inspection_fail"],
            "network": ["wireless_dropout"],
            "security": ["unauthorized_agv_command"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["13.56.142.1", "54.95.198.117"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.50",
        },
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 2: DISTRIBUTION CENTER (40 devices)
    # Traditional DC with cross-docking, RFID tracking
    # ============================================================
    "distribution_center": {
        "name": "Distribution Center",
        "description": "Regional distribution center with pallet conveyors, cross-docking operations, "
                       "and RFID tracking at dock doors. Features Siemens S7-1500 conveyor automation, "
                       "Impinj and Zebra RFID readers for inventory tracking, and SICK barcode scanners. "
                       "40 devices across operations core, receiving, shipping, and conveyor zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "devices": [
            # ============================================================
            # DC CORE ZONE (Level 3) - 4 devices
            # ============================================================
            {"type": "scada_server", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Operations_Server", "protocols": ["s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Distribution Operations"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "dc_core",
             "name": "DC_Historian", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Proficy Historian",
             "role": "Data Historian"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Core_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Core Switch",
             "cve_ids": ["CVE-2022-46140", "CVE-2023-44373"]},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "dc_core",
             "name": "DC_Core_Switch_2", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Core Switch"},

            # ============================================================
            # RECEIVING ZONE (Level 2) - 10 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_Main_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Receiving Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2022-38465", "CVE-2023-46156"]},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_1_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader",
             "cve_ids": ["CVE-2023-28762"]},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_2_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_3_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "receiving",
             "name": "Dock_Door_4_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "receiving",
             "name": "Receiving_RFID_Gateway_1", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway",
             "cve_ids": ["CVE-2023-24063", "CVE-2023-27839"]},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "receiving",
             "name": "Receiving_RFID_Gateway_2", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "receiving",
             "name": "Receiving_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Pallet Barcode Scanner"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Dock I/O"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "receiving",
             "name": "Receiving_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # SHIPPING ZONE (Level 2) - 10 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_Main_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Shipping Controller",
             "cve_ids": ["CVE-2019-13945", "CVE-2022-38465"]},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "shipping",
             "name": "Ship_Door_1_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_reader", "vendor": "impinj", "count": 1, "zone": "shipping",
             "name": "Ship_Door_2_RFID", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Speedway R700",
             "role": "Dock Door RFID Reader"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "shipping",
             "name": "Shipping_RFID_Gateway_1", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "rfid_gateway", "vendor": "zebra", "count": 1, "zone": "shipping",
             "name": "Shipping_RFID_Gateway_2", "protocols": ["snmp", "modbus_tcp"],
             "fingerprint_model": "FX9600",
             "role": "RFID Aggregation Gateway"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "shipping",
             "name": "Shipping_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "Pallet Barcode Scanner"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_IO_Module", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Dock I/O"},
            {"type": "safety_plc", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Dock_Safety_Controller", "protocols": ["profinet", "profisafe"],
             "fingerprint_model": "6ES7 516-3FN02-0AB0",
             "role": "Dock Safety Controller"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Safety_Light_Curtain_IO", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Safety I/O"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "shipping",
             "name": "Shipping_Switch", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # CONVEYOR BACKBONE (Level 1) - 16 devices
            # ============================================================
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_1_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_2_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Zone_3_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 511-1AK02-0AB0",
             "role": "Conveyor Zone Controller"},
            {"type": "plc", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Controller_PLC", "protocols": ["profinet", "s7comm_plus"],
             "fingerprint_model": "6ES7 517-3AP00-0AB0",
             "role": "Cross-Dock Sortation"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive",
             "cve_ids": ["CVE-2022-30065", "CVE-2022-43398"]},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_3", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_VFD_4", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_1", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_2", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_3", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "drive", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Sortation_Divert_VFD_4", "protocols": ["profinet", "modbus_tcp"],
             "fingerprint_model": "6SL3210-1KE21-7UF1",
             "role": "Divert Drive"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Sensors_IO_1", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Conveyor Sensors"},
            {"type": "io_module", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Sensors_IO_2", "protocols": ["profinet"],
             "fingerprint_model": "6ES7 155-6AU01-0BN0",
             "role": "Conveyor Sensors"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Switch_1", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},
            {"type": "switch", "vendor": "siemens", "count": 1, "zone": "conveyor_backbone",
             "name": "Conveyor_Switch_2", "protocols": ["profinet", "snmp"],
             "fingerprint_model": "6GK5 208-0BA00-2AB2",
             "role": "Zone Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "dc_core",
             "name": "DC_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             "cve_ids": ["CVE-2022-1523", "CVE-2022-1524", "CVE-2023-22846"]},
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "dc_core",
             "name": "DC_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             "cve_ids": ["CVE-2019-0708"]},
        ],
        "flows": [
            # ============================================================
            # RECEIVING ZONE - PROFINET FLOWS (Siemens)
            # ============================================================
            # Receiving PLC to I/O module - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Receiving_Main_PLC", "target": "Receiving_IO_Module",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Receiving PLC to RFID readers - Modbus TCP (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Dock_Door_1_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Dock_Door_2_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Dock_Door_3_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Dock_Door_4_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Receiving PLC to RFID gateways (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Receiving_RFID_Gateway_1",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Receiving_Main_PLC", "target": "Receiving_RFID_Gateway_2",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Receiving PLC to barcode scanner (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Receiving_Main_PLC", "target": "Receiving_Scanner_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SHIPPING ZONE - PROFINET FLOWS (Siemens)
            # ============================================================
            # Shipping PLC to I/O module - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Shipping_Main_PLC", "target": "Shipping_IO_Module",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Shipping PLC to RFID readers (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Shipping_Main_PLC", "target": "Ship_Door_1_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Shipping_Main_PLC", "target": "Ship_Door_2_RFID",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Shipping PLC to RFID gateways (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Shipping_Main_PLC", "target": "Shipping_RFID_Gateway_1",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Shipping_Main_PLC", "target": "Shipping_RFID_Gateway_2",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Shipping PLC to barcode scanner (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Shipping_Main_PLC", "target": "Shipping_Scanner_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # Safety PLC to Safety I/O - PROFIsafe (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source": "Dock_Safety_Controller", "target": "Safety_Light_Curtain_IO",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # Safety PLC to zone PLCs - safety interlock (4ms)
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source": "Dock_Safety_Controller", "target": "Shipping_Main_PLC",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "profisafe", "pattern": "safety", "interval_ms": 4,
             "source": "Dock_Safety_Controller", "target": "Receiving_Main_PLC",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # ============================================================
            # CONVEYOR BACKBONE - PROFINET FLOWS (Siemens)
            # ============================================================
            # Conveyor PLCs to VFDs - PROFINET cyclic (8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Conveyor_Zone_1_PLC", "target": "Conveyor_VFD_1",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Conveyor_Zone_1_PLC", "target": "Conveyor_VFD_2",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Conveyor_Zone_2_PLC", "target": "Conveyor_VFD_3",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Conveyor_Zone_2_PLC", "target": "Conveyor_VFD_4",
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # Sortation PLC to divert VFDs (8ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Sortation_Controller_PLC", "target": "Sortation_Divert_VFD_1",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Sortation_Controller_PLC", "target": "Sortation_Divert_VFD_2",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Sortation_Controller_PLC", "target": "Sortation_Divert_VFD_3",
             "jitter_ms": 1, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 8,
             "source": "Sortation_Controller_PLC", "target": "Sortation_Divert_VFD_4",
             "jitter_ms": 1, "jitter_type": "gaussian"},

            # Conveyor PLCs to I/O modules - PROFINET cyclic (4ms)
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Conveyor_Zone_1_PLC", "target": "Conveyor_Sensors_IO_1",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Conveyor_Zone_2_PLC", "target": "Conveyor_Sensors_IO_2",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Inter-PLC communication - zone handoff (50ms)
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Zone_1_PLC", "target": "Conveyor_Zone_2_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Zone_2_PLC", "target": "Conveyor_Zone_3_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 50,
             "source": "Conveyor_Zone_3_PLC", "target": "Sortation_Controller_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Receiving/Shipping to Conveyor handoff (100ms)
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 100,
             "source": "Receiving_Main_PLC", "target": "Conveyor_Zone_1_PLC",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "profinet", "pattern": "poll", "interval_ms": 100,
             "source": "Conveyor_Zone_3_PLC", "target": "Shipping_Main_PLC",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SCADA/OPERATIONS (S7comm+ - Siemens native)
            # ============================================================
            # Operations Server to all PLCs - S7comm+ (500ms)
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Receiving_Main_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Shipping_Main_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Conveyor_Zone_1_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Conveyor_Zone_2_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Conveyor_Zone_3_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Sortation_Controller_PLC",
             "jitter_ms": 50, "jitter_type": "uniform"},
            {"protocol": "s7comm_plus", "pattern": "poll", "interval_ms": 500,
             "source": "DC_Operations_Server", "target": "Dock_Safety_Controller",
             "jitter_ms": 50, "jitter_type": "uniform"},

            # Historian data collection (30s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Historian", "target": "DC_Operations_Server",
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            # Operations Server to all switches (30s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "DC_Core_Switch_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "DC_Core_Switch_2"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "Receiving_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "Shipping_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "Conveyor_Switch_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "DC_Operations_Server", "target": "Conveyor_Switch_2"},

            # SNMP to RFID readers/gateways (60s)
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Dock_Door_1_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Dock_Door_2_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Dock_Door_3_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Dock_Door_4_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Ship_Door_1_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Ship_Door_2_RFID"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Receiving_RFID_Gateway_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Receiving_RFID_Gateway_2"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Shipping_RFID_Gateway_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Operations_Server", "target": "Shipping_RFID_Gateway_2"},

            # ============================================================
            # EWON REMOTE ACCESS - Talk2M Cloud Communication (30s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source": "DC_Remote_Gateway", "target": "talk2m_cloud",
             "external_ip": "54.95.198.117", "external_port": 443,
             "description": "eWON Talk2M VPN heartbeat",
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # eWON Modbus polling to conveyor PLCs (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "DC_Remote_Gateway", "target": "Conveyor_Zone_1_PLC",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # JUMP SERVER - External RDP Access
            # ============================================================
            {"protocol": "rdp", "pattern": "external", "interval_ms": 60000,
             "source": "DC_Jump_Server", "target": "external_admin",
             "external_ip": "203.0.113.51", "external_port": 3389,
             "description": "Remote admin RDP session",
             "jitter_ms": 15000, "jitter_type": "uniform"},

            # Jump server SNMP monitoring
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "DC_Jump_Server", "target": "DC_Core_Switch_1"},
        ],
        "zones": [
            {"id": "dc_core", "name": "DC Operations Core", "level": 3,
             "subnet_offset": 0, "vlan": 200, "security_level": "high"},
            {"id": "receiving", "name": "Receiving Area", "level": 2,
             "subnet_offset": 1, "vlan": 210, "security_level": "standard"},
            {"id": "shipping", "name": "Shipping Area", "level": 2,
             "subnet_offset": 2, "vlan": 220, "security_level": "standard"},
            {"id": "conveyor_backbone", "name": "Conveyor Backbone", "level": 1,
             "subnet_offset": 3, "vlan": 230, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["delayed_response", "rfid_read_timeout"],
            "protocol": ["profinet_alarm", "modbus_exception", "snmp_timeout"],
            "sequence": ["duplicate_rfid_read", "out_of_order"],
            "payload": ["rfid_read_error", "barcode_no_read"],
            "network": ["network_congestion"],
            "security": ["rfid_spoofing"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["54.95.198.117", "51.38.74.240"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.51",
        },
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 3: COLD CHAIN WAREHOUSE (35 devices)
    # Temperature-controlled with monitoring and compliance
    # ============================================================
    "cold_chain_warehouse": {
        "name": "Cold Chain Warehouse",
        "description": "Temperature-controlled warehouse with frozen (-20C) and chilled (2-8C) zones, "
                       "refrigeration system automation, and compliance logging. Features Schneider M580 "
                       "refrigeration PLCs, Honeywell temperature controllers, MiR cold-rated AMRs, "
                       "and historian for temperature compliance. 35 devices across HVAC, frozen, chilled, "
                       "and monitoring zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "devices": [
            # ============================================================
            # HVAC CONTROL ZONE (Level 3) - 6 devices
            # ============================================================
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "Refrigeration_Master_PLC", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEH586040",
             "role": "Refrigeration Master Controller",
             "cve_ids": ["CVE-2022-45788", "CVE-2022-45789", "CVE-2023-27979"]},
            {"type": "plc", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "Refrigeration_Backup_PLC", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "BMEH586040",
             "role": "Refrigeration Backup Controller"},
            {"type": "historian", "vendor": "ge", "count": 1, "zone": "hvac_control",
             "name": "Temperature_Compliance_Historian", "protocols": ["ethernet_ip"],
             "fingerprint_model": "Proficy Historian",
             "role": "Compliance Data Historian"},
            {"type": "hmi", "vendor": "schneider", "count": 1, "zone": "hvac_control",
             "name": "HVAC_Control_Room_HMI", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HMIGTO5310",
             "role": "HVAC Operator Interface"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "hvac_control",
             "name": "HVAC_Core_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "HVAC Network Switch"},
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "hvac_control",
             "name": "Cold_Chain_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Monitoring Gateway",
             "external_comms": True,
             "cve_ids": ["CVE-2022-1523", "CVE-2022-1524", "CVE-2023-22846"]},
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "hvac_control",
             "name": "Cold_Chain_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             "cve_ids": ["CVE-2019-0708"]},

            # ============================================================
            # FROZEN ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Zone_Controller_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Freezer Controller"},
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Zone_Controller_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Freezer Controller"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_3", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "frozen_zone",
             "name": "Frozen_Temp_Sensor_4", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "frozen_zone",
             "name": "Freezer_Compressor_VFD_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive",
             "cve_ids": ["CVE-2022-22804", "CVE-2022-22805"]},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "frozen_zone",
             "name": "Freezer_Compressor_VFD_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},

            # ============================================================
            # CHILLED ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Zone_Controller_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Cooler Controller"},
            {"type": "temperature_controller", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Zone_Controller_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "HC900 Controller",
             "role": "Cooler Controller"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_3", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "sensor", "vendor": "honeywell", "count": 1, "zone": "chilled_zone",
             "name": "Chilled_Temp_Sensor_4", "protocols": ["modbus_tcp"],
             "fingerprint_model": "STT850",
             "role": "Temperature Transmitter"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "chilled_zone",
             "name": "Chiller_Compressor_VFD_1", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},
            {"type": "drive", "vendor": "schneider", "count": 1, "zone": "chilled_zone",
             "name": "Chiller_Compressor_VFD_2", "protocols": ["modbus_tcp"],
             "fingerprint_model": "ATV930",
             "role": "Compressor Drive"},

            # ============================================================
            # AMBIENT/CONVEYOR ZONE (Level 1) - 9 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1769-L33ER",
             "role": "Conveyor Controller"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_VFD_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Conveyor Drive"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Conveyor_VFD_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 525",
             "role": "Conveyor Drive"},
            {"type": "fleet_manager", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_Fleet_Controller", "protocols": ["modbus_tcp"],
             "fingerprint_model": "MiR Fleet",
             "role": "Cold-Rated AMR Fleet"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_1", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_2", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_3", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "amr", "vendor": "mir", "count": 1, "zone": "ambient_zone",
             "name": "Cold_AMR_4", "protocols": ["modbus_tcp", "ethernet_ip"],
             "fingerprint_model": "MiR500",
             "role": "Cold-Rated Mobile Robot"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "ambient_zone",
             "name": "Ambient_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Zone Switch"},

            # ============================================================
            # MONITORING ZONE (Level 1) - 4 devices
            # ============================================================
            {"type": "io_module", "vendor": "schneider", "count": 1, "zone": "monitoring",
             "name": "Door_Interlock_IO", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "role": "Door Interlocks"},
            {"type": "safety_plc", "vendor": "schneider", "count": 1, "zone": "monitoring",
             "name": "Cold_Storage_Safety_PLC", "protocols": ["modbus_tcp"],
             "fingerprint_model": "TM5CSLC100FS",
             "role": "Safety Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "monitoring",
             "name": "Monitoring_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Monitoring Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "monitoring",
             "name": "Monitoring_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Monitoring Switch"},
        ],
        "flows": [
            # ============================================================
            # FROZEN ZONE - TEMPERATURE CONTROL (Honeywell)
            # ============================================================
            # Frozen zone controllers to temperature sensors - Modbus (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Frozen_Zone_Controller_1", "target": "Frozen_Temp_Sensor_1",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Frozen_Zone_Controller_1", "target": "Frozen_Temp_Sensor_2",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Frozen_Zone_Controller_2", "target": "Frozen_Temp_Sensor_3",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Frozen_Zone_Controller_2", "target": "Frozen_Temp_Sensor_4",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Frozen controllers to compressor VFDs - Modbus (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Frozen_Zone_Controller_1", "target": "Freezer_Compressor_VFD_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Frozen_Zone_Controller_2", "target": "Freezer_Compressor_VFD_2",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # CHILLED ZONE - TEMPERATURE CONTROL (Honeywell)
            # ============================================================
            # Chilled zone controllers to temperature sensors (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Chilled_Zone_Controller_1", "target": "Chilled_Temp_Sensor_1",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Chilled_Zone_Controller_1", "target": "Chilled_Temp_Sensor_2",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Chilled_Zone_Controller_2", "target": "Chilled_Temp_Sensor_3",
             "jitter_ms": 500, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Chilled_Zone_Controller_2", "target": "Chilled_Temp_Sensor_4",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # Chilled controllers to compressor VFDs (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Chilled_Zone_Controller_1", "target": "Chiller_Compressor_VFD_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Chilled_Zone_Controller_2", "target": "Chiller_Compressor_VFD_2",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # MASTER REFRIGERATION PLC (Schneider M580)
            # ============================================================
            # Master PLC to zone controllers - Modbus (500ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Refrigeration_Master_PLC", "target": "Frozen_Zone_Controller_1",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Refrigeration_Master_PLC", "target": "Frozen_Zone_Controller_2",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Refrigeration_Master_PLC", "target": "Chilled_Zone_Controller_1",
             "jitter_ms": 50, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 500,
             "source": "Refrigeration_Master_PLC", "target": "Chilled_Zone_Controller_2",
             "jitter_ms": 50, "jitter_type": "gaussian"},

            # Master PLC to HMI - operator interface (200ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 200,
             "source": "HVAC_Control_Room_HMI", "target": "Refrigeration_Master_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # Backup PLC heartbeat to Master (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Refrigeration_Backup_PLC", "target": "Refrigeration_Master_PLC",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # AMBIENT/CONVEYOR ZONE (Rockwell)
            # ============================================================
            # Conveyor PLC to VFDs - EtherNet/IP cyclic (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Cold_Conveyor_PLC", "target": "Cold_Conveyor_VFD_1",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Cold_Conveyor_PLC", "target": "Cold_Conveyor_VFD_2",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # MiR Fleet to cold-rated AMRs - Modbus (250ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "Cold_Fleet_Controller", "target": "Cold_AMR_1",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "Cold_Fleet_Controller", "target": "Cold_AMR_2",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "Cold_Fleet_Controller", "target": "Cold_AMR_3",
             "jitter_ms": 30, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 250,
             "source": "Cold_Fleet_Controller", "target": "Cold_AMR_4",
             "jitter_ms": 30, "jitter_type": "gaussian"},

            # ============================================================
            # SAFETY & MONITORING
            # ============================================================
            # Safety PLC to door interlocks (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Cold_Storage_Safety_PLC", "target": "Door_Interlock_IO",
             "jitter_ms": 10, "jitter_type": "gaussian"},

            # Safety PLC to refrigeration PLCs (100ms)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Cold_Storage_Safety_PLC", "target": "Refrigeration_Master_PLC",
             "jitter_ms": 10, "jitter_type": "gaussian"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 100,
             "source": "Cold_Storage_Safety_PLC", "target": "Refrigeration_Backup_PLC",
             "jitter_ms": 10, "jitter_type": "gaussian"},

            # ============================================================
            # HISTORIAN - COMPLIANCE DATA (30s logging)
            # ============================================================
            # Historian to all temperature sensors
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Temp_Sensor_1",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Temp_Sensor_2",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Temp_Sensor_3",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Temp_Sensor_4",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Temp_Sensor_1",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Temp_Sensor_2",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Temp_Sensor_3",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Temp_Sensor_4",
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Historian to zone controllers
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Zone_Controller_1",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Frozen_Zone_Controller_2",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Zone_Controller_1",
             "jitter_ms": 3000, "jitter_type": "uniform"},
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Chilled_Zone_Controller_2",
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # Historian to master PLC
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 30000,
             "source": "Temperature_Compliance_Historian", "target": "Refrigeration_Master_PLC",
             "jitter_ms": 3000, "jitter_type": "uniform"},

            # ============================================================
            # REMOTE GATEWAY - External monitoring
            # ============================================================
            # Gateway to Master PLC (60s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 60000,
             "source": "Cold_Chain_Remote_Gateway", "target": "Refrigeration_Master_PLC",
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Refrigeration_Master_PLC", "target": "HVAC_Core_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Refrigeration_Master_PLC", "target": "Ambient_Zone_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Refrigeration_Master_PLC", "target": "Monitoring_Switch_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Refrigeration_Master_PLC", "target": "Monitoring_Switch_2"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "Refrigeration_Master_PLC", "target": "Cold_Chain_Remote_Gateway"},

            # ============================================================
            # EWON REMOTE ACCESS - Talk2M Cloud Communication (30s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source": "Cold_Chain_Remote_Gateway", "target": "talk2m_cloud",
             "external_ip": "51.38.74.240", "external_port": 443,
             "description": "eWON Talk2M VPN heartbeat",
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # ============================================================
            # JUMP SERVER - External RDP Access
            # ============================================================
            {"protocol": "rdp", "pattern": "external", "interval_ms": 60000,
             "source": "Cold_Chain_Jump_Server", "target": "external_admin",
             "external_ip": "203.0.113.52", "external_port": 3389,
             "description": "Remote admin RDP session",
             "jitter_ms": 15000, "jitter_type": "uniform"},

            # Jump server SNMP monitoring
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "Cold_Chain_Jump_Server", "target": "HVAC_Core_Switch"},
        ],
        "zones": [
            {"id": "hvac_control", "name": "HVAC/Refrigeration Control", "level": 3,
             "subnet_offset": 0, "vlan": 300, "security_level": "high"},
            {"id": "frozen_zone", "name": "Frozen Storage (-20C)", "level": 2,
             "subnet_offset": 1, "vlan": 310, "security_level": "standard"},
            {"id": "chilled_zone", "name": "Chilled Storage (2-8C)", "level": 2,
             "subnet_offset": 2, "vlan": 320, "security_level": "standard"},
            {"id": "ambient_zone", "name": "Ambient/Loading", "level": 1,
             "subnet_offset": 3, "vlan": 330, "security_level": "standard"},
            {"id": "monitoring", "name": "Temperature Monitoring", "level": 1,
             "subnet_offset": 4, "vlan": 340, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["temperature_reading_delay", "compliance_gap"],
            "protocol": ["modbus_exception", "sensor_timeout"],
            "sequence": ["temperature_spike", "door_interlock_fault"],
            "payload": ["out_of_range_temperature", "sensor_drift"],
            "network": ["network_latency"],
            "security": ["unauthorized_setpoint_change"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["51.38.74.240", "87.98.169.126"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.52",
        },
        "total_duration_ms": 300000,
    },

    # ============================================================
    # TEMPLATE 4: PARCEL SORTING HUB (50 devices)
    # High-speed sortation with scanning tunnels
    # ============================================================
    "parcel_sorting_hub": {
        "name": "Parcel Sorting Hub",
        "description": "High-speed parcel sorting facility with tilt-tray sorter, 6-sided barcode scanning "
                       "tunnels, automatic label application, and destination chute management. Features "
                       "Rockwell ControlLogix for high-speed sortation, Cognex DataMan barcode readers, "
                       "and CIP Safety for light curtains. 50 devices across sort control, induction, "
                       "sort loop, scan tunnel, and chute zones.",
        "vertical": "distribution_logistics",
        "phase_preset": "standard",
        "devices": [
            # ============================================================
            # SORT CONTROL ZONE (Level 3) - 5 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_Master_PLC_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Sortation Master Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_Master_PLC_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "error_config": {"exception_rate": 0.0002, "timeout_rate": 0.0001},
             "role": "Sortation Master Controller",
             "cve_ids": ["CVE-2022-1159"]},
            {"type": "scada_server", "vendor": "rockwell", "count": 1, "zone": "sort_control",
             "name": "Sort_SCADA_Server", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Sortation SCADA"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_control",
             "name": "Sort_Control_Switch_1", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Control Room Switch"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_control",
             "name": "Sort_Control_Switch_2", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Control Room Switch"},

            # ============================================================
            # INDUCTION ZONE (Level 2) - 8 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "induct_zone",
             "name": "Induction_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L83E",
             "role": "Induction Controller"},
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_1", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader",
             "cve_ids": ["CVE-2023-4707", "CVE-2023-4708"]},
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_2", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader"},
            {"type": "barcode_scanner", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Induct_Scanner_3", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "DataMan 370",
             "role": "Induction Barcode Reader"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Dimension_Camera_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Dimensioning Camera"},
            {"type": "vision_system", "vendor": "cognex", "count": 1, "zone": "induct_zone",
             "name": "Dimension_Camera_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "In-Sight 7802",
             "role": "Dimensioning Camera"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "induct_zone",
             "name": "Induct_Singulator_IO", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Singulator I/O"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "induct_zone",
             "name": "Induct_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Induction Switch"},

            # ============================================================
            # SORT LOOP ZONE (Level 2) - 12 devices
            # ============================================================
            {"type": "plc", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Tray_Master_PLC", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L85E",
             "role": "Tilt-Tray Master"},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Sorter_Drive_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 755",
             "role": "Sorter Main Drive",
             "cve_ids": ["CVE-2022-3156", "CVE-2023-2072"]},
            {"type": "drive", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Sorter_Drive_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "PowerFlex 755",
             "role": "Sorter Main Drive"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_5", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_6", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_7", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "sort_loop",
             "name": "Tilt_Controller_8", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Tilt-Tray Controller"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "sort_loop",
             "name": "Sort_Loop_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Sort Loop Switch"},

            # ============================================================
            # SCAN TUNNEL ZONE (Level 1) - 10 devices
            # ============================================================
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Top", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Top"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Bottom", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Bottom"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Left", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Left"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Right", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Right"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Front", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Front"},
            {"type": "barcode_scanner", "vendor": "sick", "count": 1, "zone": "scan_tunnel",
             "name": "Scan_Tunnel_Back", "protocols": ["ethernet_ip", "modbus_tcp"],
             "fingerprint_model": "SICK CLV650",
             "role": "6-Sided Scanner - Back"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Weigh_In_Motion_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Weigh-In-Motion Scale"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Weigh_In_Motion_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Weigh-In-Motion Scale"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Label_Applicator_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Print-and-Apply"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "scan_tunnel",
             "name": "Label_Applicator_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Print-and-Apply"},

            # ============================================================
            # CHUTE ZONE (Level 1) - 15 devices
            # ============================================================
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Safety_PLC_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Chute Safety Controller"},
            {"type": "safety_plc", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Safety_PLC_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1756-L73S",
             "role": "Chute Safety Controller"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Chute_Full_Sensor_Bank_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Chute Full Sensors"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_1", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_2", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_3", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_4", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_5", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_6", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_7", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "io_module", "vendor": "rockwell", "count": 1, "zone": "chute_zone",
             "name": "Safety_Light_Curtain_8", "protocols": ["ethernet_ip"],
             "fingerprint_model": "1734-AENT",
             "role": "Safety Light Curtain"},
            {"type": "switch", "vendor": "cisco", "count": 1, "zone": "chute_zone",
             "name": "Chute_Zone_Switch", "protocols": ["snmp"],
             "fingerprint_model": "Stratix 5700",
             "role": "Chute Zone Switch"},

            # ============================================================
            # DMZ ZONE - Remote Access and Jump Server
            # ============================================================
            {"type": "remote_gateway", "vendor": "hms", "count": 1, "zone": "sort_control",
             "name": "Sorting_Remote_Gateway", "protocols": ["modbus_tcp", "snmp"],
             "fingerprint_model": "Flexy 205",
             "role": "Remote Access Gateway",
             "external_comms": True,
             "cve_ids": ["CVE-2022-1523", "CVE-2022-1524", "CVE-2023-22846"]},
            {"type": "jump_server", "vendor": "microsoft", "count": 1, "zone": "sort_control",
             "name": "Sorting_Jump_Server", "protocols": ["snmp"],
             "fingerprint_model": "Jump Server 2016 (Vulnerable)",
             "role": "Remote Access Jump Server",
             "external_comms": True,
             "cve_ids": ["CVE-2019-0708"]},
        ],
        "flows": [
            # ============================================================
            # SORT LOOP - HIGH SPEED FLOWS (2-4ms critical)
            # ============================================================
            # Tilt-Tray Master to all tilt controllers - EtherNet/IP cyclic (2ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_1",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_2",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_3",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_4",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_5",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_6",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_7",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 2,
             "source": "Tilt_Tray_Master_PLC", "target": "Tilt_Controller_8",
             "jitter_ms": 0.3, "jitter_type": "gaussian"},

            # Tilt-Tray Master to sorter drives - cyclic (4ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Tilt_Tray_Master_PLC", "target": "Sorter_Drive_1",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Tilt_Tray_Master_PLC", "target": "Sorter_Drive_2",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # ============================================================
            # SORT CONTROL - MASTER PLCs
            # ============================================================
            # Master PLCs coordination (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_1", "target": "Sort_Master_PLC_2",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Sort Masters to Tilt-Tray Master (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_1", "target": "Tilt_Tray_Master_PLC",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Sort Masters to Induction PLC (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Sort_Master_PLC_1", "target": "Induction_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # INDUCTION ZONE - SCANNERS & VISION
            # ============================================================
            # Induction PLC to singulator I/O (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Induction_PLC", "target": "Induct_Singulator_IO",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Induction barcode scanners to PLC - Cognex (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Induct_Scanner_1", "target": "Induction_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Induct_Scanner_2", "target": "Induction_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Induct_Scanner_3", "target": "Induction_PLC",
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Dimension cameras to PLC (100ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source": "Dimension_Camera_1", "target": "Induction_PLC",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source": "Dimension_Camera_2", "target": "Induction_PLC",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # SCAN TUNNEL - 6-SIDED SCANNING (SICK)
            # ============================================================
            # All 6 scanners to Sort Master - fast scan results (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Top", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Bottom", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Left", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Right", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Front", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Scan_Tunnel_Back", "target": "Sort_Master_PLC_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Weigh-in-motion to Sort Master (50ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Sort_Master_PLC_1", "target": "Weigh_In_Motion_1",
             "jitter_ms": 8, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 50,
             "source": "Sort_Master_PLC_1", "target": "Weigh_In_Motion_2",
             "jitter_ms": 8, "jitter_type": "gaussian"},

            # Label applicators (100ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source": "Sort_Master_PLC_1", "target": "Label_Applicator_1",
             "jitter_ms": 15, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 100,
             "source": "Sort_Master_PLC_1", "target": "Label_Applicator_2",
             "jitter_ms": 15, "jitter_type": "gaussian"},

            # ============================================================
            # CHUTE ZONE - SENSORS & SAFETY
            # ============================================================
            # Sort Master to chute full sensors (10ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_1", "target": "Chute_Full_Sensor_Bank_1",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_1", "target": "Chute_Full_Sensor_Bank_2",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_2", "target": "Chute_Full_Sensor_Bank_3",
             "jitter_ms": 2, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 10,
             "source": "Sort_Master_PLC_2", "target": "Chute_Full_Sensor_Bank_4",
             "jitter_ms": 2, "jitter_type": "gaussian"},

            # Safety PLCs to light curtains - CIP Safety (4ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_1", "target": "Safety_Light_Curtain_1",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_1", "target": "Safety_Light_Curtain_2",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_1", "target": "Safety_Light_Curtain_3",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_1", "target": "Safety_Light_Curtain_4",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_2", "target": "Safety_Light_Curtain_5",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_2", "target": "Safety_Light_Curtain_6",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_2", "target": "Safety_Light_Curtain_7",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 4,
             "source": "Chute_Safety_PLC_2", "target": "Safety_Light_Curtain_8",
             "jitter_ms": 0.5, "jitter_type": "gaussian"},

            # Safety PLCs to Sort Masters - E-stop interlock (20ms)
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Chute_Safety_PLC_1", "target": "Sort_Master_PLC_1",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Chute_Safety_PLC_2", "target": "Sort_Master_PLC_2",
             "jitter_ms": 3, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "cyclic_io", "interval_ms": 20,
             "source": "Chute_Safety_PLC_1", "target": "Tilt_Tray_Master_PLC",
             "jitter_ms": 3, "jitter_type": "gaussian"},

            # ============================================================
            # SCADA MONITORING
            # ============================================================
            # SCADA to all PLCs (200ms)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Sort_Master_PLC_1",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Sort_Master_PLC_2",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Tilt_Tray_Master_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Induction_PLC",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Chute_Safety_PLC_1",
             "jitter_ms": 25, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 200,
             "source": "Sort_SCADA_Server", "target": "Chute_Safety_PLC_2",
             "jitter_ms": 25, "jitter_type": "gaussian"},

            # SCADA to vision/scanners status (1s)
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source": "Sort_SCADA_Server", "target": "Dimension_Camera_1",
             "jitter_ms": 100, "jitter_type": "gaussian"},
            {"protocol": "ethernet_ip", "pattern": "poll", "interval_ms": 1000,
             "source": "Sort_SCADA_Server", "target": "Dimension_Camera_2",
             "jitter_ms": 100, "jitter_type": "gaussian"},

            # ============================================================
            # SNMP NETWORK MONITORING
            # ============================================================
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Sort_SCADA_Server", "target": "Sort_Control_Switch_1"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Sort_SCADA_Server", "target": "Sort_Control_Switch_2"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Sort_SCADA_Server", "target": "Induct_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Sort_SCADA_Server", "target": "Sort_Loop_Switch"},
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 30000,
             "source": "Sort_SCADA_Server", "target": "Chute_Zone_Switch"},

            # ============================================================
            # EWON REMOTE ACCESS - Talk2M Cloud Communication (30s heartbeat)
            # ============================================================
            {"protocol": "https", "pattern": "external", "interval_ms": 30000,
             "source": "Sorting_Remote_Gateway", "target": "talk2m_cloud",
             "external_ip": "87.98.169.126", "external_port": 443,
             "description": "eWON Talk2M VPN heartbeat",
             "jitter_ms": 5000, "jitter_type": "uniform"},

            # eWON Modbus polling to SCADA (5s)
            {"protocol": "modbus_tcp", "pattern": "poll", "interval_ms": 5000,
             "source": "Sorting_Remote_Gateway", "target": "Sort_SCADA_Server",
             "jitter_ms": 500, "jitter_type": "gaussian"},

            # ============================================================
            # JUMP SERVER - External RDP Access
            # ============================================================
            {"protocol": "rdp", "pattern": "external", "interval_ms": 60000,
             "source": "Sorting_Jump_Server", "target": "external_admin",
             "external_ip": "203.0.113.53", "external_port": 3389,
             "description": "Remote admin RDP session",
             "jitter_ms": 15000, "jitter_type": "uniform"},

            # Jump server SNMP monitoring
            {"protocol": "snmp", "pattern": "poll", "interval_ms": 60000,
             "source": "Sorting_Jump_Server", "target": "Sort_Control_Switch_1"},
        ],
        "zones": [
            {"id": "sort_control", "name": "Sort Control Room", "level": 3,
             "subnet_offset": 0, "vlan": 400, "security_level": "high"},
            {"id": "induct_zone", "name": "Induction Zone", "level": 2,
             "subnet_offset": 1, "vlan": 410, "security_level": "standard"},
            {"id": "sort_loop", "name": "Main Sort Loop", "level": 2,
             "subnet_offset": 2, "vlan": 420, "security_level": "standard"},
            {"id": "scan_tunnel", "name": "Scanning Tunnel", "level": 1,
             "subnet_offset": 3, "vlan": 430, "security_level": "standard"},
            {"id": "chute_zone", "name": "Destination Chutes", "level": 1,
             "subnet_offset": 4, "vlan": 440, "security_level": "standard"},
        ],
        "suggested_anomalies": {
            "timing": ["high_speed_desync", "scanner_lag", "safety_response_delay"],
            "protocol": ["ethernet_ip_error", "cip_safety_fault"],
            "sequence": ["tilt_misfire", "double_induction"],
            "payload": ["no_read", "dimension_error", "weight_variance"],
            "network": ["scanner_network_congestion"],
            "security": ["unauthorized_sort_divert"],
        },
        "external_comms": {
            "enable_remote_access": True,
            "remote_access_gateway": "ewon",
            "cloud_service": "talk2m",
            "cloud_ips": ["87.98.169.126", "13.56.142.1"],
            "enable_jump_server": True,
            "jump_server_external_ip": "203.0.113.53",
        },
        "total_duration_ms": 300000,
    },
}
