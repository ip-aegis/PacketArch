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


def create_flow_from_definition(flow_def: dict, devices: dict) -> FlowContext | None:
    """Create a FlowContext from scenario definition."""
    try:
        source_device = devices.get(flow_def.get("sourceDeviceId"))
        target_device = devices.get(flow_def.get("targetDeviceId"))

        if not source_device or not target_device:
            logger.warning(f"Missing device for flow {flow_def.get('id')}")
            return None

        # Get network info
        src_network = source_device.get("network", {})
        dst_network = target_device.get("network", {})

        # Create device contexts
        source = DeviceContext(
            device_id=source_device.get("id", ""),
            mac_address=src_network.get("macAddress", "00:00:00:00:00:01"),
            ip_address=src_network.get("ipAddress", "10.0.0.1"),
            port=flow_def.get("protocolConfig", {}).get("sourcePort", 50000),
        )

        # Get destination port based on protocol
        protocol = flow_def.get("protocol", "modbus_tcp")
        default_port = 502 if protocol == "modbus_tcp" else 44818

        destination = DeviceContext(
            device_id=target_device.get("id", ""),
            mac_address=dst_network.get("macAddress", "00:00:00:00:00:02"),
            ip_address=dst_network.get("ipAddress", "10.0.0.2"),
            port=flow_def.get("protocolConfig", {}).get("port", default_port),
            unit_id=flow_def.get("protocolConfig", {}).get("unitId", 1),
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
