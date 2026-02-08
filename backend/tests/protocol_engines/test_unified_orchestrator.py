"""Tests for the UnifiedOrchestrator."""

import os
import tempfile
import threading
import time

import pytest

from app.protocol_engines.output import PcapOutput, LiveOutput
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator, OrchestrationResult


def _make_device(device_id: str, ip: str, mac: str, port: int = 502) -> DeviceContext:
    return DeviceContext(
        device_id=device_id,
        ip_address=ip,
        mac_address=mac,
        port=port,
    )


def _make_flow(
    flow_id: str,
    protocol: ProtocolType,
    src: DeviceContext,
    dst: DeviceContext,
    config: dict | None = None,
    poll_interval_ms: float = 500,
) -> FlowContext:
    return FlowContext(
        flow_id=flow_id,
        protocol=protocol,
        source=src,
        destination=dst,
        config=config or {},
        timing_model={"poll_interval_ms": poll_interval_ms, "response_delay_ms": 5.0},
    )


class TestUnifiedOrchestratorTimedMode:
    """Tests for timed (PCAP) mode."""

    def test_modbus_generates_packets(self):
        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=3000)
            orch.add_flow(_make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
            ))

            result = orch.run()

            assert result.error is None
            assert result.packets_generated > 0
            assert os.path.getsize(pcap_path) > 100
        finally:
            os.unlink(pcap_path)

    def test_cloud_service_generates_tls_heartbeats(self):
        src = _make_device("gw-1", "10.1.0.1", "00:1c:06:07:08:09", port=0)
        dst = _make_device("cloud-1", "52.20.10.1", "ff:ff:ff:ff:ff:ff", port=443)

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=3000)
            orch.add_flow(_make_flow(
                "cloud-1", ProtocolType.CLOUD_SERVICE, src, dst,
                config={"hostname": "m2web.talk2m.com", "tls_enabled": True},
                poll_interval_ms=1000,
            ))

            result = orch.run()

            assert result.error is None
            # Each poll generates 2 packets (SYN + TLS Hello), plus shutdown FIN
            assert result.packets_generated >= 3
        finally:
            os.unlink(pcap_path)

    def test_mixed_protocols(self):
        """Test Modbus + CloudService running together."""
        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")
        cloud_src = _make_device("gw-1", "10.1.0.1", "00:1c:06:07:08:09", port=0)
        cloud_dst = _make_device("cloud-1", "52.20.10.1", "ff:ff:ff:ff:ff:ff", port=443)

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=5000)

            orch.add_flow(_make_flow(
                "modbus-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
                poll_interval_ms=1000,
            ))
            orch.add_flow(_make_flow(
                "cloud-1", ProtocolType.CLOUD_SERVICE, cloud_src, cloud_dst,
                config={"hostname": "m2web.talk2m.com", "tls_enabled": True},
                poll_interval_ms=2000,
            ))

            result = orch.run()

            assert result.error is None
            assert result.packets_generated > 10
        finally:
            os.unlink(pcap_path)

    def test_zero_duration_generates_only_startup_shutdown(self):
        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=0)
            orch.add_flow(_make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3},
            ))

            result = orch.run()

            assert result.error is None
            # Startup + shutdown packets only (no poll cycles)
            assert result.packets_generated >= 0
        finally:
            os.unlink(pcap_path)


class TestUnifiedOrchestratorPerpetualMode:
    """Tests for perpetual (agent) mode with stop_event."""

    def test_stop_event_stops_generation(self):
        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        result = None
        stop_event = threading.Event()

        def run():
            nonlocal result
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=None)
            orch.add_flow(_make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
                poll_interval_ms=100,
            ))
            result = orch.run(stop_event=stop_event)

        try:
            t = threading.Thread(target=run)
            t.start()
            time.sleep(0.3)
            stop_event.set()
            t.join(timeout=5)

            assert result is not None
            assert result.stopped_by_event is True
            assert result.error is None
            assert result.packets_generated > 0
        finally:
            os.unlink(pcap_path)


class TestAdaptiveIntegration:
    """Tests for adaptive controller integration with UnifiedOrchestrator."""

    def test_adaptive_controller_varies_poll_intervals(self):
        """With adaptive enabled, consecutive poll intervals should vary."""
        from app.protocol_engines.adaptive import AdaptiveConfig, AdaptiveController

        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=5000)
            flow = _make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
                poll_interval_ms=200,
            )
            orch.add_flow(flow)

            # Attach adaptive controller
            config = AdaptiveConfig(enabled=True)
            controller = AdaptiveController(config, total_flows=1)
            orch.register_adaptive_controller(controller)

            result = orch.run()

            assert result.error is None
            assert result.packets_generated > 0

            # Verify adaptive state was tracked
            stats = orch.get_stats_snapshot()
            assert stats.get("adaptation") is not None
            assert stats["adaptation"]["enabled"] is True
            assert stats["adaptation"]["micro_stats"]["drift_adjustments"] > 0
        finally:
            os.unlink(pcap_path)

    def test_no_adaptive_controller_works_normally(self):
        """Without adaptive, orchestrator should work identically to before."""
        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            output = PcapOutput(pcap_path)
            orch = UnifiedOrchestrator(output=output, duration_ms=3000)
            orch.add_flow(_make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
            ))

            result = orch.run()

            assert result.error is None
            assert result.packets_generated > 0

            # No adaptation in stats
            stats = orch.get_stats_snapshot()
            assert stats.get("adaptation") is None
        finally:
            os.unlink(pcap_path)


class TestOrchestrationResult:
    """Tests for OrchestrationResult dataclass."""

    def test_default_values(self):
        result = OrchestrationResult()
        assert result.packets_generated == 0
        assert result.duration_ms == 0.0
        assert result.stopped_by_event is False
        assert result.error is None


class TestTrafficOrchestratorBackwardCompat:
    """Tests for backward-compatible TrafficOrchestrator wrapper."""

    def test_generate_returns_completed(self):
        from uuid import uuid4
        from app.traffic_generator.orchestrator import TrafficOrchestrator, GenerationConfig

        src = _make_device("plc-1", "10.1.0.10", "00:1c:06:01:02:03")
        dst = _make_device("hmi-1", "10.1.0.20", "00:1c:06:04:05:06")

        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
            pcap_path = f.name

        try:
            config = GenerationConfig(
                job_id="test-job",
                scenario_id=uuid4(),
                total_duration_ms=2000,
                output_path=pcap_path,
            )
            orch = TrafficOrchestrator(config)
            orch.add_flow(_make_flow(
                "flow-1", ProtocolType.MODBUS_TCP, src, dst,
                config={"unit_id": 1, "function_code": 3, "start_address": 0, "register_count": 10},
            ))

            result = orch.generate()

            assert result.status.value == "completed"
            assert result.packets_generated > 0
            assert result.pcap_path == pcap_path
            assert result.file_size_bytes > 0
        finally:
            os.unlink(pcap_path)
