#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Comprehensive audit of all scenario templates.

Validates:
1. Fingerprint references resolve to DeviceTemplate entries
2. Protocol/device type compatibility
3. Flow source/target compatibility
4. Timing ranges
5. Naming patterns
6. Zone assignments

Usage:
    cd backend && python scripts/audit_templates.py [--output-format json|markdown]
    cd backend && python scripts/audit_templates.py --vertical manufacturing
    cd backend && python scripts/audit_templates.py --template discrete_manufacturing
"""

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add backend to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =============================================================================
# Severity and Issue Types
# =============================================================================


class Severity(Enum):
    CRITICAL = "critical"  # Blocks traffic generation
    WARNING = "warning"    # Suboptimal but functional
    INFO = "info"          # Suggestions


@dataclass
class AuditIssue:
    """A single audit issue."""
    severity: Severity
    category: str
    vertical: str
    template_name: str
    device_name: str | None
    message: str
    suggestion: str | None = None
    flow_index: int | None = None  # For flow-related issues

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "vertical": self.vertical,
            "template_name": self.template_name,
            "device_name": self.device_name,
            "message": self.message,
            "suggestion": self.suggestion,
            "flow_index": self.flow_index,
        }


# =============================================================================
# Protocol/Device Type Compatibility Rules
# =============================================================================

# Protocols appropriate for each device type
DEVICE_PROTOCOL_COMPATIBILITY = {
    "plc": ["modbus_tcp", "ethernet_ip", "profinet", "s7comm", "s7comm_plus", "opc_ua", "bacnet", "dnp3", "iec104"],
    "safety_plc": ["profinet", "profisafe", "s7comm", "s7comm_plus", "ethernet_ip", "modbus_tcp", "cip_safety"],
    "hmi": ["profinet", "s7comm", "s7comm_plus", "ethernet_ip", "opc_ua", "modbus_tcp", "bacnet"],
    "drive": ["profinet", "ethernet_ip", "modbus_tcp", "bacnet"],
    "servo": ["profinet", "ethernet_ip", "modbus_tcp"],
    "io_module": ["profinet", "ethernet_ip", "modbus_tcp", "dnp3"],
    "sensor": ["profinet", "ethernet_ip", "modbus_tcp", "bacnet", "snmp", "opc_ua", "dnp3"],
    "actuator": ["profinet", "ethernet_ip", "modbus_tcp"],
    "switch": ["profinet", "snmp", "ethernet_ip", "modbus_tcp"],
    "router": ["snmp"],
    "rtu": ["modbus_tcp", "dnp3", "snmp", "iec104", "ethernet_ip"],
    "scada_server": ["opc_ua", "modbus_tcp", "ethernet_ip", "s7comm", "s7comm_plus", "dnp3", "snmp", "bacnet"],
    "historian": ["opc_ua", "modbus_tcp", "ethernet_ip"],
    "engineering_station": ["profinet", "s7comm", "s7comm_plus", "ethernet_ip", "opc_ua", "modbus_tcp"],
    # Building automation
    "bac": ["bacnet", "snmp", "modbus_tcp"],
    "bms_server": ["bacnet", "snmp", "opc_ua"],
    "bms_controller": ["bacnet", "snmp", "modbus_tcp"],
    "ahu_controller": ["bacnet", "modbus_tcp"],
    "vav_controller": ["bacnet"],
    "chiller_controller": ["bacnet", "modbus_tcp"],
    "boiler_controller": ["bacnet", "modbus_tcp"],
    "lighting_controller": ["bacnet", "modbus_tcp", "snmp"],
    "energy_meter": ["modbus_tcp", "bacnet", "snmp"],
    "access_controller": ["bacnet", "snmp"],
    "thermostat": ["bacnet", "modbus_tcp"],
    # Data center infrastructure
    "ups": ["snmp", "modbus_tcp"],
    "pdu": ["snmp", "modbus_tcp"],
    "crac_unit": ["snmp", "modbus_tcp", "bacnet"],
    # Transportation/ITS
    "master_station": ["snmp", "modbus_tcp"],
    "traffic_controller": ["snmp"],
    "dms": ["snmp"],
    "radar_sensor": ["snmp"],
    "weather_station": ["snmp"],
    "camera": ["snmp"],
    "thermal_sensor": ["snmp"],
    "video_detector": ["snmp"],
    "detector_rack": ["snmp"],
    "tunnel_controller": ["snmp", "modbus_tcp"],
    "fire_panel": ["snmp", "modbus_tcp", "bacnet"],
    "ventilation_controller": ["snmp", "modbus_tcp", "bacnet"],
    "toll_controller": ["snmp"],
    "rsu": ["snmp"],
    "anpr_camera": ["snmp"],
    # Generic/fallback
    "gateway": ["modbus_tcp", "ethernet_ip", "profinet", "opc_ua", "dnp3", "bacnet", "snmp", "s7comm", "s7comm_plus"],
    "analyzer": ["modbus_tcp", "profinet", "ethernet_ip", "bacnet"],
    "flow_meter": ["modbus_tcp", "profinet", "ethernet_ip", "bacnet"],
    "flow_sensor": ["modbus_tcp", "profinet", "ethernet_ip"],
    "level_sensor": ["modbus_tcp", "profinet", "ethernet_ip"],
    "transmitter": ["modbus_tcp", "profinet", "ethernet_ip"],
    "valve": ["modbus_tcp", "profinet", "ethernet_ip"],
    "pump_controller": ["modbus_tcp", "profinet", "ethernet_ip", "dnp3"],
    "compressor_controller": ["modbus_tcp", "ethernet_ip", "profinet"],
    "turbine_controller": ["modbus_tcp", "ethernet_ip", "dnp3"],
    "motor_controller": ["modbus_tcp", "ethernet_ip", "profinet"],
    "relay": ["dnp3", "modbus_tcp", "iec104"],
    "protection_relay": ["iec104", "dnp3", "modbus_tcp", "iec61850"],
    "meter": ["modbus_tcp", "dnp3", "iec104", "snmp"],
    "power_meter": ["modbus_tcp", "dnp3", "bacnet", "snmp"],
    # Vision/identification systems
    "vision_sensor": ["profinet", "ethernet_ip"],
    "barcode_scanner": ["profinet", "ethernet_ip"],
    "scada": ["s7comm", "opc_ua", "modbus_tcp"],
    "dcs_controller": ["modbus_tcp", "opc_ua", "ethernet_ip"],
    # Remote I/O and safety systems
    "remote_io": ["profinet", "ethernet_ip", "modbus_tcp", "dnp3"],
    "safety_io": ["profinet", "profisafe", "ethernet_ip", "cip_safety", "modbus_tcp"],
    # Building automation specialty
    "niagara_jace": ["bacnet", "modbus_tcp", "snmp"],
    # Transportation specialty
    "chem_sensor": ["modbus_tcp", "snmp"],
    "seismic_sensor": ["modbus_tcp", "snmp"],
    "toll_host": ["snmp", "modbus_tcp"],
    "lane_controller": ["snmp", "modbus_tcp"],
    "barrier_controller": ["snmp", "modbus_tcp"],
    "classification_sensor": ["snmp"],
    "network_switch": ["snmp", "profinet"],
}

# Flow timing ranges by protocol (min_ms, max_ms)
PROTOCOL_TIMING_RANGES = {
    "profinet": (0.25, 128),       # 250us to 128ms (typical RT)
    "profisafe": (1, 128),         # Safety protocol
    "ethernet_ip": (2, 5000),      # RPI ranges
    "modbus_tcp": (50, 60000),     # Typical polling (50ms to 1min)
    "s7comm": (10, 10000),         # S7 polling
    "s7comm_plus": (10, 10000),    # S7-1500 polling
    "opc_ua": (100, 120000),       # OPC UA subscriptions (up to 2min)
    "bacnet": (1000, 120000),      # BACnet polling (1-120s typical)
    "snmp": (100, 300000),         # SNMP polling (100ms to 5min)
    "dnp3": (500, 120000),         # DNP3 polling (up to 2min for integrity polls)
    "iec104": (500, 120000),       # IEC 104 polling (up to 2min for GI)
}


# =============================================================================
# Template Auditor
# =============================================================================


class TemplateAuditor:
    """Audits scenario templates for issues."""

    def __init__(self):
        self.issues: list[AuditIssue] = []
        self.device_templates = {}
        self.template_models = set()  # All available model names
        self._load_device_templates()

    def _load_device_templates(self):
        """Load device templates for fingerprint validation."""
        try:
            # Import directly from the module file to avoid __init__.py imports
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "device_templates",
                BACKEND_DIR / "app" / "services" / "device_templates.py"
            )
            device_templates_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(device_templates_module)

            self.device_templates = device_templates_module.DEVICE_TEMPLATES
            self.get_template_by_vendor_model = device_templates_module.get_template_by_vendor_model

            # Build set of all model names for suggestions
            for template in self.device_templates.values():
                self.template_models.add(template.model.lower())
                self.template_models.add(template.model_name.lower())
        except Exception as e:
            print(f"Warning: Could not load device templates: {e}")
            self.device_templates = {}
            self.get_template_by_vendor_model = lambda v, m: None

    def _add_issue(
        self,
        severity: Severity,
        category: str,
        vertical: str,
        template_name: str,
        device_name: str | None,
        message: str,
        suggestion: str | None = None,
        flow_index: int | None = None,
    ):
        """Add an audit issue."""
        self.issues.append(AuditIssue(
            severity=severity,
            category=category,
            vertical=vertical,
            template_name=template_name,
            device_name=device_name,
            message=message,
            suggestion=suggestion,
            flow_index=flow_index,
        ))

    def _suggest_fingerprint(self, vendor: str, model: str) -> str | None:
        """Suggest a valid fingerprint for a vendor/model."""
        vendor_lower = vendor.lower()
        model_lower = model.lower()

        # Find templates for this vendor
        vendor_templates = []
        for template in self.device_templates.values():
            if template.vendor.lower() == vendor_lower:
                vendor_templates.append(template)

        if not vendor_templates:
            # Try partial vendor match
            for template in self.device_templates.values():
                if vendor_lower in template.vendor.lower():
                    vendor_templates.append(template)

        if not vendor_templates:
            return f"No templates found for vendor '{vendor}'. Check vendor spelling."

        # Find closest model match
        suggestions = []
        for template in vendor_templates:
            # Check if model is substring
            if model_lower in template.model.lower() or model_lower in template.model_name.lower():
                suggestions.append(f"{template.model} ({template.model_name})")
            elif template.model.lower() in model_lower or template.model_name.lower() in model_lower:
                suggestions.append(f"{template.model} ({template.model_name})")

        if suggestions:
            return f"Try: {', '.join(suggestions[:3])}"

        # Return first 3 available models for vendor
        available = [f"{t.model} ({t.model_name})" for t in vendor_templates[:3]]
        return f"Available for {vendor}: {', '.join(available)}"

    def _load_templates(self, vertical: str) -> dict[str, dict]:
        """Load scenario templates for a vertical."""
        templates = {}
        try:
            if vertical == "manufacturing":
                from app.scenario_templates.manufacturing import MANUFACTURING_TEMPLATES
                templates = MANUFACTURING_TEMPLATES
            elif vertical == "water":
                from app.scenario_templates.water import WATER_TEMPLATES
                templates = WATER_TEMPLATES
            elif vertical == "energy":
                from app.scenario_templates.energy import ENERGY_TEMPLATES
                templates = ENERGY_TEMPLATES
            elif vertical == "oil_gas":
                from app.scenario_templates.oil_gas import OIL_GAS_TEMPLATES
                templates = OIL_GAS_TEMPLATES
            elif vertical == "building_automation":
                from app.scenario_templates.building_automation import BUILDING_AUTOMATION_TEMPLATES
                templates = BUILDING_AUTOMATION_TEMPLATES
            elif vertical == "transportation":
                from app.scenario_templates.transportation import TRANSPORTATION_TEMPLATES
                templates = TRANSPORTATION_TEMPLATES
        except ImportError as e:
            print(f"Warning: Could not load {vertical} templates: {e}")
        return templates

    def _validate_fingerprints(self, vertical: str, template_name: str, template: dict):
        """Validate fingerprint references for all devices."""
        devices = template.get("devices", [])

        # Device types that are typically Windows/Linux workstations without
        # protocol-specific fingerprints (they use standard TCP stacks)
        workstation_types = {
            "engineering_station", "scada_server", "scada", "historian",
            "gateway", "server", "workstation", "switch", "router",
        }
        # Device types that are often simple I/O-controlled devices without
        # dedicated network identities (printers, generic actuators, etc.)
        simple_io_types = {"actuator"}

        for device in devices:
            vendor = device.get("vendor", "unknown")
            model = device.get("fingerprint_model")
            device_name = device.get("name_pattern", "unknown")
            device_type = device.get("type", "unknown")

            if not model:
                # Skip warning for workstation types that don't have protocol fingerprints
                # and simple I/O-controlled devices without dedicated network identities
                if device_type in workstation_types or device_type in simple_io_types:
                    continue

                # Missing fingerprint is a warning, not critical
                # Many devices work without fingerprints (they get generic behavior)
                self._add_issue(
                    Severity.WARNING,
                    "fingerprint",
                    vertical,
                    template_name,
                    device_name,
                    f"Device missing fingerprint_model (vendor={vendor}, type={device_type})",
                    "Add fingerprint_model for better device emulation",
                )
                continue

            # Check if fingerprint resolves
            resolved = self.get_template_by_vendor_model(vendor, model)
            if not resolved:
                suggestion = self._suggest_fingerprint(vendor, model)
                self._add_issue(
                    Severity.CRITICAL,
                    "fingerprint",
                    vertical,
                    template_name,
                    device_name,
                    f"Fingerprint not found: vendor='{vendor}', model='{model}'",
                    suggestion,
                )

    def _validate_protocols(self, vertical: str, template_name: str, template: dict):
        """Validate protocol/device type compatibility."""
        devices = template.get("devices", [])

        for device in devices:
            device_type = device.get("type", "unknown")
            protocols = device.get("protocols", [])
            device_name = device.get("name_pattern", "unknown")

            if device_type == "unknown":
                self._add_issue(
                    Severity.WARNING,
                    "protocol",
                    vertical,
                    template_name,
                    device_name,
                    "Device has unknown type",
                    "Specify device type for proper protocol validation",
                )
                continue

            # Get allowed protocols for this device type
            allowed = DEVICE_PROTOCOL_COMPATIBILITY.get(device_type, [])

            if not allowed:
                # Device type not in our compatibility map - just a note
                self._add_issue(
                    Severity.INFO,
                    "protocol",
                    vertical,
                    template_name,
                    device_name,
                    f"Device type '{device_type}' not in protocol compatibility map",
                    "Consider adding device type to compatibility rules",
                )
                continue

            # Check each protocol
            for protocol in protocols:
                protocol_lower = protocol.lower()
                if protocol_lower not in allowed:
                    self._add_issue(
                        Severity.WARNING,
                        "protocol",
                        vertical,
                        template_name,
                        device_name,
                        f"Protocol '{protocol}' may not be appropriate for device type '{device_type}'",
                        f"Typical protocols for {device_type}: {', '.join(allowed[:5])}",
                    )

    def _validate_flows(self, vertical: str, template_name: str, template: dict):
        """Validate flow source/target compatibility and timing."""
        flows = template.get("flows", [])
        devices = template.get("devices", [])

        # Build set of device types in this template
        device_types = {d.get("type") for d in devices}

        for i, flow in enumerate(flows):
            protocol = flow.get("protocol", "unknown")
            source_types = flow.get("source_types", [])
            target_types = flow.get("target_types", [])
            interval_ms = flow.get("interval_ms", 0)

            # Check source types exist
            for source_type in source_types:
                if source_type not in device_types:
                    self._add_issue(
                        Severity.WARNING,
                        "flow",
                        vertical,
                        template_name,
                        None,
                        f"Flow {i}: source_type '{source_type}' not found in template devices",
                        f"Available types: {', '.join(device_types)}",
                        flow_index=i,
                    )

            # Check target types exist
            for target_type in target_types:
                if target_type not in device_types:
                    self._add_issue(
                        Severity.WARNING,
                        "flow",
                        vertical,
                        template_name,
                        None,
                        f"Flow {i}: target_type '{target_type}' not found in template devices",
                        f"Available types: {', '.join(device_types)}",
                        flow_index=i,
                    )

            # Check timing range (skip for event-driven patterns)
            flow_pattern = flow.get("pattern", "").lower()
            event_driven_patterns = {"spontaneous", "unsolicited", "event", "cov", "alarm"}

            if flow_pattern not in event_driven_patterns:
                timing_range = PROTOCOL_TIMING_RANGES.get(protocol.lower())
                if timing_range:
                    min_ms, max_ms = timing_range
                    if interval_ms < min_ms:
                        self._add_issue(
                            Severity.INFO,
                            "timing",
                            vertical,
                            template_name,
                            None,
                            f"Flow {i}: interval_ms={interval_ms} is below typical range for {protocol} ({min_ms}-{max_ms}ms)",
                            "This may be intentional for high-speed applications",
                            flow_index=i,
                        )
                    elif interval_ms > max_ms:
                        self._add_issue(
                            Severity.INFO,
                            "timing",
                            vertical,
                            template_name,
                            None,
                            f"Flow {i}: interval_ms={interval_ms} is above typical range for {protocol} ({min_ms}-{max_ms}ms)",
                            "Consider if this polling rate is realistic",
                            flow_index=i,
                        )

    def _validate_naming(self, vertical: str, template_name: str, template: dict):
        """Validate device naming patterns."""
        devices = template.get("devices", [])
        name_patterns = []

        for device in devices:
            name_pattern = device.get("name_pattern", "")
            device_type = device.get("type", "unknown")

            if not name_pattern:
                self._add_issue(
                    Severity.INFO,
                    "naming",
                    vertical,
                    template_name,
                    None,
                    f"Device type '{device_type}' has no name_pattern",
                    "Add name_pattern for unique device identification",
                )
                continue

            # Check for duplicate patterns (without considering count)
            if name_pattern in name_patterns:
                self._add_issue(
                    Severity.INFO,
                    "naming",
                    vertical,
                    template_name,
                    name_pattern,
                    f"Duplicate name_pattern: '{name_pattern}'",
                    "Consider making name patterns unique per device type",
                )
            name_patterns.append(name_pattern)

    def _validate_zones(self, vertical: str, template_name: str, template: dict):
        """Validate devices are assigned to valid zones."""
        devices = template.get("devices", [])
        zones = template.get("zones", [])

        zone_ids = {z.get("id") for z in zones}

        for device in devices:
            device_zone = device.get("zone", "")
            device_name = device.get("name_pattern", "unknown")

            if not device_zone:
                self._add_issue(
                    Severity.INFO,
                    "zone",
                    vertical,
                    template_name,
                    device_name,
                    "Device has no zone assigned",
                    "Assign device to a zone for proper network segmentation",
                )
                continue

            if device_zone not in zone_ids:
                self._add_issue(
                    Severity.WARNING,
                    "zone",
                    vertical,
                    template_name,
                    device_name,
                    f"Device zone '{device_zone}' not defined in template zones",
                    f"Available zones: {', '.join(zone_ids)}",
                )

    def _validate_cves(self, vertical: str, template_name: str, template: dict):
        """Validate CVE references format."""
        import re
        cve_pattern = re.compile(r'^CVE-\d{4}-\d{4,}$')

        devices = template.get("devices", [])

        for device in devices:
            cve_ids = device.get("cve_ids", [])
            device_name = device.get("name_pattern", "unknown")

            for cve in cve_ids:
                if not cve_pattern.match(cve):
                    self._add_issue(
                        Severity.INFO,
                        "cve",
                        vertical,
                        template_name,
                        device_name,
                        f"Invalid CVE format: '{cve}'",
                        "CVE IDs should be in format CVE-YYYY-NNNNN",
                    )

    def audit_template(self, vertical: str, template_name: str, template: dict):
        """Run all validators on a single template."""
        self._validate_fingerprints(vertical, template_name, template)
        self._validate_protocols(vertical, template_name, template)
        self._validate_flows(vertical, template_name, template)
        self._validate_naming(vertical, template_name, template)
        self._validate_zones(vertical, template_name, template)
        self._validate_cves(vertical, template_name, template)

    def audit_vertical(self, vertical: str):
        """Audit all templates in a vertical."""
        templates = self._load_templates(vertical)
        for name, template in templates.items():
            self.audit_template(vertical, name, template)

    def audit_all(self) -> list[AuditIssue]:
        """Run all validators on all templates."""
        verticals = [
            "manufacturing",
            "water",
            "energy",
            "oil_gas",
            "building_automation",
            "transportation",
        ]

        for vertical in verticals:
            self.audit_vertical(vertical)

        return self.issues

    def get_summary(self) -> dict:
        """Get summary statistics."""
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        by_vertical = defaultdict(lambda: defaultdict(int))

        for issue in self.issues:
            by_severity[issue.severity.value] += 1
            by_category[issue.category] += 1
            by_vertical[issue.vertical][issue.severity.value] += 1

        return {
            "total_issues": len(self.issues),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "by_vertical": {k: dict(v) for k, v in by_vertical.items()},
        }


# =============================================================================
# Report Formatters
# =============================================================================


def format_markdown(auditor: TemplateAuditor) -> str:
    """Format audit results as markdown."""
    lines = []
    summary = auditor.get_summary()

    lines.append("# Scenario Template Audit Report")
    lines.append("")
    lines.append(f"**Total Issues:** {summary['total_issues']}")
    lines.append("")

    # Severity breakdown
    lines.append("## Summary by Severity")
    lines.append("")
    for severity in ["critical", "warning", "info"]:
        count = summary["by_severity"].get(severity, 0)
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "")
        lines.append(f"- {emoji} **{severity.upper()}**: {count}")
    lines.append("")

    # By vertical
    lines.append("## Issues by Vertical")
    lines.append("")
    for vertical, counts in sorted(summary["by_vertical"].items()):
        total = sum(counts.values())
        critical = counts.get("critical", 0)
        warning = counts.get("warning", 0)
        lines.append(f"- **{vertical}**: {total} issues ({critical} critical, {warning} warnings)")
    lines.append("")

    # Detailed issues by severity
    for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
        issues = [i for i in auditor.issues if i.severity == severity]
        if not issues:
            continue

        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity.value, "")
        lines.append(f"## {emoji} {severity.value.upper()} Issues ({len(issues)})")
        lines.append("")

        # Group by vertical/template
        by_location = defaultdict(list)
        for issue in issues:
            key = f"{issue.vertical}/{issue.template_name}"
            by_location[key].append(issue)

        for location, loc_issues in sorted(by_location.items()):
            lines.append(f"### {location}")
            lines.append("")
            for issue in loc_issues:
                device_info = f" [{issue.device_name}]" if issue.device_name else ""
                flow_info = f" (flow #{issue.flow_index})" if issue.flow_index is not None else ""
                lines.append(f"- **[{issue.category}]**{device_info}{flow_info}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - *Suggestion:* {issue.suggestion}")
            lines.append("")

    return "\n".join(lines)


def format_json(auditor: TemplateAuditor) -> str:
    """Format audit results as JSON."""
    return json.dumps({
        "summary": auditor.get_summary(),
        "issues": [i.to_dict() for i in auditor.issues],
    }, indent=2)


def format_text(auditor: TemplateAuditor) -> str:
    """Format audit results as plain text."""
    lines = []
    summary = auditor.get_summary()

    lines.append("=" * 60)
    lines.append("SCENARIO TEMPLATE AUDIT REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total Issues: {summary['total_issues']}")
    lines.append(f"  Critical: {summary['by_severity'].get('critical', 0)}")
    lines.append(f"  Warning:  {summary['by_severity'].get('warning', 0)}")
    lines.append(f"  Info:     {summary['by_severity'].get('info', 0)}")
    lines.append("")

    # Critical issues first
    critical_issues = [i for i in auditor.issues if i.severity == Severity.CRITICAL]
    if critical_issues:
        lines.append("-" * 60)
        lines.append(f"CRITICAL ISSUES ({len(critical_issues)})")
        lines.append("-" * 60)
        for issue in critical_issues:
            lines.append(f"\n[{issue.category}] {issue.vertical}/{issue.template_name}")
            if issue.device_name:
                lines.append(f"  Device: {issue.device_name}")
            lines.append(f"  Issue: {issue.message}")
            if issue.suggestion:
                lines.append(f"  Suggestion: {issue.suggestion}")

    # Warning issues
    warning_issues = [i for i in auditor.issues if i.severity == Severity.WARNING]
    if warning_issues:
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"WARNING ISSUES ({len(warning_issues)})")
        lines.append("-" * 60)
        for issue in warning_issues:
            lines.append(f"\n[{issue.category}] {issue.vertical}/{issue.template_name}")
            if issue.device_name:
                lines.append(f"  Device: {issue.device_name}")
            lines.append(f"  Issue: {issue.message}")
            if issue.suggestion:
                lines.append(f"  Suggestion: {issue.suggestion}")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Audit scenario templates")
    parser.add_argument(
        "--output-format", "-f",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--vertical", "-v",
        choices=["manufacturing", "water", "energy", "oil_gas", "building_automation", "transportation"],
        help="Audit only this vertical"
    )
    parser.add_argument(
        "--template", "-t",
        help="Audit only this template"
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["critical", "warning", "info"],
        help="Filter by minimum severity"
    )
    parser.add_argument(
        "--category", "-c",
        choices=["fingerprint", "protocol", "flow", "timing", "naming", "zone", "cve"],
        help="Filter by category"
    )

    args = parser.parse_args()

    # Run audit
    auditor = TemplateAuditor()

    if args.vertical:
        if args.template:
            templates = auditor._load_templates(args.vertical)
            if args.template in templates:
                auditor.audit_template(args.vertical, args.template, templates[args.template])
            else:
                print(f"Template '{args.template}' not found in {args.vertical}")
                sys.exit(1)
        else:
            auditor.audit_vertical(args.vertical)
    else:
        auditor.audit_all()

    # Apply filters
    if args.severity:
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        min_level = severity_order[args.severity]
        auditor.issues = [
            i for i in auditor.issues
            if severity_order[i.severity.value] <= min_level
        ]

    if args.category:
        auditor.issues = [i for i in auditor.issues if i.category == args.category]

    # Format output
    if args.output_format == "markdown":
        output = format_markdown(auditor)
    elif args.output_format == "json":
        output = format_json(auditor)
    else:
        output = format_text(auditor)

    print(output)

    # Exit with error code if critical issues found
    critical_count = sum(1 for i in auditor.issues if i.severity == Severity.CRITICAL)
    if critical_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
