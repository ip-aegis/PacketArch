"""Traffic generator container entrypoint."""

import copy
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


def build_device_fingerprint(device: dict, protocol: str) -> dict:
    """Build enriched fingerprint for a device, merging CVE overrides.

    Args:
        device: Device dictionary from scenario
        protocol: Protocol being used (for context-specific enrichment)

    Returns:
        Enriched fingerprint dictionary
    """
    # Get base fingerprint
    fingerprint = copy.deepcopy(
        device.get("vendor_fingerprint") or
        device.get("vendorFingerprint") or
        {}
    )

    # Merge CVE identity overrides (all protocol identity types)
    cve_overrides = device.get("cveIdentityOverrides", {})
    if cve_overrides:
        logger.info(f"Device {device.get('name')}: Merging CVE overrides: {list(cve_overrides.keys())}")
        for key in [
            "modbus_identity", "ethernet_ip_identity", "profinet_identity",
            "cip_identity_object", "bacnet_identity", "snmp_identity", "s7_identity"
        ]:
            if key in cve_overrides:
                if key in fingerprint and isinstance(fingerprint[key], dict):
                    fingerprint[key].update(cve_overrides[key])
                else:
                    fingerprint[key] = cve_overrides[key]
                logger.info(f"  Merged {key}: {fingerprint[key]}")

    # Enrich fingerprint with device info for protocol identity fields
    device_name = device.get("name", "")
    fingerprint_model = device.get("fingerprintModel", "")
    vendor = device.get("vendor", "")

    # PROFINET: Ensure station_name is set (critical for Cyber Vision detection)
    if "profinet_identity" in fingerprint or protocol in ("profinet", "profisafe"):
        if "profinet_identity" not in fingerprint:
            fingerprint["profinet_identity"] = {}
        pn_id = fingerprint["profinet_identity"]
        if not pn_id.get("station_name"):
            station = device_name.lower().replace(" ", "-").replace("_", "-") if device_name else None
            if station:
                pn_id["station_name"] = station
                logger.debug(f"Generated PROFINET station_name '{station}' from device name")

    # EtherNet/IP: Ensure product_name is set
    if "ethernet_ip_identity" in fingerprint or protocol == "ethernet_ip":
        if "ethernet_ip_identity" not in fingerprint:
            fingerprint["ethernet_ip_identity"] = {}
        eip_id = fingerprint["ethernet_ip_identity"]
        if not eip_id.get("product_name"):
            product = fingerprint_model or device_name
            if product:
                eip_id["product_name"] = product
                logger.debug(f"Generated EtherNet/IP product_name '{product}' from device info")

    # Modbus: Ensure vendor_name and product_code are set
    if "modbus_identity" in fingerprint or protocol == "modbus_tcp":
        if "modbus_identity" not in fingerprint:
            fingerprint["modbus_identity"] = {}
        mb_id = fingerprint["modbus_identity"]
        if not mb_id.get("vendor_name") and vendor:
            mb_id["vendor_name"] = vendor.title()
        if not mb_id.get("product_code") and fingerprint_model:
            mb_id["product_code"] = fingerprint_model

    return fingerprint


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

        # Build fingerprints for BOTH source and destination (for discovery)
        src_fingerprint = build_device_fingerprint(source_device, protocol)
        dst_fingerprint = build_device_fingerprint(target_device, protocol)

        # Create device contexts with vendor fingerprints for device identification
        source = DeviceContext(
            device_id=source_device.get("id", ""),
            mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
            ip_address=src_network.get("ipAddress", "10.0.0.1"),
            port=flow_def.get("protocolConfig", {}).get("sourcePort", 50000),
            vendor_fingerprint=src_fingerprint,
        )

        # Get destination port based on protocol
        PROTOCOL_PORTS = {
            "modbus_tcp": 502,
            "s7comm": 102,
            "s7comm_plus": 102,
            "ethernet_ip": 44818,
            "bacnet_ip": 47808,
            "dnp3": 20000,
            "opcua": 4840,
            "iec104": 2404,
        }
        default_port = PROTOCOL_PORTS.get(protocol, 44818)

        destination = DeviceContext(
            device_id=target_device.get("id", ""),
            mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
            ip_address=dst_network.get("ipAddress", "10.0.0.2"),
            port=flow_def.get("protocolConfig", {}).get("port", default_port),
            unit_id=flow_def.get("protocolConfig", {}).get("unitId", 1),
            vendor_fingerprint=dst_fingerprint,
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
    devices = definition.get("devices", {})
    flows = definition.get("flows", {})

    logger.info(f"Found {len(devices)} devices and {len(flows)} flows")

    if not flows:
        logger.warning("No flows defined in scenario")
        sys.exit(0)

    # Create orchestrator
    global _orchestrator
    orchestrator = LiveTrafficOrchestrator(interface, duration_ms)
    _orchestrator = orchestrator  # Set global for signal handling

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
