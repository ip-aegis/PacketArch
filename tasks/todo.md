# Attack PCAP Export + Kill-Chain Timing Fix

## Context / findings
- Attack traffic already registers in the PCAP path via `GenerationRequest.attack_playbook_id`,
  and attack packets are tagged `flow_id="__attack__<action_type>"`.
- **Critical bug:** attack stage advancement + action-firing use wall-clock `time.monotonic()`
  (`attack_orchestrator.py:219,361,412`). This is CORRECT for the live agent (virtual time lags
  wall clock ~10× — see agent v1.23.2 / v1.41.0) but WRONG for PCAP timed mode, which drains the
  heap in a fraction of wall time. Result today: baked-attack PCAPs render only stage 0's first
  action. The fix must be mode-aware (virtual clock in timed/PCAP mode, wall clock in live mode).
- User decisions: (1) two files from one run — baseline + attack-only (+ combined/regular);
  (2) no labels sidecar for now; (3) fix the timing bug as part of this feature.

## Plan

### Part A — Mode-aware kill-chain timing (prerequisite; protocol_engines)
- [ ] `attack_orchestrator.py`: replace wall-clock `_stage_start_monotonic` elapsed with a
      mode-aware clock. Add `virtual_time: bool` (default False) set at construction/registration.
      - timed/PCAP: elapsed = (current_time_ms - _stage_start_ms)/1000
      - live/perpetual: keep `time.monotonic()` (unchanged behavior)
      Track `_stage_start_ms` (set wherever `_stage_start_monotonic` is set: schedule_initial_events,
      start cmd, _advance_stage). Store `self._current_time_ms` for get_state_snapshot in virtual mode.
- [ ] Time-compression so the WHOLE kill chain fits the requested PCAP window: scale effective
      per-stage duration so a 30-min playbook renders inside a 5-min PCAP. Keep warmup scaling.
- [ ] `unified_orchestrator.register_attack_orchestrator`: pass `virtual_time=(self.duration_ms is not None)`.
- [ ] Test: short PCAP + multi-stage playbook; assert ALL stages + >1 action fire.

### Part B — Two-file (split) PCAP output (backend, mostly not agent-staged)
- [ ] `protocol_engines/output.py`: extend `PacketOutput.write_packet` with `is_attack: bool = False`
      (PcapOutput/LiveOutput accept + ignore). Add `SplitPcapOutput` holding up to 3 PcapWriters
      (combined/baseline/attack), routing by `is_attack`.
- [ ] `unified_orchestrator.py` (2 write sites): pass `is_attack=event.flow_id.startswith("__attack__")`.
- [ ] `traffic_generator/orchestrator.py` (GenerationConfig): optional attack/baseline output paths;
      build `SplitPcapOutput` when attack export requested, else single `PcapOutput`.
- [ ] `traffic_generator/tasks.py`: compute 3 filenames; return artifact list.

### Part C — Job model + API + schema
- [ ] `models/generation_job.py`: add `artifacts` JSON column; keep `output_filename` = combined.
      Alembic migration.
- [ ] `schemas/generation.py`: add `export_attack_pcap: bool = False`; add `artifacts` to response.
- [ ] `api/routes/generation.py`: download gains `?artifact=combined|baseline|attack` (default combined).
      Validate playbook present when export_attack_pcap=True.

### Part D — Frontend
- [ ] `GeneratePcapModal.tsx`: "Also export attack-only PCAP" toggle (only when playbook selected);
      per-artifact download buttons on completion.
- [ ] `api/generation.ts`: thread `export_attack_pcap`; `downloadPcap(jobId, filename, artifact)`.

### Part E — Version + verify + deploy
- [ ] Bump `docker/packetarch-agent/app/version.py` → 2.2.0 (protocol_engines touched; live on-wire
      behavior unchanged — timing fix + split output are PCAP-only).
- [ ] Backend tests; generate attack PCAP end-to-end; verify 3 files + full kill chain.
- [ ] `docker compose up -d --build backend frontend` (dev == prod).

## Review

Done + verified 2026-07-01 (agent → 2.2.0):

- **Part A (timing):** mode-aware clock in `attack_orchestrator.py` — virtual
  (`current_time_ms`) for timed/PCAP, wall-clock for live. `set_virtual_time_mode`
  wired from `unified_orchestrator.register_attack_orchestrator`. Time-compression
  (`_apply_time_compression`) fits the whole kill chain in the PCAP window with a
  margin so the last stage completes. Fixed a **2nd bug**: `_resolve_targets` only
  read the frontend device shape → PCAP path (flat shape) got zero targets → zero
  attack packets; now accepts both. Fixed double-warmup in `schedule_initial_events`.
- **Part B (split output):** `SplitPcapOutput` routes by the `__attack__` flow tag;
  `PacketOutput.write_packet` gained `is_attack`; 2 write sites in
  `unified_orchestrator` pass it; `TrafficOrchestrator.generate` builds it when
  `export_attack_pcap` + a playbook are set.
- **Part C:** `generation_jobs.artifacts` JSON column (+ migration
  `add_gen_job_artifacts`), `export_attack_pcap` on `GenerationRequest`, `artifacts`
  on response, `/download?artifact=combined|baseline|attack`.
- **Part D:** `GeneratePcapModal` "Also export attack-only PCAP" toggle (enabled only
  with a playbook) + per-artifact download buttons; `generation.ts` types + artifact
  download param.
- **Part E:** version → 2.2.0; migration applied; backend+frontend+worker rebuilt/deployed.

Verification:
- Engine test (`tests/protocol_engines/test_attack_pcap.py`): all stages render
  (network_recon 4/4, triton_like 6/6 compressed into 90s), packets tagged is_attack.
- End-to-end SplitPcapOutput: 3 valid PCAPs, baseline+attack == combined.
- Full pipeline (real scenario, Celery task): combined 7904 = baseline 6498 + attack 1406,
  3 artifacts persisted to job.
- `tsc -b` clean for both edited frontend files (repo has unrelated pre-existing TS errors).

Audit follow-ups NOT done (brainstorm, deferred): DB-backed/portable + AI-authored
playbooks; ground-truth label sidecar; deterministic/seeded target selection;
closed-loop IDS detection scoring; attack-runs table; campaign chaining.
