# CV 5.6 — empty communications map remediation

Plan: /home/rocsmith/.claude/plans/sparkling-exploring-eich.md
Spec: uploads/CV-5.6-Communications-Map-Remediation.md

## 0. Confirm the /scv surface
- [ ] BLOCKED: needs CV UI credentials for 10.10.20.115 (operator to supply).
      Read-only probes already done: /scv exists, center_type=standalone,
      both API tokens 401 on /scv, groupId on /cvapi/v1/networks is the OH
      level (60/60) so there is no token-only asset-group detector.

## 1. UI credentials on each Center
- [x] models/cyber_vision_center.py: ui_username + ui_password columns
- [x] alembic revision add_cv_center_ui_creds (down_revision add_cyber_vision_centers)
- [x] cv_centers: create_center / update_center / to_summary / ui_client / cv_ui_client
- [x] schemas/cyber_vision.py: CVCenterCreate / Update / Response
- [x] routes/cyber_vision.py: keyword pass-through (create + update)
- [x] frontend: api/cyberVision.ts types + CyberVisionTab fields (prefill username!)

## 2. The /scv UI session client
- [x] services/cyber_vision_ui_service.py: center-type probe, form-encoded u/p
      login, check_session CSRF from response header, shared cookie jar,
      one re-auth on 401 / CSRF-403 with a FRESH csrf token
- [x] methods: import_networks_csv, list_asset_groups, delete_networks,
      network_details, test_connection

## 3. Creation via CSV import
- [x] _csv_rows() with csv.writer + UTF-8 (names carry commas and em dashes)
- [x] _create_networks(center, svc, to_create) -> warnings; 3 outcomes
- [x] _net_item: strip the name (the /16 umbrella is currently unstripped)
- [x] provision_networks: result["warnings"]; reconcile_cv_networks aggregation

## 4. Repair script
- [x] cli/repair_cv_networks.py: dry-run report (4 checks) + --scenario X --apply
- [x] scripts/cv-repair-networks.sh wrapper
- [x] assert asset group GONE after delete, before create

## 5. Docs
- [x] API_AUDIT_5.6.md: correct §2, add §10
- [x] tasks/lessons.md entry
- [x] move the spec into docs/cyber-vision/
- [x] CLAUDE.md: third credential kind

## 6. Verify
- [x] backend suite in a throwaway container
- [x] alembic single head; upgrade + downgrade
- [x] docker compose up -d --build backend celery_worker frontend

## Review

Everything except §0 is done; §0 needs credentials only the operator has.

**What shipped**

- `cyber_vision_centers` gains `ui_username` + `ui_password` (Fernet, never
  returned), resolved only through the new `cv_centers.ui_client` /
  `cv_ui_client`. Both halves or neither. Migration `add_cv_center_ui_creds`,
  single alembic head before and after, applied live on boot.
- `services/cyber_vision_ui_service.py` — the `/scv` session client. Modelled
  on `CMLService`, with the two mechanics that precedent does not hint at:
  form-encoded `u`/`p` login, and a CSRF token read from `check_session`'s
  response header, re-fetched (never reused) after a re-auth because it is
  bound to the `_gorilla_csrf` cookie.
- `cv_provisioning_service._create_networks` — CSV import with a classic
  fallback. No creds or a failed import falls back and warns; a *partial*
  import warns and deliberately does NOT fall back. Warnings ride out on
  `provision_networks()["warnings"]` and aggregate into the reconcile
  response, so they are visible beyond the log.
- `_net_item` now strips the name. The spec claimed this was already done; it
  was not — zone names came pre-stripped from `_group_label`, the scenario /16
  umbrella name did not.
- `app/cli/repair_cv_networks.py` + `scripts/cv-repair-networks.sh`. Read-only
  report by default (the four checks); `--scenario X --apply` repairs one
  scenario and refuses to sweep. Detector is **presence in the asset-group
  list by name**, never `interfaceCount` — a /16 umbrella legitimately reports
  zero interfaces.
- Frontend: two fields in the Center editor plus a "UI login" tag. The
  username is prefilled on edit (unlike the secrets) or saving an edit would
  silently clear it.
- Docs: audit §2 corrected, §8 reopened, new §10; two `lessons.md` entries;
  spec moved into `docs/cyber-vision/`; CLAUDE.md gained the third credential
  kind and a fix to the test recipe.

**Decisions worth knowing**

- **Teardown still uses the classic delete.** Whether a classic DELETE removes
  a CSV-created network's asset group is unmeasured, and changing the
  destructive path on an inference buys risk for unreported map clutter. The
  repair script's assert-gone step is what will produce the evidence — that
  assert is a correctness requirement anyway, since a surviving asset group
  turns the follow-up create into a no-op upsert.
- **Repair heals in-script** rather than deferring to
  `POST /cyber-vision/reconcile`, because that route sweeps every scenario on
  every center — the opposite of the spec's "one scenario at a time, do not
  sweep". It calls the two existing scenario-scoped functions, passing
  `networks_state=` explicitly (the default path reads a stale ORM attribute).

**Verified**

- Full backend suite green: 1255 passed, 2 xfailed. New file
  `tests/services/test_cv_networks_csv.py` (19 tests) covers the CSV builder
  (including comma/em-dash quoting), the three fallback outcomes asserted on
  the classic fake's call count, and the client's login/CSRF mechanics via
  `httpx.MockTransport`.
- `tsc --noEmit` clean. GPL headers present on all new files.
- Deployed: `backend`, `celery_worker`, `frontend` rebuilt; migration ran.
- Repair script exits 2 with the right message against the live Center, which
  has no UI credentials yet.
- Read-only probes against `.115` confirmed the premise: `/scv` is live,
  `center_type=standalone`, both API tokens 401 on `/scv`, and
  `groupId` on `/cvapi/v1/networks` is the OH level (60/60 vs our stored
  state) — so no token-only detector exists.

**Not done**

- §0. The `/scv` login flow, the CSRF dance and the CSV column list are
  implemented from the spec's description, not yet from a live authenticated
  round trip. With UI credentials for `.115`: confirm
  `GET /scv/4.0/networks/csv/sample` matches `CSV_COLUMNS`, confirm the
  asset-group list is missing all 60 networks, then repair one scenario with
  `--apply` and verify.
