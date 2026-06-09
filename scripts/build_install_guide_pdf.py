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

import os

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

VERSION = "1.8.0"
COMMIT = "d53bf59"
DATE = "June 9, 2026"

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
        "<b>5/5</b> Runs <font face='Courier'>docker compose up -d "
        "--build</font> and prints the access URLs.",
    ]))

    s.append(Paragraph("Manual equivalent", h3))
    s.append(codeblock(
        "git clone https://github.com/ip-aegis/PacketArch.git ~/packetarch\n"
        "cd ~/packetarch\n"
        "# create .env (see Environment Variables section), then:\n"
        "sudo docker compose up -d --build"))

    s.append(Paragraph("After it finishes", h3))
    s.append(bullets([
        "Open <font face='Courier'>https://&lt;server-ip&gt;/</font> and "
        "accept the self-signed certificate.",
        "API docs are at <font face='Courier'>https://&lt;server-ip&gt;/"
        "api/docs</font>.",
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
        "UI &mdash; you only rebuild the OVA at major releases.", body))

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
        "git clone git@github.com:ip-aegis/PacketArch.git\n"
        "cd PacketArch\n\n"
        "# 1. Database + Redis\n"
        "cd docker && docker-compose -f docker-compose.dev.yml up -d\n\n"
        "# 2. Backend (http://localhost:8001)\n"
        "cd ../backend && poetry install\n"
        "poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001\n\n"
        "# 3. Frontend (new terminal -> http://localhost:3001)\n"
        "cd ../frontend && pnpm install && pnpm dev"))
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
