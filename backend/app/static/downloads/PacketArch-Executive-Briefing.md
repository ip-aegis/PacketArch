---
marp: true
theme: default
paginate: true
backgroundColor: #0b1020
color: #eaeaea
style: |
  section {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 24px;
    padding: 60px 70px;
    background-image:
      radial-gradient(circle at 10% 0%, rgba(0,212,255,0.10), transparent 40%),
      radial-gradient(circle at 100% 100%, rgba(15,188,249,0.08), transparent 45%);
  }
  section.lead {
    background:
      linear-gradient(135deg, #0b1020 0%, #11183a 60%, #1a2354 100%);
    text-align: center;
    justify-content: center;
  }
  section.lead h1 {
    font-size: 64px;
    letter-spacing: 1px;
    border-bottom: 3px solid #00d4ff;
    display: inline-block;
    padding-bottom: 12px;
  }
  section.lead h2 {
    color: #9bd9ff;
    font-weight: 400;
  }
  h1 {
    color: #00d4ff;
    font-size: 40px;
    margin-bottom: 0.25em;
    border-bottom: 2px solid rgba(0,212,255,0.25);
    padding-bottom: 6px;
  }
  h2 {
    color: #7ad8ff;
    font-size: 28px;
    margin-top: 0;
    font-weight: 500;
  }
  h3 {
    color: #c0e8ff;
    font-size: 22px;
    margin-bottom: 0.3em;
  }
  strong { color: #ffffff; }
  em { color: #9bd9ff; font-style: normal; }
  code {
    background: #16213e;
    color: #00ff9d;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 19px;
  }
  table {
    font-size: 20px;
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    margin-top: 6px;
  }
  th {
    background: #102045;
    color: #00d4ff;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 2px solid #00d4ff;
  }
  td {
    background: #11173a;
    color: #eaeaea;
    padding: 7px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  tr:nth-child(even) td { background: #141b44; }
  ul, ol {
    font-size: 22px;
    margin: 0.3em 0;
    line-height: 1.5;
  }
  li { margin: 0.25em 0; }
  ul li::marker { color: #00d4ff; }
  ol li::marker { color: #00d4ff; font-weight: bold; }
  blockquote {
    border-left: 4px solid #00d4ff;
    background: #11183a;
    color: #ffffff;
    padding: 12px 18px;
    margin: 14px 0;
    font-size: 22px;
    border-radius: 0 8px 8px 0;
  }
  .pill {
    display: inline-block;
    background: #00d4ff;
    color: #0b1020;
    padding: 4px 14px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 18px;
    margin-right: 6px;
  }
  .kpi {
    display: inline-block;
    background: #11183a;
    border: 1px solid rgba(0,212,255,0.35);
    border-radius: 10px;
    padding: 14px 20px;
    margin: 6px 8px 6px 0;
    min-width: 160px;
    text-align: center;
  }
  .kpi b {
    display: block;
    color: #00d4ff;
    font-size: 34px;
    line-height: 1.1;
  }
  .kpi span {
    color: #c0e8ff;
    font-size: 16px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  footer {
    color: #6a7ab0;
    font-size: 14px;
  }
  section::after {
    color: #6a7ab0;
    font-size: 14px;
  }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# PacketArch

## The OT Traffic Simulation Platform for Industrial Security Teams

<span class="pill">Executive Briefing</span> <span class="pill">Version 1.5</span>

**May 2026**

---

<!-- _class: lead -->

# Why We Are Here

## OT networks are the next attack surface — and the hardest one to defend confidently.

This briefing covers what PacketArch does, what it replaces, and what it returns to the business.

---

# The OT Security Problem

## Defenders are flying blind on the plant floor

- **No safe place to test.** Production lines cannot be the lab.
- **Real PLCs cost thousands** and ship with months-long lead times.
- **Generic packet tools don't speak OT** — no Modbus state, no vendor identity, no Cyber Vision fingerprint.
- **Detection tooling is unproven** until it has seen realistic ICS traffic *and* realistic attacks.
- **Tabletop exercises are theater.** Teams need traffic on the wire.

> **Result:** millions invested in OT visibility tools that have never been validated end-to-end.

---

# What PacketArch Is

## A software platform that produces protocol-accurate industrial network traffic — on demand.

- Design plant networks visually, or describe them in plain English.
- Generate **packet-perfect** ICS traffic to PCAP, or inject it live onto a lab segment.
- Run **adversary playbooks** against your sensors and SOC — with after-action reports.
- Integrates natively with **Cisco Cyber Vision** for closed-loop validation.

**One platform. Six verticals. Zero hardware required to get started.**

---

# Platform At A Glance

<div class="kpi"><b>295</b><span>Device Templates</span></div>
<div class="kpi"><b>18</b><span>OT Vendors</span></div>
<div class="kpi"><b>7</b><span>ICS Protocols</span></div>
<div class="kpi"><b>6</b><span>Industry Verticals</span></div>
<div class="kpi"><b>6</b><span>Attack Playbooks</span></div>
<div class="kpi"><b>2</b><span>Deployment Modes</span></div>

**Built for:** SOC validation - red/blue team exercises - sensor onboarding - training - tool selection - vendor bake-offs.

---

# Capability Matrix

| Capability | What It Delivers |
|------------|------------------|
| **Visual Scenario Studio** | Drag-and-drop plant networks, IEC 62443 zones & conduits |
| **AI-Assisted Authoring** | Natural-language scenario generation and review |
| **Protocol Accuracy** | Stateful engines for 7 ICS protocols, vendor-real fingerprints |
| **Live Attack Simulation** | 6 kill-chain playbooks with per-action telemetry |
| **After-Action Reporting** | MITRE ATT&CK coverage, IOCs, packet-level evidence |
| **Adaptive Traffic** | Phase scheduling, time-of-day shaping, drift & jitter |
| **Process Simulation** | Realistic sensor values driven by physical models |
| **Cyber Vision Integration** | Bidirectional device matching and enrichment |

---

# Common Workflows

## How teams actually use PacketArch

| Workflow | Who runs it | Outcome |
|----------|-------------|---------|
| **Sensor / Tool Validation** | OT security ops | Prove Cyber Vision (or any DPI) sees what's actually on the wire — before trusting it in production |
| **SOC Exercise (Red vs Blue)** | SOC + IR teams | Run a kill-chain playbook against the live SOC, score detection coverage from the after-action report |
| **Cyber Vision PoC Acceleration** | Solutions engineering | Replace the 3-6 month "wait for the lab" with a Day-1 realistic site — close PoCs faster |
| **Detection Engineering** | Detection / threat-intel | Generate adversary ICS traffic on demand, tune Snort / Suricata / Splunk rules against ground truth |
| **Training & Certification** | Training / curriculum | Repeatable, resettable scenarios — every cohort runs against identical traffic, every time |
| **Vendor Bake-Off** | Procurement / TAC | Drive every candidate tool against one canonical scenario to compare apples-to-apples |

---

# Workflow Spotlight — End-to-End in a Day

## Example: validate a new Cyber Vision sensor deployment

1. **Design** — pick the manufacturing template, AI-tweak it to match the customer's plant (5 minutes).
2. **Deploy** — start a live traffic agent on the lab segment Cyber Vision is monitoring (1 click).
3. **Match** — open the Cyber Vision Compare panel; confirm 100% MAC / 95% IP match across all devices.
4. **Enrich** — push vendor / model / firmware back into CV with one click.
5. **Stress** — run a `NETWORK_RECON` playbook to validate CV's anomaly detection lights up.
6. **Report** — download the after-action JSON for the customer's compliance file.

> **From empty install to evidence-grade report — single afternoon, single workstation.**

---

# Industry Verticals We Cover

| Vertical | Representative Scenarios |
|----------|--------------------------|
| **Manufacturing** | Assembly cells, robotic lines, SCADA over PROFINET / EtherNet-IP |
| **Water & Wastewater** | Treatment trains, lift stations, telemetry over Modbus / SNMP |
| **Energy & Power** | Substations, generation control, IEC-style telemetry |
| **Oil & Gas** | Wellhead control, custody transfer, pipeline RTUs |
| **Building Automation** | HVAC, access control, BACnet/IP estates |
| **Transportation / ITS** | Traffic cabinets, NTCIP signaling, roadside sensors |

Every vertical ships with **pre-built templates**, **process models**, and **vendor-correct device libraries**.

---

# Protocol Coverage

| Protocol | Port(s) | Status |
|----------|---------|--------|
| **Modbus TCP** | 502 | Production |
| **EtherNet/IP (CIP)** | 44818 / 2222 | Production |
| **PROFINET** | Layer 2 | Production |
| **S7comm / S7comm+** | 102 | Production |
| **BACnet/IP** | 47808 | Production |
| **SNMP / NTCIP** | 161 / 162 | Production |
| OPC UA, DNP3, IEC 60870-5-104 | Various | On roadmap |

Each engine generates **startup, polling, and shutdown** sequences — not just packet shapes, but conversations.

---

# AI-Augmented Authoring

## Describe the plant. PacketArch builds it.

> "Create a water treatment site with three pump stations, a Siemens S7-1500 master, and a Cisco IE switch in each zone."

- **Task-routed model selection** — Anthropic, OpenAI, or **Cisco CIRCUIT** per workload.
- **Scenario review** scores realism, conduit compliance, vendor accuracy.
- **AI Help** explains every screen and every recommendation in context.
- **Portable Scenario v1** — any LLM can author scenarios in a documented, importable JSON format.

**AI is a feature flag.** Air-gapped sites run identically with AI off.

---

# Live Attack Simulation

## Six end-to-end ICS adversary playbooks, executed against your real lab segment.

| Playbook | Inspiration |
|----------|-------------|
| **TRITON-like** | Safety system compromise |
| **PIPEDREAM-like** | Modular ICS toolkit |
| **INDUSTROYER-like** | Substation manipulation |
| **HAVEX-like** | OPC reconnaissance & exfil |
| **Insider Threat** | Trusted-user misuse |
| **Network Recon** | Pre-attack discovery |

Plays out across the kill chain with real packets — recon, lateral movement, ICS-protocol abuse, C2 beaconing, impact.

---

# After-Action Reports

## Prove the exercise happened. Prove what the SOC saw — and what it missed.

- **Per-action telemetry** — packets emitted, targets hit, function codes used, registers touched.
- **MITRE ATT&CK coverage grid** — planned vs. fired techniques.
- **IOC capture** — attacker IPs, ports, SNMP communities, beacon patterns.
- **History on the scenario** — every run preserved for compliance and trend reporting.
- **Downloadable JSON** for SIEM correlation and tabletop evidence.

> **One click after each run produces an audit-grade record.**

---

# Cisco Cyber Vision Integration

## Close the loop between simulation and your live OT visibility tool.

| Feature | Outcome |
|---------|---------|
| **Inventory pull** | Compare PacketArch scenario to your real CV inventory |
| **Device matching** | MAC at 100% confidence, IP at 95% |
| **Enrichment push** | Send vendor, model, firmware back into CV |
| **Fingerprint uniqueness** | Per-instance serials prevent CV merging |
| **Site identity rail** | Consistent naming across CV centers and exercises |

**Validate that CV sees what you simulated** — before you trust it in production.

---

# Deployment Models

| Mode | Use Case | Footprint |
|------|----------|-----------|
| **PCAP-only** | Air-gapped labs, offline training, dataset generation | Single server, no agents |
| **Live Agent** | SOC validation, sensor tuning, red-team exercises | Server + lightweight Docker agents per segment |

- **Same engines power both.** PCAP and live output are byte-for-byte equivalent for the same scenario.
- **One-script offline installer** with `docker save` images — works on disconnected sites.
- **Agents phone home** over WebSocket — no inbound firewall rules required.

---

# Security & Compliance Posture

| Area | Approach |
|------|----------|
| **Transport** | TLS everywhere; self-signed by default, custom cert hot-swap supported |
| **Secrets** | Bcrypt-hashed agent tokens, Fernet-encrypted API keys |
| **Setup** | First-run wizard; no default admin password |
| **Licensing** | GPL-3.0, full third-party license manifest shipped |
| **Air-Gap** | Offline tarball, AI flag off by default, no outbound calls required |
| **Data Residency** | Self-hosted; nothing leaves the customer environment unless they enable cloud AI |
| **IEC 62443** | Conduit modeling and compliance checks built into scenario authoring |

---

# Economics — What PacketArch Replaces

| Traditional Approach | Typical Cost | PacketArch Equivalent |
|----------------------|--------------|------------------------|
| Hardware testbed (12 PLCs + switches) | **$80K - $250K** | Software scenario, minutes to build |
| Custom traffic generator contract | **$150K+ / engagement** | Built-in, unlimited reuse |
| Red-team ICS engagement | **$60K - $200K** | Repeatable playbooks, in-house |
| Cyber Vision PoC delays | **3 - 6 months** | Days, with realistic traffic on day 1 |
| Training lab refresh | **Annual hardware spend** | Snapshot, clone, reset on demand |

> A single avoided testbed pays for **multi-year platform deployment** across all labs.

---

# What An Engagement Looks Like

## A typical 90-day journey from install to value

1. **Install (Day 1)** — Offline tarball, one script, running on customer hardware.
2. **First Scenario (Week 1)** — Import a vertical template or describe one in plain English.
3. **Sensor Onboarding (Week 2-3)** — Generate traffic to Cyber Vision, validate inventory match.
4. **First Exercise (Week 4-6)** — Run a kill-chain playbook against the SOC, review after-action report.
5. **Operationalize (Week 8-12)** — Scheduled regression runs, training cohorts, vendor bake-offs.

**No vendor lock-in. No data leaves the site. No production risk.**

---

# Roadmap

| Theme | Items |
|-------|-------|
| **Protocols** | OPC UA, DNP3, IEC 60870-5-104 |
| **Attack Library** | Expanded playbooks, custom action authoring |
| **Reporting** | Executive PDF exports, multi-run trend dashboards |
| **Federation** | Multi-lab scenario sync, central template registry |
| **Tool Integrations** | Splunk, Microsoft Sentinel, Dragos, Claroty connectors |

Roadmap is **customer-driven** — verticals and protocol additions are prioritized by deployed sites.

---

# Why PacketArch — In One Slide

- **Protocol-correct** where generic tools are not.
- **Vendor-realistic** down to MAC OUI and firmware string.
- **Repeatable** — same scenario, every time, every site.
- **Closed-loop** with Cyber Vision and your SOC tooling.
- **Operates air-gapped** — no cloud dependency required.
- **Auditable** — every attack run produces an evidence record.
- **Economical** — one platform replaces hardware labs, traffic contracts, and one-off red-team engagements.

---

# Call to Action

## Three ways to engage

1. **Executive demo** — 45 minutes, see a kill chain run end-to-end against a live SOC.
2. **Proof of value** — 30-day install in your lab, against your sensors, with your team.
3. **Strategic deployment** — multi-site rollout, training package, integration support.

**Contact:** `github.com/ip-aegis/PacketArch`

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank You

## PacketArch

**Protocol-Accurate OT Traffic Simulation — for the teams defending what runs the physical world.**

<span class="pill">Version 1.5</span> May 2026
