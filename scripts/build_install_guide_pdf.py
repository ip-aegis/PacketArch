#!/usr/bin/env python3
"""Generate the PacketArch Installation Guide PDF for the current release.

Content is sourced from the committed install scripts/docs at HEAD:
  - README.md, CLAUDE.md
  - scripts/server-init.sh           (git-clone production install)
  - scripts/release-bundle/*         (offline air-gapped bundle)
  - scripts/ova/README.md            (virtual appliance)
  - scripts/build-release.sh         (release variants)

Run:  cd backend && poetry run python ../scripts/build_install_guide_pdf.py
Out:  dist/PacketArch-Installation-Guide-v<version>.pdf
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

def _derive_version() -> str:
    """App version from the backend settings (single source of truth)."""
    env = os.environ.get("PACKETARCH_VERSION")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(here, "..", "backend", "app", "core", "config.py")
    with open(cfg) as fh:
        m = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', fh.read())
    if not m:
        raise SystemExit("could not read app_version from backend/app/core/config.py")
    return m.group(1)


def _git(*args: str, default: str = "unknown") -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return default


VERSION = _derive_version()
COMMIT = _git("rev-parse", "--short", "HEAD")
DATE = datetime.date.today().strftime("%B %-d, %Y")

# --- palette -------------------------------------------------------------
INK = colors.HexColor("#1a2230")
ACCENT = colors.HexColor("#1668dc")  # PacketArch blue
ACCENT_DK = colors.HexColor("#0d3a7d")
MUTED = colors.HexColor("#5b6675")
RULE = colors.HexColor("#d0d7e2")
CODE_BG = colors.HexColor("#0f1626")
CODE_FG = colors.HexColor("#e6edf3")
TABLE_HDR = colors.HexColor("#1668dc")
TABLE_ALT = colors.HexColor("#eef3fb")
WARN_BG = colors.HexColor("#fff4e6")
WARN_BD = colors.HexColor("#d48806")

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "dist")
OUT_PATH = os.path.join(OUT_DIR, f"PacketArch-Installation-Guide-v{VERSION}.pdf")

# --- styles --------------------------------------------------------------
ss = getSampleStyleSheet()


def style(name, **kw):
    kw.setdefault("parent", ss["Normal"])
    return ParagraphStyle(name, **kw)


body = style("body", fontName="Helvetica", fontSize=10, leading=15,
             textColor=INK, spaceAfter=8, alignment=TA_LEFT)
h1 = style("h1", fontName="Helvetica-Bold", fontSize=19, leading=23,
           textColor=ACCENT_DK, spaceBefore=4, spaceAfter=10)
h2 = style("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=18,
           textColor=INK, spaceBefore=16, spaceAfter=6)
h3 = style("h3", fontName="Helvetica-Bold", fontSize=11, leading=15,
           textColor=ACCENT_DK, spaceBefore=11, spaceAfter=4)
small = style("small", fontName="Helvetica", fontSize=8.5, leading=12,
              textColor=MUTED)
bullet = style("bullet", parent=body, spaceAfter=3, leading=14)
code = style("code", fontName="Courier", fontSize=8, leading=11.5,
             textColor=CODE_FG)
warn = style("warn", fontName="Helvetica", fontSize=9.5, leading=14,
             textColor=colors.HexColor("#7a4a00"))
cell = style("cell", fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
cellb = style("cellb", parent=cell, fontName="Helvetica-Bold")
cellh = style("cellh", fontName="Helvetica-Bold", fontSize=9, leading=12,
              textColor=colors.white)
cellc = style("cellc", fontName="Courier", fontSize=8.5, leading=11, textColor=INK)


# --- flowable helpers ----------------------------------------------------
def codeblock(text):
    """A dark code box."""
    p = Preformatted(text.strip("\n"), code)
    t = Table([[p]], colWidths=[6.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def callout(text):
    p = Paragraph(text, warn)
    t = Table([[p]], colWidths=[6.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, WARN_BD),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def bullets(items):
    li = [ListItem(Paragraph(t, bullet), leftIndent=6, value="•")
          for t in items]
    return ListFlowable(li, bulletType="bullet", start="•",
                        leftIndent=14, bulletColor=ACCENT)


def table(headers, rows, col_widths, code_cols=()):
    data = [[Paragraph(h, cellh) for h in headers]]
    for r in rows:
        row = []
        for i, c in enumerate(r):
            stl = cellc if i in code_cols else cell
            row.append(Paragraph(c, stl))
        data.append(row)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    sty = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HDR),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, ACCENT_DK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(sty))
    return t


def rule():
    return HRFlowable(width="100%", thickness=0.6, color=RULE,
                      spaceBefore=8, spaceAfter=8)


# --- page furniture ------------------------------------------------------
def header_footer(canvas, doc):
    canvas.saveState()
    w, h = letter
    # footer rule + text
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.9 * inch, 0.7 * inch, w - 0.9 * inch, 0.7 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.9 * inch, 0.52 * inch,
                      f"PacketArch v{VERSION} — Installation Guide")
    canvas.drawRightString(w - 0.9 * inch, 0.52 * inch,
                           f"Page {doc.page}")
    # top accent tick on interior pages
    if doc.page > 1:
        canvas.setFillColor(ACCENT)
        canvas.rect(0.9 * inch, h - 0.62 * inch, 0.35 * inch, 0.05 * inch,
                    fill=1, stroke=0)
    canvas.restoreState()


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = BaseDocTemplate(
        OUT_PATH, pagesize=letter,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.9 * inch,
        title=f"PacketArch v{VERSION} Installation Guide",
        author="Rocky Smith",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame], onPage=header_footer)
    ])

    s = []  # story

    # ---------------- COVER ----------------
    s.append(Spacer(1, 1.4 * inch))
    s.append(Paragraph("PacketArch", style(
        "cover", fontName="Helvetica-Bold", fontSize=42, leading=46,
        textColor=ACCENT_DK, alignment=TA_CENTER)))
    s.append(Spacer(1, 6))
    s.append(Paragraph("Installation Guide", style(
        "covers", fontName="Helvetica", fontSize=20, leading=24,
        textColor=INK, alignment=TA_CENTER)))
    s.append(Spacer(1, 14))
    s.append(HRFlowable(width="42%", thickness=2, color=ACCENT,
                        hAlign="CENTER"))
    s.append(Spacer(1, 14))
    s.append(Paragraph(
        "OT Traffic Simulation Platform &mdash; deployment options, "
        "system requirements, and setup commands",
        style("covsub", fontName="Helvetica-Oblique", fontSize=11.5,
              leading=16, textColor=MUTED, alignment=TA_CENTER)))
    s.append(Spacer(1, 1.8 * inch))
    cover_meta = Table(
        [["Release", f"v{VERSION}"],
         ["Build commit", COMMIT],
         ["Document date", DATE],
         ["Repository", "github.com/ip-aegis/PacketArch"],
         ["License", "GPL-3.0"]],
        colWidths=[1.5 * inch, 3.2 * inch], hAlign="CENTER")
    cover_meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT_DK),
        ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]))
    s.append(cover_meta)
    s.append(PageBreak())

    # ---------------- OVERVIEW / CHOOSING ----------------
    s.append(Paragraph("Choosing an Installation Method", h1))
    s.append(Paragraph(
        "PacketArch ships as a Docker Compose stack (FastAPI backend, "
        "React/Nginx frontend, PostgreSQL/TimescaleDB, and Redis). There "
        "are four supported ways to install it depending on whether your "
        "environment has internet access and how you prefer to manage "
        "upgrades. All four land on the same first-run setup wizard.", body))
    s.append(Spacer(1, 4))
    s.append(table(
        ["Method", "Best for", "Internet?", "Upgrades via"],
        [["1. Git-clone production install",
          "A standard internet-connected Linux server",
          "Required", "In-app button or git pull + rebuild"],
         ["2. Offline / air-gapped bundle",
          "Isolated labs with no internet egress",
          "Not required", "New release tarball (install.sh --upgrade)"],
         ["3. Virtual appliance (OVA)",
          "Drop-in VM for VirtualBox / VMware / ESXi",
          "First boot only", "In-app upgrade button"],
         ["4. Developer / source setup",
          "Local development & contributing",
          "Required", "git pull"]],
        col_widths=[1.9 * inch, 2.05 * inch, 0.85 * inch, 1.9 * inch]))
    s.append(Spacer(1, 10))
    s.append(Paragraph(
        "<b>Variants.</b> Each release is built in two flavors. The "
        "<b>full</b> variant includes live traffic agents and the live "
        "deployment dashboard. The <b>PCAP-only</b> variant "
        "(<font face='Courier'>LIVE_TRAFFIC_ENABLED=false</font>) ships as "
        "an AI-assisted PCAP generator with the live-agent half disabled.",
        body))

    # ---------------- SYSTEM REQUIREMENTS ----------------
    s.append(PageBreak())
    s.append(Paragraph("System Requirements", h1))
    s.append(table(
        ["Resource", "Minimum", "Recommended"],
        [["Operating system",
          "Linux x86_64 (Ubuntu 22.04+, RHEL 9, Fedora)",
          "Ubuntu 22.04 / 24.04 LTS"],
         ["CPU", "2 cores", "4+ cores"],
         ["Memory", "8 GB RAM", "16 GB RAM"],
         ["Disk", "20 GB free", "40 GB+ (images + DB + PCAP output)"],
         ["Docker", "24.0+ with Compose plugin", "Latest stable Docker CE"],
         ["Privileges", "sudo (write /opt, bind 443)", "&mdash;"]],
        col_widths=[1.5 * inch, 2.85 * inch, 2.35 * inch]))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Required network ports", h3))
    s.append(table(
        ["Port", "Service", "Exposure"],
        [["443", "Web UI (HTTPS, self-signed by default)", "Inbound: admin -&gt; server"],
         ["443", "Agent &lt;-&gt; server WebSocket (wss)", "Inbound: agent -&gt; server"],
         ["5432", "PostgreSQL / TimescaleDB", "Localhost only"],
         ["6379", "Redis", "Localhost only"]],
        col_widths=[0.8 * inch, 3.7 * inch, 2.2 * inch], code_cols=(0,)))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "<b>Optional egress.</b> PacketArch runs fully offline. To enable "
        "AI-powered scenario generation, the backend needs outbound HTTPS "
        "to <font face='Courier'>api.anthropic.com</font>. Leave "
        "<font face='Courier'>AI_ENABLED=false</font> to disable it; AI "
        "surfaces hide automatically.", body))
    s.append(PageBreak())

    # ---------------- METHOD 1: GIT CLONE ----------------
    s.append(Paragraph("Method 1 &mdash; Git-Clone Production Install", h1))
    s.append(Paragraph(
        "The standard path for an internet-connected server. It installs "
        "Docker if missing, clones the repository, generates secrets, and "
        "builds and starts the stack. This install is "
        "<b>self-upgradeable</b> from the UI (Settings -&gt; System).", body))

    s.append(Paragraph("One-line bootstrap", h3))
    s.append(codeblock(
        "curl -sSL https://raw.githubusercontent.com/ip-aegis/PacketArch/"
        "master/scripts/server-init.sh \\\n  | bash"))
    s.append(Paragraph(
        "Run as a regular user with sudo privileges (<b>not</b> root). The "
        "script performs five steps:", body))
    s.append(bullets([
        "<b>1/5</b> Installs Docker CE + Compose plugin if not present.",
        "<b>2/5</b> Installs Git if not present.",
        "<b>3/5</b> Clones <font face='Courier'>ip-aegis/PacketArch</font> "
        "to <font face='Courier'>~/packetarch</font> (branch "
        "<font face='Courier'>master</font>).",
        "<b>4/5</b> Generates <font face='Courier'>.env</font> with random "
        "<font face='Courier'>POSTGRES_PASSWORD</font>, "
        "<font face='Courier'>SECRET_KEY</font>, "
        "<font face='Courier'>ENCRYPTION_KEY</font>, the host "
        "<font face='Courier'>DOCKER_GID</font>, and self-upgrade "
        "pointers (<font face='Courier'>HOST_INSTALL_DIR</font>, "
        "<font face='Courier'>COMPOSE_PROJECT_NAME=packetarch</font>).",
        "<b>5/5</b> Checks Docker egress "
        "(<font face='Courier'>check-docker-egress.sh</font>), runs "
        "<font face='Courier'>docker compose up -d --build</font>, and then "
        "<i>the script</i> prints the access URLs. The compose command itself "
        "prints no URLs \u2014 if you follow the manual equivalent below, use "
        "the table in \u201cAccess and first login\u201d.",
    ]))

    s.append(Paragraph("Manual equivalent", h3))
    s.append(codeblock(
        "git clone https://github.com/ip-aegis/PacketArch.git ~/packetarch\n"
        "cd ~/packetarch\n"
        "# create .env (see Environment Variables section), then:\n"
        "sudo ./scripts/check-docker-egress.sh      # preflight; see below\n"
        "sudo docker compose up -d --build"))
    s.append(Paragraph("Access and first login", h3))
    s.append(Paragraph(
        "<font face='Courier'>docker compose up -d --build</font> prints no "
        "URLs of its own. These are the addresses either path produces:", body))
    s.append(table(
        ["Service", "URL"],
        [["Frontend (the platform)", "https://&lt;server-ip&gt;/"],
         ["Health probe", "https://&lt;server-ip&gt;/health"],
         ["API docs (Swagger)", "https://&lt;server-ip&gt;/api/docs &mdash; only when DEBUG=true"],
         ["pgAdmin (tools profile)", "http://localhost:5050 via SSH tunnel"]],
        col_widths=[2.2 * inch, 4.0 * inch], code_cols=(1,)))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "The certificate is self-signed by default, so expect a browser trust "
        "warning. If the page loads but login reports <b>Backend "
        "unreachable</b>, nginx cannot reach the application \u2014 see "
        "&ldquo;Troubleshooting&rdquo;.", small))

    s.append(Paragraph("After it finishes", h3))
    s.append(bullets([
        "Open <font face='Courier'>https://&lt;server-ip&gt;/</font> and "
        "accept the self-signed certificate.",
        "API docs (<font face='Courier'>/api/docs</font>) are served only when "
        "<font face='Courier'>DEBUG=true</font>. A production install sets "
        "<font face='Courier'>DEBUG=false</font>, so they are disabled on "
        "purpose \u2014 do not enable DEBUG on a production box just to read "
        "them (it also turns on SQL echo and returns raw errors to clients).",
        "Complete the first-run setup wizard to create the admin account "
        "(see the dedicated section).",
        "Open inbound <font face='Courier'>443</font> (and "
        "<font face='Courier'>80</font>) in your cloud/network firewall for "
        "off-box access.",
    ]))
    s.append(callout(
        "Docker group changes from a fresh Docker install take "
        "effect on next login. If <font face='Courier'>docker</font> "
        "commands need sudo right after install, log out and back in."))
    s.append(PageBreak())

    # ---------------- METHOD 2: OFFLINE BUNDLE ----------------
    s.append(Paragraph("Method 2 &mdash; Offline / Air-Gapped Bundle", h1))
    s.append(Paragraph(
        "A self-contained tarball with every Docker image pre-saved, so no "
        "registry or internet access is needed at install time. This is the "
        "right choice for isolated labs.", body))

    s.append(Paragraph("Building the bundle (on a connected machine)", h3))
    s.append(codeblock(
        "./scripts/build-release.sh                # full variant\n"
        "PCAP_ONLY=1 ./scripts/build-release.sh    # PCAP-only variant\n"
        "# output: dist/packetarch-" + VERSION + "-offline.tar.gz"))
    s.append(Paragraph(
        "The bundle contains all images (backend, frontend, agent, "
        "postgres/timescaledb, redis) saved to tarballs, an offline "
        "<font face='Courier'>docker-compose.yml</font>, "
        "<font face='Courier'>install.sh</font>, "
        "<font face='Courier'>README_SITE.md</font>, and the license files. "
        "Tagging <font face='Courier'>v*</font> in CI builds both variants "
        "automatically and attaches them to the GitHub Release.", body))

    s.append(Paragraph("Installing on the target server", h3))
    s.append(codeblock(
        "tar xzf packetarch-*-offline.tar.gz\n"
        "cd packetarch-*-offline\n"
        "sudo ./install.sh"))
    s.append(Paragraph("The installer (idempotent, safe to re-run):", body))
    s.append(bullets([
        "<b>[1/5]</b> Stages files into "
        "<font face='Courier'>/opt/packetarch</font> "
        "(override with <font face='Courier'>--install-dir PATH</font>).",
        "<b>[2/5]</b> <font face='Courier'>docker load</font>s every "
        "bundled image into the local daemon.",
        "<b>[3/5]</b> Generates <font face='Courier'>.env</font> with random "
        "secrets (chmod 600). <b>No admin password is generated</b> &mdash; "
        "you pick it in the wizard.",
        "<b>[4/5]</b> Starts the stack with "
        "<font face='Courier'>docker compose --env-file .env up -d</font>.",
        "<b>[5/5]</b> Waits up to 5 minutes for the backend healthcheck.",
    ]))
    s.append(Paragraph("install.sh flags", h3))
    s.append(table(
        ["Flag", "Effect"],
        [["--upgrade",
          "Load new images and restart; preserve existing .env + volumes. "
          "Requires an existing .env."],
         ["--force-env",
          "Overwrite an existing .env (generates new secrets &mdash; breaks "
          "existing logins and DB access)."],
         ["--install-dir PATH",
          "Where to place the installation (default /opt/packetarch)."]],
        col_widths=[1.7 * inch, 5.0 * inch], code_cols=(0,)))
    s.append(Spacer(1, 6))
    s.append(Paragraph("Prerequisites checked by the installer", h3))
    s.append(bullets([
        "Must run as root (use <font face='Courier'>sudo</font>).",
        "Docker installed and the Docker Compose plugin available.",
        "Run from inside the extracted release directory (a "
        "<font face='Courier'>VERSION</font> file must be present).",
    ]))
    s.append(PageBreak())

    # ---------------- METHOD 3: OVA ----------------
    s.append(Paragraph("Method 3 &mdash; Virtual Appliance (OVA)", h1))
    s.append(Paragraph(
        "A distributable <font face='Courier'>.ova</font> you import into "
        "VirtualBox, VMware Workstation/Player, or ESXi/vSphere. The "
        "appliance is a real git clone pinned to a release tag using the "
        "production compose file, so it stays self-upgradeable from the "
        "UI. The release pipeline now builds the "
        "<font face='Courier'>.ova</font> in CI and attaches it to the "
        "GitHub Release, so most operators download it rather than building "
        "it &mdash; you only rebuild at major releases.", body))

    s.append(Paragraph("Building the OVA", h3))
    s.append(codeblock(
        "# Fedora:  sudo dnf install guestfs-tools qemu-img git curl\n"
        "# Ubuntu:  sudo apt-get install libguestfs-tools qemu-utils git curl\n\n"
        "sudo ./scripts/ova/build-ova.sh\n"
        "# output: dist/packetarch-" + VERSION + "-appliance.ova"))
    s.append(Paragraph("Useful build overrides:", body))
    s.append(table(
        ["Variable", "Default", "Purpose"],
        [["OVA_GIT_REF", "latest v* tag", "Tag/branch the appliance is pinned to"],
         ["DISK_SIZE", "60G", "Thin-provisioned virtual disk size"],
         ["VM_CPUS / VM_MEM", "4 / 8192", "OVF-suggested resources"],
         ["CONSOLE_PASS", "packetarch", "Console password for the ubuntu user"]],
        col_widths=[1.7 * inch, 1.3 * inch, 3.7 * inch], code_cols=(0,)))

    s.append(Paragraph("Deploying the appliance", h3))
    s.append(bullets([
        "Import the <font face='Courier'>.ova</font> into your hypervisor.",
        "Place it on a network with <b>DHCP and internet</b>, then power on.",
        "<b>First boot builds from source (~10&ndash;15 min)</b>; later boots "
        "start in seconds. Watch "
        "<font face='Courier'>/var/log/packetarch-firstboot.log</font>.",
        "Browse to <font face='Courier'>https://&lt;appliance-ip&gt;/</font>, "
        "accept the cert, and complete the wizard.",
    ]))
    s.append(callout(
        "Change the default console login "
        "(<font face='Courier'>ubuntu</font> / "
        "<font face='Courier'>packetarch</font>) after first login. For a "
        "truly air-gapped, no-build appliance, use the offline tarball "
        "(Method 2) on a plain VM instead."))
    s.append(PageBreak())

    # ---------------- METHOD 4: DEV ----------------
    s.append(Paragraph("Method 4 &mdash; Developer / Source Setup", h1))
    s.append(Paragraph(
        "For local development and contributing. Runs the backend and "
        "frontend natively with only PostgreSQL and Redis in Docker.", body))
    s.append(Paragraph("Prerequisites", h3))
    s.append(bullets([
        "Docker &amp; Docker Compose",
        "Python 3.11+ with Poetry",
        "Node.js 18+ with pnpm",
    ]))
    s.append(Paragraph("Setup", h3))
    s.append(codeblock(
        "git clone https://github.com/ip-aegis/PacketArch.git\n"
        "cd PacketArch\n\n"
        "# 1. Dev .env (password must match the backend default DATABASE_URL)\n"
        "printf 'POSTGRES_PASSWORD=packetarch_dev\\n"
        "SECRET_KEY=dev-secret-not-for-production\\n' > .env\n\n"
        "# 2. Database + Redis (from the repo root)\n"
        "docker compose up -d postgres redis\n\n"
        "# 3. Backend (http://localhost:8001)\n"
        "cd backend && poetry install\n"
        "poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001\n\n"
        "# 4. Frontend (new terminal -> http://localhost:3001)\n"
        "cd frontend && pnpm install && pnpm dev"))
    s.append(Paragraph("Development ports", h3))
    s.append(table(
        ["Service", "Port"],
        [["Backend (FastAPI)", "8001"],
         ["Frontend (Vite)", "3001"],
         ["PostgreSQL", "5432"],
         ["Redis", "6379"],
         ["pgAdmin (optional)", "5050"]],
        col_widths=[3.0 * inch, 1.2 * inch], code_cols=(1,)))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "On Windows, use <font face='Courier'>python -m poetry run "
        "uvicorn ...</font> if Poetry is not on PATH.", small))
    s.append(PageBreak())

    # ---------------- FIRST-RUN WIZARD ----------------
    s.append(Paragraph("First-Run Setup Wizard", h1))
    s.append(Paragraph(
        "Regardless of install method, a fresh install lands on a setup "
        "wizard at <font face='Courier'>https://&lt;server&gt;/</font> "
        "instead of a login page. Until the wizard finishes, every API "
        "route except setup/about/health returns 503. The wizard walks "
        "through four steps:", body))
    s.append(bullets([
        "<b>Admin account</b> &mdash; username, password, optional email.",
        "<b>Site identity</b> &mdash; site name, server FQDN/IP (used in "
        "agent install commands), time zone.",
        "<b>Capabilities</b> &mdash; optional AI (Anthropic API key) and "
        "optional Cisco Cyber Vision import; both can be added later under "
        "Settings.",
        "<b>Confirm</b> &mdash; review, accept the GPL-3.0 license, click "
        "<b>Complete setup</b>. You are auto-logged-in to the dashboard.",
    ]))
    s.append(callout(
        "<b>The setup wizard is unprotected</b> &mdash; the first "
        "person who reaches the URL becomes the admin. Complete it "
        "<b>before</b> anyone else can browse to the server. Save the admin "
        "password somewhere safe; it is the only credential to recover it "
        "from."))
    s.append(Paragraph("Recovering from a botched setup", h3))
    s.append(Paragraph(
        "If someone else claimed admin during the window, or you want to "
        "start over, reset and re-run the wizard:", body))
    s.append(codeblock(
        "cd /opt/packetarch\n"
        "sudo docker compose exec postgres psql -U packetarch -d packetarch -c \\\n"
        '  "DELETE FROM users; UPDATE system_settings SET value=\'false\' '
        "WHERE key='setup.completed';\"\n"
        "sudo docker compose restart backend"))
    s.append(Paragraph(
        "Upgrades from pre-wizard installs do not show the wizard: on every "
        "boot, auto-graduation flips setup as complete if an admin user "
        "already exists.", small))

    # ---------------- ENV VARS ----------------
    env_block = []
    env_block.append(Paragraph("Environment Variables (.env)", h2))
    env_block.append(Paragraph(
        "Generated automatically by the installers. Treat "
        "<font face='Courier'>.env</font> as secret material (chmod 600).",
        body))
    env_block.append(table(
        ["Variable", "Description"],
        [["POSTGRES_PASSWORD", "Database password (random per install)."],
         ["SECRET_KEY", "JWT signing key (random per install)."],
         ["ENCRYPTION_KEY",
          "Fernet key that encrypts stored secrets (CV token, AI keys) at "
          "rest. Persists them across restarts."],
         ["ADMIN_PASSWORD",
          "Left blank on fresh installs (wizard creates admin). A set value "
          "is a legacy headless-bootstrap path."],
         ["AI_ENABLED",
          "Gates AI features. Default true (git install) / false (offline "
          "bundle)."],
         ["LIVE_TRAFFIC_ENABLED",
          "Gates live agents + deployment dashboard. false in the PCAP-only "
          "variant."],
         ["DOCKER_GID",
          "Host docker group id so the backend can use the Docker socket."],
         ["HOST_INSTALL_DIR / COMPOSE_PROJECT_NAME",
          "Targets for the in-app self-upgrade (git-clone installs)."],
         ["BUILD_COMMIT / BUILD_DATE",
          "Build provenance stamped at release-build time; surfaced in the "
          "UI footer / About page."],
         ["COMPOSE_SUBNET",
          "Subnet for the stack's own bridge network, PINNED rather than "
          "taken from Docker's pools (default 10.200.0.0/24). A site or VPN "
          "route that overlaps Docker's pools makes the stack come up and "
          "still be unreachable \u2014 see Troubleshooting. Changing it needs "
          "the network recreated (down, then up)."],
         ["DOCKER_BUILD_NETWORK",
          "Leave unset on a healthy host. 'host' makes every image build use "
          "the host network stack \u2014 a stopgap for a host whose bridged "
          "build sandbox has no egress."],
         ["DEBUG", "false in production."]],
        col_widths=[2.3 * inch, 4.4 * inch], code_cols=(0,)))
    s.append(KeepTogether(env_block))
    s.append(PageBreak())

    # ---------------- POST-INSTALL ----------------
    s.append(Paragraph("Post-Install Tasks", h1))

    s.append(Paragraph("Provide your own TLS certificate", h3))
    s.append(Paragraph(
        "By default the frontend mints a self-signed cert. To use a real "
        "one, drop it in <font face='Courier'>./certs</font> and restart:",
        body))
    s.append(codeblock(
        "sudo mkdir -p /opt/packetarch/certs\n"
        "sudo cp server.crt /opt/packetarch/certs/server.crt\n"
        "sudo cp server.key /opt/packetarch/certs/server.key\n"
        "sudo chmod 600 /opt/packetarch/certs/server.key\n"
        "sudo docker compose restart frontend"))

    s.append(Paragraph("Install remote traffic agents (full variant)", h3))
    s.append(Paragraph(
        "Agents connect outbound over WebSocket (TLS on 443) &mdash; no "
        "inbound ports needed on the agent host. Generate a token in the UI "
        "under Settings -&gt; Agents, then on each agent box:", body))
    s.append(codeblock(
        "curl -fsSLk https://<your-server>/agent/install.sh | sudo bash -s -- \\\n"
        "    --server https://<your-server> --token <agent-token> --insecure"))

    s.append(Paragraph("Turn AI on or off", h3))
    s.append(Paragraph(
        "Edit <font face='Courier'>.env</font>, set "
        "<font face='Courier'>AI_ENABLED=true|false</font>, then "
        "<font face='Courier'>docker compose up -d backend</font>. When on, "
        "set an Anthropic API key under Settings -&gt; AI Provider (keys "
        "are encrypted at rest).", body))

    # ---------------- UPGRADES & BACKUPS ----------------
    s.append(Paragraph("Upgrades", h2))
    s.append(Paragraph("There are three upgrade mechanisms:", body))
    s.append(bullets([
        "<b>In-app (git-clone &amp; OVA installs):</b> Settings -&gt; "
        "System -&gt; Upgrade. Git-fetches a newer tag, rebuilds, "
        "migrates, and restarts &mdash; with automatic backup and rollback "
        "on failure. CLI equivalent: "
        "<font face='Courier'>sudo scripts/upgrade.sh --to vX.Y.Z</font>.",
        "<b>Offline bundle:</b> ship the new tarball, then "
        "<font face='Courier'>down</font> -&gt; "
        "<font face='Courier'>./install.sh --upgrade</font> -&gt; "
        "<font face='Courier'>up -d</font>. Preserves "
        "<font face='Courier'>.env</font> and volumes.",
        "<b>Traffic agents:</b> self-update over WebSocket from the UI "
        "(Settings -&gt; Agents -&gt; Build Image, then per-agent Update).",
    ]))
    s.append(codeblock(
        "# Offline upgrade\n"
        "cd /opt/packetarch\n"
        "sudo docker compose down\n"
        "sudo ./install.sh --upgrade     # loads new images, keeps .env + data\n"
        "sudo docker compose up -d"))

    s.append(Paragraph("Backups", h2))
    s.append(Paragraph(
        "The bundle ships backup/restore scripts that snapshot the Postgres "
        "DB + PCAP volumes into one tarball. Back up before every upgrade.",
        body))
    s.append(codeblock(
        "cd /opt/packetarch\n"
        "sudo ./packetarch-backup.sh                      # redacts .env secrets\n"
        "sudo ./packetarch-backup.sh --output /mnt/safe/pa.tgz --with-secrets\n"
        "sudo ./packetarch-restore.sh /mnt/safe/pa.tgz    # --yes to skip prompt"))
    s.append(Paragraph(
        "Each tarball holds <font face='Courier'>postgres.dump</font>, "
        "<font face='Courier'>pcap_output.tar.gz</font>, "
        "<font face='Courier'>pcap_uploads.tar.gz</font>, a redacted/raw "
        "<font face='Courier'>.env</font>, and a "
        "<font face='Courier'>manifest.json</font> (version + timestamp).",
        small))

    s.append(Paragraph("Uninstall", h2))
    s.append(codeblock(
        "cd /opt/packetarch\n"
        "sudo docker compose down -v     # -v removes volumes (DATA LOSS)\n"
        "sudo rm -rf /opt/packetarch"))

    # ---------------- common ops ----------------
    s.append(Paragraph("Common Operations", h2))
    s.append(table(
        ["Task", "Command"],
        [["Status", "docker compose ps"],
         ["Logs", "docker compose logs -f backend"],
         ["Restart all", "docker compose restart"],
         ["Rebuild backend", "docker compose up -d --build backend"],
         ["Stop / start", "docker compose down  /  docker compose up -d"]],
        col_widths=[1.6 * inch, 5.1 * inch], code_cols=(1,)))

    s.append(PageBreak())

    # ---------------- TROUBLESHOOTING ----------------
    s.append(Paragraph("Troubleshooting", h1))
    s.append(Paragraph(
        "Two read-only commands answer most of this. Run them before "
        "changing anything \u2014 between them they name every install "
        "failure seen in the field so far.", body))
    s.append(codeblock(
        "./scripts/check-docker-egress.sh    # can containers build, route and RESOLVE?\n"
        "./scripts/collect-diagnostics.sh    # one redacted file to send back"))
    s.append(Paragraph(
        "<font face='Courier'>collect-diagnostics.sh</font> locates the "
        "install from its own path, so it works on any of the four methods "
        "without being told which. It replaces every secret value from "
        "<font face='Courier'>.env</font> with "
        "<font face='Courier'>&lt;redacted:KEY&gt;</font> throughout its "
        "output, including inside container logs. In the offline bundle and "
        "the appliance both scripts sit flat beside "
        "<font face='Courier'>docker-compose.yml</font>, so drop the "
        "<font face='Courier'>scripts/</font> prefix.", body))

    s.append(Paragraph("Which install path am I on?", h3))
    s.append(table(
        ["Layout", "Install dir", "Tell"],
        [["Git clone", "wherever you cloned, usually ~/packetarch",
          ".git/ is present"],
         ["Offline bundle", "/opt/packetarch (--install-dir overrides)",
          "VERSION file, no .git/"],
         ["Appliance (OVA)", "/opt/packetarch",
          "/var/log/packetarch-firstboot.log and .firstboot-done"]],
        col_widths=[1.4 * inch, 2.8 * inch, 2.5 * inch], code_cols=(1, 2)))

    s.append(Paragraph(
        "Everything is green and the platform is still unreachable", h2))
    s.append(Paragraph(
        "This is the failure that costs the most time, because nothing looks "
        "wrong. On a VPN'd corporate laptop the tunnel usually routes "
        "<font face='Courier'>172.16.0.0/12</font>, which covers almost all "
        "of Docker's default address pools "
        "(<font face='Courier'>172.17\u2013172.31.0.0/16</font>). When the "
        "stack's bridge lands inside that block:", body))
    s.append(bullets([
        "every container starts and <font face='Courier'>docker compose ps"
        "</font> is green;",
        "<font face='Courier'>curl https://localhost/health</font> "
        "<i>inside</i> the frontend container returns 200;",
        "the host still gets a TCP reset on 80/443, because the reply routes "
        "out through the VPN instead of back to the bridge;",
        "and Docker's embedded DNS (<font face='Courier'>127.0.0.11</font>) "
        "can stop returning answers, so the name "
        "<font face='Courier'>backend</font> no longer resolves. nginx "
        "re-resolves its upstream on every request, so every "
        "<font face='Courier'>/api/</font> call returns 502 after the "
        "resolver timeout and the login page reports <b>Backend "
        "unreachable</b>.",
    ]))
    s.append(Paragraph(
        "PacketArch pins its subnet so this cannot happen by accident. If "
        "your site routes the default too, pick a free /24:", body))
    s.append(codeblock(
        "echo 'COMPOSE_SUBNET=10.201.0.0/24' >> .env\n"
        "docker compose down && docker compose up -d   # a subnet change needs\n"
        "                                              # the network RECREATED"))
    s.append(callout(
        "<b>Do not work around this with <font face='Courier'>extra_hosts"
        "</font> entries in <font face='Courier'>docker-compose.yml</font>.</b> "
        "They pin container IP addresses that change on every recreate; they "
        "cannot help the frontend at all, because nginx resolves through "
        "127.0.0.11 rather than /etc/hosts; and they are a local edit to a "
        "TRACKED file, which <font face='Courier'>scripts/upgrade.sh</font> "
        "refuses to upgrade over (it stops unless you pass "
        "<font face='Courier'>--force</font>, and then stashes them). Put "
        "<font face='Courier'>COMPOSE_SUBNET</font> in "
        "<font face='Courier'>.env</font> instead \u2014 .env is untracked, so "
        "upgrades leave it alone."))

    s.append(Paragraph("A green healthcheck is a claim, not evidence", h2))
    s.append(Paragraph(
        "Read what a check executes before believing it. "
        "<font face='Courier'>collect-diagnostics.sh</font> prints the "
        "literal text of every one, alongside each container's restart "
        "count \u2014 a service can report healthy while crashlooping "
        "behind it.", body))
    s.append(table(
        ["Service", "Probe", "What green proves"],
        [["postgres", "pg_isready",
          "the server accepts connections. NOT that credentials work"],
         ["backend", "curl /health", "the app is up, which needs the database"],
         ["celery_worker", "celery ping + a real DB connect",
          "broker and database both reachable"],
         ["frontend", "curl -fsk https://127.0.0.1/health",
          "TLS up, 'backend' resolved AND reached (the endpoint is proxied)"],
         ["host-agent", "heartbeat age + main-loop age",
          "process alive and its request loop turning"]],
        col_widths=[1.1 * inch, 2.2 * inch, 3.4 * inch], code_cols=(1,)))

    s.append(Paragraph(
        "Backend crashlooping on \u201cpassword authentication failed\u201d", h2))
    s.append(Paragraph(
        "Postgres applies <font face='Courier'>POSTGRES_PASSWORD</font> only "
        "when it initialises an EMPTY data directory. A data volume that "
        "outlived its <font face='Courier'>.env</font> keeps the password it "
        "was built with, so a regenerated .env silently stops matching. "
        "Re-cloning into a fresh directory, deleting .env, or "
        "<font face='Courier'>install.sh --force-env</font> all produce it. "
        "Repair it without losing data:", body))
    s.append(codeblock("./scripts/fix-db-password.sh        # --check to report only"))

    s.append(Paragraph("Builds fail on pip / apt / npm / apk", h2))
    s.append(Paragraph(
        "Those steps run inside a bridged build sandbox, not on the host "
        "network stack, so a host with perfectly good internet can fail every "
        "build. Run the egress preflight: it separates firewall FORWARD "
        "drops, a VPN MTU below the bridge's (which HANGS mid-download rather "
        "than erroring), an unreachable container resolver, and subnet "
        "collisions. Prefer the "
        "<font face='Courier'>/etc/docker/daemon.json</font> fix \u2014 most "
        "of those causes also break RUNTIME egress to a Cyber Vision Center, "
        "a CML server or an AI provider, and a build that succeeds is not an "
        "install that works. The supported stopgap is an .env line, never a "
        "compose edit:", body))
    s.append(codeblock(
        "echo 'DOCKER_BUILD_NETWORK=host' >> .env\n"
        "docker compose up -d --build"))

    s.append(Spacer(1, 14))
    s.append(rule())
    s.append(Paragraph(
        "PacketArch is &copy; 2026 Rocky Smith "
        "(rocky.d.smith@proton.me) and is licensed under GPL-3.0. "
        "Issues &amp; questions: github.com/ip-aegis/PacketArch/issues",
        small))

    doc.build(s)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
