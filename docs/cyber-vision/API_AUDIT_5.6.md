# Cisco Cyber Vision API Audit — CV 5.6

**Audited:** 2026-09-14 against the dev Center at `10.10.20.115` (CV **5.6**).
**Method:** the new-UI spec was fetched from the Center; the classic surface was
**live-probed**, because the Center no longer publishes its spec (see below).
**Scope:** every CV API call PacketArch makes. Call sites were enumerated by
grepping `_request(` — including the calls whose endpoint is built into a
variable first (`get_devices_raw`'s
`/presets/{id}/visualisations/networknode-list`), which a literal-path grep
alone would miss.

Re-run this audit after every CV Center upgrade.

---

## 1. The two API surfaces

PacketArch talks to two coexisting, independently-versioned CV APIs on the same
host. They use the same header name (`x-token-id`) but **separate token
stores** — a classic token is rejected by the new API and vice versa. Both
tokens live on the `cyber_vision_centers` row (`api_token`, `new_ui_token`).

| | Classic | New UI |
|---|---|---|
| Base path | `/api/3.0` | `/cvapi/v1` |
| Client | `services/cyber_vision_service.py` | `services/cyber_vision_v1_service.py` |
| Call sites | ~27 | 6 |
| Spec on file | `cisco-cyber-vision-api-v3-5.4.0.json` | `cisco-cyber-vision-api-v4-5.6.0.json` |
| Spec version | `3.0.0-5.4.0` (**stale — CV 5.4**) | `1.0.0-5.6.0` (current) |
| Authority | **live probe only** | published spec |

### The classic spec is no longer served

CV 5.6 returns 404 for every known classic-spec path (`/ui/…-v3.json`,
`/api/3.0/swagger.json`, `/api/3.0/openapi.json`, `/doc/`). The copy in this
directory is the **5.4 vintage** and is now the only written record of a
surface we depend on heavily. Treat it as a historical reference, not as truth
for 5.6 — it is already known to be incomplete (§5).

### Filename vs. version — do not be misled

The new-UI spec is served as `cisco-cyber-vision-api-**v4**.json` but declares
`basePath: /cvapi/**v1**/` and `info.version: 1.0.0-5.6.0`. The `v4` in the
filename is a UI asset name, **not** an API version. The API is still v1. No
client change is implied by that filename.

Source: `https://10.10.20.115/ui/cisco-cyber-vision-api-v4.json`
UI page: `https://10.10.20.115/ui/#/configuration/api`

---

## 2. Headline: how networks are created in the new UI

**The new-UI API cannot create networks.** `/cvapi/v1/networks` is **GET-only** —
confirmed live, not just inferred from the spec:

```
POST    /cvapi/v1/networks  -> 405 Method Not Allowed
OPTIONS /cvapi/v1/networks  -> 405 Method Not Allowed
GET     /cvapi/v1/networks  -> 200
```

Across all 13 new-UI paths the only network *writes* are
`PUT /oh/{levelId}/networks` (assign an **existing** network to a hierarchy
level) and the custom-properties CRUD. Network creation, update and deletion
remain exclusively on classic `POST|PUT|DELETE /api/3.0/networks/`.

> **CORRECTION (2026-09-15).** The paragraph below was wrong, and §10 is the
> full account. Classic network creation is not merely the only route — on
> 5.6 it is **broken**. The network is created and assets are attributed to
> it, but CV never materializes the network's **asset group**, and the new
> UI's communications map groups on asset groups, so the network is invisible
> there. Networks are now created through the new UI's **CSV import**
> (`POST /scv/4.0/networks/csv`), with the classic call kept only as a
> fallback. Reads are unaffected.

~~**PacketArch is already structurally correct here**: `cv_provisioning_service`
creates networks on the classic API and uses the new-UI API only to read them
back and assign them into the Organization Hierarchy. No change required.~~

### The same network reports a different `type` on each API

This is the one genuine trap. For network `113b80a5-…` ("Semiconductor Fab —
300mm Wafer Line", `10.1.0.0/16`):

| API | `type` |
|---|---|
| classic `/api/3.0/networks/` | `"OT Internal"` |
| new-UI `/cvapi/v1/networks` | `"OT"` |

Two vocabularies for one field on one object. **Never round-trip a network
object from the new-UI API into a classic write** — it will change the type.
Writes must use the classic vocabulary (`OT Internal` / `IT Internal` /
`External`); `cv_provisioning_service.DEFAULT_NETWORK_TYPE = "OT Internal"` is
correct.

The two APIs also expose different fields for the same object:

- classic: `{id, name, type, ipRange, vlanId, duplicated, splitDevicesPerSensor}`
- new-UI: `{id, name, type, ipRange, vlanId, duplicated, groupId, customProperties}`

`groupId` (the assigned OH level) and `customProperties` are **new-UI only**;
`splitDevicesPerSensor` is **classic only**. Neither API is a superset.

---

## 2.1 How PacketArch actually builds a scenario in CV (the old/new mix)

Verified against the live Center, 2026-09-14. Provisioning a scenario touches
**both** APIs, in this order (`services/cv_provisioning_service.py`):

| # | Step | API | Call |
|---|---|---|---|
| 1 | Create the /16 + each zone /24 as custom networks | **classic** | `POST /api/3.0/networks/` (batch, array body) |
| 2 | Resolve the new network ids | **classic** | `GET /api/3.0/networks/`, matched on `ipRange` |
| 3 | Read the hierarchy, find `Global` | **new-UI** | `GET /cvapi/v1/oh` |
| 4 | Create the scenario level, then the zone levels | **new-UI** | `POST /cvapi/v1/oh` |
| 5 | Re-read to learn the new level ids | **new-UI** | `GET /cvapi/v1/oh` (create returns no `id`) |
| 6 | Assign each network to its level | **new-UI** | `PUT /cvapi/v1/oh/{levelId}/networks` |

**This mix is correct and there is no alternative.** Networks can only be
created on the classic API (§2), and the Organization Hierarchy exists only on
the new-UI API. The two halves are joined by the network **id**, and that join
is safe: all 60 network ids are **identical across both APIs** (verified — the
sets are equal). `ipRange` is unique across all 60, so the step-2 resolve is
unambiguous.

### Data Center vs. Electrical — built identically

Both are the same shape: a parent level holding the scenario /16, with one
child level per zone holding that zone's /24.

```
Global
 * Data Center  <- Data Center Infrastructure [10.6.0.0/16]
    * Cooling Control     <- Cooling Control Network   [10.6.1.0/24]
    * DCIM Core Network   <- DCIM Core Network         [10.6.0.0/24]
    * External/Internet   <- External/Internet (...)   [10.6.99.0/24]
    * Power Distribution  <- Power Distribution Network[10.6.2.0/24]
    * Rack Monitoring     <- Rack Monitoring Network   [10.6.3.0/24]
 * Electrical   <- Electrical Substation IED Network [10.4.0.0/16]
    * Bay Control Network <- Bay Control Network       [10.4.1.0/24]
    * Feeder Protection   <- Feeder Protection Network [10.4.2.0/24]
    * Revenue Metering    <- Revenue Metering Network  [10.4.4.0/24]
    * Substation LAN      <- Substation LAN            [10.4.0.0/24]
    * Transformer         <- Transformer Protection Net[10.4.3.0/24]
    * WAN/SCADA Backhaul  <- WAN/SCADA Backhaul        [10.4.99.0/24]
```

Field-by-field the network objects are indistinguishable — same `type`
(`OT Internal` classic / `OT` new-UI), `vlanId=None`, `duplicated=False`,
`splitDevicesPerSensor=False`, one network per level, no orphans. Electrical
simply has 6 zones to Data Center's 5.

**The only real difference is the level NAME**, and it is not a per-scenario
behaviour — it is the 20-char OH cap eating different amounts of each:

| Classic-side name (full) | New-UI OH level |
|---|---|
| `Data Center Infrastructure` | `Data Center` |
| `Electrical Substation IED Network` | `Electrical` |
| `Municipal Water Treatment Plant` | `Municipal Water` |
| `Strict Purdue Segmented Manufacturing` | `Strict Purdue` |
| `Semiconductor Fab — 300mm Wafer Line` | `Semiconductor Fab` |

A **word-boundary** cut can land far below 20 characters — `Data Center
Infrastructure` loses 15 chars, not 6 — which is why the new UI looks so much
terser than the classic side. 25 of the 60 names are shortened this way.
**This divergence is expected**, but see the defect below.

The names also diverge by **character set**, not just length. Classic networks
and groups accept 60 chars and the full character set; OH levels accept 20
chars and only a whitelist (§3). So a zone named `Zone [A]` becomes network
`Zone [A]` but OH level `Zone (A)`:

| | Length cap | Character set |
|---|---|---|
| classic network / group name | 60 | unrestricted |
| new-UI OH level name | **20** | whitelist — `[ ] { } \| \ < > = ! ? ; " ~ ^ `` rewritten |

**Never join the two sides on the name string.** They are deliberately
different renderings of the same thing; the join is the network **id**, which
is identical across both APIs.

### Defect: sibling levels could collapse onto one another

`_group_label` deconflicts a zone name reused across scenarios by appending
` (scenario name)` — that suffix is the *only* thing distinguishing
`External/Internet (Data Center Infrastructure)` from
`External/Internet (Heat & Hot-Water …)`. The 20-char word-boundary cut then
**deletes the suffix wholesale**: both become `External/Internet`.

Today that is harmless because those two sit under *different* parents, and
`_match_existing_oh_level` keys on `(parentLevelId, name)`. But two zones in
the **same** scenario whose names agree in the first ~20 characters
(`Process Control / Operations` and `Process Control / Safety` both cut to
`Process Control /`) would both resolve to the **same level id**: one zone
level silently missing, and both zones' networks assigned into one. Nothing
errors.

No current scenario collides: all 49 live levels were checked for duplicate
`(parentLevelId, name)` pairs and none exist, and re-truncating the 60 live
network names per scenario /16 produces no collisions either. So this is
**latent, not active**. Fixed anyway: `_oh_level_names_for_siblings()` now
truncates the sibling set as a group and, on collision, falls back to a hard
cut (which keeps exactly the characters the word cut discarded —
`Process Control / Op` vs `Process Control / Sa`), then to a numeric suffix.
Deterministic, so re-provisioning does not churn level names, and renames go
through the persisted level id so nothing is orphaned.

> **Why the rename is safe here.** `_match_existing_oh_level` prefers the
> persisted id and only falls back to matching on `(parentLevelId, name)`. A
> changed name would therefore create a DUPLICATE level for any scenario whose
> `definition['cyber_vision']['org_hierarchy']` is missing or stale. Checked:
> all 6 scenarios carrying CV state have a persisted `scenario_level_id` and a
> full `zones` map (5+6+10+6+9+6 = 42 zone levels, +6 scenario levels, +Global
> = exactly the 49 levels live on the Center). Every level is reachable by id,
> so the renames apply in place. **Re-check this before any future change that
> alters generated OH names.**

Also fixed: a word-boundary cut could leave a dangling separator —
`Process Control / Operations` → `Process Control /`. Trailing punctuation is
now trimmed (`Process Control`). This renames one existing level on the next
reconcile.

---

## 3. New UI `/cvapi/v1` — 13 paths, 6 consumed

| Path | Methods | PacketArch | Live result |
|---|---|---|---|
| `/oh` | GET, POST | `get_oh_levels`, `create_oh_levels` | 200 ✅ |
| `/oh/{levelId}` | PATCH, DELETE | `rename_oh_level`, `delete_oh_level` | route ok, writes unverified |
| `/oh/{levelId}/networks` | PUT | `assign_networks_to_level` | route ok, write unverified |
| `/networks` | GET | `get_networks` | 200 ✅ |
| `/networks/{id}/custom-properties` | GET, POST | — | not consumed |
| `/networks/{id}/custom-properties/{pid}` | GET, PATCH, DELETE | — | not consumed |
| `/assets` | GET | — | 200 ✅ (not consumed) |
| `/assets/alerts` | GET | — | 200 ✅ (not consumed) |
| `/assets/vulnerabilities` | GET | — | 200 ✅ (not consumed) |
| `/assets/vulnerabilities/{cveId}` | GET | — | not consumed |
| `/assets/{id}/custom-properties` | GET, POST | — | not consumed |
| `/assets/{id}/custom-properties/{pid}` | GET, PATCH, DELETE | — | not consumed |
| `/assets/{id}/vulnerabilities/acknowledgement` | POST, DELETE | — | not consumed |

The unconsumed surface is **intentional**, not drift — the client wraps only
what provisioning needs. See §7 for what is worth picking up.

### Verified response shapes (live, 5.6)

`GET /oh` → `{centerId, items[], pageSize, totalCount}`, item:

```json
{ "id": "…", "name": "AMHS - Material", "description": "",
  "parentLevelId": "…", "hierarchy": "Global/Semiconductor Fab/AMHS - Material" }
```

> **The spec's own example is wrong here.** It shows `pathId: "/"` and the
> endpoint description says "pagination using pathId". The live 5.6 Center
> returns **`hierarchy`** and no `pathId` at all. Our client keys on
> `hierarchy` / `parentLevelId` and is correct. Trust the probe, not the
> example. The `OrgHierarchyItem` *definition* (as opposed to the example)
> also says `hierarchy`, so only the example is at fault.

The root `Global` level has **no** `parentLevelId`. `totalCount` was 49.

`GET /networks` → `{items[], pageSize}` — note **no `totalCount`** on this one.

### Gotcha: the `/oh` pagination `Link` header is malformed

```
Link: <http://10.10.20.115/oh?cursor=MTc0&max=3>; rel="next"
```

The URL is missing the `/cvapi/v1` prefix **and** is downgraded to `http`.
Following it verbatim would hit a 404 (or plaintext). `/networks` returns a
correct URL, so this is an `/oh`-specific server bug.

`_paginated_get()` regexes **only the cursor value** out of the header and
rebuilds the request itself, so PacketArch is immune. **Do not "simplify" that
code to follow the Link URL** — it would break `/oh` pagination.

### Gotcha: create returns no ids

`OrgHierarchyCreateResult` is `{message, name, parentLevelId}` — there is **no
`id`**. You cannot learn a new level's id from the create response; you must
re-`GET /oh` and match on `(parentLevelId, name)`.
`provision_org_hierarchy` already does exactly this. Correct as written.

`POST /oh` also supports **partial success** (`successCount` / `failedCount` /
`results[]`), so a 201 does **not** mean every level was created.

### OH level-name rules — CONFIRMED on 5.6

Probed directly by PATCH-renaming one existing level and restoring it
(reversible in one call; creates and deletes nothing). Both rules are still in
force on CV 5.6, and the charset rule is **much stricter than "ASCII"**:

**Length: exactly 20 characters.** 20 accepted, 21 rejected. The boundary is
exact and the message names it:

```
PATCH /cvapi/v1/oh/{id}  {"name": "<20 chars>"} -> 204
PATCH /cvapi/v1/oh/{id}  {"name": "<21 chars>"} -> 400
    {"message":"only 20 characters allowed for name"}
```

`OH_LEVEL_NAME_LIMIT = 20` is therefore correct and must stay.

**Charset: a whitelist, not "is it ASCII".** Swept character by character:

| | Characters |
|---|---|
| **Accepted** | letters, digits, space, and `#$%&'()*+,-./:@_` |
| **Rejected** (`"Name is invalid"`) | `!` `"` `;` `<` `=` `>` `?` `[` `\` `]` `^` `` ` `` `{` `\|` `}` `~` — plus all non-ASCII |

Every character in that reject list is **plain ASCII**, so the old
`encode("ascii", "ignore")` fold passed them straight through to CV. Any
scenario or zone name containing one would 400 the `POST /cvapi/v1/oh` batch
and **take down the whole org-hierarchy phase for that scenario** — the same
failure mode previously seen with an em dash, just via a path the ASCII fold
did not cover. Note `(` `)` `&` `/` `-` ARE accepted, which is why existing
names like `Heat & Hot-Water` and `Fab Operations / MES` work.

**Fixed:** `_oh_ascii()` now filters to the verified whitelist, mapping the
meaning-bearing rejects to accepted equivalents (`[` `]` `{` `}` → `(` `)`,
`\` `|` → `/`, `"` `` ` `` → `'`) and everything else to a space, rather than
deleting a word separator outright.

**Also fixed:** a fully non-ASCII name (`日本語ゾーン`) folded to the empty
string, and CV rejects `""` just as it rejects a bad character. `_oh_level_name`
now takes a `fallback`, and callers pass something identity-bearing (`Zone
<zone-id>` / `Scenario <id>`) so two such zones stay distinct. Note the
fallback fires only on a name that folds to **nothing** — a name made entirely
of rejected punctuation folds to a shorter punctuation string, which CV
accepts, so it keeps that rather than taking the fallback.

**Interaction worth knowing:** the whitelist can *collapse* names that used to
differ (`Zone [A]` and `Zone {A}` both become `Zone (A)`), so the sibling
dedup's hard-cut step can no longer separate them — the difference is gone
before truncation runs. The numeric-suffix step catches these. Verified for
brackets-vs-braces, pipe-vs-backslash, `<=?`-vs-`>=!`, quote-vs-backtick, a
three-way collapse, and a collapse behind a >20-char shared prefix: all stay
distinct, within 20 chars, and deterministic.

**Verified:** 26 cases — every rejected character individually, the full
printable-ASCII string, non-ASCII, empty, and a 12-case fuzz — sanitized and
then PATCHed into the live Center. CV accepted every one; the probe level was
restored to `Rack Monitoring` and re-read to confirm.

---

## 4. Classic `/api/3.0` — live probe results

**The classic API is fully alive on 5.6 and no consumed response *shape* has
changed.** Every GET below returned 200 with the fields our code reads.
Response shape is not the same as pagination behaviour, though — see the
`limit`/`offset` defect in §4.1.

| Endpoint | Result | Notes |
|---|---|---|
| `GET /networks/` | ✅ 200 | 60 items, shape unchanged |
| `GET /presets` | ✅ 200 | 37 items, `filters.{tags,groups,networks,…}` intact |
| `GET /groups` | ✅ 200 | empty list (no groups on this Center) |
| `GET /devices` | ✅ 200 | shape unchanged |
| `GET /devices/{id}` | ✅ 200 | shape unchanged; see §5 |
| `GET /components` | ✅ 200 | 8182 items |
| `GET /flows` | ✅ 200 | 71591 items |
| `GET /vulnerabilities` | ✅ 200 | 3623 items |
| `GET /sensors` | ✅ 200 | 10 items |
| `GET /deployments` | ✅ 200 | 6 items, `deploymentTokens[]` intact |
| `POST /networks/check` | ✅ 200 | `{nbExternalCommToRemove, nbCmpToRemove}` |

**Not probed (writes against a live Center):** `POST/PUT/DELETE /networks/`,
`POST /presets`, `DELETE /presets/{id}`, `POST /presets/{id}/refreshData`,
`POST /groups`, `PUT /groups/{id}`, `POST /devices/{id}/label`,
`POST/PUT/DELETE /devices/{id}/usersProperties…`, `DELETE /sensors/{id}`.
These are **unverified on 5.6**, not verified.

### 4.1 Defect: `limit` / `offset` are silently ignored

CV 5.6 honours **1-based `page` + `size`** and nothing else. `limit` and
`offset` are accepted, ignored, and the **entire collection** is returned with
a 200 — no error, no truncation:

| Request | Rows returned |
|---|---|
| `GET /flows` (no params) | 71718 |
| `GET /flows?limit=5` | **71718** |
| `GET /flows?limit=5&offset=5` | **71718** |
| `GET /flows?page=1&size=5` | 5 ✅ |
| `GET /flows?page=2&size=5` | 5 ✅ (different first id) |
| `GET /vulnerabilities?limit=5` | **3623** |
| `GET /vulnerabilities?page=1&size=5` | 5 ✅ |
| `GET /components?limit=5` | **8182** |
| `GET /devices?limit=5` | 10 (the default page) |

`get_flows()` and `get_vulnerabilities()` passed `limit`/`offset`, so
`GET /api/v1/cyber-vision/flows?limit=100` — an endpoint whose own validation
promises `le=500` — was pulling **all 71k flows** into memory and returning
them all. **Fixed:** both now translate through `_paged_slice()`, which
requests `page`/`size` and slices the window (correct even for a
non-page-aligned `offset`, at most two requests).

`get_devices()` and `get_devices_raw()` already used `page`/`size` and were
**never affected** — `get_devices_raw`'s auto-pagination was probed and pages
correctly on 5.6. `get_components()` takes no page size and fetches the whole
collection by design (8182 rows here); it is unchanged but worth bounding if
it is ever put on a hot path.

### Legacy `/api/1.0` still routes — for group delete only

`delete_group()` uses `DELETE /api/1.0/group/{id}` (singular, legacy). A major
upgrade is exactly when such a path disappears, so it was probed directly.
It survives, and **our form is the only one that routes**:

| Call | Result |
|---|---|
| `DELETE /api/1.0/group/{id}` ← what we send | **400** (handler ran) |
| `DELETE /api/1.0/group?id={id}` | 404 |
| `DELETE /api/1.0/groups/{id}` | 404 |
| `DELETE /api/1.0/group` | 404 |
| `GET /api/1.0/presets` | 404 — `/api/1.0` is not generally routed |

The 400 carries a CV-shaped body (`{"status":"error","message":"Missing
required parameter : \"id\""}`), i.e. the route exists and the handler rejected
the deliberately-bogus all-zero UUID. The delete path itself was not exercised
(the Center has no groups to delete). **Keep this call as-is.**

---

## 5. Defect found: device user-properties

`GET /api/3.0/devices/{id}/usersProperties` returns **404 on CV 5.6.** All
spelling variants were tried and all 404:

```
/usersProperties  404      /userProperties   404
/properties       404      /usersproperties  404
```

The 5.4 spec on file does not document this endpoint either, nor
`POST /devices/{id}/label` or `DELETE /devices/{id}/usersProperties/{pid}` —
these three call sites were always undocumented.

**The properties still exist** — they are embedded in the device detail
response. `GET /api/3.0/devices/{id}` returns a `userProperties` field
(singular "user") alongside `otherProperties` and `normalizedProperties`.

### Impact

`get_device_properties()` catches the 404 and returns `[]`. So
`enrich_device(skip_existing=True)` computes an empty `existing_labels` set and
**re-adds every property on every run** — silently, with no error.

Blast radius is currently limited: `enrich_device()` has **no callers**. The
live enrichment route (`api/routes/cyber_vision.py:862`) uses
`enrich_device_direct()`, which does no dedup at all.

### RESOLVED: the sub-resource is WRITE-ONLY, not gone

The open worry was that `add_device_property()` POSTs to the same
sub-resource whose GET is now missing — if that POST 404'd too, CV device
enrichment would be entirely dead on 5.6 and `enrich_device_direct` would
swallow it at debug level.

**It is not dead.** Probed in two stages:

1. *Zero-risk route check* — POST with a schema-invalid body returns **500**
   ("internal error": the handler ran and choked on the body), whereas a
   genuinely absent route returns **404** (verified against both a known-dead
   route and a known-live one). So the POST route exists.
2. *Full round-trip* (operator-approved) — add a property, read it back,
   delete it:

```
POST   /devices/{id}/usersProperties        -> 200, property id returned
GET    /devices/{id}  .userProperties       -> [{"id":…,"key":"PKTAUDIT-probe","value":…}]
DELETE /devices/{id}/usersProperties/{pid}  -> OK, userProperties back to []
```

So on CV 5.6 this sub-resource is **write-only**: `POST` and
`DELETE .../{propertyId}` both work; only the collection `GET` is gone.

### The field is `key` on read, `label` on write

`add_device_property()` POSTs `{"label": …, "value": …}`, but CV reads the
property back as **`{"id", "key", "value"}`** — matching the sibling
`otherProperties` / `normalizedProperties` arrays on the same payload.

This is exactly what would have re-broken the dedup at a new address: reading
only `label` off those entries yields a set of empty strings, so
`skip_existing` would still have re-added everything. `enrich_device()` reads
`label` **or** `key`.

**Verified end to end** against the live Center: seed a property, then call
`enrich_device(skip_existing=True)` with that same label plus a new one — the
existing one is skipped (not duplicated), the new one is added, and both are
cleaned up afterwards.

### Fixes applied

- `get_device_properties()` now reads `userProperties` from
  `GET /devices/{id}` instead of the dead sub-resource. **Caveat:** every
  device on the probed Center has an empty `userProperties`, so the shape of a
  *populated* entry is unverified. The sibling arrays on that same payload
  (`otherProperties`, `normalizedProperties`) use `{key, value}`, not
  `{label, value}` — so the dedup in `enrich_device()` now reads
  `label` **or** `key`. With only `label` it would have degraded to a set of
  empty strings and the original bug would have survived at a new address.
- `enrich_device_direct()` logs add-failures at **warning**, not debug, so a
  broken write surface is visible instead of silent.
- `create_oh_levels()` callers now inspect `failedCount` / `results[]` and log
  CV's actual reason for a partial failure.

---

## 6. Verdict per client method

### `cyber_vision_v1_service.py` (new UI)

| Method | Verdict |
|---|---|
| `get_oh_levels` | ✅ correct — `hierarchy`/`parentLevelId` confirmed live |
| `create_oh_levels` | ✅ path/body correct; partial-success handling improved |
| `rename_oh_level` | ✅ path/body match spec (write unverified) |
| `delete_oh_level` | ✅ matches spec, incl. the "no children/members" rule |
| `assign_networks_to_level` | ✅ matches spec; 500-network cap now documented |
| `get_networks` | ✅ correct — `groupId` confirmed present live |

### `cyber_vision_service.py` (classic)

All read methods verified live. `delete_group`'s legacy `/api/1.0` path
verified as still routed. `get_device_properties` was **broken** and is fixed.
`get_flows` / `get_vulnerabilities` paginated with ignored params and are
fixed. Write methods are unverified but unchanged in path and body vs. the 5.4
spec.

> **Rule for any new classic call: paginate with `page` + `size`.** Never
> `limit`/`offset` — CV accepts them, ignores them, and hands back the whole
> collection with a 200.

---

## 7. Available but unconsumed (recommendation only — not wired up)

The new-UI `/assets*` surface is live and returns useful data we currently
duplicate or lack:

- **`GET /assets`** — one call returns identity, `vendor`, `networkInterfaces`
  (ip/mac/vlan/networkName), `sensorAssociations`, `activeAlertCount` and
  `vulnerabilityCount` per asset. The classic equivalent needs several calls.
- **`GET /assets/vulnerabilities`** — `Vulnerability.source` distinguishes
  `"public"` (`CVE-*`) from `"private"` (`PVT-*`) KDB entries, and carries
  `csrsScore` alongside `cvssScore`. Directly relevant to the CVE pipeline
  (`services/cve_data`, `cve_fingerprint_service.py`), which today has no way
  to tell a public CVE from a CV-private one.
- **`POST /assets/{id}/vulnerabilities/acknowledgement`** — bulk CVE ack with a
  comment; would let PacketArch acknowledge the CVEs it deliberately simulates.
- **Asset/network custom properties** — a cleaner enrichment channel than
  classic `usersProperties`, and notably **not** the broken surface from §5.

Deliberately left for a separate decision; none of it is required for
correctness today.

---

## 8. Open items — all closed

1. ~~Re-verify the 20-char / ASCII OH level-name rules on 5.6.~~ **DONE** —
   operator-approved PATCH-rename probe. Both rules confirmed, and the charset
   turned out to reject 16 plain-ASCII characters the old fold let through
   (§3). Fixed and re-verified against the Center.
2. ~~Confirm `POST /api/3.0/devices/{id}/usersProperties` still works.~~
   **DONE** — operator-approved add/read-back/delete round-trip. POST and
   DELETE both work; the sub-resource is write-only. Turned up that CV returns
   the field as `key`, not `label` (§5). All probe properties deleted;
   `userProperties` back to `[]`.

**One open item, reopened by §10.** Every write path PacketArch uses against
CV has been exercised on 5.6 except `POST/PUT/DELETE /api/3.0/networks/`,
`POST /presets`, `DELETE /presets/{id}`, `POST|PUT /groups`, and
`DELETE /sensors/{id}`.

The original reasoning here was that these "run on every scenario
provision/teardown in normal operation and would be loudly broken if they had
regressed." **That reasoning was wrong, and `POST /networks/` is the
counter-example** — it regressed *silently*, because its only visible effect
lives in a part of CV's UI no API PacketArch calls can see. See §10, and
`tasks/lessons.md`.

---

## 9. How to re-run this audit

```bash
# new-UI spec (the only one CV still publishes)
curl -sk https://<center>/ui/cisco-cyber-vision-api-v4.json -o \
  docs/cyber-vision/cisco-cyber-vision-api-v4-<ver>.json

# live probe — uses the configured Center + decrypted tokens
docker compose exec -T -e PYTHONPATH=/app backend python /tmp/cv56_probe.py
```

Probe scripts resolve clients through `services/cv_centers.py`
(`cv_client` / `cv_v1_client`) — per CLAUDE.md, never read CV config any other
way. Keep probes **read-only** against shared Centers.

---

## 10. Defect: classic network creation leaves the communications map empty

**Added 2026-09-15.** This supersedes §2's original verdict and reopens §8.

The operator-facing symptom is that the new UI's communications map
(`/ui/#/communications`) shows little or nothing for PacketArch scenarios,
while every other surface looks healthy.

### Mechanism

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

The map is driven by `POST /scv/4.0/communications/asset-groups` and groups on
exactly those. Per Cisco, CV 5.6.0 moved network creation to the new UI and
removed network configuration from the classic UI but kept the classic API —
and creating a network through that API does not populate the database
correctly. The network lists on both APIs, assets are attributed to it by CV's
own `networkInterfaces[].networkName`, and yet **no asset group is created**,
so it can never appear on the map. **That route is being deprecated and there
is no API replacement planned for some time.**

### Measured behaviour

Verified against two live 5.6 Centers:

| Operation | Asset group created? | Notes |
|---|---|---|
| classic `POST /api/3.0/networks/` | **No** | network lists fine, assets attributed, map blank |
| classic `PUT /api/3.0/networks/` with identical values | **No** | change-impact preview `0/0`, nothing changes |
| new-UI CSV import — **create** | **Yes** | immediate, with all member interfaces |
| new-UI CSV import — **upsert** of an existing bad row | **No** | returns `updated:1` and repairs nothing |

The last row is the trap: re-importing looks like success and fixes nothing.
Only a *create* materializes the asset group, so repairing an existing bad
network means delete-then-create.

### There is no token-only detector

Probed read-only against `10.10.20.115` on 2026-09-15:

| Probe | Result |
|---|---|
| `GET /scv/3.0/center-type` (no auth) | `{"center_type":"standalone"}` |
| `GET /scv/4.0/asset-group` with the classic token / the new-UI token / no auth | `401` in all three cases |
| `GET /cvapi/v1/{groups,asset-group,asset-groups}`, `GET /cvapi/v1/networks/{id}` | `404` |
| `GET /cvapi/v1/networks` `groupId` vs `GET /cvapi/v1/oh` level ids | **60/60 are OH level ids** |

`groupId` on the new-UI network object is the **Organization Hierarchy level**,
not the asset group — confirmed against PacketArch's own stored
`org_hierarchy` state. No token-authenticated surface exposes the asset-group
fact, so the health check genuinely requires a UI session.

### Live confirmation, and the blast radius is narrower than it looks

Measured on `10.10.20.115` (CV 5.6) on 2026-09-15 with a UI session, across
the 6 provisioned scenarios / 60 networks:

| Scenario | CV state written | Networks with an asset group |
|---|---|---|
| Semiconductor Fab — 300mm Wafer Line | 2026-07-23 | 10 / 10 |
| Municipal Water Treatment Plant | 2026-07-23 | 7 / 7 |
| Strict Purdue Segmented Manufacturing | 2026-07-23 | 7 / 7 |
| Electrical Substation IED Network | 2026-07-23 | 7 / 7 |
| Data Center Infrastructure | 2026-07-23 | 7 / 7 |
| **Heat & Hot-Water Cost Allocation Retrofit** | **2026-08-10** | **0 / 11** |

**The split is the upgrade date, not the scenario.** This Center was upgraded
to 5.6 between those two dates. Networks created on 5.5.x kept their asset
groups; every network created afterwards has none. Verified as a real absence
rather than a name-matching artifact — no asset group on the Center mentions
`Heat`, `Energy`, `Wing` or `BMS`, and all 47 groups are `type: "network"`.

Two consequences:

- **The symptom is usually a partial map, not an empty one.** An install that
  provisioned most of its scenarios before the upgrade sees most zones render
  normally, which makes this harder to spot than "the map is blank" suggests
  — and makes the per-scenario report the right diagnostic shape.
- **Nothing degrades retroactively.** An upgrade does not strip existing asset
  groups, so only scenarios provisioned (or re-provisioned) after the upgrade
  need repair. `scripts/cv-repair-networks.sh` skips the healthy ones.

Also confirmed live: `GET /scv/4.0/networks/csv/sample` returns
`ip_range,type,name,vlan_id,Location,Department` with `OT Internal` /
`IT Internal` / `External` in the `type` column — matching `CSV_COLUMNS` and
the classic vocabulary exactly; `center-type` is `standalone`; the
form-encoded `u`/`p` login succeeds and `check_session` returns an 88-char
`x-csrf-token` header.

### What PacketArch does now

Network **creation** goes through the new UI's CSV import
(`services/cyber_vision_ui_service.py`, wired in at
`cv_provisioning_service._create_networks`). Reads stay on the classic API,
which lists both kinds of network identically, so id resolution by `ipRange`
and the whole Organization Hierarchy half are unchanged.

Each Center therefore carries a **third credential kind** — a UI
username/password, resolved only through `cv_centers.ui_client`:

| Credential | Used for |
|---|---|
| Classic API token | `/api/3.0` — reads, presets, groups, network *reads* |
| New UI API token | `/cvapi/v1` — Organization Hierarchy, network reads |
| **UI username + password** | **`/scv/4.0` — network creation via CSV import** |

Without UI credentials, or if the import itself fails, creation falls back to
the classic API and logs a warning containing the literal string
`will NOT appear on the communications map`. This is deliberate: a
half-registered network still serves the classic UI and asset attribution, so
falling back beats failing the deploy. A **partial** import warns but does NOT
fall back, because an `updated` row does not repair a bad network.

### The `/scv` surface

`/scv` is the UI's own private API. None of it is in any published spec and it
can change in any CV release.

| Call | Purpose |
|---|---|
| `GET /scv/3.0/center-type` | `standalone` or `CVSM` — decides the login route |
| `POST /scv/1.0/login` | login for a standalone Center |
| `POST /scv/4.0/login` | login for a CVSM Center |
| `GET /scv/1.0/check_session` | **returns the CSRF token** |
| `GET /scv/4.0/networks/csv/sample` | the CSV template — authoritative column list |
| `POST /scv/4.0/networks/csv` | multipart `file`; upserts by `ip_range` |
| `DELETE /scv/4.0/networks` | body `{"idList": [...]}` |
| `GET /scv/4.0/network/{id}/details` | one network incl. `orgHierarchy` |
| `GET /scv/4.0/asset-group?type=all&hasParent=false` | asset groups — the health check |
| `GET /scv/4.0/oh/groups` | OH tree with `impactRating`, `networksCount` |

Two auth mechanics that are not guessable:

1. **The login body is form-encoded, not JSON**, with fields `u` and `p`.
   Sending JSON returns `401 INVALID_CREDENTIALS` regardless of how correct
   the credentials are, which reads exactly like a wrong password.
2. **Writes require a gorilla/csrf token.** `GET /scv/1.0/check_session` sets
   the `_gorilla_csrf` cookie **and returns the matching token in the
   `x-csrf-token` response header**; every `/scv/4.0` write must echo that
   value in the `x-csrf-token` *request* header. The cookie value on its own is
   not the token. Without it: `403 Forbidden - CSRF token not found in
   request`. The token is bound to the cookie, so it must be **re-fetched
   after any re-login** — a rotated cookie plus a held-over token yields the
   same CSRF 403, which looks nothing like session expiry.

### CSV format

From CV's own template (`GET /scv/4.0/networks/csv/sample`):

```
ip_range,type,name,vlan_id,Location,Department
10.1.0.0/24,OT Internal,Factory Floor,,Building A,Manufacturing
```

- Required columns: `ip_range`, `type`, `name`, `vlan_id`. Any further column
  becomes a **custom property** on the network.
- `type` uses the **classic** vocabulary — `OT Internal` / `IT Internal` /
  `External`. This is *not* the new-UI API's reading of the same field, which
  reports `OT` for the same object (§2). Feeding it `OT` mistypes the network.
  `build_networks_csv` takes the classic `_net_item` payload dicts for exactly
  this reason: the vocabulary cannot drift.
- **CV trims whitespace in `name`**, so `_net_item` strips at generation —
  otherwise a recorded name would not match what CV stores.
- Quote properly. Zone labels are `f"{zone} ({scenario})"` and scenario names
  are free text, so commas and em dashes are routine; `build_networks_csv`
  uses `csv.writer`.
- The response is `{"created": N, "updated": N, "skipped": N, "errors": [...]}`.
  **Check `created`** — `updated` does not repair a bad network.

### Verification — run all four after every CV upgrade

`scripts/cv-repair-networks.sh` (read-only by default) reports all of them per
scenario. The first, third and fourth can all pass while the map stays empty:

1. **Networks exist** — every expected range present (classic `GET /networks/`).
2. **Asset group exists** for each — `GET /scv/4.0/asset-group`. *This is the
   one that detects this defect.* Key on **presence by name**, never on
   `interfaceCount`: a scenario's `/16` umbrella legitimately reports `0`
   because CV attributes assets to the more specific `/24`s.
3. **Assigned to the right OH level**, not parked at `Global`.
4. **PacketArch's stored ids match CV** — stale ids cause `404 Network IDs not
   found` on hierarchy assignment.

### Repair, exercised end to end

Run against `Heat & Hot-Water Cost Allocation Retrofit` on `.115`, 2026-09-15
— the one scenario on that Center provisioned after its 5.6 upgrade:

```
  - deleting 11 network(s) via the CV UI API
  - verified their asset groups are gone
  - CSV import: {'created': 11, 'updated': 0, 'skipped': 0, 'errors': []}
  - verified every recreated network now has an asset group
  - re-resolved stored ids (11 networks)
  - re-assigned the Organization Hierarchy
  => all 11 networks have an asset group.
```

`created: 11, updated: 0` — every row took the create path, which is the whole
point. All four checks then pass for all 60 networks on the Center.

> **The `verified their asset groups are gone` line proved nothing here, and
> must not be read as a measurement of delete semantics.** A *broken* network
> has no asset group to begin with, so the assertion was vacuously true. It is
> still the right guard — a surviving group would mean the follow-up create
> silently becomes an upsert — but it only carries information when deleting a
> *healthy* network. See the open item below.

### Repairing an existing install

`scripts/cv-repair-networks.sh --scenario <id|name> --apply`, one scenario at
a time. It skips networks that already have an asset group, deletes the rest,
**asserts their asset groups are actually gone** (a survivor would turn the
create into a no-op upsert), CSV-creates them, verifies the asset groups now
exist, then re-resolves PacketArch's stored ids and re-applies the
Organization Hierarchy — necessary because a recreated network gets a new id
and OH membership is keyed by id, so every repaired network returns to
`Global`. Between the delete and the create, assets in that range fall back to
CV's built-in `10/8`.

### Open items

- **`/scv` is a workaround, not a supported integration.** Cisco has not
  committed to a replacement API timeline. It may break on any CV upgrade, and
  the failure is *silent* — the classic fallback "works" — so the next
  regression will again only be visible as an empty map. Re-run the four
  checks above after every CV upgrade.
- **Does a classic `DELETE /api/3.0/networks/` remove a CSV-created network's
  asset group, or orphan it?** Still unmeasured — the measured-behaviour table
  covers create and upsert only, and the repair run above could not settle it
  because the networks it deleted had no asset groups to lose. Teardown still
  uses the classic delete. The clean experiment is isolated and cheap: CSV-
  create a throwaway range (it gains an asset group), classic-DELETE it, then
  re-list asset groups. If the group survives, teardown should prefer the
  `/scv` delete with the classic call as fallback, because an orphaned group
  would turn a later create of that range into a repair-nothing upsert.
- **Ask Cisco:** if CSV import took the *create* path for an already-present
  `ip_range`, repairs would need no deletes at all. Worth requesting.
