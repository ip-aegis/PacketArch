# Cyber Vision 5.6: Empty Communications Map — Cause, Fix, and Repair Procedure

**Date:** 2026-09-15
**Applies to:** Cyber Vision Center **5.6.0+** with PacketArch **1.19.3 or earlier**
**Status:** root cause confirmed by Cisco; PacketArch fix implemented.

> **Provenance.** This document was written against an off-site MXD
> deployment, and its §5 "Reference result" table describes the two Centers
> repaired there — not any lab Center. The PacketArch-side fix it specifies is
> now implemented (`services/cyber_vision_ui_service.py`,
> `cv_provisioning_service._create_networks`,
> `scripts/cv-repair-networks.sh`); see `API_AUDIT_5.6.md` §10 for the
> engineering account and for what is measured versus still assumed. Two
> claims in §4/§6 were aspirational when written and are true only as of the
> implementation: name stripping at generation, and the per-Center UI
> credentials.

---

## TL;DR

After upgrading a Cyber Vision Center to 5.6, the new UI's **communications map**
(`/ui/#/communications`) shows little or nothing for PacketArch scenarios, even
though every network, group and Organization Hierarchy level looks correct and
Cyber Vision has clearly seen the traffic.

The cause is not PacketArch state drift. CV 5.6 moved network creation into the
new UI, and a network created through the **classic** `POST /api/3.0/networks/`
API — which is what PacketArch used — **is not written to the CV database
correctly**. It lists in both APIs and assets are even attributed to it, but CV
never creates the network's **asset group**, and the communications map groups on
asset groups. A network with no asset group cannot appear on the map.

Two consequences:

1. **Recreating networks and the org hierarchy does not help.** Those objects
   were never the problem.
2. **Re-importing an existing bad network does not repair it.** Only a *create*
   materializes the asset group, so repair means delete-then-create.

---

## 1. Symptom

On an affected Center:

- The communications map is empty, or shows only one or two zones out of dozens.
- Everything else looks healthy. On the Center this was diagnosed against:
  - 79 of 79 expected networks present, correct name, type and IP range
  - 80 Organization Hierarchy levels, no duplicates, every network assigned to
    its level
  - all zone groups populated with components
  - 364 assets, every simulated one attributed to a per-zone network by CV's own
    `networkInterfaces[].networkName`
  - flows present and timestamped to the minute

- Exactly the zones that *do* render are the ones with an asset group. On that
  Center, 2 of 79 networks had one — and those two were the only two the
  operator could see.

This is why the problem is easy to misdiagnose: every check PacketArch and the
classic API can perform comes back clean.

---

## 2. Root cause

The communications map is driven by `POST /scv/4.0/communications/asset-groups`.
Its companion `…/controls` call returns the groups the map is able to plot, and
on an affected Center that list contains only the CV built-ins plus whichever
networks happen to have been registered properly.

CV materializes one **asset group** per properly-registered network:

```json
{
  "groupId": "dade974c-343f-5421-948c-35eaddc099bd",
  "name": "Intake Zone",
  "description": "Network group for subnet: Intake Zone (10.2.2.0/24)",
  "type": "network",
  "groupOrigin": "system",
  "interfaceCount": 8
}
```

Per Cisco: CV 5.6.0 moved network creation to the new UI and removed network
configuration from the classic UI, but kept the classic API. Creating a network
through that API does not populate the database correctly, and the map is the
visible casualty. **That route is being deprecated and there is no API
replacement planned for some time.** The supported automation path is the new
UI's **CSV import**.

### Measured behaviour

Verified against two live 5.6 Centers:

| Operation | Asset group created? | Notes |
|---|---|---|
| classic `POST /api/3.0/networks/` | **No** | network lists fine, assets attributed, map blank |
| classic `PUT /api/3.0/networks/` with identical values | **No** | change-impact preview `0/0`, nothing changes |
| new-UI CSV import — **create** | **Yes** | immediate, with all member interfaces |
| new-UI CSV import — **upsert** of an existing bad row | **No** | returns `updated:1` and repairs nothing |

The last row is the trap. Re-importing looks like success and fixes nothing.

---

## 3. How to check your own install

Log in to the Center's new UI API and list asset groups:

```bash
# 1. Log in. NOTE: form-encoded u/p, not JSON (see §6).
curl -sk -c /tmp/cvj -X POST "https://<center>/scv/1.0/login" \
  --data-urlencode 'u=<user>' --data-urlencode 'p=<password>'

# 2. List asset groups.
curl -sk -b /tmp/cvj \
  "https://<center>/scv/4.0/asset-group?type=all&hasParent=false"
```

Every PacketArch network name should appear in `items[]`. Any that does not is
invisible on the communications map.

A healthy Center shows one entry per scenario network. Typical breakage looks
like nine or ten entries, all CV built-ins (`10/8 private network`,
`IPv4 multicast`, …) with `interfaceCount: 0`, and none of your zones.

> The `/16` scenario umbrella networks legitimately show `interfaceCount: 0`.
> The per-zone `/24`s are more specific, so CV attributes assets to those. A
> `/16` with no interfaces is expected, not a fault.

---

## 4. The fix in PacketArch

Network **creation** now goes through the new UI's CSV import. Reads stay on the
classic API, which lists both kinds of network identically.

### New per-Center credentials

CV UI network creation requires a real UI **session**, not an API token, so each
Cyber Vision Center now carries UI login credentials alongside its two API
tokens:

- **Settings → Cyber Vision → (edit a Center)** → *UI username* / *UI password*
- The password is encrypted at rest and never returned by the API. The username
  is returned, so you can see which account a Center uses.
- Both halves are required; a Center with only one is treated as unconfigured.

These are a third, distinct credential kind:

| Credential | Used for |
|---|---|
| Classic API token | `/api/3.0` — reads, presets, groups, network *reads* |
| New UI API token | `/cvapi/v1` — Organization Hierarchy, network reads |
| **UI username + password** | **`/scv/4.0` — network creation via CSV import** |

### Behaviour without UI credentials

Creation falls back to the classic API and logs a warning stating that the
networks will not render on the communications map. This is deliberate: a
half-registered network still serves the classic UI and asset attribution, so
falling back beats failing the deploy. The same fallback applies if the UI
import itself fails.

A *partial* import (fewer `created` than requested) warns but does **not** fall
back, because an `updated` row does not repair a bad network.

---

## 5. Repair procedure for an existing install

Networks created before the fix are already registered incorrectly. A CSV
upsert will not repair them — they must be deleted and created again.

**Read this before starting:**

- Recreating a network gives it a **new id**. Organization Hierarchy membership
  is keyed by network id, so **every repaired network returns to `Global` and
  must be re-assigned.** Skipping this step leaves the hierarchy flat.
- PacketArch's stored network ids (in
  `scenario.definition['cyber_vision']['networks']`) also become stale and must
  be re-resolved. They are keyed by IP range, so re-running provisioning
  resolves them without creating anything.
- Between the delete and the create, assets in that range fall back to CV's
  built-in `10/8`.
- Work **one scenario at a time** and verify before continuing. Do not sweep.

### Order of operations

1. **Add UI credentials** for the Center (Settings → Cyber Vision).
2. **Record the current state** — asset groups, and each network's OH level.
3. **Skip anything already working.** A network that already has an asset group
   needs no repair; leave it alone.
4. **Per scenario:**
   a. `DELETE /scv/4.0/networks` with `{"idList": [...]}` for that scenario's
      broken networks.
   b. `POST /scv/4.0/networks/csv` with that scenario's rows (see §6 for the
      format).
   c. **Verify** every range came back *and* its asset group now exists. Stop
      if anything is missing.
5. **Re-resolve ids and re-assign the hierarchy.** Re-run network provisioning
   (creates nothing — everything now exists) and then org-hierarchy
   provisioning, passing the freshly-resolved network state.
6. **Verify the whole Center** — see §7.

### Reference result

Applied to two Centers, per-scenario, with verification between each:

| | Center A | Center B |
|---|---|---|
| Networks repaired | 77 | 15 |
| Asset groups before → after | 11 → 88 | 10 → 25 |
| Networks present / with asset group / on expected OH level / ids in sync | 79/79 | 16/16 |
| Networks left at `Global` | 0 | 0 |
| Duplicate OH levels | 0 | 0 |

Every create returned `{"created":N,"updated":0,"skipped":0,"errors":[]}`.

---

## 6. Reference: the new UI network surface

`/scv/4.0` is the UI's own private API. None of it is in the published
OpenAPI spec, and it can change in any CV release.

| Call | Purpose |
|---|---|
| `GET /scv/3.0/center-type` | `standalone` or `CVSM` — decides the login route |
| `POST /scv/1.0/login` | login for a standalone Center |
| `POST /scv/4.0/login` | login for a CVSM Center |
| `GET /scv/1.0/check_session` | **returns the CSRF token** (see below) |
| `GET /scv/4.0/networks/csv/sample` | the CSV template — authoritative column list |
| `POST /scv/4.0/networks/csv` | multipart `file`; upserts by `ip_range` |
| `DELETE /scv/4.0/networks` | body `{"idList": [...]}` |
| `GET /scv/4.0/network/{id}/details` | one network incl. `orgHierarchy`, `totalAssetsCount` |
| `GET /scv/4.0/asset-group?type=all&hasParent=false` | asset groups — the health check |
| `GET /scv/4.0/oh/groups` | OH tree with `impactRating`, `networksCount`, `sensorsCount` |

### Two auth mechanics that are not guessable

**1. The login body is form-encoded, not JSON.** The field names are `u` and
`p`:

```
u=<user>&p=<password>
```

Sending JSON returns `401 INVALID_CREDENTIALS` regardless of how correct the
credentials are, which reads exactly like a wrong password.

**2. Writes require a gorilla/csrf token.** CV's backend is Go and uses
gorilla/csrf. `GET /scv/1.0/check_session` sets the `_gorilla_csrf` cookie **and
returns the matching token in the `x-csrf-token` response header**. Every
`/scv/4.0` write must echo that value in the `x-csrf-token` *request* header.
The cookie value on its own is **not** the token. Without the header:

```
403 Forbidden - CSRF token not found in request
```

### CSV format

From CV's own template (`GET /scv/4.0/networks/csv/sample`):

```
ip_range,type,name,vlan_id,Location,Department
10.1.0.0/24,OT Internal,Factory Floor,,Building A,Manufacturing
192.168.1.0/24,IT Internal,Office Network,100,Building B,IT
172.16.0.0/12,External,External Partners,,,
```

- Required columns: `ip_range`, `type`, `name`, `vlan_id`.
- **Any further columns become custom properties** on the network — useful for
  stamping scenario, zone, or Purdue level.
- `type` uses the **classic** vocabulary — `OT Internal`, `IT Internal`,
  `External`. This is *not* the new-UI API's reading of the same field, which
  reports `OT` for the same object. Feeding it `OT` mistypes the network.
- **CV trims whitespace in `name`.** A scenario name with a trailing space comes
  back trimmed, so any name-keyed comparison against CV will mismatch.
  PacketArch now strips names at generation for this reason.
- The response is `{"created": N, "updated": N, "skipped": N, "errors": [...]}`.
  Check `created` — `updated` does not repair a bad network.

---

## 7. Verification

After any repair or upgrade, check all four of these — the first three can all
pass while the map stays empty:

1. **Networks exist** — every expected range present (classic `GET /networks/`).
2. **Asset group exists** for each — `GET /scv/4.0/asset-group`. *This is the
   one that detects the 5.6 problem.*
3. **Assigned to the right OH level**, not parked at `Global` — check `groupId`
   on `GET /cvapi/v1/networks` against the expected level id.
4. **PacketArch's stored ids match CV** — stale ids cause
   `404 Network IDs not found` on hierarchy assignment.

---

## 8. Known limitations and open items

- **The `/scv/4.0` dependency is a workaround, not a supported integration.**
  Cisco has not committed to a replacement API timeline. It may break on any CV
  upgrade, and the failure is *silent* — the classic fallback "works," so the
  next regression will again only be visible as an empty map. Re-run the §7
  checks after every CV upgrade.
- **Repair is not automatic.** Because it requires deleting networks and
  re-applying hierarchy assignments, PacketArch does not do it implicitly during
  provisioning. It is a deliberate operator action.
- **Organization Hierarchy level names** are capped by CV at 20 characters with
  a restricted character set, so long scenario and zone names are shortened and
  can read poorly (`Solar Farm with`, `Point of`). This is a separate, cosmetic
  issue from the map problem.
- **Asking Cisco:** if CSV import took the *create* path for an already-present
  `ip_range`, repairs would need no deletes at all. Worth requesting.

---

## 9. Related documentation

- `docs/cyber-vision/API_AUDIT_5.6.md` — full CV 5.6 API audit. Section 2 carries
  a correction about classic network creation; section 10 covers this issue in
  engineering detail.
- `tasks/lessons.md` — why a complete, passing audit still missed this, and the
  practices added as a result.
