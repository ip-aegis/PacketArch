"""Traffic generator container entrypoint."""

import json
import logging
import os
import signal
import sys

from app.live_orchestrator import (
    DeviceContext,
    FlowContext,
    LiveTrafficOrchestrator,
)

# Global orchestrator reference for signal handling
_orchestrator: LiveTrafficOrchestrator | None = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if _orchestrator:
        _orchestrator.stop()


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_scenario(scenario_json: str) -> dict:
    """Parse scenario JSON from environment variable."""
    try:
        return json.loads(scenario_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scenario JSON: {e}")
        sys.exit(1)


def get_device_fingerprint(device: dict) -> dict:
    """Get the fingerprint for a device.

    The fingerprint is already fully enriched by the backend with:
    - Base vendor fingerprint values
    - CVE vulnerability overrides (firmware versions, etc.)
    - Unique instance identifiers (serial numbers, device_instance, etc.)

    This function simply returns the fingerprint as-is. All enrichment
    happens in the backend's ScenarioDefinitionEnricher before deployment.

    Args:
        device: Device dictionary from scenario

    Returns:
        Fingerprint dictionary (already enriched by backend)
    """
    return (
        device.get("vendorFingerprint") or
        device.get("vendor_fingerprint") or
        {}
    )


def get_vulnerability_override(device: dict) -> dict | None:
    """Get CVE vulnerability override from device.

    The cveIdentityOverrides field contains CVE-specific identity overrides
    that modify protocol responses to include vulnerable firmware versions.
    This data is computed during scenario creation and stored in the device.

    Args:
        device: Device dictionary from scenario

    Returns:
        Vulnerability override dictionary or None
    """
    return device.get("cveIdentityOverrides")


def create_device_context(device_id: str, device: dict) -> DeviceContext:
    """Create a DeviceContext from a device dictionary.

    This is used to create device contexts for ALL devices in the scenario,
    including those that don't appear in any flow. This ensures comprehensive
    device discovery for Cyber Vision.

    Args:
        device_id: The device ID
        device: Device dictionary from scenario

    Returns:
        DeviceContext object
    """
    network = device.get("network", {})
    fingerprint = get_device_fingerprint(device)
    vulnerability_override = get_vulnerability_override(device)

    return DeviceContext(
        device_id=device_id,
        mac_address=network.get("macAddress", "00:00:00:00:00:01"),
        ip_address=network.get("ipAddress", "10.0.0.1"),
        port=502,  # Default port, not used for discovery
        vendor_fingerprint=fingerprint,
        vulnerability_override=vulnerability_override,
    )


def create_flow_from_definition(flow_def: dict, devices: dict) -> FlowContext | None:
    """Create a FlowContext from scenario definition."""
    try:
        source_device = devices.get(flow_def.get("sourceDeviceId"))
        target_device = devices.get(flow_def.get("targetDeviceId"))

        if not source_device or not target_device:
            logger.warning(f"Missing device for flow {flow_def.get('id')}")
            return None

        # Get protocol
        protocol = flow_def.get("protocol", "modbus_tcp")

        # Get network info
        src_network = source_device.get("network", {})
        dst_network = target_device.get("network", {})

        # Get fingerprints and CVE overrides for BOTH source and destination
        # Fingerprints are already enriched by the backend with unique identifiers
        src_fingerprint = get_device_fingerprint(source_device)
        dst_fingerprint = get_device_fingerprint(target_device)
        src_vulnerability = get_vulnerability_override(source_device)
        dst_vulnerability = get_vulnerability_override(target_device)

        # Create device contexts with vendor fingerprints and CVE overrides
        source = DeviceContext(
            device_id=source_device.get("id", ""),
            mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
            ip_address=src_network.get("ipAddress", "10.0.0.1"),
            port=flow_def.get("protocolConfig", {}).get("sourcePort", 50000),
            vendor_fingerprint=src_fingerprint,
            vulnerability_override=src_vulnerability,
        )

        # Get destination port based on protocol
        PROTOCOL_PORTS = {
            "modbus_tcp": 502,
            "modbus": 502,
            "s7comm": 102,
            "s7comm_plus": 102,
            "ethernet_ip": 44818,
            "cip": 44818,
            "bacnet": 47808,
            "bacnet_ip": 47808,
            "snmp": 161,
            "dnp3": 20000,
            "opc_ua": 4840,
            "opcua": 4840,
            "iec104": 2404,
            "iec_104": 2404,
        }
        default_port = PROTOCOL_PORTS.get(protocol, 502)

        destination = DeviceContext(
            device_id=target_device.get("id", ""),
            mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
            ip_address=dst_network.get("ipAddress", "10.0.0.2"),
            port=flow_def.get("protocolConfig", {}).get("port", default_port),
            unit_id=flow_def.get("protocolConfig", {}).get("unitId", 1),
            vendor_fingerprint=dst_fingerprint,
            vulnerability_override=dst_vulnerability,
        )

        # Get timing
        timing = flow_def.get("timing", {})
        timing_model = {
            "poll_interval_ms": timing.get("intervalMs", 1000),
            "jitter_min_ms": timing.get("jitterMs", 0) * -0.5,
            "jitter_max_ms": timing.get("jitterMs", 50) * 0.5,
        }

        return FlowContext(
            flow_id=flow_def.get("id", ""),
            source=source,
            destination=destination,
            protocol=protocol,
            config=flow_def.get("protocolConfig", {}),
            timing_model=timing_model,
        )

    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        return None


def load_scenario() -> dict:
    """Load scenario from file or environment variable."""
    # Check for file-based scenario first (for large scenarios)
    scenario_file = os.environ.get("SCENARIO_FILE", "")
    if scenario_file and os.path.exists(scenario_file):
        logger.info(f"Loading scenario from file: {scenario_file}")
        try:
            with open(scenario_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load scenario from file: {e}")
            sys.exit(1)

    # Fall back to environment variable
    scenario_json = os.environ.get("SCENARIO_JSON", "")
    if scenario_json:
        logger.info("Loading scenario from SCENARIO_JSON environment variable")
        return parse_scenario(scenario_json)

    logger.error("No scenario provided. Set SCENARIO_FILE or SCENARIO_JSON.")
    sys.exit(1)


def main():
    """Main entry point."""
    # Get configuration from environment
    interface = os.environ.get("NETWORK_INTERFACE", "eth0")
    run_mode = os.environ.get("RUN_MODE", "timed")
    deployment_id = os.environ.get("DEPLOYMENT_ID", "unknown")

    # For perpetual mode, duration is None; for timed mode, use DURATION_MS
    if run_mode == "perpetual":
        duration_ms = None
    else:
        duration_ms = int(os.environ.get("DURATION_MS", "60000"))

    logger.info(f"Starting traffic generator")
    logger.info(f"Deployment ID: {deployment_id}")
    logger.info(f"Interface: {interface}")
    logger.info(f"Run mode: {run_mode}")
    logger.info(f"Duration: {'perpetual' if duration_ms is None else f'{duration_ms}ms'}")

    # Load scenario (from file or env var)
    scenario = load_scenario()
    scenario_name = scenario.get("name", "Unknown")
    logger.info(f"Scenario: {scenario_name}")

    # Get definition
    definition = scenario.get("definition", {})
    devices_raw = definition.get("devices", {})
    flows_raw = definition.get("flows", {})

    # Handle both dict and list formats for devices
    if isinstance(devices_raw, dict):
        devices = devices_raw
    elif isinstance(devices_raw, list):
        devices = {d.get("id", str(i)): d for i, d in enumerate(devices_raw)}
    else:
        devices = {}

    # Handle both dict and list formats for flows
    if isinstance(flows_raw, dict):
        flows = flows_raw
    elif isinstance(flows_raw, list):
        flows = {f.get("id", str(i)): f for i, f in enumerate(flows_raw)}
    else:
        flows = {}

    logger.info(f"Found {len(devices)} devices and {len(flows)} flows")

    if not flows:
        logger.warning("No flows defined in scenario")
        sys.exit(0)

    # Create orchestrator
    global _orchestrator
    orchestrator = LiveTrafficOrchestrator(interface, duration_ms)
    _orchestrator = orchestrator  # Set global for signal handling

    # Create DeviceContext for ALL devices in scenario (for comprehensive discovery)
    all_device_contexts = []
    for device_id, device in devices.items():
        device_context = create_device_context(device_id, device)
        all_device_contexts.append(device_context)
    orchestrator.set_all_devices(all_device_contexts)
    logger.info(f"Registered {len(all_device_contexts)} devices for discovery")

    # Add flows
    for flow_id, flow_def in flows.items():
        flow_context = create_flow_from_definition(flow_def, devices)
        if flow_context:
            orchestrator.add_flow(flow_context)

    if not orchestrator.flows:
        logger.error("No valid flows to generate")
        sys.exit(1)

    # Run generation
    try:
        packets_sent = orchestrator.run()
        logger.info(f"Traffic generation complete. Packets sent: {packets_sent}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Traffic generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
