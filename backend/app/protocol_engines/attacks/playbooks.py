"""Pre-built ICS attack playbooks modeled on real-world campaigns.

Each playbook is a multi-stage kill-chain composed of :class:`AttackAction`
instances that map to registered generators in ``action_registry.py`` and
``ics_actions.py``.

Playbooks follow the same static-data pattern as ``PHASE_TEMPLATES`` and
``BEACON_PATTERNS`` -- defined as Python dataclass instances, not DB models.
"""

from __future__ import annotations

from .types import AttackAction, AttackPlaybook, KillChainStage

# ---------------------------------------------------------------------------
# 1. TRITON-like (S0609) -- Safety System Attack
# ---------------------------------------------------------------------------

TRITON_LIKE = AttackPlaybook(
    playbook_id="triton_like",
    name="TRITON-like Safety System Attack",
    description=(
        "Modeled after the TRITON/TRISIS malware that targeted Schneider Electric "
        "Triconex safety instrumented systems (SIS) in a Middle Eastern petrochemical "
        "facility. The attacker gains initial access, performs deep reconnaissance of "
        "safety controllers via S7/Modbus, uploads malicious logic, and attempts to "
        "disable safety functions to enable a potentially catastrophic physical event."
    ),
    mitre_software_id="S0609",
    severity="critical",
    category="apt",
    required_protocols=["s7comm", "modbus_tcp"],
    industry_verticals=["manufacturing", "energy", "oil_gas"],
    reference_url="https://attack.mitre.org/software/S0609/",
    stages=[
        # Stage 1: Initial Compromise
        KillChainStage(
            stage_id="initial_compromise",
            name="Initial Compromise",
            description=(
                "Attacker establishes foothold on engineering workstation via "
                "spear-phishing or supply chain compromise. C2 beacon activates."
            ),
            duration_seconds=120,
            color="#faad14",
            mitre_tactics=["TA0108"],  # Initial Access
            expected_cv_alerts=["New external communication detected", "Periodic beaconing pattern"],
            actions=[
                AttackAction(
                    action_id="triton_c2_establish",
                    name="Establish C2 Channel",
                    action_type="c2_beacon",
                    description="Compromised EWS begins beaconing to external C2 server.",
                    parameters={"pattern": "jittered_1m", "protocol": "https", "count": 5, "duration_ms": 60_000},
                    target_selector="ews",
                    mitre_technique="T0885",
                    expected_cv_detection="Periodic outbound beaconing from engineering workstation",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 2: Network Reconnaissance
        KillChainStage(
            stage_id="network_recon",
            name="Network Reconnaissance",
            description=(
                "Attacker maps the OT network, scanning for PLCs, safety controllers, "
                "and communication paths between zones."
            ),
            duration_seconds=180,
            color="#ffc53d",
            mitre_tactics=["TA0102"],  # Discovery
            expected_cv_alerts=["Port scan detected", "Modbus device enumeration"],
            actions=[
                AttackAction(
                    action_id="triton_port_scan",
                    name="OT Network Port Scan",
                    action_type="port_scan",
                    description="Scan for S7comm (102), Modbus (502), and other OT ports.",
                    parameters={"scan_ot_ports": True},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="Port scanning activity from engineering workstation",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="triton_modbus_enum",
                    name="Modbus Unit ID Enumeration",
                    action_type="modbus_unit_enum",
                    description="Enumerate Modbus unit IDs to find safety controllers.",
                    parameters={"unit_range": [1, 64], "interval_ms": 150},
                    target_selector="plc",
                    mitre_technique="T0842",
                    expected_cv_detection="Modbus function code scanning across unit IDs",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 3: Lateral Movement
        KillChainStage(
            stage_id="lateral_movement",
            name="Lateral Movement",
            description=(
                "Attacker moves from the engineering workstation toward the safety "
                "controller network, establishing device-to-device communication paths."
            ),
            duration_seconds=240,
            color="#fa8c16",
            mitre_tactics=["TA0109"],  # Lateral Movement
            expected_cv_alerts=["New communication pair detected", "Cross-zone traffic"],
            actions=[
                AttackAction(
                    action_id="triton_lateral",
                    name="Cross-Device Lateral Movement",
                    action_type="cross_device_comm",
                    description="Generate traffic between devices that don't normally communicate.",
                    parameters={"count": 8, "interval_ms": 2000, "target_type": "plc"},
                    target_selector="any",
                    mitre_technique="T0867",
                    expected_cv_detection="Anomalous communication pair between EWS and safety controller",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="triton_exfil_recon",
                    name="Exfiltrate Network Map",
                    action_type="dns_tunnel",
                    description="Exfiltrate discovered network topology via DNS tunneling.",
                    parameters={"data_size": 2048},
                    target_selector="ews",
                    mitre_technique="T0884",
                    expected_cv_detection="DNS tunneling with high-entropy subdomain queries",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 4: SIS Discovery
        KillChainStage(
            stage_id="sis_discovery",
            name="SIS Discovery",
            description=(
                "Deep enumeration of safety instrumented system controllers using "
                "S7comm SZL reads and Modbus register probing."
            ),
            duration_seconds=300,
            color="#ff7a45",
            mitre_tactics=["TA0102"],  # Discovery
            expected_cv_alerts=["S7 system information read", "Modbus register probing"],
            actions=[
                AttackAction(
                    action_id="triton_s7_szl",
                    name="S7 SZL System Enumeration",
                    action_type="s7_read_szl",
                    description="Read SZL lists to identify controller model, firmware, and configuration.",
                    parameters={"szl_ids": [0x0011, 0x001C, 0x0111, 0x0F00], "interval_ms": 400},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="S7comm SZL read requests from non-standard source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="triton_modbus_probe",
                    name="Safety Register Mapping",
                    action_type="modbus_read_probe",
                    description="Probe register ranges used by safety logic to understand SIS configuration.",
                    parameters={
                        "address_ranges": [[0, 50], [1000, 1100], [4000, 4100]],
                        "quantity": 10,
                        "step": 10,
                        "interval_ms": 200,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="Unusual Modbus register read pattern on safety controller",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 5: Payload Deployment
        KillChainStage(
            stage_id="payload_deploy",
            name="Payload Deployment",
            description=(
                "Attacker uploads malicious logic to the safety controller, modifying "
                "safety parameters and injecting rogue program blocks."
            ),
            duration_seconds=240,
            color="#f5222d",
            mitre_tactics=["TA0111"],  # Impair Process Control
            expected_cv_alerts=["S7 block upload detected", "Register write to safety controller"],
            actions=[
                AttackAction(
                    action_id="triton_write_safety",
                    name="Modify Safety Setpoints",
                    action_type="modbus_write_register",
                    description="Write to safety-critical registers to alter trip points.",
                    parameters={
                        "address": 4000,
                        "count": 8,
                        "use_multi_write": True,
                        "interval_ms": 1000,
                    },
                    target_selector="plc",
                    mitre_technique="T0836",
                    expected_cv_detection="Unauthorized Modbus write to safety controller registers",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="triton_upload_block",
                    name="Upload Malicious Program Block",
                    action_type="s7_upload_block",
                    description="Upload rogue program block to override safety logic.",
                    target_selector="plc",
                    mitre_technique="T0845",
                    expected_cv_detection="S7 block transfer to safety controller",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 6: Impact
        KillChainStage(
            stage_id="impact",
            name="Impact - Safety System Disable",
            description=(
                "Final stage: attacker disables the safety system by stopping the CPU "
                "and flooding coil outputs to mask the unsafe process state."
            ),
            duration_seconds=120,
            color="#cf1322",
            mitre_tactics=["TA0105"],  # Impact
            expected_cv_alerts=["PLC CPU stop command", "Coil write flood", "Safety system offline"],
            actions=[
                AttackAction(
                    action_id="triton_stop_cpu",
                    name="Stop Safety Controller CPU",
                    action_type="s7_stop_cpu",
                    description="Send CPU STOP command to disable safety controller execution.",
                    target_selector="plc",
                    mitre_technique="T0816",
                    expected_cv_detection="S7 CPU STOP command sent to safety controller",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="triton_coil_flood",
                    name="Coil Output Flood",
                    action_type="coil_flood",
                    description="Rapid coil writes to mask process state while safety is offline.",
                    parameters={"address": 0, "count": 48, "rate_ms": 30},
                    target_selector="plc",
                    mitre_technique="T0855",
                    expected_cv_detection="Abnormal Modbus write rate to coil outputs",
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 2. PIPEDREAM-like (S1045) -- Multi-Protocol Toolkit
# ---------------------------------------------------------------------------

PIPEDREAM_LIKE = AttackPlaybook(
    playbook_id="pipedream_like",
    name="PIPEDREAM-like Multi-Protocol Toolkit",
    description=(
        "Modeled after PIPEDREAM (INCONTROLLER), a state-sponsored ICS attack toolkit "
        "targeting Schneider Electric and OMRON PLCs via multiple protocols. Features "
        "Modbus, EtherNet/IP (CIP), and S7comm capabilities for scanning, profiling, "
        "and disrupting industrial control systems across diverse environments."
    ),
    mitre_software_id="S1045",
    severity="critical",
    category="apt",
    required_protocols=["modbus_tcp", "ethernet_ip", "s7comm"],
    industry_verticals=["manufacturing", "energy", "water"],
    reference_url="https://attack.mitre.org/software/S1045/",
    stages=[
        # Stage 1: Initial Access
        KillChainStage(
            stage_id="initial_access",
            name="Initial Access",
            description=(
                "Attacker gains access to the OT network via compromised VPN credentials "
                "or IT/OT boundary device. C2 implant activates on a dual-homed host."
            ),
            duration_seconds=120,
            color="#faad14",
            mitre_tactics=["TA0108"],
            expected_cv_alerts=["New external communication detected"],
            actions=[
                AttackAction(
                    action_id="pipedream_c2",
                    name="Activate C2 Implant",
                    action_type="c2_beacon",
                    description="C2 beacon from compromised IT/OT gateway.",
                    parameters={"pattern": "jittered_1m", "protocol": "http", "count": 6, "duration_ms": 60_000},
                    target_selector="ews",
                    mitre_technique="T0885",
                    expected_cv_detection="Periodic HTTP beaconing from OT network host",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 2: OT Scanning
        KillChainStage(
            stage_id="ot_scanning",
            name="OT Network Scanning",
            description=(
                "Broad multi-protocol scanning to identify all reachable controllers. "
                "Uses port scanning, Modbus enumeration, and EtherNet/IP ListIdentity."
            ),
            duration_seconds=240,
            color="#ffc53d",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=["Port scan detected", "Modbus enumeration", "EtherNet/IP discovery"],
            actions=[
                AttackAction(
                    action_id="pipedream_port_scan",
                    name="Multi-Protocol Port Scan",
                    action_type="port_scan",
                    description="Scan for Modbus (502), EtherNet/IP (44818), S7comm (102), and HTTP.",
                    parameters={"ports": [80, 102, 443, 502, 2222, 44818, 47808], "scan_type": "syn"},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SYN scan of OT protocol ports",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="pipedream_modbus_enum",
                    name="Modbus Unit Discovery",
                    action_type="modbus_unit_enum",
                    description="Enumerate Modbus unit IDs across the network.",
                    parameters={"unit_range": [1, 48], "interval_ms": 120},
                    target_selector="plc",
                    mitre_technique="T0842",
                    expected_cv_detection="Modbus Report Server ID requests across unit range",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="pipedream_enip_discover",
                    name="EtherNet/IP Device Discovery",
                    action_type="enip_list_identity",
                    description="Broadcast EtherNet/IP ListIdentity to find CIP devices.",
                    parameters={"interval_ms": 250},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="EtherNet/IP ListIdentity broadcast from non-standard source",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 3: Device Profiling
        KillChainStage(
            stage_id="device_profiling",
            name="Device Profiling",
            description=(
                "Deep enumeration of discovered devices using CIP service queries, "
                "S7 SZL reads, and Modbus register probing to build target profiles."
            ),
            duration_seconds=300,
            color="#fa8c16",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=["CIP service enumeration", "S7 system read", "Modbus register probing"],
            actions=[
                AttackAction(
                    action_id="pipedream_cip_enum",
                    name="CIP Service Enumeration",
                    action_type="enip_cip_enum",
                    description="Query CIP identity objects and services on discovered devices.",
                    parameters={"interval_ms": 350},
                    target_selector="plc",
                    mitre_technique="T0846",
                    expected_cv_detection="CIP ListServices from unauthorized source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="pipedream_s7_szl",
                    name="S7 Controller Identification",
                    action_type="s7_read_szl",
                    description="Read SZL to identify S7 controller model and firmware.",
                    parameters={"szl_ids": [0x0011, 0x001C], "interval_ms": 500},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="S7comm SZL read from non-engineering source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="pipedream_modbus_probe",
                    name="Modbus Register Mapping",
                    action_type="modbus_read_probe",
                    description="Map register space to identify process variables and control points.",
                    parameters={
                        "address_ranges": [[0, 100], [4000, 4200], [8192, 8300]],
                        "quantity": 10,
                        "step": 10,
                        "interval_ms": 180,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="Broad Modbus register read sweep",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="pipedream_exfil_profiles",
                    name="Exfiltrate Device Profiles",
                    action_type="dns_tunnel",
                    description="Exfiltrate collected device profiles to C2 via DNS tunneling.",
                    parameters={"data_size": 8192},
                    target_selector="ews",
                    mitre_technique="T0884",
                    expected_cv_detection="High-entropy DNS queries indicating data exfiltration",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 4: Configuration Manipulation
        KillChainStage(
            stage_id="config_manipulation",
            name="Configuration Manipulation",
            description=(
                "Attacker modifies controller configurations: writes to Modbus coils "
                "and registers to alter process setpoints and control logic."
            ),
            duration_seconds=240,
            color="#ff4d4f",
            mitre_tactics=["TA0111"],
            expected_cv_alerts=["Unauthorized Modbus write", "Coil state change"],
            actions=[
                AttackAction(
                    action_id="pipedream_write_coils",
                    name="Coil State Manipulation",
                    action_type="modbus_write_coil",
                    description="Toggle critical coil outputs to alter actuator states.",
                    parameters={"address": 0, "count": 12, "interval_ms": 800},
                    target_selector="plc",
                    mitre_technique="T0855",
                    expected_cv_detection="Unauthorized Modbus coil writes from non-HMI source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="pipedream_write_regs",
                    name="Setpoint Modification",
                    action_type="modbus_write_register",
                    description="Modify process setpoints in holding registers.",
                    parameters={"address": 4000, "count": 6, "use_multi_write": True, "interval_ms": 1200},
                    target_selector="plc",
                    mitre_technique="T0836",
                    expected_cv_detection="Holding register write from unauthorized source",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 5: Process Disruption
        KillChainStage(
            stage_id="process_disruption",
            name="Process Disruption",
            description=(
                "Coordinated disruption using coil floods and rapid register "
                "manipulation to destabilize the physical process."
            ),
            duration_seconds=180,
            color="#f5222d",
            mitre_tactics=["TA0105"],
            expected_cv_alerts=["Write flood detected", "Process variable anomaly", "S7 CPU stop"],
            actions=[
                AttackAction(
                    action_id="pipedream_coil_flood",
                    name="Coil Output Flood",
                    action_type="coil_flood",
                    description="Rapid-fire coil toggling to disrupt actuator control.",
                    parameters={"address": 0, "count": 64, "rate_ms": 40},
                    target_selector="plc",
                    mitre_technique="T0855",
                    expected_cv_detection="Modbus coil write flood detected",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="pipedream_s7_stop",
                    name="Stop S7 Controller",
                    action_type="s7_stop_cpu",
                    description="Send CPU STOP to S7 controllers to halt process execution.",
                    target_selector="plc",
                    mitre_technique="T0816",
                    expected_cv_detection="S7 CPU STOP command detected",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 6: Denial of Service
        KillChainStage(
            stage_id="denial_of_service",
            name="Denial of Service",
            description=(
                "Final stage: force remaining Modbus devices into listen-only mode "
                "to prevent operator recovery, then maintain coil flood."
            ),
            duration_seconds=120,
            color="#cf1322",
            mitre_tactics=["TA0105"],
            expected_cv_alerts=["Modbus force listen-only mode", "Sustained write flood"],
            actions=[
                AttackAction(
                    action_id="pipedream_force_listen",
                    name="Force Listen-Only Mode",
                    action_type="modbus_force_listen",
                    description="Force all Modbus devices into listen-only mode to block operator commands.",
                    parameters={"unit_id": 0},
                    target_selector="plc",
                    mitre_technique="T0814",
                    expected_cv_detection="Modbus diagnostic command: Force Listen Only Mode (broadcast)",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="pipedream_sustained_flood",
                    name="Sustained Disruption",
                    action_type="coil_flood",
                    description="Maintain coil flood to prevent process recovery.",
                    parameters={"address": 0, "count": 128, "rate_ms": 25},
                    target_selector="plc",
                    mitre_technique="T0855",
                    expected_cv_detection="Sustained abnormal Modbus write rate",
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 3. INDUSTROYER-like (S0604) -- Grid Attack
# ---------------------------------------------------------------------------

INDUSTROYER_LIKE = AttackPlaybook(
    playbook_id="industroyer_like",
    name="INDUSTROYER-like Grid Attack",
    description=(
        "Modeled after INDUSTROYER/CrashOverride, the malware used in the 2016 "
        "Ukraine power grid attack. Targets substation automation systems using "
        "multiple OT protocols to open circuit breakers, disable protection relays, "
        "and deploy a wiper to prevent recovery."
    ),
    mitre_software_id="S0604",
    severity="critical",
    category="apt",
    required_protocols=["s7comm", "modbus_tcp", "snmp"],
    industry_verticals=["energy", "water"],
    reference_url="https://attack.mitre.org/software/S0604/",
    stages=[
        # Stage 1: C2 Establishment
        KillChainStage(
            stage_id="c2_establishment",
            name="C2 Establishment",
            description=(
                "Backdoor activates on compromised SCADA server. Establishes C2 "
                "communication and begins initial network mapping."
            ),
            duration_seconds=180,
            color="#faad14",
            mitre_tactics=["TA0108", "TA0011"],
            expected_cv_alerts=["New external communication", "Beaconing pattern detected"],
            actions=[
                AttackAction(
                    action_id="industroyer_c2",
                    name="Activate Backdoor",
                    action_type="c2_beacon",
                    description="C2 implant on SCADA server begins beaconing.",
                    parameters={"pattern": "jittered_1m", "protocol": "https", "count": 8, "duration_ms": 120_000},
                    target_selector="hmi",
                    mitre_technique="T0885",
                    expected_cv_detection="Periodic HTTPS beaconing from SCADA server",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="industroyer_initial_scan",
                    name="Initial Network Scan",
                    action_type="port_scan",
                    description="Map the substation network to find RTUs and protection relays.",
                    parameters={"scan_ot_ports": True},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="Port scan from SCADA server targeting OT ports",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 2: Discovery
        KillChainStage(
            stage_id="discovery",
            name="Substation Discovery",
            description=(
                "Comprehensive device enumeration using SNMP walks, Modbus unit "
                "enumeration, and S7 SZL reads to map the substation architecture."
            ),
            duration_seconds=300,
            color="#ffc53d",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=["SNMP enumeration", "Modbus device scan", "S7 system information read"],
            actions=[
                AttackAction(
                    action_id="industroyer_snmp_walk",
                    name="SNMP MIB Walk",
                    action_type="snmp_walk",
                    description="Walk SNMP MIBs on network infrastructure to map topology.",
                    parameters={"community": "public", "start_oid": "1.3.6.1.2.1.1", "num_requests": 20, "interval_ms": 180},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SNMP GetBulk walk from non-NMS source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="industroyer_modbus_enum",
                    name="RTU Modbus Enumeration",
                    action_type="modbus_unit_enum",
                    description="Enumerate Modbus unit IDs to find RTUs and IEDs.",
                    parameters={"unit_range": [1, 32], "interval_ms": 200},
                    target_selector="rtu",
                    mitre_technique="T0842",
                    expected_cv_detection="Modbus Report Server ID scan from SCADA server",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="industroyer_s7_profile",
                    name="S7 Controller Profiling",
                    action_type="s7_read_szl",
                    description="Read SZL to identify protection relay controller models.",
                    parameters={"szl_ids": [0x0011, 0x001C, 0x0111], "interval_ms": 600},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="S7comm SZL read from non-engineering workstation",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 3: Staging
        KillChainStage(
            stage_id="staging",
            name="Staging & Data Exfil",
            description=(
                "Attacker stages payloads and exfiltrates substation configuration "
                "data to C2 for analysis and attack customization."
            ),
            duration_seconds=240,
            color="#fa8c16",
            mitre_tactics=["TA0010"],
            expected_cv_alerts=["HTTP data exfiltration", "Large outbound transfer"],
            actions=[
                AttackAction(
                    action_id="industroyer_exfil",
                    name="Exfiltrate Station Config",
                    action_type="http_exfil",
                    description="Exfiltrate substation configuration and topology data.",
                    parameters={"data_size": 16384},
                    target_selector="hmi",
                    mitre_technique="T0882",
                    expected_cv_detection="Unusual HTTP POST with large payload from SCADA server",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 4: Breaker Manipulation
        KillChainStage(
            stage_id="breaker_manipulation",
            name="Breaker Manipulation",
            description=(
                "Core attack: open circuit breakers by writing to Modbus coil "
                "outputs mapped to breaker control points."
            ),
            duration_seconds=180,
            color="#ff4d4f",
            mitre_tactics=["TA0111"],
            expected_cv_alerts=["Unauthorized breaker open command", "Coil write to breaker control"],
            actions=[
                AttackAction(
                    action_id="industroyer_open_breakers",
                    name="Open Circuit Breakers",
                    action_type="modbus_write_coil",
                    description="Write to coil outputs to trip circuit breakers.",
                    parameters={"address": 100, "count": 8, "interval_ms": 500},
                    target_selector="rtu",
                    mitre_technique="T0855",
                    expected_cv_detection="Unauthorized Modbus coil write to breaker control address",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="industroyer_upload_malicious",
                    name="Upload Malicious Block",
                    action_type="s7_upload_block",
                    description="Upload logic to prevent automatic breaker reclosing.",
                    target_selector="plc",
                    mitre_technique="T0845",
                    expected_cv_detection="S7 block transfer to protection relay controller",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 5: Protection Disabling
        KillChainStage(
            stage_id="protection_disabling",
            name="Protection Disabling",
            description=(
                "Disable protection relays and force Modbus devices into "
                "listen-only mode to prevent operator intervention."
            ),
            duration_seconds=120,
            color="#f5222d",
            mitre_tactics=["TA0105"],
            expected_cv_alerts=["Modbus force listen-only", "S7 CPU stop on protection relay"],
            actions=[
                AttackAction(
                    action_id="industroyer_force_listen",
                    name="Force Listen-Only Mode",
                    action_type="modbus_force_listen",
                    description="Force RTUs into listen-only mode to block operator commands.",
                    parameters={"unit_id": 0},
                    target_selector="rtu",
                    mitre_technique="T0814",
                    expected_cv_detection="Modbus diagnostic: Force Listen Only Mode (broadcast)",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="industroyer_stop_relays",
                    name="Stop Protection Relays",
                    action_type="s7_stop_cpu",
                    description="Stop CPU on S7-based protection relay controllers.",
                    target_selector="relay",
                    mitre_technique="T0816",
                    expected_cv_detection="S7 CPU STOP command sent to protection relay",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 6: Wiper
        KillChainStage(
            stage_id="wiper",
            name="Wiper & Anti-Recovery",
            description=(
                "Deploy data destruction to SCADA systems and maintain breaker "
                "flood to prevent power restoration."
            ),
            duration_seconds=60,
            color="#cf1322",
            mitre_tactics=["TA0105"],
            expected_cv_alerts=["Sustained write flood", "Multiple devices offline"],
            actions=[
                AttackAction(
                    action_id="industroyer_sustained",
                    name="Sustained Breaker Flood",
                    action_type="coil_flood",
                    description="Maintain rapid coil writes to prevent breaker reclosing.",
                    parameters={"address": 100, "count": 96, "rate_ms": 35},
                    target_selector="rtu",
                    mitre_technique="T0855",
                    expected_cv_detection="Sustained abnormal Modbus write rate on breaker coils",
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 4. HAVEX-like (S0093) -- Recon & Data Theft
# ---------------------------------------------------------------------------

HAVEX_LIKE = AttackPlaybook(
    playbook_id="havex_like",
    name="HAVEX-like Recon & Data Theft",
    description=(
        "Modeled after HAVEX (Dragonfly/Energetic Bear), a reconnaissance-focused "
        "RAT that targeted energy and manufacturing sectors via trojanized ICS vendor "
        "software installers. Focused on OPC/CIP device enumeration and data theft "
        "rather than destructive attacks."
    ),
    mitre_software_id="S0093",
    severity="high",
    category="apt",
    required_protocols=["ethernet_ip", "modbus_tcp", "snmp"],
    industry_verticals=["manufacturing", "energy"],
    reference_url="https://attack.mitre.org/software/S0093/",
    stages=[
        # Stage 1: Trojanized Update
        KillChainStage(
            stage_id="trojanized_update",
            name="Trojanized Update",
            description=(
                "Malware delivered via compromised ICS vendor software update. "
                "RAT activates and establishes C2 from the engineering workstation."
            ),
            duration_seconds=120,
            color="#faad14",
            mitre_tactics=["TA0108", "TA0011"],
            expected_cv_alerts=["New external communication from EWS"],
            actions=[
                AttackAction(
                    action_id="havex_c2",
                    name="RAT C2 Activation",
                    action_type="c2_beacon",
                    description="Trojanized software phones home via HTTPS.",
                    parameters={"pattern": "jittered_1m", "protocol": "https", "count": 10, "duration_ms": 90_000},
                    target_selector="ews",
                    mitre_technique="T0885",
                    expected_cv_detection="Periodic HTTPS connections from engineering workstation to unknown host",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 2: CIP Enumeration
        KillChainStage(
            stage_id="cip_enumeration",
            name="CIP Device Enumeration",
            description=(
                "HAVEX's primary capability: enumerate EtherNet/IP devices using "
                "ListIdentity broadcasts and CIP service queries."
            ),
            duration_seconds=240,
            color="#ffc53d",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=["EtherNet/IP device discovery", "CIP service enumeration"],
            actions=[
                AttackAction(
                    action_id="havex_enip_list",
                    name="EtherNet/IP ListIdentity Scan",
                    action_type="enip_list_identity",
                    description="Broadcast ListIdentity to discover all EtherNet/IP devices.",
                    parameters={"interval_ms": 200},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="EtherNet/IP ListIdentity from non-standard source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="havex_cip_enum",
                    name="CIP Service Discovery",
                    action_type="enip_cip_enum",
                    description="Enumerate CIP services and identity objects on each device.",
                    parameters={"interval_ms": 300},
                    target_selector="plc",
                    mitre_technique="T0846",
                    expected_cv_detection="CIP ListServices from engineering workstation",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 3: Deep Recon
        KillChainStage(
            stage_id="deep_recon",
            name="Deep Reconnaissance",
            description=(
                "Extended enumeration via SNMP walks and Modbus register probing "
                "to build a comprehensive inventory of the OT environment."
            ),
            duration_seconds=360,
            color="#fa8c16",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=["SNMP MIB walk", "Modbus register probing"],
            actions=[
                AttackAction(
                    action_id="havex_snmp_walk",
                    name="SNMP System Enumeration",
                    action_type="snmp_walk",
                    description="Walk system and interface MIBs to map network infrastructure.",
                    parameters={"community": "public", "start_oid": "1.3.6.1.2.1.1", "num_requests": 25, "interval_ms": 200},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SNMP GetBulk walk across multiple OIDs from EWS",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="havex_modbus_probe",
                    name="Modbus Register Survey",
                    action_type="modbus_read_probe",
                    description="Read holding register ranges to map process data.",
                    parameters={
                        "address_ranges": [[0, 200], [4000, 4200]],
                        "quantity": 10,
                        "step": 20,
                        "interval_ms": 250,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="Systematic Modbus register read sweep from EWS",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 4: Data Collection
        KillChainStage(
            stage_id="data_collection",
            name="Data Collection & Exfiltration",
            description=(
                "Aggregate collected device inventories, network maps, and process "
                "data, then exfiltrate to C2 infrastructure."
            ),
            duration_seconds=180,
            color="#ff7a45",
            mitre_tactics=["TA0010", "TA0009"],
            expected_cv_alerts=["DNS tunneling detected", "Large data exfiltration"],
            actions=[
                AttackAction(
                    action_id="havex_dns_exfil",
                    name="DNS Tunnel Exfiltration",
                    action_type="dns_tunnel",
                    description="Exfiltrate device inventory via DNS tunneling to avoid DPI.",
                    parameters={"data_size": 12288},
                    target_selector="ews",
                    mitre_technique="T0884",
                    expected_cv_detection="High-entropy DNS queries with encoded data payloads",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="havex_http_exfil",
                    name="HTTP Data Exfiltration",
                    action_type="http_exfil",
                    description="Exfiltrate network topology and process data via HTTP POST.",
                    parameters={"data_size": 32768},
                    target_selector="ews",
                    mitre_technique="T0882",
                    expected_cv_detection="Large HTTP POST from engineering workstation to external host",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 5: Persistence
        KillChainStage(
            stage_id="persistence",
            name="Persistence & Ongoing Collection",
            description=(
                "Maintain long-term access with low-rate C2 beaconing and periodic "
                "data collection for future operations."
            ),
            duration_seconds=300,
            color="#fa8c16",
            mitre_tactics=["TA0011", "TA0003"],
            expected_cv_alerts=["Low-rate periodic beaconing"],
            actions=[
                AttackAction(
                    action_id="havex_persist_c2",
                    name="Low-Rate Persistence Beacon",
                    action_type="c2_beacon",
                    description="Switch to low-rate beaconing for persistent access.",
                    parameters={"pattern": "jittered_1m", "protocol": "https", "count": 5, "duration_ms": 240_000},
                    target_selector="ews",
                    mitre_technique="T0885",
                    expected_cv_detection="Sustained low-rate beaconing from compromised host",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="havex_persist_exfil",
                    name="Periodic Data Refresh",
                    action_type="dns_tunnel",
                    description="Periodically exfiltrate updated process data.",
                    parameters={"data_size": 4096},
                    target_selector="ews",
                    mitre_technique="T0884",
                    expected_cv_detection="Recurring DNS tunnel exfiltration",
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 5. INSIDER_THREAT -- Generic Insider Threat
# ---------------------------------------------------------------------------

INSIDER_THREAT = AttackPlaybook(
    playbook_id="insider_threat",
    name="Insider Threat - Unauthorized OT Access",
    description=(
        "Simulates an insider threat scenario where a disgruntled or compromised "
        "employee with legitimate network access performs unauthorized actions: "
        "reading sensitive process data during off-hours, modifying control "
        "parameters, and exfiltrating proprietary process configurations. "
        "Works with any protocol and any industry vertical."
    ),
    mitre_software_id="",
    severity="high",
    category="insider",
    required_protocols=[],
    industry_verticals=[
        "manufacturing", "energy", "water", "oil_gas",
        "building_automation", "transportation",
    ],
    reference_url="https://attack.mitre.org/tactics/TA0006/",
    stages=[
        # Stage 1: Normal Operations
        KillChainStage(
            stage_id="normal_ops",
            name="Normal Operations Baseline",
            description=(
                "Insider operates normally within expected parameters to establish "
                "a behavioral baseline and avoid initial detection."
            ),
            duration_seconds=120,
            color="#52c41a",
            mitre_tactics=["TA0043"],
            expected_cv_alerts=[],
            actions=[
                AttackAction(
                    action_id="insider_normal_reads",
                    name="Routine Register Reads",
                    action_type="modbus_read_probe",
                    description="Normal-looking register reads within expected address ranges.",
                    parameters={
                        "address_ranges": [[0, 20]],
                        "quantity": 10,
                        "step": 10,
                        "interval_ms": 1000,
                        "unit_id": 1,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 2: Off-Hours Access
        KillChainStage(
            stage_id="off_hours",
            name="Off-Hours Access",
            description=(
                "Insider begins accessing systems outside normal working hours, "
                "querying devices and reading system information."
            ),
            duration_seconds=180,
            color="#faad14",
            mitre_tactics=["TA0001"],
            expected_cv_alerts=["Off-hours OT access detected"],
            actions=[
                AttackAction(
                    action_id="insider_offhours_modbus",
                    name="Off-Hours Modbus Reads",
                    action_type="modbus_read_probe",
                    description="Register reads during non-business hours.",
                    parameters={
                        "address_ranges": [[0, 100], [4000, 4100]],
                        "quantity": 10,
                        "step": 10,
                        "interval_ms": 500,
                        "unit_id": 1,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="OT access from authorized user during off-hours",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="insider_offhours_s7",
                    name="Off-Hours S7 System Reads",
                    action_type="s7_read_szl",
                    description="Query S7 controller system info during off-hours.",
                    parameters={"szl_ids": [0x0011, 0x001C], "interval_ms": 800},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="S7 SZL read during non-business hours",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 3: Unauthorized Reads
        KillChainStage(
            stage_id="unauthorized_reads",
            name="Unauthorized Data Access",
            description=(
                "Insider accesses register ranges and devices outside their normal "
                "job responsibilities, probing sensitive process data."
            ),
            duration_seconds=240,
            color="#fa8c16",
            mitre_tactics=["TA0009"],
            expected_cv_alerts=["Access to unauthorized register ranges", "Cross-device reads"],
            actions=[
                AttackAction(
                    action_id="insider_wide_probe",
                    name="Wide Register Probe",
                    action_type="modbus_read_probe",
                    description="Read register ranges outside normal responsibilities.",
                    parameters={
                        "address_ranges": [[0, 200], [4000, 4500], [8000, 8200]],
                        "quantity": 10,
                        "step": 10,
                        "interval_ms": 300,
                        "unit_id": 1,
                    },
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="Unusual register address range access from authorized user",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="insider_s7_deep_read",
                    name="Deep S7 Configuration Read",
                    action_type="s7_read_szl",
                    description="Read detailed S7 configuration data for exfiltration.",
                    parameters={"szl_ids": [0x0011, 0x001C, 0x0111, 0x0F00, 0x0131], "interval_ms": 600},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="Extensive S7 SZL read sequence from non-engineering source",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 4: Configuration Changes
        KillChainStage(
            stage_id="config_changes",
            name="Unauthorized Configuration Changes",
            description=(
                "Insider makes unauthorized modifications to process setpoints "
                "and control parameters, potentially causing process disruption."
            ),
            duration_seconds=180,
            color="#ff4d4f",
            mitre_tactics=["TA0111"],
            expected_cv_alerts=["Unauthorized register write", "Process parameter change"],
            actions=[
                AttackAction(
                    action_id="insider_write_regs",
                    name="Modify Process Setpoints",
                    action_type="modbus_write_register",
                    description="Write to holding registers to change process setpoints.",
                    parameters={"address": 4000, "count": 4, "use_multi_write": False, "interval_ms": 2000},
                    target_selector="plc",
                    mitre_technique="T0836",
                    expected_cv_detection="Holding register write from user outside change window",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="insider_gradual_manip",
                    name="Gradual Value Manipulation",
                    action_type="register_manipulation",
                    description="Slowly drift register values to cause process deviation.",
                    parameters={
                        "address": 40000,
                        "register_count": 4,
                        "steps": 15,
                        "interval_ms": 3000,
                        "drift_per_step": 25,
                    },
                    target_selector="plc",
                    mitre_technique="T0836",
                    expected_cv_detection="Gradual process variable drift detected",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 5: Data Exfiltration
        KillChainStage(
            stage_id="data_exfil",
            name="Data Exfiltration",
            description=(
                "Insider exfiltrates proprietary process configurations, recipes, "
                "and control logic via covert channels."
            ),
            duration_seconds=180,
            color="#f5222d",
            mitre_tactics=["TA0010"],
            expected_cv_alerts=["HTTP data exfiltration", "DNS tunneling detected"],
            actions=[
                AttackAction(
                    action_id="insider_http_exfil",
                    name="HTTP Data Theft",
                    action_type="http_exfil",
                    description="Exfiltrate process recipes and configuration data via HTTP.",
                    parameters={"data_size": 24576},
                    target_selector="hmi",
                    mitre_technique="T0882",
                    expected_cv_detection="Large HTTP POST to external host from OT workstation",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="insider_dns_exfil",
                    name="DNS Covert Channel",
                    action_type="dns_tunnel",
                    description="Exfiltrate sensitive data via DNS tunneling to personal server.",
                    parameters={"data_size": 8192},
                    target_selector="hmi",
                    mitre_technique="T0884",
                    expected_cv_detection="DNS tunneling with encoded data in subdomain queries",
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 6. NETWORK_RECON -- Network Reconnaissance (Entry-Level Demo)
# ---------------------------------------------------------------------------

NETWORK_RECON = AttackPlaybook(
    playbook_id="network_recon",
    name="Network Reconnaissance",
    description=(
        "Entry-level demonstration playbook simulating a network reconnaissance "
        "campaign. Covers host discovery, port scanning, multi-protocol service "
        "enumeration, and vulnerability probing. Useful for validating detection "
        "capabilities and as a building block for more advanced scenarios."
    ),
    mitre_software_id="",
    severity="medium",
    category="reconnaissance",
    required_protocols=[],
    industry_verticals=[
        "manufacturing", "energy", "water", "oil_gas",
        "building_automation", "transportation",
    ],
    reference_url="https://attack.mitre.org/tactics/TA0043/",
    stages=[
        # Stage 1: Host Discovery
        KillChainStage(
            stage_id="host_discovery",
            name="Host Discovery",
            description=(
                "Initial network mapping using ICMP echo requests to identify "
                "live hosts on the OT network."
            ),
            duration_seconds=90,
            color="#ffc53d",
            mitre_tactics=["TA0043"],
            expected_cv_alerts=["ICMP sweep detected"],
            actions=[
                AttackAction(
                    action_id="recon_icmp_sweep",
                    name="ICMP Ping Sweep",
                    action_type="icmp_sweep",
                    description="ICMP echo request sweep to discover live hosts.",
                    parameters={"interval_ms": 80},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="ICMP echo request sweep across OT subnet",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 2: Port Scanning
        KillChainStage(
            stage_id="port_scanning",
            name="Port Scanning",
            description=(
                "SYN scan of common OT protocol ports on discovered hosts to "
                "identify running services."
            ),
            duration_seconds=180,
            color="#faad14",
            mitre_tactics=["TA0043"],
            expected_cv_alerts=["Port scan detected", "SYN scan on OT ports"],
            actions=[
                AttackAction(
                    action_id="recon_port_scan",
                    name="OT Port Scan",
                    action_type="port_scan",
                    description="SYN scan of standard OT ports (102, 502, 44818, 47808, 161).",
                    parameters={"scan_ot_ports": True, "scan_type": "syn"},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SYN scan targeting industrial protocol ports",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 3: Service Enumeration
        KillChainStage(
            stage_id="service_enumeration",
            name="Service Enumeration",
            description=(
                "Protocol-specific enumeration using Modbus unit ID scanning, "
                "EtherNet/IP ListIdentity, SNMP walks, and BACnet Who-Is to "
                "fingerprint discovered services."
            ),
            duration_seconds=360,
            color="#fa8c16",
            mitre_tactics=["TA0102"],
            expected_cv_alerts=[
                "Modbus enumeration", "EtherNet/IP discovery",
                "SNMP MIB walk", "BACnet Who-Is broadcast",
            ],
            actions=[
                AttackAction(
                    action_id="recon_modbus_enum",
                    name="Modbus Unit Enumeration",
                    action_type="modbus_unit_enum",
                    description="Scan Modbus unit IDs using Report Server ID (FC 17).",
                    parameters={"unit_range": [1, 48], "interval_ms": 150},
                    target_selector="plc",
                    mitre_technique="T0842",
                    expected_cv_detection="Modbus function code 17 scan across unit ID range",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="recon_enip_list",
                    name="EtherNet/IP Device Discovery",
                    action_type="enip_list_identity",
                    description="Broadcast EtherNet/IP ListIdentity for CIP device discovery.",
                    parameters={"interval_ms": 250},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="EtherNet/IP ListIdentity from non-standard host",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="recon_snmp_walk",
                    name="SNMP System Walk",
                    action_type="snmp_walk",
                    description="Walk system MIB to extract device descriptions and network info.",
                    parameters={"community": "public", "start_oid": "1.3.6.1.2.1.1", "num_requests": 15, "interval_ms": 200},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SNMP GetBulk walk from non-NMS source",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="recon_bacnet_whois",
                    name="BACnet Who-Is Discovery",
                    action_type="bacnet_whois",
                    description="BACnet Who-Is broadcast to discover building automation devices.",
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="BACnet Who-Is from non-BMS source",
                    delay_after_ms=2000,
                ),
            ],
        ),
        # Stage 4: Vulnerability Probing
        KillChainStage(
            stage_id="vuln_probing",
            name="Vulnerability Probing",
            description=(
                "Targeted probing for common OT vulnerabilities: SNMP community "
                "string brute force and S7 system information reads to identify "
                "exploitable weaknesses."
            ),
            duration_seconds=240,
            color="#ff7a45",
            mitre_tactics=["TA0102", "TA0043"],
            expected_cv_alerts=["SNMP brute force", "S7 system information access"],
            actions=[
                AttackAction(
                    action_id="recon_snmp_brute",
                    name="SNMP Community Brute Force",
                    action_type="snmp_community_brute",
                    description="Try common community strings to find writable SNMP access.",
                    parameters={
                        "communities": [
                            "public", "private", "community", "admin", "monitor",
                            "snmp", "default", "cisco", "siemens", "manager",
                            "operator", "readonly", "readwrite", "test",
                        ],
                        "interval_ms": 120,
                    },
                    target_selector="any",
                    mitre_technique="T0866",
                    expected_cv_detection="Multiple SNMP community string attempts from single source",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="recon_s7_info",
                    name="S7 System Information Read",
                    action_type="s7_read_szl",
                    description="Read S7 SZL to identify controller model, firmware, and known vulnerabilities.",
                    parameters={"szl_ids": [0x0011, 0x001C, 0x0111], "interval_ms": 500},
                    target_selector="plc",
                    mitre_technique="T0802",
                    expected_cv_detection="S7comm SZL read from unauthorized source",
                    delay_after_ms=2000,
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# 7. SNORT_VALIDATION -- IDS/IPS Rule Validation Suite
# ---------------------------------------------------------------------------

SNORT_VALIDATION = AttackPlaybook(
    playbook_id="snort_validation",
    name="Snort/Suricata IDS Validation Suite",
    description=(
        "Comprehensive IDS testing playbook that generates traffic specifically "
        "designed to trigger Snort and Suricata detection rules. Covers 15 "
        "signatures across ICS/OT protocols (Modicon M580 UMAS), C2 beaconing "
        "(Emotet, Trickbot, TRITON), data exfiltration (DNS tunneling), anomaly "
        "detection, and polyglot malware patterns. Ideal for validating IDS "
        "deployments, tuning rule sets, and demonstrating detection capabilities."
    ),
    mitre_software_id="",  # Multiple malware families covered
    severity="low",  # Testing playbook, not simulating actual attack
    category="ids_testing",
    required_protocols=["modbus_tcp", "http", "dns"],
    industry_verticals=["all"],
    reference_url="https://github.com/ip-aegis/PacketArch/blob/master/docs/SNORT_VALIDATION.md",
    stages=[
        # Stage 1: Reconnaissance
        KillChainStage(
            stage_id="reconnaissance",
            name="Reconnaissance & Enumeration",
            description="Port scanning and service discovery to establish baseline traffic.",
            duration_seconds=120,
            color="#91d5ff",  # Light blue
            mitre_tactics=["TA0043"],  # Reconnaissance
            expected_cv_alerts=["Port scan detected from external source"],
            actions=[
                AttackAction(
                    action_id="snort_port_scan",
                    name="OT Port Scanning",
                    action_type="port_scan",
                    description="Scan common OT ports (21, 53, 80, 443, 502, 102, 44818, 47808, 161).",
                    parameters={"scan_ot_ports": True, "scan_type": "syn"},
                    target_selector="any",
                    mitre_technique="T0846",
                    expected_cv_detection="SYN scan across OT protocol ports",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 2: ICS/OT Protocol Probing
        KillChainStage(
            stage_id="ics_probing",
            name="ICS/OT Protocol Exploitation",
            description=(
                "Trigger ICS-specific Snort rules using Modicon M580 UMAS vulnerability "
                "patterns (CVE-2018-7842, CVE-2019-6806, CVE-2019-6807). Generates "
                "Modbus TCP traffic with UMAS function codes 0x30, 0x22, 0x23."
            ),
            duration_seconds=180,
            color="#ffa39e",  # Light red
            mitre_tactics=["TA0104"],  # Impair Process Control
            expected_cv_alerts=[
                "Modicon M580 UMAS 0x30 vulnerability (sid:5800420)",
                "Modicon M580 UMAS READ_VARIABLES (sid:5800061)",
                "Modicon M580 UMAS WRITE_VARIABLES (sid:5800073)",
            ],
            actions=[
                AttackAction(
                    action_id="snort_umas_0x30",
                    name="UMAS Function Code 0x30",
                    action_type="modicon_umas_0x30",
                    description="Trigger sid:5800420 with UMAS 0x30 burst (20+ packets/sec).",
                    parameters={"interval_ms": 50, "burst_count": 25, "unit_id": 1},
                    target_selector="plc",
                    mitre_technique="T0869",
                    expected_cv_detection="Modicon M580 UMAS function code 0x30 exploit attempt",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="snort_umas_0x22",
                    name="UMAS READ_VARIABLES",
                    action_type="modicon_umas_0x22",
                    description="Trigger sid:5800061 with unauthorized variable read pattern.",
                    parameters={"interval_ms": 50, "burst_count": 25, "unit_id": 1},
                    target_selector="plc",
                    mitre_technique="T0868",
                    expected_cv_detection="Modicon M580 UMAS READ_VARIABLES attempt",
                    delay_after_ms=2000,
                ),
                AttackAction(
                    action_id="snort_umas_0x23",
                    name="UMAS WRITE_VARIABLES",
                    action_type="modicon_umas_0x23",
                    description="Trigger sid:5800073 with malicious write to safety controller.",
                    parameters={"interval_ms": 100, "repeat_count": 5, "unit_id": 1},
                    target_selector="plc",
                    mitre_technique="T0836",
                    expected_cv_detection="Modicon M580 UMAS WRITE_VARIABLES exploit",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 3: C2 Beaconing & Exfiltration
        KillChainStage(
            stage_id="c2_beaconing",
            name="C2 Beaconing & Data Exfiltration",
            description=(
                "Simulate malware C2 communication patterns (Emotet, TRITON) and DNS "
                "exfiltration to trigger C2 and data theft signatures."
            ),
            duration_seconds=300,
            color="#ffbb96",  # Light orange
            mitre_tactics=["TA0011", "TA0010"],  # Command and Control, Exfiltration
            expected_cv_alerts=[
                "Emotet malware C2 beacon (sid:51971)",
                "DNS exfiltration via .c0m.li (sid:27737)",
                "TRITON DNS beacon to mooo.com (sid:50300)",
            ],
            actions=[
                AttackAction(
                    action_id="snort_emotet",
                    name="Emotet C2 Beacon",
                    action_type="emotet_beacon",
                    description="Trigger sid:51971 with HTTP POST to /balloon/ringin/chunk/.",
                    parameters={
                        "interval_ms": 60000,
                        "beacon_count": 5,
                        "c2_server": "emotet-c2.malicious.com",
                        "dst_port": 443,
                    },
                    target_selector="ews",
                    mitre_technique="T1071.001",
                    expected_cv_detection="Emotet malware beaconing from engineering workstation",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="snort_dns_exfil",
                    name="DNS Data Exfiltration",
                    action_type="dns_exfil",
                    description="Trigger sid:27737 with DNS queries to .c0m.li typo domain.",
                    parameters={"interval_ms": 30000, "query_count": 10},
                    target_selector="any",
                    mitre_technique="T1048.003",
                    expected_cv_detection="DNS exfiltration attempt via suspicious TLD",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="snort_triton_dns",
                    name="TRITON DNS Beacon",
                    action_type="triton_dns_beacon",
                    description="Trigger sid:50300 with TRITON-specific DNS pattern (udp-*.mooo.com).",
                    parameters={"interval_ms": 300000, "beacon_count": 2, "base_domain": "mooo.com"},
                    target_selector="ews",
                    mitre_technique="T1071.004",
                    expected_cv_detection="TRITON malware DNS C2 beacon detected",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 4: Advanced C2 Techniques
        KillChainStage(
            stage_id="advanced_c2",
            name="Advanced C2 Patterns",
            description=(
                "Multi-protocol C2 communication using Trickbot, OlympicDestroyer, "
                "and vsFTPd backdoor techniques to trigger advanced malware signatures."
            ),
            duration_seconds=300,
            color="#ffccc7",  # Lighter red
            mitre_tactics=["TA0011"],  # Command and Control
            expected_cv_alerts=[
                "Trickbot malware C2 (sid:54201)",
                "OlympicDestroyer C2 with header anomalies (sid:48435)",
                "vsFTPd backdoor exploitation (sid:19415)",
            ],
            actions=[
                AttackAction(
                    action_id="snort_trickbot",
                    name="Trickbot Command Retrieval",
                    action_type="trickbot_command",
                    description="Trigger sid:54201 with HTTP GET to /images/imgpaper.png and WinHTTP UA.",
                    parameters={
                        "interval_ms": 300000,
                        "command_count": 2,
                        "c2_server": "trickbot-c2.evil.com",
                        "dst_port": 443,
                    },
                    target_selector="ews",
                    mitre_technique="T1071.001",
                    expected_cv_detection="Trickbot C2 command retrieval detected",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="snort_olympic",
                    name="OlympicDestroyer C2 Check-in",
                    action_type="olympic_destroyer_c2",
                    description="Trigger sid:48435 with HTTP POST missing User-Agent/Referer headers.",
                    parameters={
                        "interval_ms": 180000,
                        "checkin_count": 2,
                        "c2_server": "olympic-c2.hostile.net",
                    },
                    target_selector="ews",
                    mitre_technique="T1071.001",
                    expected_cv_detection="OlympicDestroyer C2 with anomalous headers",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="snort_vsftpd",
                    name="vsFTPd Backdoor Exploit",
                    action_type="vsftpd_backdoor",
                    description="Trigger sid:19415 with FTP USER command containing :) smiley.",
                    parameters={"target_port": 21, "username": "backdoor:)", "attempt_count": 3},
                    target_selector="any",
                    mitre_technique="T1190",
                    expected_cv_detection="vsFTPd 2.3.4 backdoor exploitation attempt",
                    delay_after_ms=3000,
                ),
            ],
        ),
        # Stage 5: Data Exfiltration & Keylogging
        KillChainStage(
            stage_id="data_exfiltration",
            name="Data Exfiltration & Keylogging",
            description=(
                "Credential theft via DNS tunneling (UDPOS) and keylogger data "
                "exfiltration (HawkEye) to trigger data theft signatures."
            ),
            duration_seconds=240,
            color="#fff1b8",  # Yellow
            mitre_tactics=["TA0010", "TA0009"],  # Exfiltration, Collection
            expected_cv_alerts=[
                "UDPOS credential exfiltration (sid:45964)",
                "HawkEye keylogger data theft (sid:49778)",
            ],
            actions=[
                AttackAction(
                    action_id="snort_udpos",
                    name="UDPOS DNS Credential Theft",
                    action_type="udpos_credential_exfil",
                    description="Trigger sid:45964 with DNS queries containing \\x03bin pattern.",
                    parameters={"interval_ms": 30000, "exfil_count": 8},
                    target_selector="any",
                    mitre_technique="T1048.003",
                    expected_cv_detection="UDPOS credential exfiltration via DNS",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="snort_hawkeye",
                    name="HawkEye Keylogger Exfil",
                    action_type="hawkeye_keylogger",
                    description="Trigger sid:49778 with file data containing HawkEye signature.",
                    parameters={
                        "interval_ms": 120000,
                        "exfil_count": 2,
                        "exfil_method": "smtp",
                        "smtp_server": "mail.exfil.com",
                    },
                    target_selector="ews",
                    mitre_technique="T1056.001",
                    expected_cv_detection="HawkEye Keylogger data exfiltration via SMTP",
                    delay_after_ms=5000,
                ),
            ],
        ),
        # Stage 6: Anomaly Detection & Binary Signatures
        KillChainStage(
            stage_id="anomaly_detection",
            name="Anomaly Detection & Binary Patterns",
            description=(
                "Advanced malware patterns including APT keepalives (Night Dragon), "
                "temporal anomalies (Angler EK), spyware authentication (iSpyoo), "
                "and PE file markers (Dridex) to trigger anomaly-based and binary signatures."
            ),
            duration_seconds=360,
            color="#d3adf7",  # Purple
            mitre_tactics=["TA0011", "TA0043"],  # C&C, Reconnaissance
            expected_cv_alerts=[
                "Night Dragon APT keepalive (sid:18459)",
                "Angler Exploit Kit temporal anomaly (sid:32390)",
                "iSpyoo spyware authentication (sid:50438)",
                "Dridex banking trojan file marker (sid:45932)",
            ],
            actions=[
                AttackAction(
                    action_id="snort_night_dragon",
                    name="Night Dragon APT Keepalive",
                    action_type="night_dragon_keepalive",
                    description="Trigger sid:18459 with binary pattern \\xFF\\x00\\x00\\x00\\x07.",
                    parameters={"interval_ms": 60000, "keepalive_count": 6, "target_port": 443},
                    target_selector="ews",
                    mitre_technique="T1071.001",
                    expected_cv_detection="Night Dragon backdoor keepalive packets",
                    delay_after_ms=3000,
                ),
                AttackAction(
                    action_id="snort_angler_ek",
                    name="Angler EK Landing Page",
                    action_type="angler_ek_landing",
                    description="Trigger sid:32390 with HTTP response containing future date (year 2099).",
                    parameters={"serve_count": 3, "interval_ms": 60000},
                    target_selector="any",
                    mitre_technique="T1189",
                    expected_cv_detection="Angler Exploit Kit temporal anomaly detected",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="snort_ispyoo",
                    name="iSpyoo Spyware Authentication",
                    action_type="ispyoo_auth",
                    description="Trigger sid:50438 with POST /authenticate.aspx and form fields.",
                    parameters={
                        "interval_ms": 90000,
                        "attempt_count": 4,
                        "target_path": "/authenticate.aspx",
                    },
                    target_selector="any",
                    mitre_technique="T1437.001",
                    expected_cv_detection="iSpyoo Android spyware authentication attempt",
                    delay_after_ms=5000,
                ),
                AttackAction(
                    action_id="snort_dridex",
                    name="Dridex PE File Delivery",
                    action_type="dridex_file_marker",
                    description="Trigger sid:45932 with PE file containing .coda and .crt sections.",
                    parameters={
                        "interval_ms": 180000,
                        "delivery_count": 2,
                        "delivery_method": "http_download",
                    },
                    target_selector="any",
                    mitre_technique="T1566.001",
                    expected_cv_detection="Dridex banking trojan PE file marker",
                    delay_after_ms=5000,
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ALL_PLAYBOOKS = [
    TRITON_LIKE,
    PIPEDREAM_LIKE,
    INDUSTROYER_LIKE,
    HAVEX_LIKE,
    INSIDER_THREAT,
    NETWORK_RECON,
    SNORT_VALIDATION,
]

PLAYBOOK_REGISTRY: dict[str, AttackPlaybook] = {p.playbook_id: p for p in _ALL_PLAYBOOKS}


def get_playbook(playbook_id: str) -> AttackPlaybook | None:
    """Look up a playbook by its unique ID."""
    return PLAYBOOK_REGISTRY.get(playbook_id)


def list_playbooks() -> list[AttackPlaybook]:
    """Return all pre-built playbooks."""
    return list(PLAYBOOK_REGISTRY.values())
