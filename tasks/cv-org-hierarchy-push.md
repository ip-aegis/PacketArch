# CV New-UI Org Hierarchy Push — 2026-08-12

## Findings (live audit against CV 5.5.x @ 10.120.1.75)

- 6 deployments in `running` state; 3 agents online.
- Only **1 of 10** scenarios (Electrical Substation IED Network) has a complete
  org-hierarchy tree in CV. Solar Farm has 7 custom networks but all sit at
  `Global` (the OH step never ran). 8 scenarios have no OH tree at all.
- **Blocker**: `Pharma — Vaccine Bioreactor Plant` truncates to
  `Pharma — Vaccine`, which carries a non-ASCII em dash. CV rejects non-ASCII
  OH names outright ("Name is invalid") → that scenario can never provision.
- OH level cap of 20 chars re-confirmed live (21 chars → 400 "only 20
  characters allowed for name"). Probe levels created and cleaned up.
- Word-boundary truncation is lossy and leaves dangling tokens:
  `Electrical` (10/20), `Rockwell` (8/20), `Point of`, `Aseptic Fill /`,
  `Purification (TFF`, `Solar Farm with`.
- Stale orphan tree `Water Treatment Plan` → `Water Control Net` from an
  earlier name of the Municipal Water scenario; no scenario references it, so
  reconcile would build a second tree beside it.
- Custom network names never get renamed on drift (matched by ipRange only):
  `10.2.2.0/24` is still `Water Control Network` but is now the `Intake Zone`.

## Plan

- [ ] 1. Rewrite `_oh_level_name` — ASCII-fold, then budget-aware compaction
      (phrase map → connector drop → generic-tail drop → longest-first word
      abbreviation → separator tighten → parenthetical drop → word truncate).
- [ ] 2. `provision_networks`: rename drifted networks via `update_networks`,
      scoped to ranges inside the scenario /16 (never CV built-ins).
- [ ] 3. `prune_orphan_oh_levels`: find candidates BEFORE reassignment (levels
      unreferenced by any scenario state holding a network inside a scenario
      /16), delete deepest-first AFTER, skipping any still holding
      networks/children. Wire to `POST /reconcile?prune_orphans=true`.
- [ ] 4. Unit-test the name compaction (no test coverage exists today).
- [ ] 5. Deploy backend, run the push, re-audit the live tree.

## Review

All 5 items done. Deployed (`backend` + `celery_worker` rebuilt) and verified
live.

**Code changes** (all in `cv_provisioning_service.py` unless noted):

1. `_oh_level_name` rewritten as an 8-step budget-aware compaction. 147 new
   unit tests in `backend/tests/test_cv_oh_level_names.py` pin the invariants
   (fits / ASCII / non-empty / no dangling token / idempotent) plus the specific
   reductions. Two ordering bugs found and fixed by the tests themselves:
   separator tightening is now only KEPT when it alone makes the name fit
   (otherwise it destroyed the word boundaries truncation needs —
   `Parcel Sorting Hub - 7/13/2026` → `Parcel Sort` instead of
   `Parcel Sort Hub`), and the final fallback is a greedy word fill rather than
   backing off to the previous boundary (`Solar Farm Batt` → `Solar Farm Batt
   Engy`, using the full 20).
2. `provision_networks` now realigns drifted network names via
   `update_networks`, scoped by the new `_range_within` predicate. Factored that
   containment check out of `_scenario_network_ids`, which had inlined it.
3. `find_orphan_oh_levels` / `prune_orphan_oh_levels`, wired to
   `POST /reconcile?prune_orphans=true` (opt-in — it is the only destructive
   part of a reconcile). Find runs before the push, prune after.
4. Empty-name fallbacks in `provision_org_hierarchy` so a name that ASCII-folds
   to nothing can't 400 an entire scenario.

**Two bugs the dry runs caught before any CV write:**

- `_range_within` used `subnet_of` against CV's whole network list, which
  includes IPv6 built-ins (`ff00::/8`) — `subnet_of` raises TypeError across
  address families. Now rejects version mismatches up front.
- **`Global` was flagged as an orphan candidate.** Solar Farm's 7 networks were
  parked at the root (its OH step had never run), and the root is referenced by
  no scenario — so it met both ownership tests. Deleting CV's root would have
  taken the entire hierarchy. Root levels are now excluded from the candidate
  seed, plus an independent root check in the deleter.

**Push result** (`prune_orphans=true`): 38 groups checked, 72 networks (0
created — all already existed, 2 renamed), 10/10 scenarios' OH trees
provisioned, 2 orphan levels deleted, 7 vertical presets rebuilt, 0 errors.
Re-running is a clean no-op (0/0/0/0), confirming idempotency.

**Live verification:**

- OH tree: 73 levels = Global + 10 scenario + 62 zone. Every scenario /16 sits
  at its scenario level, every zone /24 at its zone level. `Global` now holds
  only CV's 11 built-in ranges.
- Asset mapping, by CV's OWN `networkInterfaces[].networkName` attribution (not
  our prefix math): 242/242 simulated asset interfaces attributed to a
  PacketArch per-zone network, **zero** falling back to the built-in 10/8.
  242 = exactly the device count of the 6 scenarios with running deployments.
- The 4 scenarios with 0 CV assets (Parcel Sorting Hub, Pharma, Semiconductor
  Fab, Urban Intersection) are precisely the 4 with no running deployment — CV
  has never seen their traffic. Their hierarchy and subnets are now pre-staged,
  so assets will land correctly on first deploy.

**Not done / follow-ups:**

- Changes are deployed but UNCOMMITTED. Per repo convention this needs a PR, not
  a push to master.
- `pytest` is not in the backend runtime image; it had to be pip-installed into
  the container to run the suite (and is gone after the rebuild). Worth a dev
  target if tests are meant to be runnable on-box.
- `_OH_WORD_ABBREV` is hand-curated against the current template set. A new
  vertical with unfamiliar vocabulary falls through to word-fill truncation —
  correct and safe, just less readable. Extend the map as templates land.
- The v1 `/assets` endpoint (with `customProperties`, `functionalGroupId`,
  vulnerability counts) is live and useful but still unconsumed by PacketArch —
  a plausible next integration for pushing enrichment INTO CV.
