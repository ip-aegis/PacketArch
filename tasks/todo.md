# Studio v2 Overhaul — Execution Tracker

Design doc: https://claude.ai/code/artifact/e7e65e37-a46f-474c-9b5d-2e0052bbe524
(Previous todo content — attack PCAP export — shipped in v1.12.0, see memory/attack_pcap_export_audit.)

## Phase 0 — Stop the bleeding (current studio) — DONE (commit 1a016df)
- [x] P0.1 Ctrl+S data loss → shared buildScenarioUpdatePayload() for autosave + Ctrl+S
- [x] P0.2 Device-delete undo cascade → deleteDeviceWithHistory() used by all 4 delete paths
- [x] P0.3 Marquee selection sync via onSelectionChange; Ctrl+A selects in React Flow too
- [x] Verified: Docker build (tsc) passed; deployed; committed + pushed

## Phase 1 — v2 core (in progress)
- [x] /studio2 unadvertised parallel route (src/studio2/Studio2Page.tsx)
- [x] Design token file (studio2/tokens.ts — surfaces, category accents, protocol edge palette, status)
- [x] OT glyph set v1 (studio2/glyphs.tsx — 22 glyphs, category + override mapping)
- [x] Scenario document store + command bus (studio2/document/documentStore.ts — undo by construction, coalesced drags, cascades enumerated in builders)
- [x] Single zod codec (studio2/document/codec.ts — load/autosave/Ctrl+S one path; definitionExtras round-trips unknown fields)
- [x] Canvas on new architecture: DeviceNode2 (3 LOD tiers, hover handles), FlowEdge2 (zoom-gated labels), ZoneNode2 (read-only), Studio2Canvas
- [x] Shell: TopBar (undo/redo, save state, workspace switcher) + BottomStrip (single zoom cluster)
- [x] Left rail: device palette (search, grouped, drag AND click-to-place, shift-click for rapid placement)
- [x] Inspector: selection-driven device/flow/scenario forms (sectioned, all edits undoable via command bus)
- [x] Protocol picker on connect (1 common → immediate; several → inline midpoint menu; none → rejected)
- [x] IP auto-assign on device add (coalesced into the add-device undo step)
- [x] Purdue auto-layout for unpositioned scenarios + tidy/layout actions
- [ ] Remaining Phase 1 polish: bulk edit, vendor/firmware/CVE sections in inspector

## Phase 2 — zones as containers (in progress)
- [x] Zones are React Flow parent containers: devices render as children (doc keeps absolute positions — v1/backend shape unchanged)
- [x] Drag a device in/out of a zone = membership change (undoable setDeviceZone command; smallest containing zone wins)
- [x] Zone drag moves members (moveZone command shifts member absolute positions in the same undo step)
- [x] Zone resize via NodeResizer (selected zones show handles; onResizeEnd dispatches updateZone)
- [x] Draw-zone tool: "Add zone" in rail → click canvas places 480×320 zone (shift-click repeats, Esc cancels)
- [x] Zone inspector form (name/type/Purdue level/subnet/VLAN + delete-zone-keeps-devices)
- [x] Zone delete cascade: members leave zone (not deleted), touching conduits removed — undoable
- [x] Conduit edges rendered (dashed, name/direction/protocol-count label) + read-only conduit inspector + delete
- [x] Rail/inspector toggle buttons in top bar
- [x] Conduit tool: click zone A → zone B (dedupe, Esc cancels) + full editor (name/direction/SL/protocol chips)
- [x] Group-by cluster view: zone/protocol/vendor/purdueLevel/deviceType via shared clusterGrouping utils; ClusterNode2 + AggregateEdge2; double-click expands in place; `g` cycles; bottom-strip select; view-only (position dispatches suppressed)

Phase 2 COMPLETE — /studio2 at full Build parity with v1 (minus vendor/firmware/CVE inspector sections, tracked in Phase 1 polish)

## Later phases
- Phase 3: Verify workspace (unified Health)
- Phase 4: Run workspace + copilot
- Phase 5: swap default, delete v1 shell
