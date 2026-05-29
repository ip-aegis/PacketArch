#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Add snmp_identity to all device templates that are missing it.

This script reads each vendor template file, identifies templates without
snmp_identity, generates appropriate SNMP identity data, and writes the
updated file back.

Run from backend/: python scripts/add_snmp_identity.py
"""
import re
import sys
import os

# Add the backend dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# VENDOR_ENTERPRISE_OIDS mapping (vendor -> PEN OID)
VENDOR_OIDS = {
    "siemens": "1.3.6.1.4.1.4329",
    "rockwell": "1.3.6.1.4.1.53148",
    "schneider": "1.3.6.1.4.1.3833",
    "abb": "1.3.6.1.4.1.26381",
    "emerson": "1.3.6.1.4.1.3530",
    "honeywell": "1.3.6.1.4.1.2879",
    "ge": "1.3.6.1.4.1.3861",
    "yokogawa": "1.3.6.1.4.1.2745",
    "cisco": "1.3.6.1.4.1.9",
    "moxa": "1.3.6.1.4.1.8691",
    "hirschmann": "1.3.6.1.4.1.248",
    "hms": "1.3.6.1.4.1.8284",
    "phoenix_contact": "1.3.6.1.4.1.4346",
    "beckhoff": "1.3.6.1.4.1.2510",
    "wago": "1.3.6.1.4.1.13576",
    "omron": "1.3.6.1.4.1.1103",
    "mitsubishi": "1.3.6.1.4.1.18296",
    "sel": "1.3.6.1.4.1.1027",
    "sick": "1.3.6.1.4.1.1713",
    "advantech": "1.3.6.1.4.1.10297",
    "johnson_controls": "1.3.6.1.4.1.21239",
    "tridium": "1.3.6.1.4.1.18943",
    "trane": "1.3.6.1.4.1.11108",
    "delta_controls": "1.3.6.1.4.1.12412",
    "distech": "1.3.6.1.4.1.37567",
    "kuka": "1.3.6.1.4.1.25882",
    "cognex": "1.3.6.1.4.1.10642",
    "fanuc": "1.3.6.1.4.1.5765",
    "endress_hauser": "1.3.6.1.4.1.8714",
    "keyence": "1.3.6.1.4.1.18943",
    "pepperl_fuchs": "1.3.6.1.4.1.14498",
    "datalogic": "1.3.6.1.4.1.20858",
    "banner": "1.3.6.1.4.1.33692",
    "turck": "1.3.6.1.4.1.14924",
    "ifm": "1.3.6.1.4.1.19448",
    "microsoft": "1.3.6.1.4.1.311",
    "kepware": "1.3.6.1.4.1.49374",
    "matrikon": "1.3.6.1.4.1.49374",
    "dahua": "1.3.6.1.4.1.3808",
    "hikvision": "1.3.6.1.4.1.39165",
    "axis": "1.3.6.1.4.1.368",
    "zebra": "1.3.6.1.4.1.10642",
}

# Vendor-specific sys_descr prefix patterns
VENDOR_SYS_DESCR_PREFIXES = {
    "siemens": {
        "plc": "Siemens SIMATIC",
        "hmi": "Siemens SIMATIC HMI",
        "drive": "Siemens SINAMICS",
        "vfd": "Siemens SINAMICS",
        "io": "Siemens SIMATIC",
        "network_switch": "Siemens",
        "protection_relay": "Siemens SIPROTEC",
        "scada": "Siemens SIMATIC",
        "engineering_station": "Siemens SIMATIC",
        "building_controller": "Siemens Desigo",
        "traffic_controller": "Siemens SITRAFFIC",
        "default": "Siemens",
    },
    "rockwell": {
        "plc": "Rockwell Automation",
        "hmi": "Rockwell Automation",
        "drive": "Rockwell Automation",
        "vfd": "Rockwell Automation",
        "io": "Rockwell Automation",
        "network_switch": "Rockwell Automation",
        "servo": "Rockwell Automation",
        "default": "Rockwell Automation",
    },
    "schneider": {
        "plc": "Schneider Electric",
        "hmi": "Schneider Electric",
        "drive": "Schneider Electric",
        "vfd": "Schneider Electric",
        "io": "Schneider Electric",
        "network_switch": "Schneider Electric",
        "rtu": "Schneider Electric",
        "ups": "Schneider Electric",
        "pdu": "Schneider Electric",
        "default": "Schneider Electric",
    },
    "abb": {
        "default": "ABB",
    },
    "honeywell": {
        "default": "Honeywell",
    },
    "emerson": {
        "default": "Emerson",
    },
    "ge": {
        "default": "GE",
    },
    "yokogawa": {
        "default": "Yokogawa",
    },
    "sel": {
        "default": "Schweitzer Engineering Laboratories",
    },
}

# sys_name abbreviation patterns by vendor
VENDOR_SYS_NAME_PATTERNS = {
    "siemens": lambda model_name, model: f"S7-{model.split()[0] if model else 'DEV'}-001" if "S7" in (model_name or "") else f"SIE-{(model_name or 'DEV').split()[0][:8].upper()}-001",
    "rockwell": lambda model_name, model: f"RA-{(model or model_name or 'DEV').split()[0][:10]}-001",
    "schneider": lambda model_name, model: f"SE-{(model or model_name or 'DEV').split()[0][:10]}-001",
}

# Device type to location mapping
DEVICE_TYPE_LOCATIONS = {
    "plc": "Production Floor",
    "hmi": "Control Room",
    "drive": "Motor Control Center",
    "vfd": "Motor Control Center",
    "io": "Field Cabinet",
    "network_switch": "Network Cabinet",
    "protection_relay": "Substation",
    "rtu": "Remote Site",
    "scada": "Control Room",
    "engineering_station": "Engineering Office",
    "building_controller": "Mechanical Room",
    "traffic_controller": "Intersection Cabinet",
    "gateway": "Network Cabinet",
    "sensor": "Field",
    "transmitter": "Field",
    "analyzer": "Process Area",
    "meter": "Electrical Room",
    "robot": "Production Cell",
    "safety_controller": "Safety Cabinet",
    "safety_plc": "Safety Cabinet",
    "servo": "Machine",
    "remote_access": "Network Cabinet",
    "camera": "Field",
    "ups": "Electrical Room",
    "pdu": "Data Center",
    "cooling": "Data Center",
}


def get_vendor_oid(vendor: str) -> str:
    """Get the enterprise OID for a vendor."""
    key = vendor.lower().replace(" ", "_").replace("-", "_").replace("+", "_")
    if key in VENDOR_OIDS:
        return VENDOR_OIDS[key]
    # Try prefix match
    for vk, oid in VENDOR_OIDS.items():
        if key.startswith(vk) or vk.startswith(key):
            return oid
    return "1.3.6.1.4.1.8072.3.2.10"  # net-snmp fallback


def generate_sys_descr(vendor: str, model_name: str, model: str, device_type: str, firmware: str, vendor_family: str = "", description: str = "") -> str:
    """Generate a human-readable sys_descr string."""
    vendor_lower = vendor.lower()

    # Get vendor-specific prefix
    vendor_prefixes = VENDOR_SYS_DESCR_PREFIXES.get(vendor_lower, {"default": vendor})
    dt_lower = device_type.lower() if device_type else ""
    prefix = vendor_prefixes.get(dt_lower, vendor_prefixes.get("default", vendor))

    # Build sys_descr using model_name (human-readable) rather than model (order number)
    name = model_name or model or "Device"

    # For Siemens, use specific family prefixes
    if vendor_lower == "siemens":
        if "S7-" in (vendor_family or "") or "s7" in (model_name or "").lower():
            prefix = "Siemens SIMATIC"
        elif "SINAMICS" in (vendor_family or "") or "sinamics" in (model_name or "").lower():
            prefix = "Siemens SINAMICS"
            # Remove SINAMICS from name to avoid duplication
            name = name.replace("SINAMICS ", "")
        elif "ET 200" in (model_name or "") or "ET-200" in (vendor_family or "") or "et200" in (vendor_family or "").lower().replace("-", "").replace(" ", ""):
            prefix = "Siemens SIMATIC"
        elif "HMI" in dt_lower or "hmi" in (model_name or "").lower() or any(x in (model_name or "") for x in ["KTP", "TP1", "TP7", "WinCC Unified"]):
            prefix = "Siemens SIMATIC HMI"
        elif "WinCC" in (model_name or ""):
            prefix = "Siemens SIMATIC"
        elif "TIA" in (model_name or ""):
            prefix = "Siemens SIMATIC"
        elif "SIPROTEC" in (vendor_family or "") or "SIPROTEC" in (model_name or ""):
            prefix = "Siemens SIPROTEC"
            # Remove SIPROTEC from name to avoid duplication
            name = name.replace("SIPROTEC ", "")
        elif "Desigo" in (model_name or ""):
            prefix = "Siemens"
        elif "Catalyst IE" in (model_name or ""):
            prefix = "Cisco"

    # Deduplicate: if name starts with a word that's already the last word of prefix
    prefix_last_word = prefix.split()[-1].lower() if prefix else ""
    name_first_word = name.split()[0].lower() if name else ""
    if prefix_last_word and name_first_word and prefix_last_word == name_first_word:
        # e.g., prefix="Siemens SINAMICS" + name="SINAMICS G120" → strip SINAMICS from name
        name = " ".join(name.split()[1:])

    # For vendor names in model_name (e.g., "SICK CLV650" with vendor="SICK")
    if name.lower().startswith(vendor_lower) and len(vendor_lower) >= 3:
        # Don't duplicate vendor if prefix already contains it
        if vendor_lower in prefix.lower():
            name = name[len(vendor):].strip()

    # Construct the sys_descr
    sys_descr = f"{prefix} {name}"

    # Add firmware version
    if firmware:
        # Check if firmware already starts with V
        fw = firmware if firmware.startswith("V") or firmware.startswith("v") else f"V{firmware}"
        sys_descr += f" {fw}"

    return sys_descr


def generate_sys_name(vendor: str, model_name: str, model: str) -> str:
    """Generate a sys_name for SNMP."""
    # Use model_name abbreviated, uppercase, with dashes
    name = model_name or model or "DEVICE"
    # Take first meaningful word(s)
    parts = name.replace("/", "-").replace("_", "-").split()
    if len(parts) >= 2:
        short = f"{parts[0][:6]}-{parts[1][:6]}"
    else:
        short = parts[0][:12]
    return f"{short}-001".upper()


def get_location(device_type: str) -> str:
    """Get typical location for device type."""
    dt = device_type.lower() if device_type else ""
    return DEVICE_TYPE_LOCATIONS.get(dt, "Industrial Network")


def generate_oid_suffix(template_id: str) -> str:
    """Generate a unique OID suffix from template ID using hash."""
    # Create a simple numeric suffix from the template ID
    # Use a hash-based approach for uniqueness
    h = hash(template_id) % 100000
    parts = template_id.split("/")
    if len(parts) >= 3:
        return f"{abs(h) % 1000}.{abs(h) // 1000 % 100}"
    return str(abs(h) % 10000)


def find_templates_without_snmp(content: str):
    """Find all templates in the file that lack snmp_identity."""
    # Find all DeviceTemplate blocks
    templates = []

    # Pattern: DeviceTemplate( followed by id="xxx"
    template_pattern = re.compile(r'    DeviceTemplate\(\s*\n\s+id="([^"]+)"', re.MULTILINE)

    for match in template_pattern.finditer(content):
        template_id = match.group(1)
        start_pos = match.start()

        # Find the end of this template (matching closing paren)
        # We need to count parens
        depth = 0
        end_pos = start_pos
        in_string = False
        string_char = None
        i = content.index('DeviceTemplate(', start_pos)

        for j in range(i, len(content)):
            ch = content[j]
            if in_string:
                if ch == '\\':
                    continue
                if ch == string_char:
                    in_string = False
                continue
            if ch in ('"', "'"):
                # Check for triple quotes
                if content[j:j+3] in ('"""', "'''"):
                    in_string = True
                    string_char = content[j:j+3]
                    continue
                in_string = True
                string_char = ch
                continue
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end_pos = j + 1
                    break

        template_text = content[start_pos:end_pos]
        has_snmp = 'snmp_identity' in template_text

        # Extract model_name
        mn = re.search(r'model_name="([^"]+)"', template_text)
        model_name = mn.group(1) if mn else None

        # Extract model
        md = re.search(r'\n\s+model="([^"]+)"', template_text)
        model = md.group(1) if md else None

        # Extract vendor
        vn = re.search(r'vendor="([^"]+)"', template_text)
        vendor = vn.group(1) if vn else None

        # Extract vendor_family
        vf = re.search(r'vendor_family="([^"]+)"', template_text)
        vendor_family = vf.group(1) if vf else None

        # Extract device_type
        dt = re.search(r'device_type="([^"]+)"', template_text)
        device_type = dt.group(1) if dt else None

        # Extract description
        desc = re.search(r'description="([^"]+)"', template_text)
        description = desc.group(1) if desc else None

        # Extract default firmware version
        fw_match = re.search(r'is_default=True[^)]*?\)', template_text)
        firmware = None
        if fw_match:
            # Find the version in the FirmwareVariant containing is_default=True
            # Look backwards from is_default for version=
            fw_block_end = fw_match.end()
            # Find the FirmwareVariant( that contains this is_default
            fw_start = template_text.rfind('FirmwareVariant(', 0, fw_match.start())
            if fw_start >= 0:
                fw_block = template_text[fw_start:fw_block_end]
                fw_ver = re.search(r'version="([^"]+)"', fw_block)
                if fw_ver:
                    firmware = fw_ver.group(1)

        if not firmware:
            # Try first FirmwareVariant
            fw_ver = re.search(r'version="([^"]+)"', template_text)
            if fw_ver:
                firmware = fw_ver.group(1)

        templates.append({
            'id': template_id,
            'start': start_pos,
            'end': end_pos,
            'has_snmp': has_snmp,
            'model_name': model_name,
            'model': model,
            'vendor': vendor,
            'vendor_family': vendor_family,
            'device_type': device_type,
            'description': description,
            'firmware': firmware,
            'text': template_text,
        })

    return templates


def check_snmp_has_firmware(template: dict) -> bool:
    """Check if existing snmp_identity has firmware version in sys_descr."""
    if not template['has_snmp']:
        return False
    text = template['text']
    snmp_match = re.search(r'snmp_identity\s*=\s*\{([^}]+)\}', text, re.DOTALL)
    if not snmp_match:
        return False
    snmp_block = snmp_match.group(1)
    sys_descr_match = re.search(r'"sys_descr"\s*:\s*"([^"]+)"', snmp_block)
    if not sys_descr_match:
        return False
    sys_descr = sys_descr_match.group(1)
    # Check if firmware version is present
    # Patterns: "V3.0.3", "Version 17.12", "Firmware V3.30", "v4.8", bare "7.82.0127" at end
    has_fw = bool(re.search(r'V\d|Version|Firmware|v\d|\d+\.\d+\.\d+\s*$|\d+\.\d+\s*$', sys_descr))
    return has_fw


def build_snmp_identity_text(template: dict, indent: str = "        ") -> str:
    """Build the snmp_identity dict as a Python code string."""
    vendor = template['vendor'] or "Unknown"
    model_name = template['model_name']
    model = template['model']
    device_type = template['device_type'] or ""
    firmware = template['firmware'] or ""
    vendor_family = template['vendor_family'] or ""
    description = template.get('description') or ""
    template_id = template['id']

    sys_descr = generate_sys_descr(vendor, model_name, model, device_type, firmware, vendor_family, description)

    vendor_oid = get_vendor_oid(vendor)
    oid_suffix = generate_oid_suffix(template_id)
    sys_object_id = f"{vendor_oid}.{oid_suffix}"

    sys_name = generate_sys_name(vendor, model_name, model)
    location = get_location(device_type)

    lines = [
        f'{indent}snmp_identity={{',
        f'{indent}    "sys_descr": "{sys_descr}",',
        f'{indent}    "sys_object_id": "{sys_object_id}",',
        f'{indent}    "sys_name": "{sys_name}",',
        f'{indent}    "sys_location": "{location}",',
        f'{indent}}},',
    ]
    return '\n'.join(lines)


def add_snmp_to_template(content: str, template: dict) -> str:
    """Add snmp_identity to a template that's missing it."""
    template['text']

    # Determine indent — typically 8 spaces for fields
    indent = "        "

    # Find the insertion point: just before the closing ), after the last field
    # We insert after the last identity dict or firmware_variants
    # Look for the last significant field

    # Find the position of the closing ) of the DeviceTemplate
    # It's at template['end'] - 1 (the ) character)
    end_in_content = template['end']

    # Find the last comma before the closing )
    # We need to find the line just before the closing ),
    # Insert our snmp_identity there

    # The closing pattern is typically:
    #     },     <-- last field's closing brace
    # ),         <-- template closing

    # or:
    #         "key": "value",
    #     },
    # ),

    # Let's find the last }, or last value before the template's closing )
    closing_pos = end_in_content - 1  # Position of )

    # Find the newline before the closing )
    last_newline = content.rfind('\n', template['start'], closing_pos)

    # The line at last_newline should be just whitespace + )
    # or it might be the closing of a dict + ),

    # Insert snmp_identity just before this closing line
    snmp_text = build_snmp_identity_text(template, indent)

    # Insert with a blank line before
    insert_pos = last_newline
    insertion = f"\n\n{snmp_text}"

    new_content = content[:insert_pos] + insertion + content[insert_pos:]
    return new_content


def fix_existing_snmp_firmware(content: str, template: dict) -> str:
    """Add firmware version to existing snmp_identity sys_descr if missing."""
    if not template['firmware']:
        return content

    text = template['text']
    start = template['start']

    # Find the sys_descr in the template
    snmp_match = re.search(r'"sys_descr"\s*:\s*"([^"]+)"', text)
    if not snmp_match:
        return content

    old_descr = snmp_match.group(1)

    # Check if firmware is already present
    if re.search(r'V\d|Version|Firmware|v\d', old_descr):
        return content

    # Add firmware version
    fw = template['firmware']
    if not fw.startswith('V') and not fw.startswith('v'):
        fw = f"V{fw}"

    new_descr = f"{old_descr} {fw}"

    # Replace in content (using the absolute position)
    abs_pos = start + snmp_match.start(1)
    abs_end = start + snmp_match.end(1)

    content = content[:abs_pos] + new_descr + content[abs_end:]
    return content


def process_vendor_file(filepath: str, dry_run: bool = False) -> tuple[int, int]:
    """Process a single vendor file, adding snmp_identity where needed.

    Returns (added_count, fixed_count).
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    templates = find_templates_without_snmp(content)

    total = len(templates)
    missing = [t for t in templates if not t['has_snmp']]
    needs_fw_fix = [t for t in templates if t['has_snmp'] and not check_snmp_has_firmware(t)]

    print(f"\n{'='*60}")
    print(f"File: {os.path.basename(filepath)}")
    print(f"Total templates: {total}")
    print(f"Missing snmp_identity: {len(missing)}")
    print(f"Has snmp_identity but missing firmware in sys_descr: {len(needs_fw_fix)}")

    if not missing and not needs_fw_fix:
        print("Nothing to do!")
        return 0, 0

    # Process in reverse order (so positions don't shift)
    # First fix existing ones (these don't change positions much)
    for t in reversed(needs_fw_fix):
        if dry_run:
            sys_descr_match = re.search(r'"sys_descr"\s*:\s*"([^"]+)"', t['text'])
            old = sys_descr_match.group(1) if sys_descr_match else "?"
            fw = t['firmware'] or "?"
            print(f"  FIX: {t['id']} — add '{fw}' to: \"{old}\"")
        else:
            content = fix_existing_snmp_firmware(content, t)

    # Re-parse after firmware fixes to get updated positions
    if not dry_run and needs_fw_fix:
        templates = find_templates_without_snmp(content)
        missing = [t for t in templates if not t['has_snmp']]

    # Add missing snmp_identity (process in reverse to preserve positions)
    for t in reversed(missing):
        if dry_run:
            sys_descr = generate_sys_descr(
                t['vendor'] or "?", t['model_name'], t['model'],
                t['device_type'] or "", t['firmware'] or "", t['vendor_family'] or "",
                t.get('description') or ""
            )
            print(f"  ADD: {t['id']} — \"{sys_descr}\"")
        else:
            content = add_snmp_to_template(content, t)

    if not dry_run and content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Wrote {len(missing)} additions, {len(needs_fw_fix)} fixes")

    return len(missing), len(needs_fw_fix)


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("DRY RUN MODE — no files will be modified\n")

    vendors_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'app', 'services', 'device_templates', 'vendors'
    )

    vendor_files = sorted([
        f for f in os.listdir(vendors_dir)
        if f.endswith('.py') and f != '__init__.py' and not f.startswith('_')
    ])

    total_added = 0
    total_fixed = 0

    for vf in vendor_files:
        filepath = os.path.join(vendors_dir, vf)
        added, fixed = process_vendor_file(filepath, dry_run=dry_run)
        total_added += added
        total_fixed += fixed

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_added} snmp_identity added, {total_fixed} firmware versions fixed")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
