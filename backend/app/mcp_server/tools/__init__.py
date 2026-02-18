"""MCP tools for scenario manipulation and AI generation."""

from app.mcp_server.tools.ai_generation_tools import (
    generate_scenario_from_nl,
    suggest_vertical_template,
    inject_anomaly_campaign,
    list_anomaly_templates,
    analyze_scenario_for_anomalies,
)
from app.mcp_server.tools.fingerprint_tools import (
    list_vendor_fingerprints,
    get_fingerprint_detail,
    suggest_fingerprint_for_device,
    apply_fingerprint_to_device,
    configure_device_realism,
    configure_flow_realism,
    apply_realism_preset,
    search_cves,
    get_cve_detail,
    list_vulnerable_variants,
    apply_cve_to_device,
    suggest_cves_for_device,
    get_scenario_vulnerability_profile,
)
from app.mcp_server.tools.protocol_tools import (
    configure_modbus_device,
    configure_modbus_flow,
    configure_ethernet_ip_device,
    configure_ethernet_ip_connection,
    configure_profinet_device,
    configure_profinet_ar,
    configure_s7_device,
    configure_s7_communication,
    configure_dnp3_device,
    configure_dnp3_flow,
    configure_iec104_device,
    configure_iec104_flow,
    configure_bacnet_device,
    configure_bacnet_polling,
    configure_snmp_device,
    configure_snmp_polling,
    configure_opcua_device,
    configure_opcua_subscription,
    configure_iec61850_ied,
    configure_goose_publisher,
)
from app.mcp_server.tools.layout_tools import (
    set_device_position,
    set_zone_bounds,
    auto_layout_scenario,
    move_devices_to_zone,
)
from app.mcp_server.tools.external_comm_tools import (
    add_external_communication,
    list_external_communications,
    remove_external_communication,
    get_external_comm_patterns,
)
from app.mcp_server.tools.attack_tools import (
    list_attack_playbooks,
    get_playbook_details,
    suggest_attack_for_scenario,
)

__all__ = [
    # AI generation tools
    "generate_scenario_from_nl",
    "suggest_vertical_template",

    "inject_anomaly_campaign",
    "list_anomaly_templates",
    "analyze_scenario_for_anomalies",
    # Fingerprint tools
    "list_vendor_fingerprints",
    "get_fingerprint_detail",
    "suggest_fingerprint_for_device",
    "apply_fingerprint_to_device",
    # Realism tools
    "configure_device_realism",
    "configure_flow_realism",
    "apply_realism_preset",
    # CVE tools
    "search_cves",
    "get_cve_detail",
    "list_vulnerable_variants",
    "apply_cve_to_device",
    "suggest_cves_for_device",
    "get_scenario_vulnerability_profile",
    # Protocol-specific tools
    "configure_modbus_device",
    "configure_modbus_flow",
    "configure_ethernet_ip_device",
    "configure_ethernet_ip_connection",
    "configure_profinet_device",
    "configure_profinet_ar",
    "configure_s7_device",
    "configure_s7_communication",
    "configure_dnp3_device",
    "configure_dnp3_flow",
    "configure_iec104_device",
    "configure_iec104_flow",
    "configure_bacnet_device",
    "configure_bacnet_polling",
    "configure_snmp_device",
    "configure_snmp_polling",
    "configure_opcua_device",
    "configure_opcua_subscription",
    "configure_iec61850_ied",
    "configure_goose_publisher",
    # Layout tools
    "set_device_position",
    "set_zone_bounds",
    "auto_layout_scenario",
    "move_devices_to_zone",
    # External communication tools
    "add_external_communication",
    "list_external_communications",
    "remove_external_communication",
    "get_external_comm_patterns",
    # Phase management tools (from scenario_tools)
    "apply_phase_preset",
    "update_phase_timing",
    "reorder_phases",
    "list_phase_presets",
    # Attack simulation tools
    "list_attack_playbooks",
    "get_playbook_details",
    "suggest_attack_for_scenario",
]
