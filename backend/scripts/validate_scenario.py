#!/usr/bin/env python3
"""Local fingerprint validation — generate PCAPs from scenario templates
and validate every device's protocol identity packets.

No database, no server, no remote agent required.

Usage:
    cd /home/rocsmith/PacketArch/backend

    # Validate ALL scenario templates
    poetry run python scripts/validate_scenario.py

    # Validate one template
    poetry run python scripts/validate_scenario.py --template siemens_discrete_manufacturing

    # Validate one vertical
    poetry run python scripts/validate_scenario.py --vertical manufacturing

    # Keep PCAPs for Wireshark inspection
    poetry run python scripts/validate_scenario.py --keep-pcaps

    # Show all checks (not just failures)
    poetry run python scripts/validate_scenario.py -v

    # Shorter PCAP duration for faster runs
    poetry run python scripts/validate_scenario.py --duration-ms 5000
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress noisy scapy warnings
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import rdpcap

from app.protocol_engines.ambient.noise_generator import (
    AmbientDevice,
    BackgroundNoiseGenerator,
)
from app.protocol_engines.output import PcapOutput
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator

from scripts.lib.scenario_builder import (
    ScenarioBuildResult,
    build_scenario_from_template,
    list_all_templates,
    list_templates_for_vertical,
)
from scripts.lib.pcap_validators import (
    PcapFingerprintValidator,
    ScenarioValidationReport,
)
from scripts.lib.template_lint import (
    LintIssue,
    errors_only,
    lint_template,
)

# ─────────────────────────────────────────────────────────────────
# Console Formatting
# ─────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# ─────────────────────────────────────────────────────────────────
# Core Functions
# ─────────────────────────────────────────────────────────────────

def validate_template(
    vertical: str,
    template_name: str,
    range_index: int,
    duration_ms: int,
    output_dir: Path,
    keep_pcaps: bool,
    verbose: bool,
) -> ScenarioValidationReport:
    """Validate a single scenario template end-to-end."""

    # ── Build ────────────────────────────────────────────────────
    try:
        result = build_scenario_from_template(vertical, template_name, range_index)
    except Exception as e:
        print(f"  {FAIL} Build failed: {e}")
        return ScenarioValidationReport(
            template_name=template_name,
            vertical=vertical,
            device_count=0,
            flow_count=0,
            pcap_packets=0,
            generation_time_ms=0,
            pcap_path=None,
        )

    n_devices = len(result.devices)
    n_flows = len(result.flow_contexts)
    n_expected = len(result.device_expectations)

    print(f"\n{'=' * 70}")
    print(f" {BOLD}{result.display_name}{RESET}")
    print(f" {n_devices} devices, {n_flows} flows, {n_expected} devices to validate")
    print(f"{'=' * 70}")

    if result.warnings:
        for w in result.warnings:
            print(f"  [{WARN}] {w}")

    if n_flows == 0:
        print(f"  [{WARN}] No flows generated — skipping")
        return ScenarioValidationReport(
            template_name=template_name,
            vertical=vertical,
            device_count=n_devices,
            flow_count=0,
            pcap_packets=0,
            generation_time_ms=0,
            pcap_path=None,
        )

    # ── Generate PCAP ────────────────────────────────────────────
    pcap_path = output_dir / f"{template_name}.pcap"
    t0 = time.monotonic()
    try:
        output = PcapOutput(str(pcap_path))
        orchestrator = UnifiedOrchestrator(
            output=output,
            duration_ms=duration_ms,
        )
        for fc in result.flow_contexts:
            orchestrator.add_flow(fc)

        # Register ambient noise generator so source-only devices
        # get protocol identity discovery (Modbus MEI, EtherNet/IP
        # ListIdentity, S7 SZL, SNMP GET, BACnet Who-Is, PROFINET DCP)
        ambient_devices = _build_ambient_devices(result)
        if ambient_devices:
            noise_gen = BackgroundNoiseGenerator(ambient_devices)
            orchestrator.register_ambient_generator(noise_gen)

        orch_result = orchestrator.run()
        output.close()
        gen_time = (time.monotonic() - t0) * 1000
    except Exception as e:
        print(f"  {FAIL} PCAP generation failed: {e}")
        import traceback
        traceback.print_exc()
        return ScenarioValidationReport(
            template_name=template_name,
            vertical=vertical,
            device_count=n_devices,
            flow_count=n_flows,
            pcap_packets=0,
            generation_time_ms=0,
            pcap_path=None,
        )

    if orch_result.error:
        print(f"  [{WARN}] Orchestrator warning: {orch_result.error}")

    packets_gen = orch_result.packets_generated
    file_size = pcap_path.stat().st_size if pcap_path.exists() else 0
    print(f"  Generated {packets_gen} packets ({file_size:,} bytes) in {gen_time:.0f}ms")

    if packets_gen == 0:
        print(f"  {FAIL} No packets generated — skipping validation")
        return ScenarioValidationReport(
            template_name=template_name,
            vertical=vertical,
            device_count=n_devices,
            flow_count=n_flows,
            pcap_packets=0,
            generation_time_ms=gen_time,
            pcap_path=str(pcap_path),
        )

    # ── Validate ─────────────────────────────────────────────────
    packets = rdpcap(str(pcap_path))

    validator = PcapFingerprintValidator(packets, result.device_expectations)
    device_reports = validator.validate_all()

    # ── Display Results ──────────────────────────────────────────
    for dr in device_reports:
        has_failures = dr.fail_count > 0
        if not has_failures and not verbose:
            continue  # Skip passing devices in non-verbose mode

        proto_str = ", ".join(sorted(dr.protocols_serving))
        print(f"\n  {BOLD}{dr.device_name}{RESET} ({dr.device_ip}, {dr.vendor} {dr.model})")
        print(f"    Target protocols: {proto_str}")

        for check in dr.checks:
            if check.passed and not verbose:
                continue
            status = PASS if check.passed else FAIL
            print(f"    [{status}] {check.check_name}: {check.detail}")

    # Clean up PCAP if not keeping
    if not keep_pcaps and pcap_path.exists():
        pcap_path.unlink()

    report = ScenarioValidationReport(
        template_name=template_name,
        vertical=vertical,
        device_count=n_devices,
        flow_count=n_flows,
        pcap_packets=len(packets),
        generation_time_ms=gen_time,
        pcap_path=str(pcap_path) if keep_pcaps else None,
        device_reports=device_reports,
    )

    return report


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate fingerprint identity packets in scenario templates."
    )
    parser.add_argument(
        "--template", "-t",
        help="Validate a specific template name (e.g., siemens_discrete_manufacturing)",
    )
    parser.add_argument(
        "--vertical",
        help="Validate all templates in a vertical (e.g., manufacturing)",
    )
    parser.add_argument(
        "--duration-ms", type=int, default=10000,
        help="PCAP generation duration in milliseconds (default: 10000)",
    )
    parser.add_argument(
        "--keep-pcaps", action="store_true",
        help="Keep generated PCAP files for manual inspection",
    )
    parser.add_argument(
        "--output-dir", type=str, default="/tmp/validate_scenario",
        help="Output directory for PCAP files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show all checks including passes",
    )
    parser.add_argument(
        "--lint-only", action="store_true",
        help=(
            "Run only the static template linter (no PCAP generation). "
            "Catches protocol-consistency bugs in scenario templates. "
            "Exits non-zero if any errors found."
        ),
    )
    parser.add_argument(
        "--lint", action="store_true",
        help=(
            "Run the static linter in addition to PCAP validation. "
            "Lint errors are reported but do not fail the run."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"{BOLD}{'=' * 70}")
    print(" PacketArch Scenario Fingerprint Validator")
    print(f"{'=' * 70}{RESET}")
    print(f"  Duration: {args.duration_ms}ms | Output: {output_dir}")

    # Determine which templates to validate
    if args.template:
        # Find the vertical for this template
        all_templates = list_all_templates()
        matches = [(v, t) for v, t in all_templates if t == args.template]
        if not matches:
            print(f"\n  {FAIL} Template '{args.template}' not found.")
            print(f"  Available templates:")
            for v, t in all_templates:
                print(f"    {v}/{t}")
            return 1
        templates_to_run = matches
    elif args.vertical:
        tnames = list_templates_for_vertical(args.vertical)
        if not tnames:
            print(f"\n  {FAIL} Vertical '{args.vertical}' not found.")
            return 1
        templates_to_run = [(args.vertical, t) for t in tnames]
    else:
        templates_to_run = list_all_templates()

    print(f"  Templates: {len(templates_to_run)}")

    # ── Static linter (--lint or --lint-only) ────────────────────
    lint_report: dict[str, list[LintIssue]] = {}
    if args.lint or args.lint_only:
        from app.scenario_templates import VERTICAL_TEMPLATES
        for vertical, tname in templates_to_run:
            tpl = VERTICAL_TEMPLATES.get(vertical, {}).get(tname)
            if tpl is None:
                continue
            issues = lint_template(tname, tpl)
            if issues:
                lint_report[f"{vertical}/{tname}"] = issues

        print(f"\n{BOLD}{'─' * 70}")
        print(" STATIC TEMPLATE LINT")
        print(f"{'─' * 70}{RESET}")
        if not lint_report:
            print(f"  {PASS} no lint issues across {len(templates_to_run)} template(s)")
        else:
            total_errors = sum(len(errors_only(v)) for v in lint_report.values())
            total_warnings = sum(
                len(v) - len(errors_only(v)) for v in lint_report.values()
            )
            print(f"  Templates with issues: {len(lint_report)}/{len(templates_to_run)}")
            print(f"  Errors: {total_errors}  Warnings: {total_warnings}\n")
            for tkey, issues in sorted(lint_report.items()):
                err_n = len(errors_only(issues))
                warn_n = len(issues) - err_n
                badge = FAIL if err_n else WARN
                print(f"  [{badge}] {tkey}  ({err_n} errors, {warn_n} warnings)")
                for issue in issues:
                    print(issue.format())
                print()

        if args.lint_only:
            # Exit non-zero only on errors; warnings don't fail the build.
            had_errors = any(errors_only(v) for v in lint_report.values())
            return 1 if had_errors else 0

    # Run validation
    all_reports: list[ScenarioValidationReport] = []
    for idx, (vertical, tname) in enumerate(templates_to_run, start=1):
        report = validate_template(
            vertical=vertical,
            template_name=tname,
            range_index=idx,
            duration_ms=args.duration_ms,
            output_dir=output_dir,
            keep_pcaps=args.keep_pcaps,
            verbose=args.verbose,
        )
        all_reports.append(report)

    # ── Grand Summary ────────────────────────────────────────────
    print(f"\n\n{BOLD}{'=' * 70}")
    print(" GRAND SUMMARY")
    print(f"{'=' * 70}{RESET}")

    total_checks = sum(r.total_checks for r in all_reports)
    total_passed = sum(r.total_passed for r in all_reports)
    total_failed = sum(r.total_failed for r in all_reports)
    templates_passed = sum(1 for r in all_reports if r.all_passed)
    templates_no_packets = sum(
        1 for r in all_reports if r.pcap_packets == 0 and r.flow_count > 0
    )

    print(f"\n  Templates: {len(all_reports)} ({templates_passed} all-pass)")
    print(f"  Total checks: {total_checks}")
    print(f"  {PASS}: {total_passed}")
    print(f"  {FAIL}: {total_failed}")
    if templates_no_packets:
        print(f"  {FAIL} PCAP generation failures: {templates_no_packets} template(s)")

    if total_failed:
        print(f"\n  {BOLD}Failed templates:{RESET}")
        for r in all_reports:
            if not r.all_passed:
                fails = r.total_failed
                print(f"    {r.template_name}: {fails} failure(s)")
                for dr in r.device_reports:
                    for check in dr.failed_checks:
                        print(
                            f"      {dr.device_name} / {check.check_name}: "
                            f"expected={check.expected}, actual={check.actual}"
                        )

    # ── Success Criteria ──────────────────────────────────────────
    # 1. ALL templates must generate PCAPs (non-zero packets)
    # 2. Every device serving a protocol MUST have identity data
    # 3. All identity fields (vendor, model, firmware, serial) validated
    # 4. Zero check failures across all templates
    has_failures = total_failed > 0 or templates_no_packets > 0

    print(f"\n  {BOLD}Success Criteria:{RESET}")
    _crit(templates_no_packets == 0, "All templates generate PCAPs")
    _crit(total_failed == 0, "Zero identity check failures")
    _crit(templates_passed == len(all_reports), "All templates all-pass")
    if args.lint:
        lint_errors = sum(len(errors_only(v)) for v in lint_report.values())
        _crit(lint_errors == 0, f"Static linter clean ({lint_errors} errors)")

    if args.keep_pcaps:
        print(f"\n  PCAPs saved in: {output_dir}/")

    return 0 if not has_failures else 1


def _build_ambient_devices(result: ScenarioBuildResult) -> list[AmbientDevice]:
    """Convert scenario devices into AmbientDevice objects for noise generator."""
    ambient_devices = []
    for did, dev in result.devices.items():
        net = dev.get("network", {})
        ip = net.get("ipAddress", "")
        mac = net.get("macAddress", "")
        if not ip or not mac:
            continue

        # Compute gateway IP from device IP (x.x.x.1)
        parts = ip.rsplit(".", 1)
        gateway = f"{parts[0]}.1" if len(parts) == 2 else None

        fp = dev.get("vendorFingerprint", {})

        ambient_devices.append(AmbientDevice(
            device_id=did,
            mac_address=mac,
            ip_address=ip,
            gateway_ip=gateway,
            protocols=dev.get("protocols", []),
            device_type=dev.get("type", ""),
            vendor=dev.get("vendor", ""),
            device_name=dev.get("name", ""),
            zone_id=dev.get("zone"),
            vendor_fingerprint=fp,
        ))
    return ambient_devices


def _crit(ok: bool, label: str) -> None:
    """Print a success criteria line."""
    status = f"\033[92mPASS\033[0m" if ok else f"\033[91mFAIL\033[0m"
    print(f"    [{status}] {label}")


if __name__ == "__main__":
    sys.exit(main())
