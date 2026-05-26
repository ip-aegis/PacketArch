# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Render a scenario into a print-ready PDF report.

The report is meant for hand-off, archival, and customer-facing
documentation: a structured, well-formatted reference for what a
scenario actually contains (IP plan, zones, devices, flows, conduits,
modes). Layout is built with ReportLab Platypus flowables — pure
Python, no system-library dependencies.

Entry point: :func:`build_scenario_pdf`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ─── Brand palette ────────────────────────────────────────────────────
# Cyan accent on near-black panels, white text. Mirrors the platform's
# dark theme but tuned so it reads well on paper (light background) too.
BRAND_CYAN = colors.HexColor("#049FD9")
BRAND_CYAN_DARK = colors.HexColor("#0277A8")
BRAND_NAVY = colors.HexColor("#16213e")
BRAND_INK = colors.HexColor("#0b1020")
GREY_TEXT = colors.HexColor("#3b3f47")
GREY_LIGHT = colors.HexColor("#e6e9ef")
GREY_BORDER = colors.HexColor("#c5cad3")
ROW_ZEBRA = colors.HexColor("#f4f6fa")


def _styles() -> dict[str, ParagraphStyle]:
    """Build the paragraph style sheet for the report."""
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {}

    s["TitleBig"] = ParagraphStyle(
        name="TitleBig",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=BRAND_INK,
        leading=32,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    s["Subtitle"] = ParagraphStyle(
        name="Subtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=12,
        textColor=BRAND_CYAN_DARK,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=12,
    )
    s["SectionH"] = ParagraphStyle(
        name="SectionH",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=BRAND_NAVY,
        leading=18,
        spaceBefore=16,
        spaceAfter=8,
        borderPadding=0,
    )
    s["Body"] = ParagraphStyle(
        name="Body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=GREY_TEXT,
        leading=14,
        spaceAfter=6,
    )
    s["BodyBold"] = ParagraphStyle(
        name="BodyBold",
        parent=s["Body"],
        fontName="Helvetica-Bold",
        textColor=BRAND_INK,
    )
    s["Cell"] = ParagraphStyle(
        name="Cell",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=GREY_TEXT,
        leading=11,
    )
    s["CellMono"] = ParagraphStyle(
        name="CellMono",
        parent=s["Cell"],
        fontName="Courier",
        fontSize=9,
        textColor=BRAND_INK,
    )
    s["CellBold"] = ParagraphStyle(
        name="CellBold",
        parent=s["Cell"],
        fontName="Helvetica-Bold",
        textColor=BRAND_INK,
    )
    s["Footer"] = ParagraphStyle(
        name="Footer",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#6b6b8a"),
        alignment=TA_CENTER,
    )
    s["PageNum"] = ParagraphStyle(
        name="PageNum",
        parent=s["Footer"],
        alignment=TA_RIGHT,
    )
    return s


# ─── Helpers ──────────────────────────────────────────────────────────


def _humanize_protocol(p: str) -> str:
    """Pretty-print a protocol identifier (modbus_tcp → Modbus TCP)."""
    overrides = {
        "modbus_tcp": "Modbus TCP",
        "ethernet_ip": "EtherNet/IP",
        "s7comm": "S7comm",
        "s7comm_plus": "S7comm+",
        "profinet": "PROFINET",
        "profisafe": "PROFIsafe",
        "bacnet": "BACnet/IP",
        "bacnet_ip": "BACnet/IP",
        "snmp": "SNMP",
        "opc_ua": "OPC UA",
        "dnp3": "DNP3",
        "iec104": "IEC 60870-5-104",
        "cip_safety": "CIP Safety",
    }
    return overrides.get(p, p.replace("_", " ").upper())


def _humanize_vertical(v: str | None) -> str:
    if not v:
        return "Unspecified"
    return v.replace("_", " ").title()


def _ms_to_human(ms: int | None) -> str:
    if not ms:
        return "—"
    if ms < 1000:
        return f"{ms} ms"
    s = ms / 1000.0
    if s < 60:
        return f"{s:g} s"
    m = s / 60.0
    if m < 60:
        return f"{m:g} min"
    h = m / 60.0
    return f"{h:.1f} h"


def _ts(dt: Any) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        return dt
    try:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(dt)


def _join(values: Iterable[str], sep: str = ", ", fallback: str = "—") -> str:
    items = [v for v in values if v]
    return sep.join(items) if items else fallback


def _draw_page_decoration(canvas, doc, *, scenario_name: str) -> None:
    """Draw the cyan accent strip + footer on every page."""
    width, height = doc.pagesize
    canvas.saveState()
    # Top accent strip
    canvas.setFillColor(BRAND_CYAN)
    canvas.rect(0, height - 0.18 * inch, width, 0.18 * inch, fill=1, stroke=0)
    # Footer line
    canvas.setStrokeColor(GREY_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(0.6 * inch, 0.55 * inch, width - 0.6 * inch, 0.55 * inch)
    # Footer text
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b6b8a"))
    canvas.drawString(
        0.6 * inch, 0.38 * inch,
        f"PacketArch Scenario Report  ·  {scenario_name}",
    )
    canvas.drawRightString(
        width - 0.6 * inch, 0.38 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


# ─── Builders ─────────────────────────────────────────────────────────


def _summary_grid(
    styles: dict[str, ParagraphStyle],
    *,
    device_count: int,
    flow_count: int,
    zone_count: int,
    conduit_count: int,
    duration_ms: int | None,
    ip_range: str | None,
) -> Table:
    """Six-cell KPI grid that sits under the title."""
    cells = [
        ("Devices", str(device_count)),
        ("Flows", str(flow_count)),
        ("Zones", str(zone_count)),
        ("Conduits", str(conduit_count)),
        ("Duration", _ms_to_human(duration_ms)),
        ("IP Range", ip_range or "Not allocated"),
    ]
    label_style = ParagraphStyle(
        "kpi_label", fontName="Helvetica", fontSize=8,
        textColor=colors.HexColor("#6b6b8a"),
        alignment=TA_CENTER, leading=10,
    )
    value_style = ParagraphStyle(
        "kpi_value", fontName="Helvetica-Bold", fontSize=14,
        textColor=BRAND_INK, alignment=TA_CENTER, leading=18,
    )

    rows = [[
        [Paragraph(value, value_style), Paragraph(label.upper(), label_style)]
        for label, value in cells
    ]]
    col_w = 6.7 * inch / len(cells)
    t = Table(rows, colWidths=[col_w] * len(cells), rowHeights=[0.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GREY_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _section_header(styles: dict[str, ParagraphStyle], title: str) -> Paragraph:
    return Paragraph(title, styles["SectionH"])


def _table_with_header(
    *, header: list[str], rows: list[list], col_widths: list[float],
) -> Table:
    """Build a standard zebra-striped data table with cyan header row."""
    data = [header] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_CYAN),
        ("LEFTPADDING", (0, 0), (-1, 0), 6),
        ("RIGHTPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, GREY_BORDER),
        ("LEFTPADDING", (0, 1), (-1, -1), 6),
        ("RIGHTPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ])
    # Zebra striping
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), ROW_ZEBRA)
    t.setStyle(style)
    return t


def _modes_paragraph(
    styles: dict[str, ParagraphStyle], definition: dict
) -> Paragraph:
    """Summarize scenario-level mode flags as a one-paragraph callout."""
    parts = []
    if definition.get("clean_demo_mode"):
        parts.append(
            "<b>Clean Demo Mode</b> is ON — cyclic protocol traffic that creates "
            "phantom components in DPI tools is suppressed."
        )
    else:
        parts.append("<b>Clean Demo Mode</b> is OFF — full protocol traffic.")

    if definition.get("broadcast_traffic_enabled", True):
        parts.append(
            "<b>Broadcast / multicast ambient traffic</b> is ON — ARP, NTP, "
            "LLDP, STP, CDP, DHCP, IGMP, BACnet Who-Is, PROFINET DCP, and SNMP "
            "traps are emitted alongside the named flows."
        )
    else:
        parts.append("<b>Broadcast / multicast ambient traffic</b> is OFF.")

    ci = (definition.get("cell_isolation") or {}).get("mode", "off")
    if ci == "strict":
        parts.append(
            "<b>Cell isolation</b> is <b>strict</b> — cross-cell flows without an "
            "explicit conduit are dropped at the agent."
        )
    elif ci == "relaxed":
        parts.append(
            "<b>Cell isolation</b> is <b>relaxed</b> — non-compliant cross-cell "
            "flows are warned but still ship."
        )
    else:
        parts.append("<b>Cell isolation</b> is OFF.")

    return Paragraph("<br/><br/>".join(parts), styles["Body"])


# ─── Public entry point ───────────────────────────────────────────────


def build_scenario_pdf(scenario) -> bytes:
    """Render ``scenario`` to a PDF and return the raw bytes.

    ``scenario`` is expected to be the SQLAlchemy ``Scenario`` model
    instance (or any object exposing ``name``, ``description``,
    ``vertical``, ``total_duration_ms``, ``definition``, ``addressing_config``,
    ``created_at``, ``updated_at``).
    """
    styles = _styles()
    definition: dict = dict(scenario.definition or {})
    devices: dict = definition.get("devices") or {}
    flows: dict = definition.get("flows") or {}
    zones: dict = definition.get("zones") or {}
    conduits: dict = definition.get("conduits") or {}

    addressing = scenario.addressing_config or {}
    ip_range = addressing.get("ip_range") if isinstance(addressing, dict) else None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.8 * inch,
        title=f"PacketArch Scenario — {scenario.name}",
        author="PacketArch",
        subject="OT Scenario Report",
    )
    story: list = []

    # ── Title block ────────────────────────────────────────────────
    story.append(Paragraph(scenario.name, styles["TitleBig"]))
    subtitle_bits = [
        _humanize_vertical(scenario.vertical),
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    story.append(Paragraph(" &nbsp;·&nbsp; ".join(subtitle_bits), styles["Subtitle"]))

    if scenario.description:
        story.append(Paragraph(scenario.description, styles["Body"]))
        story.append(Spacer(1, 0.05 * inch))

    # ── KPI grid ────────────────────────────────────────────────────
    story.append(_summary_grid(
        styles,
        device_count=len(devices),
        flow_count=len(flows),
        zone_count=len(zones),
        conduit_count=len(conduits),
        duration_ms=scenario.total_duration_ms,
        ip_range=ip_range,
    ))
    story.append(Spacer(1, 0.15 * inch))

    # ── Metadata table ─────────────────────────────────────────────
    meta_rows = [
        ["Scenario ID", Paragraph(str(scenario.id), styles["CellMono"])],
        ["Vertical", _humanize_vertical(scenario.vertical)],
        ["Created", _ts(scenario.created_at)],
        ["Last Modified", _ts(scenario.updated_at)],
    ]
    if ip_range:
        meta_rows.append(["IP Range", Paragraph(ip_range, styles["CellMono"])])
    meta_table = Table(meta_rows, colWidths=[1.6 * inch, 5.1 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_INK),
        ("TEXTCOLOR", (1, 0), (1, -1), GREY_TEXT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)

    # ── Modes block ────────────────────────────────────────────────
    story.append(_section_header(styles, "Modes &amp; Behaviour"))
    story.append(_modes_paragraph(styles, definition))

    # ── Zones table ────────────────────────────────────────────────
    story.append(_section_header(styles, "Zones &amp; IP Plan"))
    if zones:
        # Build device-count by zone from the device dict
        dev_per_zone: dict[str, int] = {}
        for d in devices.values():
            zid = d.get("zoneId") or d.get("zone_id")
            if zid:
                dev_per_zone[zid] = dev_per_zone.get(zid, 0) + 1

        type_labels = {
            "vertical": "Vertical",
            "network": "Network",
            "vlan": "VLAN",
            "logical": "Logical",
        }

        sorted_zones = sorted(
            zones.values(),
            key=lambda z: (z.get("level") if z.get("level") is not None else 99, z.get("name") or ""),
        )

        rows = []
        for z in sorted_zones:
            net = (z.get("network") or {})
            subnet = net.get("subnet") or z.get("subnet") or "—"
            vlan = net.get("vlanId") or z.get("vlan") or z.get("vlanId")
            gw = net.get("gateway") or "—"
            lvl = z.get("level")
            rows.append([
                Paragraph(z.get("name") or z.get("id") or "—", styles["CellBold"]),
                f"L{lvl}" if isinstance(lvl, (int, float)) else "—",
                type_labels.get(z.get("type") or "", z.get("type") or "—"),
                Paragraph(subnet, styles["CellMono"]),
                str(vlan) if vlan is not None else "—",
                Paragraph(gw, styles["CellMono"]),
                str(dev_per_zone.get(z.get("id"), 0)),
            ])
        story.append(_table_with_header(
            header=["Zone", "Purdue", "Type", "Subnet", "VLAN", "Gateway", "Devices"],
            rows=rows,
            col_widths=[1.5 * inch, 0.55 * inch, 0.7 * inch, 1.5 * inch, 0.55 * inch, 1.3 * inch, 0.6 * inch],
        ))
    else:
        story.append(Paragraph("No zones defined.", styles["Body"]))

    # ── Devices table ──────────────────────────────────────────────
    story.append(_section_header(styles, "Devices"))
    if devices:
        # Order: by zone (Purdue level), then by name
        zone_level_lookup = {
            zid: (z.get("level") if z.get("level") is not None else 99)
            for zid, z in zones.items()
        }
        zone_name_lookup = {zid: z.get("name") or zid for zid, z in zones.items()}

        sorted_devices = sorted(
            devices.values(),
            key=lambda d: (
                zone_level_lookup.get(d.get("zoneId") or d.get("zone_id") or "", 99),
                (d.get("name") or "").lower(),
            ),
        )

        rows = []
        for d in sorted_devices:
            net = d.get("network") or {}
            protos = d.get("protocols") or []
            vendor = (d.get("vendor") or "").strip() or "—"
            model = (
                d.get("fingerprintModel")
                or d.get("fingerprint_model")
                or d.get("model")
                or "—"
            )
            zid = d.get("zoneId") or d.get("zone_id")
            rows.append([
                Paragraph(d.get("name") or d.get("id") or "—", styles["CellBold"]),
                Paragraph((d.get("type") or "—").upper(), styles["Cell"]),
                Paragraph(
                    f"{vendor.title()}<br/><font color='#6b6b8a'>{model}</font>",
                    styles["Cell"],
                ),
                Paragraph(net.get("ipAddress") or net.get("ip_address") or "—", styles["CellMono"]),
                Paragraph(net.get("macAddress") or net.get("mac_address") or "—", styles["CellMono"]),
                Paragraph(zone_name_lookup.get(zid, zid or "—"), styles["Cell"]),
                Paragraph(
                    _join(_humanize_protocol(p) for p in protos),
                    styles["Cell"],
                ),
            ])
        story.append(_table_with_header(
            header=["Name", "Type", "Vendor / Model", "IP", "MAC", "Zone", "Protocols"],
            rows=rows,
            col_widths=[1.4 * inch, 0.55 * inch, 1.2 * inch, 0.9 * inch, 1.05 * inch, 0.85 * inch, 0.75 * inch],
        ))
    else:
        story.append(Paragraph("No devices in this scenario.", styles["Body"]))

    # ── Flows ──────────────────────────────────────────────────────
    story.append(_section_header(styles, "Traffic Flows"))
    if flows:
        dev_name = {did: (d.get("name") or did) for did, d in devices.items()}
        sorted_flows = sorted(
            flows.values(),
            key=lambda f: (f.get("protocol") or "", (f.get("name") or "").lower()),
        )
        rows = []
        for f in sorted_flows:
            src = f.get("sourceDeviceId") or f.get("source_device_id")
            tgt = f.get("targetDeviceId") or f.get("target_device_id")
            timing = f.get("timing") or {}
            interval = timing.get("intervalMs") or timing.get("interval_ms")
            jitter = timing.get("jitterMs") or timing.get("jitter_ms")
            timing_str = _ms_to_human(interval)
            if jitter:
                timing_str += f" ±{_ms_to_human(jitter)}"
            rows.append([
                Paragraph(f.get("name") or "—", styles["CellBold"]),
                Paragraph(_humanize_protocol(f.get("protocol") or ""), styles["Cell"]),
                Paragraph(dev_name.get(src, src or "—"), styles["Cell"]),
                Paragraph(dev_name.get(tgt, tgt or "—"), styles["Cell"]),
                Paragraph(timing_str, styles["CellMono"]),
            ])
        story.append(_table_with_header(
            header=["Flow", "Protocol", "Source", "Target", "Interval"],
            rows=rows,
            col_widths=[1.6 * inch, 1.0 * inch, 1.7 * inch, 1.7 * inch, 0.8 * inch],
        ))
    else:
        story.append(Paragraph("No flows defined.", styles["Body"]))

    # ── Conduits ───────────────────────────────────────────────────
    story.append(_section_header(styles, "IEC 62443 Conduits"))
    if conduits:
        zone_name_lookup = {zid: z.get("name") or zid for zid, z in zones.items()}
        sorted_conduits = sorted(
            conduits.values(), key=lambda c: c.get("name") or ""
        )
        rows = []
        for c in sorted_conduits:
            src_z = c.get("sourceZoneId") or c.get("source_zone_id") or c.get("source_zone")
            tgt_z = c.get("targetZoneId") or c.get("target_zone_id") or c.get("target_zone")
            allowed = c.get("allowedProtocols") or c.get("allowed_protocols") or []
            rows.append([
                Paragraph(c.get("name") or "—", styles["CellBold"]),
                Paragraph(zone_name_lookup.get(src_z, src_z or "—"), styles["Cell"]),
                Paragraph(zone_name_lookup.get(tgt_z, tgt_z or "—"), styles["Cell"]),
                Paragraph((c.get("direction") or "bidirectional").title(), styles["Cell"]),
                Paragraph(
                    _join(
                        [_humanize_protocol(p) for p in allowed],
                        fallback="(any)",
                    ),
                    styles["Cell"],
                ),
            ])
        story.append(_table_with_header(
            header=["Conduit", "Source Zone", "Target Zone", "Direction", "Allowed Protocols"],
            rows=rows,
            col_widths=[1.5 * inch, 1.4 * inch, 1.4 * inch, 0.9 * inch, 1.6 * inch],
        ))
    else:
        story.append(Paragraph(
            "No explicit conduits declared. Cross-zone flows are auto-permitted "
            "by the deployment unless cell isolation is set to strict.",
            styles["Body"],
        ))

    # ── Build the PDF ──────────────────────────────────────────────
    def _on_page(canvas, doc):
        _draw_page_decoration(canvas, doc, scenario_name=scenario.name)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()


__all__ = ["build_scenario_pdf"]
