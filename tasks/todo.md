# Studio v2 Overhaul — Execution Tracker

Design doc: https://claude.ai/code/artifact/e7e65e37-a46f-474c-9b5d-2e0052bbe524
(Previous todo content — attack PCAP export — shipped in v1.12.0, see memory/attack_pcap_export_audit.)

## Phase 0 — Stop the bleeding (current studio)
- [ ] P0.1 Ctrl+S data loss: explicit-save omits cell_isolation / broadcast_traffic_enabled / clean_demo_mode → single shared payload serializer for autosave + Ctrl+S (ScenarioStudioPage.tsx)
- [ ] P0.2 Device-delete undo loses cascaded flows; 2 of 4 delete paths have no undo at all → shared deleteDeviceWithHistory() used by onNodesDelete, DeviceContextMenu, CanvasControls, command palette
- [ ] P0.3 Marquee/multi-select never reaches uiStore → wire onSelectionChange; Ctrl+A also selects in React Flow
- [ ] Verify: typecheck + build; deploy (docker compose up -d --build frontend); commit

## Phase 1 — v2 core (next)
- [ ] /studio2 route behind feature flag
- [ ] Design token file (single palette; category/protocol/status channels)
- [ ] OT glyph set v1 (~24 SVG glyphs)
- [ ] Scenario document store + command bus (undo by construction)
- [ ] Single zod codec (load/autosave/Ctrl+S/versions)
- [ ] Shell: top bar / left rail / bottom strip / inspector skeleton
- [ ] Devices + flows + selection + autosave on new architecture

## Later phases
- Phase 2: zones as containers, conduits, layouts, clusters
- Phase 3: Verify workspace (unified Health)
- Phase 4: Run workspace + copilot
- Phase 5: swap default, delete v1 shell
