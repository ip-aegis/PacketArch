# Push to Cyber Vision — auto preset + zone groups

Goal: one button (and a deploy-time "Provision CV" checkbox) → PacketArch creates a CV
preset scoped to the scenario's /16 (mirroring "Segmented Manufacturing"), then ~10 min
later polls CV and creates one group per scenario zone with the right devices.

Verified CV write contract (live 2026-06-16): see memory cv_groups_presets_write_api.

## Backend
- [ ] cyber_vision_service.py: `_request` gains `api_version` param (group delete is /api/1.0)
- [ ] cyber_vision_service.py: NOISE_EXCLUDE_TAGS constant (7 tags from Segmented MFG)
- [ ] cyber_vision_service.py: create_preset / delete_preset / create_group / delete_group /
      patch_group_members / get_devices_raw / cv_service_from_settings factory
- [ ] services/cv_provisioning_service.py: subnet lookup, preset meta builder,
      criticalness mapping, provision_preset(), provision_groups() (poll-until-stable)
- [ ] traffic_generator/tasks.py: `provision_cyber_vision` Celery task (poll + create groups)
- [ ] routes/cyber_vision.py: POST /provision/{scenario_id} (preset now + enqueue groups),
      GET /provision/{scenario_id}/status
- [ ] schemas/agent.py: DeploymentCreate.provision_cyber_vision: bool
- [ ] routes/agents.py deploy: if provision flag + CV configured → preset + enqueue groups

## Frontend
- [ ] api/cyberVision.ts: provisionScenario(), getProvisionStatus()
- [ ] DeploymentForm.tsx: "Provision to Cyber Vision" checkbox (gated on CV configured)
- [ ] DeploymentPanel.tsx: pass provision flag through deploy
- [ ] Manual "Push to Cyber Vision" button + status surface (CyberVisionPage)

## State
Stored in scenario.definition["cyber_vision"] = {preset_id, preset_label, status,
groups:{zone_id:cv_group_id}, device_count, error, updated_at}.

## Status: DONE (2026-06-16) — deployed (backend+frontend+celery_worker rebuilt)
All backend + frontend tasks complete. py_compile + tsc clean.

## Verify — DONE
- [x] Lint/typecheck backend + frontend (tsc clean, py_compile clean)
- [x] Backend modules import in container; celery worker registered packetarch.provision_cyber_vision
- [x] E2E preset: scenario "Strict Purdue Segmented Manufacturing" (10.2.0.0/16) →
      preset created in CV, subnet filter + 7 noise tags applied, 577-char desc
      LLM-summarized to exactly 180 chars, state persisted; preset deleted on cleanup.
- [ ] Live group phase (needs a running agent so CV discovers devices) — write
      methods themselves verified via contract round-trip (create/patch/delete all 200).

## Review
- 180-char description cap added per user: LLM summarization (AITask.DESCRIPTION_GENERATION)
  with word-boundary truncation fallback; hard [:180] guard in create_preset.
- CV-integration + phase status surfaced via shared CyberVisionBadge in BOTH the
  deployment area (studio DeploymentCard + Deployments table) and live-traffic
  dashboard card; backend adds `cyber_vision` summary to deployment + dashboard payloads.
- Phase already shown by existing PhaseTimeline/KillChainTimeline on the cards.
