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
- [ ] Left rail: device palette (search + click-to-place + drag)
- [ ] Inspector: selection-driven device/flow forms (sectioned)
- [ ] Protocol picker on connect
- [ ] IP auto-assign on device add
- [ ] Purdue auto-layout for unpositioned scenarios

## Later phases
- Phase 2: zones as containers, conduits, layouts, clusters
- Phase 3: Verify workspace (unified Health)
- Phase 4: Run workspace + copilot
- Phase 5: swap default, delete v1 shell
