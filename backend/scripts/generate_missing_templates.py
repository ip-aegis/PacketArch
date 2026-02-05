"""Generate DeviceTemplate registration code for fingerprints missing from device_templates.py.

This script directly imports the vendor fingerprint modules without going through
app.__init__ chains, to avoid dependency on scapy/sqlalchemy in the host Python.

Usage:
    cd backend && python3 scripts/generate_missing_templates.py > /tmp/missing_templates.py
"""

import sys
import re
import importlib
import importlib.util
from pathlib import Path
from collections import defaultdict

BACKEND_DIR = Path(__file__).parent.parent

# We need to load vendor_oui.py directly (no app.protocol_engines chain)
# And each vendor fingerprint file directly (no app.services chain)


def load_module_direct(name: str, filepath: Path):
    """Load a Python module directly from file path, bypassing __init__.py chains."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Step 1: Load vendor_oui.py directly (the only import the fingerprint files need)
vendor_oui = load_module_direct(
    "app.protocol_engines.vendor_oui",
    BACKEND_DIR / "app" / "protocol_engines" / "vendor_oui.py",
)

# Expose it as the expected import path
sys.modules["app"] = type(sys)("app")
sys.modules["app.protocol_engines"] = type(sys)("app.protocol_engines")
sys.modules["app.protocol_engines.vendor_oui"] = vendor_oui

# Step 2: Load each vendor fingerprint module
VF_DIR = BACKEND_DIR / "app" / "services" / "vendor_fingerprints"

vendor_modules = {}
for fname in [
    "rockwell", "siemens", "schneider", "specialty", "transportation",
    "building_automation", "energy", "ge", "microsoft", "logistics",
]:
    mod = load_module_direct(f"vfp_{fname}", VF_DIR / f"{fname}.py")
    vendor_modules[fname] = mod


def get_all_layer_a_fingerprints():
    fps = []
    fps.extend(vendor_modules["rockwell"].get_rockwell_fingerprints())
    fps.extend(vendor_modules["siemens"].get_siemens_fingerprints())
    fps.extend(vendor_modules["schneider"].get_schneider_fingerprints())
    fps.extend(vendor_modules["specialty"].get_specialty_fingerprints())
    fps.extend(vendor_modules["transportation"].get_transportation_fingerprints())
    fps.extend(vendor_modules["building_automation"].get_building_automation_fingerprints())
    fps.extend(vendor_modules["energy"].get_energy_fingerprints())
    fps.extend(vendor_modules["ge"].get_ge_fingerprints())
    fps.extend(vendor_modules["microsoft"].get_microsoft_fingerprints())
    fps.extend(vendor_modules["logistics"].get_logistics_fingerprints())
    return fps


def get_all_layer_b_keys():
    """Parse device_templates.py for (vendor, model) keys without importing it."""
    content = (BACKEND_DIR / "app" / "services" / "device_templates.py").read_text()
    keys = set()
    blocks = re.split(r'_register_template\(DeviceTemplate\(', content)
    for block in blocks[1:]:
        vendor_m = re.search(r'vendor="([^"]+)"', block)
        model_m = re.search(r'model="([^"]+)"', block)
        if vendor_m and model_m:
            keys.add((normalize_vendor(vendor_m.group(1)), model_m.group(1).lower().strip()))
    return keys


def normalize_vendor(vendor: str) -> str:
    v = vendor.lower().strip()
    aliases = {
        "schneider electric": "schneider",
        "rockwell automation": "rockwell",
        "allen-bradley": "rockwell",
        "johnson controls": "johnson_controls",
        "distech controls": "distech",
        "delta controls": "delta_controls",
        "automated logic": "automated_logic",
        "endress+hauser": "endress_hauser",
        "mobile industrial robots": "mir",
        "schweitzer engineering": "sel",
        "zebra technologies": "zebra",
    }
    for alias, canonical in aliases.items():
        if alias in v:
            return canonical
    return v


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\-]', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def make_template_id(vendor, family, model):
    return f"{slugify(vendor)}/{slugify(family)}/{slugify(model)}"


def infer_vendor_family(fp):
    model = fp.get("model", "")
    vendor = fp.get("vendor", "").lower()
    existing = fp.get("vendor_family", "")
    if existing:
        return existing

    rules = [
        ("siemens", lambda m: "6ES7 5" in m and "155" not in m, "S7-1500"),
        ("siemens", lambda m: "155" in m and "6ES7" in m, "ET200"),
        ("siemens", lambda m: "6ES7 4" in m, "S7-400"),
        ("siemens", lambda m: "6ES7 3" in m, "S7-300"),
        ("siemens", lambda m: "6ES7 2" in m, "S7-1200"),
        ("siemens", lambda m: "6SL3" in m, "SINAMICS"),
        ("siemens", lambda m: "6GK5" in m, "SCALANCE"),
        ("siemens", lambda m: any(x in m for x in ["CP-8000", "TCS-", "X-200", "XM-400"]), "ITS"),
        ("rockwell", lambda m: m.startswith("1756"), "ControlLogix"),
        ("rockwell", lambda m: m.startswith("1769"), "CompactLogix"),
        ("rockwell", lambda m: m.startswith("1766"), "MicroLogix 1400"),
        ("rockwell", lambda m: m.startswith("1763"), "MicroLogix 1100"),
        ("rockwell", lambda m: "PowerFlex" in m, "PowerFlex"),
        ("schneider", lambda m: "BMEP" in m, "Modicon M580"),
        ("schneider", lambda m: m.startswith("ATV"), "Altivar"),
        ("schneider", lambda m: m.startswith("LXM"), "Lexium"),
        ("schneider", lambda m: m.startswith("HMIG"), "Magelis"),
        ("schneider", lambda m: "MS-CPU" in m, "Modicon"),
        ("schneider", lambda m: m in ("Galaxy VM", "InRow DX", "Rack PDU", "CX9680"), "Data Center"),
        ("schneider", lambda m: "LT2" in m, "Twido"),
        ("ge", lambda m: m.startswith("IC"), "PACSystems"),
        ("ge", lambda m: "Historian" in m, "Proficy"),
        ("microsoft", lambda _: True, "Windows Server"),
    ]

    for vendor_prefix, check, family in rules:
        if vendor_prefix in vendor and check(model):
            return family

    return model.split()[0] if " " in model else model


def infer_device_type(fp):
    model = fp.get("model", "")
    checks = [
        (lambda m: "Jump Server" in m, "server"),
        (lambda m: "Historian" in m or "WCS" in m, "server"),
        (lambda m: any(m.startswith(p) for p in ["1756-L", "1769-L", "1766-L", "1763-L"]), "plc"),
        (lambda m: m.startswith("1756-EN"), "communication_module"),
        (lambda m: "6ES7" in m and "155" in m, "io_module"),
        (lambda m: "6ES7" in m, "plc"),
        (lambda m: any(x in m for x in ["6SL3", "ATV", "PowerFlex", "LXM", "ACS580"]), "drive"),
        (lambda m: any(x in m for x in ["6GK5", "X-200", "Stratix"]), "switch"),
        (lambda m: m.startswith("BMEP"), "plc"),
        (lambda m: m.startswith("HMIG"), "hmi"),
        (lambda m: m.startswith("IC"), "plc"),
        (lambda m: any(x in m for x in ["MiR", "KMP"]), "agv"),
        (lambda m: "FleetManager" in m or "Fleet" in m, "fleet_manager"),
        (lambda m: any(x in m for x in ["DataMan", "CLV"]), "barcode_scanner"),
        (lambda m: "In-Sight" in m, "vision_system"),
        (lambda m: any(x in m for x in ["Speedway", "FX7500", "FX9600"]), "rfid_reader"),
        (lambda m: any(x in m for x in ["MIC IP", "Spectra"]), "camera"),
        (lambda m: "Anybus" in m, "gateway"),
        (lambda m: any(x in m for x in ["Cosy", "Flexy"]), "remote_access"),
        (lambda m: "M2BAX" in m, "motor"),
        (lambda m: any(x in m for x in ["CP-8000", "XM-400", "MS-CPU", "ASC/"]), "traffic_controller"),
        (lambda m: "TCS-" in m, "tunnel_controller"),
        (lambda m: "TrafiSense" in m, "thermal_sensor"),
        (lambda m: "Galaxy VM" in m, "ups"),
        (lambda m: "InRow DX" in m, "crac_unit"),
        (lambda m: "Rack PDU" in m, "pdu"),
        (lambda m: any(x in m for x in ["CX9680", "NAE", "SNC"]), "building_controller"),
        (lambda m: "eBCON" in m, "zone_controller"),
        (lambda m: "ECY-VAV" in m, "vav_controller"),
        (lambda m: any(x in m for x in ["UC600", "ME812U"]), "building_controller"),
        (lambda m: m in ("Server", "Manager"), "building_controller"),
        (lambda m: "Pro Open" in m, "bms_server"),
        (lambda m: any(x in m for x in ["CENTUM", "ProSafe"]), "dcs_controller"),
        (lambda m: any(x in m for x in ["RC400G", "SC450G"]), "rtu"),
        (lambda m: any(x in m for x in ["Promag", "FMP", "FMU"]), "field_instrument"),
        (lambda m: "Pipeline LDS" in m, "leak_detection"),
        (lambda m: any(x in m for x in ["STT850", "UDC", "HC900", "UDA"]), "instrument"),
        (lambda m: "iQ WCS" in m, "wcs_server"),
    ]
    for check, dtype in checks:
        if check(model):
            return dtype
    return "controller"


def fmt_dict(d, indent=8):
    if not d:
        return "{}"
    pad = " " * indent
    inner = " " * (indent + 4)
    lines = ["{"]
    for k, v in d.items():
        if isinstance(v, str):
            v_esc = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{inner}"{k}": "{v_esc}",')
        elif isinstance(v, dict):
            lines.append(f'{inner}"{k}": {fmt_dict(v, indent + 4)},')
        elif isinstance(v, list):
            if not v:
                lines.append(f'{inner}"{k}": [],')
            elif all(isinstance(x, (int, float, str)) for x in v) and len(repr(v)) < 70:
                lines.append(f'{inner}"{k}": {v!r},')
            else:
                lines.append(f'{inner}"{k}": {v!r},')
        elif isinstance(v, bool):
            lines.append(f'{inner}"{k}": {v},')
        elif v is None:
            lines.append(f'{inner}"{k}": None,')
        else:
            lines.append(f'{inner}"{k}": {v!r},')
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def generate_template_code(fp):
    vendor = fp.get("vendor", "Unknown")
    model = fp.get("model", "Unknown")
    vendor_family = infer_vendor_family(fp)
    device_type = infer_device_type(fp)
    template_id = make_template_id(vendor, vendor_family, model)

    oui = fp.get("oui_prefixes", [])
    tcp = fp.get("tcp_stack", {})
    timing = fp.get("response_timing", {})
    error = fp.get("error_behavior", {})
    quirks = fp.get("protocol_quirks", {})

    supported = []
    for p in ["modbus", "ethernet_ip", "profinet", "s7", "bacnet", "snmp", "opc_ua"]:
        if fp.get(f"{p}_identity"):
            supported.append(p)

    fw = fp.get("firmware_version", "1.0") or "1.0"

    lines = [
        f'_register_template(DeviceTemplate(',
        f'    id="{template_id}",',
        f'    vendor="{vendor}",',
        f'    vendor_family="{vendor_family}",',
        f'    model="{model}",',
        f'    model_name="{model}",',
        f'    device_type="{device_type}",',
        f'    description="{vendor} {model}",',
        f'    oui_prefixes={oui!r},',
        f'    tcp_stack={fmt_dict(tcp)},',
        f'    response_timing={fmt_dict(timing)},',
    ]

    if error:
        lines.append(f'    error_behavior={fmt_dict(error)},')
    if supported:
        lines.append(f'    supported_protocols={supported!r},')
    if quirks:
        lines.append(f'    protocol_quirks={fmt_dict(quirks)},')

    lines.extend([
        f'    firmware_variants=[FirmwareVariant(',
        f'        version="{fw}",',
        f'        release_date=date(2024, 1, 1),',
        f'        is_default=True,',
        f'        is_latest=True,',
        f'    )],',
    ])

    for p in ["modbus", "ethernet_ip", "profinet", "s7", "bacnet", "snmp", "opc_ua"]:
        identity = fp.get(f"{p}_identity")
        if identity:
            lines.append(f'    {p}_identity={fmt_dict(identity)},')

    lines.append(f'))')
    lines.append('')
    return "\n".join(lines)


def main():
    layer_a = get_all_layer_a_fingerprints()
    layer_b_keys = get_all_layer_b_keys()

    print(f"# Layer A: {len(layer_a)} fingerprints", file=sys.stderr)
    print(f"# Layer B: {len(layer_b_keys)} templates", file=sys.stderr)

    missing = []
    for fp in layer_a:
        v = normalize_vendor(fp.get("vendor", ""))
        m = fp.get("model", "").lower().strip()
        if (v, m) not in layer_b_keys:
            missing.append(fp)

    print(f"# Missing: {len(missing)} fingerprints", file=sys.stderr)

    print(f"# Auto-generated DeviceTemplate entries for {len(missing)} fingerprints")
    print(f"# missing from device_templates.py (originally in vendor_fingerprints/)")
    print()

    by_vendor = defaultdict(list)
    for fp in missing:
        by_vendor[fp.get("vendor", "Unknown")].append(fp)

    for vendor in sorted(by_vendor.keys()):
        print(f"\n# --- {vendor} ({len(by_vendor[vendor])} entries) ---\n")
        for fp in sorted(by_vendor[vendor], key=lambda x: x.get("model", "")):
            print(generate_template_code(fp))


if __name__ == "__main__":
    main()
