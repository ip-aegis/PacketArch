# CV 5.6 API Audit — plan

Trigger: dev CV Center at 10.10.20.115 upgraded to **5.6**. Audit every CV API
call PacketArch makes; keep the findings on file. Special attention: how
networks are created in the new UI.

## Authority for each half
- **New UI `/cvapi/v1`** — spec fetched live from the Center:
  `https://10.10.20.115/ui/cisco-cyber-vision-api-v4.json`, `info.version =
  1.0.0-5.6.0`. Document authority exists.
- **Classic `/api/3.0`** — the Center **no longer serves** its spec JSON (404 on
  every known path). Our on-file `cisco-cyber-vision-api-v3.json` is
  `3.0.0-5.4.0` and is now the only written record. **Live probe is the only
  authority for this half** — and it is where breakage risk actually lives
  (~27 call sites vs 6).

## Steps
- [x] Fetch + enumerate the 5.6 new-UI spec (13 paths)
- [x] Enumerate every CV call site in the codebase
- [x] Live read-only probe: new-UI `/oh`, `/networks`, `/assets*`
- [x] Live read-only probe: classic GET sweep (9 endpoints)
- [x] Resolve whether legacy `/api/1.0` still routes (group delete)
- [x] Probe the 3 `/devices/{id}` endpoints absent from the 5.4 spec
- [x] Write `docs/cyber-vision/API_AUDIT_5.6.md` (the on-file deliverable)
- [x] Save the 5.6 spec next to the 5.4 one; annotate the 5.4 one's vintage
- [x] Fix the defects found
- [x] Rebuild backend + celery_worker; review section

## Rules for this audit
- Live center with real labs attached (`local_labs.cv_center_id`). **Read-only**:
  no creating/deleting networks, OH levels, presets or groups.
- Write-only call sites get documented as **unverified**, never as verified.

## Findings (running)
1. **`POST /cvapi/v1/networks` → 405.** The new-UI API cannot create networks —
   GET only. Creation remains classic `POST /api/3.0/networks/`. Our code is
   already structurally right.
2. **`GET /api/3.0/devices/{id}/usersProperties` → 404 on 5.6** (all 4 spelling
   variants). `get_device_properties()` swallows the 404 and returns `[]`, so
   `enrich_device(skip_existing=True)` never skips → duplicate user properties
   accumulate on every enrichment run. **Real bug.**
3. Same network object reports `type: "OT Internal"` on classic and
   `type: "OT"` on new-UI. Different vocabularies per API; don't round-trip.
4. `/cvapi/v1/oh` `Link: rel="next"` is malformed — `http://<host>/oh?...`,
   missing the `/cvapi/v1` prefix and downgraded to http. We only regex the
   cursor out, so we're immune. Do not "fix" by following the URL.
5. `OrgHierarchyCreateResult` carries no `id`; provisioning already re-GETs. OK.
   But `create_oh_levels()`'s partial-success result is discarded by both
   callers, so CV's actual reason for a failure is lost.
6. Legacy `/api/1.0/group/{id}` DELETE still routes on 5.6; it is the only
   routed form (`?id=`, `/groups/{id}`, bare `/group` all 404).
7. **`limit`/`offset` silently ignored** — CV 5.6 pages only on `page`+`size`
   and otherwise returns the entire collection with a 200. **Real bug** in
   `get_flows` / `get_vulnerabilities`.

---

## Review

**Deliverables**
- `docs/cyber-vision/API_AUDIT_5.6.md` — the audit, written to be re-run after
  every CV upgrade (§9 has the procedure).
- `docs/cyber-vision/cisco-cyber-vision-api-v4-5.6.0.json` — the 5.6 new-UI spec.
- `docs/cyber-vision/cisco-cyber-vision-api-v3-5.4.0.json` — the old root-level
  spec, `git mv`'d and renamed so its 5.4 vintage is unmistakable. Nothing
  referenced it, so the move is safe. **Do not delete it** — CV 5.6 no longer
  serves a classic spec, so this is the only written record of that surface.

**Answer to the question asked.** Networks cannot be created through the new
UI API — `/cvapi/v1/networks` is GET-only (POST → 405, verified live).
Creation is still classic `POST /api/3.0/networks/`, which is what PacketArch
already does. No change needed. The one real trap is that the two APIs report
different `type` vocabularies for the same object ("OT" vs "OT Internal"), so
a new-UI network object must never be fed into a classic write.

**Code changes** (`cyber_vision_service.py`, `cyber_vision_v1_service.py`,
`cv_provisioning_service.py`)
1. `get_device_properties()` — was calling
   `GET /devices/{id}/usersProperties`, which **404s on 5.6**. The 404 was
   swallowed as "no properties", silently defeating `skip_existing` dedup. Now
   reads the `userProperties` field off `GET /devices/{id}`. Verified live.
2. `enrich_device_direct()` — add-failures logged at WARNING, not debug, so a
   dead write surface can't look like success.
3. `_log_oh_create_failures()` — `POST /oh` partial-success results were
   discarded; CV's own reason for a rejected level is now logged.
4. **`limit`/`offset` are silently ignored by CV 5.6** — it pages only on
   1-based `page`+`size` and otherwise returns the WHOLE collection with a
   200. `get_flows(limit=100)` was pulling all **71,718** flows;
   `get_vulnerabilities` all 3623. Both now go through a new `_paged_slice()`
   that requests `page`/`size` and slices (correct for a non-aligned `offset`,
   ≤2 requests). `get_devices`/`get_devices_raw` already used `page`/`size`
   and were never affected — confirmed by probe.
5. `enrich_device()`'s dedup reads `label` **or** `key`: no probed device had a
   populated `userProperties`, and the sibling arrays on the same payload use
   `key`, so a `label`-only read would have resurrected the bug.
4. Docstrings recording the 5.6 gotchas: GET-only `/networks`, the `type`
   vocabulary split, the malformed `/oh` `Link` header, create-returns-no-id,
   the spec example's bogus `pathId`, and the 500-network assign cap.

**Verification.** ~30 live endpoint/parameter combinations probed, all
non-mutating (the five `DELETE`s in probes 2-3 targeted a deliberately bogus
all-zero UUID purely to discriminate "route exists" from "route gone", on a
Center with zero groups — nothing could be removed); classic `/api/3.0` fully
alive with no consumed shape changed; `get_device_properties` fix exercised
against the live Center on both the real and 404 paths; the pagination fix
asserted live for bounded size, correct row identity across pages, and a
non-page-aligned offset; backend + celery_worker rebuilt, `/health` 200,
clean boot.

**Not done — needs a write against the shared live Center** (§8 of the audit):
re-verifying the 20-char/ASCII OH name cap on 5.6, and confirming
`POST /devices/{id}/usersProperties` still works. The second matters: if that
POST 404s like its GET sibling, CV device enrichment is dead on 5.6.

---

## Round 2 — "how is Data Center built vs Electrical", + the cap probe

**Data Center and Electrical are built identically.** Same call sequence, same
field values (`type`, `vlanId`, `duplicated`, `splitDevicesPerSensor`), one
network per level, no orphans; Electrical just has 6 zones to Data Center's 5.
The only difference is how much of the name the 20-char OH cap eats
(`Data Center Infrastructure` -> `Data Center`). Documented in §2.1 of the
audit, including the full old/new API sequence.

**The old/new mix is correct and forced** — networks can only be created
classic-side, the hierarchy only exists new-UI-side. Join verified safe: all 60
network ids identical across both APIs; `ipRange` unique; teardown correctly
deletes networks before levels and children before parents.

**Cap probe (operator-approved).** PATCH-rename one existing level, restore it.
Confirmed on 5.6:
- **20 chars exactly** — 20 accepted, 21 rejected
  (`"only 20 characters allowed for name"`). `OH_LEVEL_NAME_LIMIT` stays.
- **Charset is a whitelist, not "is it ASCII"** — accepted: alphanumerics,
  space, `#$%&'()*+,-./:@_`. Rejected with `"Name is invalid"`: `! " ; < = > ?
  [ \ ] ^ ` { | } ~` **and all non-ASCII**.

### Further bugs found and fixed in round 2

6. **16 plain-ASCII characters were passed straight through to CV.** The old
   `encode("ascii", "ignore")` fold only caught non-ASCII, so a scenario or
   zone name containing `[ ] { } | \ < > = ! ? ; " ~ ^ `` would 400 the
   `POST /oh` batch and take down that scenario's whole org-hierarchy phase —
   the em-dash failure mode again, via a path the fold never covered.
   `_oh_ascii()` now filters to the verified whitelist and maps the
   meaning-bearing rejects to accepted equivalents.
7. **A fully non-ASCII name folded to `""`**, which CV also rejects.
   `_oh_level_name` takes a `fallback`; callers pass `Zone <id>` /
   `Scenario <id>` so two such zones stay distinct.
8. **Sibling OH levels could collapse onto one another** (latent). The
   ` (scenario name)` suffix `_group_label` adds purely to deconflict is
   deleted wholesale by a 20-char word-boundary cut, so two zones in one
   scenario could resolve to the SAME level id — one level missing, both
   networks assigned into the other, no error.
   `_oh_level_names_for_siblings()` truncates the sibling set as a group:
   word cut -> hard cut -> numeric suffix, deterministic.
9. **Dangling separators** — `Process Control / Operations` -> `Process
   Control /`. Trailing punctuation trimmed.

**Verification.** 26 cases (every rejected character individually, full
printable ASCII, non-ASCII, empty, 12-case fuzz) sanitized and PATCHed into the
live Center — all accepted. Rename-safety precondition checked first: all 6
scenarios with CV state carry a persisted `scenario_level_id` + full `zones`
map (6 + 42 + Global = exactly the 49 live levels), so renames apply in place
and orphan nothing. Center re-dumped afterwards and confirmed **byte-identical
to the pre-probe snapshot** — 49 levels, 60/60 networks, no artifacts.

### Round 3 — last open item closed

**`POST /devices/{id}/usersProperties` WORKS on 5.6.** Probed in two stages:
a zero-risk route check first (schema-invalid body -> **500**, i.e. the handler
ran, vs **404** for a genuinely absent route — both baselines confirmed), then
an operator-approved add/read-back/delete round-trip. The sub-resource is
**write-only**: POST and `DELETE .../{propertyId}` both work, only the
collection GET is gone. CV device enrichment is NOT broken on 5.6.

10. **Confirmed the `key`/`label` asymmetry.** `add_device_property` POSTs
    `{"label", "value"}` but CV reads it back as `{"id", "key", "value"}` —
    the same spelling as the sibling `otherProperties`/`normalizedProperties`
    arrays. Reading only `label` yields a set of empty strings, so the
    `skip_existing` dedup would have stayed broken at a new address even after
    the endpoint fix. The defensive `label or key` read was necessary, and is
    now verified rather than assumed.

**End-to-end proof:** seeded a property, called
`enrich_device(skip_existing=True)` with that same label plus a new one — the
existing one was skipped (not duplicated), the new one added, both deleted
afterwards, `userProperties` back to `[]`.

**Regression tests:** `backend/tests/services/test_cv_oh_names.py` — 52 cases
pinning the 20-char cap, all 16 CV-rejected ASCII characters, the allowed
punctuation, the substitutions, never-empty/never-too-long, the dangling
separator, and both sibling-collision paths (suffix-truncation and
whitelist-collapse) plus determinism.

**Final regression sweep** on the rebuilt image, all 7 green: pagination
(7 rows, was 71718/3623), device-property read path, charset sanitizer,
never-empty names, sibling dedup, live CV acceptance of a sanitized nasty name,
and center integrity (49 levels / 60 networks / 0 artifacts).

**No open items remain.**
