"""Integration tests: validate fingerprint identity packets for all scenario templates.

Generates a short PCAP for each scenario template, parses it with Scapy,
and validates that every target device emits correct protocol identity responses.

Run with:
    cd backend
    poetry run pytest tests/integration/test_scenario_fingerprints.py -v
    poetry run pytest tests/integration/test_scenario_fingerprints.py -k "manufacturing" -v
    poetry run pytest tests/integration/test_scenario_fingerprints.py -k "siemens" -v
"""

import logging
import sys
from pathlib import Path

import pytest

# Ensure backend root is on path for scripts.lib imports
_backend_dir = str(Path(__file__).parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Suppress noisy scapy warnings
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import rdpcap

from app.protocol_engines.output import PcapOutput
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from scripts.lib.scenario_builder import build_scenario_from_template, list_all_templates
from scripts.lib.pcap_validators import PcapFingerprintValidator

# Collect all templates
ALL_TEMPLATES = list_all_templates()
DURATION_MS = 10_000  # 10 seconds


@pytest.mark.integration
@pytest.mark.parametrize(
    "vertical,template_name",
    ALL_TEMPLATES,
    ids=[f"{v}/{t}" for v, t in ALL_TEMPLATES],
)
def test_scenario_fingerprints(vertical: str, template_name: str, tmp_path: Path):
    """Validate that all devices in a template produce correct identity packets."""

    # Build scenario (no DB)
    range_index = ALL_TEMPLATES.index((vertical, template_name)) + 1
    result = build_scenario_from_template(vertical, template_name, range_index)

    assert result.flow_contexts, f"No flows generated for {template_name}"

    # Generate PCAP
    pcap_path = tmp_path / f"{template_name}.pcap"
    output = PcapOutput(str(pcap_path))
    orch = UnifiedOrchestrator(output=output, duration_ms=DURATION_MS)
    for fc in result.flow_contexts:
        orch.add_flow(fc)
    orch_result = orch.run()
    output.close()

    assert orch_result.error is None, f"Orchestrator error: {orch_result.error}"
    assert orch_result.packets_generated > 0, "No packets generated"

    # Validate fingerprints
    packets = rdpcap(str(pcap_path))
    validator = PcapFingerprintValidator(packets, result.device_expectations)
    reports = validator.validate_all()

    # Collect failures
    failures = []
    for report in reports:
        for check in report.failed_checks:
            failures.append(
                f"  {report.device_name} ({report.device_ip}): "
                f"{check.check_name} — expected='{check.expected}', "
                f"actual='{check.actual}'"
            )

    assert not failures, (
        f"\nFingerprint validation failed for {template_name} "
        f"({len(failures)} failures):\n" + "\n".join(failures)
    )
