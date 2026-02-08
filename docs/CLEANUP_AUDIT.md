# PacketArch Codebase Cleanup Audit

**Date**: 2026-02-08

## Context
The codebase has grown organically across backend, frontend, and infrastructure layers. This audit identifies duplicate code, redundant processes, dead files, and inconsistent patterns — organized by effort level so you can pick off quick wins immediately or plan larger refactors.

---

## Quick Wins (1-2 hours each)

### ~~Q1. Delete Root-Level Cruft Files~~ DONE

~~7 stale markdown/text files at repo root serve no purpose.~~

**Completed**: All 8 files deleted.

### ~~Q2. Delete Legacy Deploy Scripts (+ Hardcoded Credentials)~~ DONE

~~Three root-level deploy scripts with hardcoded production passwords.~~

**Completed**: Deleted `auto_deploy.py`, `run_deploy.py`, `deploy.py`, plus `sftp_upload.py` and `test_ai_scenario.py` (also had hardcoded creds).

### ~~Q3. Sync Static Agent docker-compose.agent.yml~~ DONE

~~`backend/app/static/agent/docker-compose.agent.yml` is **outdated** — missing Docker socket volume mount, `SSL_VERIFY`, and `AGENT_INSTALL_PATH`.~~

**Completed**: Overwritten static copy with canonical `docker/packetarch-agent/docker-compose.agent.yml`.

### ~~Q4. Fix Inconsistent Error Extraction in Frontend~~ DONE

~~6 components use raw `err?.response?.data?.detail` instead of `extractErrorMessage()`.~~

**Completed**: Replaced raw access with `extractErrorMessage()` in AgentsTab.tsx, AgentDetailsDrawer.tsx (3 locations), GenerateDescriptionModal.tsx, ExternalCommPanel.tsx. PcapUploadPanel.tsx was already deleted. `useScenarioMutations.ts` intentionally kept (structural error inspection for 409 handling).

### ~~Q5. Remove Vendor Normalization Re-export~~ DONE

~~`services/fingerprint_cache.py` re-exports `normalize_vendor` for "backwards compat".~~

**Completed**: Removed `# noqa: F401` re-export comment. Import kept since `normalize_vendor` is used locally within the file. No external callers were importing it from `fingerprint_cache`.

### ~~Q6. Delete Empty Placeholder Template Files~~ DONE

~~`energy.py` and `oil_gas.py` in `scenario_templates/` were empty dicts.~~

**Completed**: Deleted both files. Removed imports and dict entries from `scenario_templates/__init__.py`.

---

## Medium Projects (half-day to 1 day each)

### ~~M1. Delete the Legacy `docker/traffic-generator/` Container~~ DONE

~~This entire directory is superseded by `docker/packetarch-agent/`.~~

**Completed**: Deleted `docker/traffic-generator/` (~5,362 lines). Added deprecation comment to `TRAFFIC_GENERATOR_IMAGE` in `docker_service.py`. Updated 7 doc files to redirect references to `unified_orchestrator.py`. Removed PCAP Learning Pipeline section and stale entries from `CLAUDE.md`.

### ~~M2. Consolidate Backend Serial/Identifier Services~~ DONE

~~Three overlapping services handling device identifiers.~~

**Completed**: Kept three files (serial_number_generator, unique_identifier_generator, device_identity_enricher) but eliminated duplication:
- Extracted shared `device_hash()` to `serial_number_generator.py`, imported by `unique_identifier_generator.py`
- Added `skip_existing` flag to enricher, allowing `agent_manager.py` to reuse it (deleted 140-line duplicate function)
- Simplified `scenario_enricher.py` to delegate to enricher functions (deleted ~120 lines)
- ~260 lines eliminated total

### ~~M3. Extract Backend API Helpers (get-or-404, pagination)~~ DONE

~~Duplicate get-or-404 and pagination patterns across 20+ route files.~~

**Completed**: Created `api/helpers.py` with `get_or_404()`, `get_or_404_where()`, and `paginate()`. Refactored 8 route files:
- `scenarios.py` (8 ownership lookups + 1 pagination)
- `agents.py` (8 lookups + 1 pagination)
- `anomalies.py` (8 lookups)
- `docker_hosts.py` (5 lookups)
- `scenario_versions.py` (7 lookups + 1 pagination)
- `devices.py` (4 lookups + 1 pagination)
- `protocols.py` (3 lookups + 1 pagination)
- `users.py` (3 lookups)
- ~200 lines eliminated across route files

### ~~M4. Centralize Protocol Metadata~~ DONE

~~BACnet vendor IDs in `bacnet/types.py` duplicate data from `vendor_oui.py`.~~

**Completed**: Moved `BACNET_VENDOR_IDS` from `bacnet/types.py` to `vendor_oui.py` (alongside existing `ODVA_VENDOR_IDS` and `PROFINET_VENDOR_IDS`). Updated imports in `bacnet/__init__.py`, `bacnet/engine.py`, and `test_bacnet.py`.

### ~~M5. Frontend: Consolidate Inline Styles into Theme Constants~~ DONE

~~Repeated color values and layout patterns across 15+ components.~~

**Completed**: Created `frontend/src/constants/theme.ts` with 17 named color constants (`TEXT_BODY`, `TEXT_PARAGRAPH`, `TEXT_MUTED`, `BG_CARD`, `BG_PANEL`, `BORDER_DEFAULT`, etc.) plus composite style objects (`CARD_STYLE`, `CODE_BLOCK_STYLE`). Refactored 17 files:
- 12 help content files (replaced identical `CARD_STYLE` patterns, `TEXT_PARAGRAPH`, `ACCENT_BLUE`, etc.)
- 5 worst-offender components (`RightSidePanel`, `ExternalCommPanel`, `RealisticSettingsPanel`, `IPManagementPage`, `FingerprintingLibraryPage`)
- ~200 inline hex color occurrences replaced with named constants

### ~~M6. Frontend: Scatter Constants into `constants/` Directory~~ DONE

~~Constants scattered across components.~~

**Completed**: Three sub-tasks:
- **PROTOCOL_COLORS duplication fixed**: Two conflicting maps (7 protocols with Cisco colors in `constants/protocols.ts` vs 13 protocols with Ant Design colors in `utils/formatUtils.ts`). Expanded canonical `PROTOCOL_COLORS_EXTENDED` to 18 protocols, added `PROTOCOL_LABELS` map, and `getProtocolColor()`/`getProtocolLabel()` helpers. Deleted duplicates from `formatUtils.ts`. Updated 5 consumer files.
- **Phase constants**: Created `constants/phases.ts` with `PHASE_NAME_MAP` and `DEFAULT_LIVE_DURATIONS` extracted from `DeploymentForm.tsx`.
- **Backend MAX_DEVICES_PER_SCENARIO**: Created `backend/app/core/constants.py`, updated 4 backend files to import from canonical location.

---

## Challenging Projects (1-3 days each)

### ~~C1. Frontend: Generic Zustand Store Factory~~ DONE

~~8+ stores repeat identical CRUD + loading + error patterns.~~

**Completed**: Created `stores/createResourceStore.ts` factory with `createResourceSlice()` that generates fetch/create/update/delete actions with configurable field names. Refactored 3 stores:
- `dockerHostsStore.ts` (158 → 93 lines) — full CRUD via factory
- `deploymentsStore.ts` (190 → 147 lines) — fetch/delete via factory, custom start/stop/polling
- `agentsStore.ts` (273 → 207 lines) — fetch-one/update/delete via factory, custom pagination/sub-resources

Remaining stores (`settingsStore`, `attackStore`, `scenarioStore`, etc.) are too specialized for the CRUD pattern. ~174 lines eliminated, zero component changes needed (public APIs preserved).

### ~~C2. Frontend: Generic API Client Factory~~ DONE

~~27 API files with repetitive CRUD patterns (~4,000 lines).~~

**Completed**: Created `api/createCrudApi.ts` factory (~60 lines) that generates `list/get/create/update/delete` methods with configurable `updateMethod` (`'patch'` | `'put'`). Output satisfies the existing `ResourceApi<T,C,U>` interface from `createResourceStore.ts`, completing the two-layer DRY pattern: `createCrudApi()` → API object → `createResourceSlice()` → store. Refactored 5 API files using spread-and-extend pattern:
- `dockerHosts.ts` (78 → 40 lines) — full CRUD via factory (`updateMethod: 'put'`), keep testConnection + listInterfaces
- `devices.ts` (90 → 55 lines) — CRUD via factory, override list for filter params, keep duplicate + getDeviceTypes
- `deployments.ts` (105 → 75 lines) — partial factory (get + delete only), non-standard start/stop kept custom
- `scenarios.ts` (306 → 265 lines) — CRUD core via factory, override list (filters) + delete (force param), keep 8 custom methods
- `agents.ts` (222 → 175 lines) — CRUD core via factory (`updateMethod: 'put'`), override list (pagination) + create (wider return type), keep 14 custom methods

Remaining 21 API files too specialized for the factory pattern (SSE streaming, key-based APIs, bespoke queries, etc.). ~170 net lines saved.

### ~~C3. Frontend: Reusable UI Scaffolding Components~~ DONE

~~13 panel components (~7,700 lines) repeat the same structure: loading/error/empty states + content.~~

**Completed**: Created 4 focused composable components in `components/common/` (+ barrel re-export) instead of a monolithic DataPanel wrapper:
- `PanelContainer` — scrollable flex-column wrapper (configurable gap/padding)
- `ErrorAlert` — dismissible error banner with compact mode
- `LoadingSpinner` — centered Spin with configurable size/padding
- `EmptyState` — icon + message + hint with theme constants

Refactored 9 panel components:
- `RealisticSettingsPanel.tsx` — 3x EmptyState, 2x LoadingSpinner, 1x PanelContainer
- `DeploymentPanel.tsx` — 1x PanelContainer, 1x ErrorAlert (compact), 1x EmptyState
- `PropertyPanel.tsx` — 2x EmptyState
- `RightSidePanel.tsx` — 1x PanelContainer, 1x EmptyState
- `AgentsTab.tsx` — 1x ErrorAlert
- `DockerHostsTab.tsx` — 1x ErrorAlert
- `AttackPanel.tsx` — 4x PanelContainer
- `AnomalyPanel.tsx` — 1x PanelContainer, 2x LoadingSpinner
- `ExternalCommPanel.tsx` — 1x PanelContainer, 1x LoadingSpinner

~150 net lines saved across the 9 files.

### ~~C4. Split Large Frontend Components~~ DONE

~~10 components exceed 450 lines.~~

**Completed**: After analysis, only 1 of 7 components had a natural extraction seam — the rest were already well-organized, delegated to child components, or would suffer from prop drilling if split further.
- Extracted `DeploymentCard` (190 lines) from `DeploymentPanel.tsx` into its own file (`deployment/DeploymentCard.tsx`), reducing DeploymentPanel from 747 → 504 lines
- `AgentsTab` (662): already delegates to AgentDetailsDrawer/AgentInstallDrawer — leave as-is
- `ExternalCommPanel` (645): cohesive CRUD panel, splitting would cause prop drilling — leave as-is
- `RealisticSettingsPanel` (462): already uses shared hooks, small sections — leave as-is
- `AgentDetailsDrawer` (551): already delegates to 4 child card components — leave as-is
- `DeploymentForm` (517): splitting forms makes them harder to follow — leave as-is
- `AgentInstallDrawer` (504): documentation content, no logic to extract — leave as-is

---

## Moonshots (1+ weeks, architectural)

### ~~X1. Split `device_templates.py` into Vendor Modules~~ DONE

~~At **19,267 lines**, this single file contains 290 device templates as Python dataclasses.~~

**Completed**: Restructured 19,267-line monolith into a package with 24 files:
- Infrastructure: `_types.py` (dataclasses), `_helpers.py`, `_registry.py`, `_api.py`, `_fingerprints.py`, `__init__.py`
- 18 vendor modules under `vendors/`: 11 per-vendor files (siemens, rockwell, schneider, honeywell, abb, yokogawa, cisco, emerson, ge, sel, hms) + 7 industry-grouped files (building_automation, transportation, process_instruments, robotics_logistics, fieldbus_networking, it_ot_boundary, japanese_plc)
- Largest file is now `vendors/siemens.py` at 3,303 lines (down from 19,267)
- Zero import changes needed — `__init__.py` re-exports all 26 public symbols
- Fixed 4 vendor naming inconsistencies (Johnson_Controls, Endress_Hauser, Delta_Controls, Automated_Logic)
- All 295 unique templates preserved, 541 tests passing

### ~~X2. Unify Protocol Engine Extractors~~ N/A

~~6 protocol extractors in `ai_services/extractors/`.~~

**Moot**: The entire `ai_services/extractors/` package was deleted as part of the PCAP Learning Pipeline removal.

### ~~X3. Move `learning.py` Business Logic to Service Layer~~ N/A

~~`api/routes/learning.py` is 1,321 lines.~~

**Moot**: `learning.py` and `learning_service.py` were both deleted as part of the PCAP Learning Pipeline removal.

---

## Summary

| Tier | Items | Status | Est. Lines Saved | Est. Time |
|------|-------|--------|-------------------|-----------|
| Quick Wins (Q1-Q6) | 6 | ALL DONE | ~600 deleted, ~50 fixed | 1 day |
| Medium (M1-M6) | 6 | ALL DONE | ~6,000 | 3-4 days |
| Challenging (C1-C4) | 4 | ALL DONE | ~3,000 | 1-2 weeks |
| Moonshots (X1-X3) | 3 | X1 DONE; X2, X3 N/A (learning pipeline deleted) | restructure ~25,000 | 2-4 weeks |
