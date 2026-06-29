# Bug: host-agent crash-loops after stack recreated from a different directory

**Status:** Fixed in this change. Production instance was recovered by
recreating the `host-agent` container from the correct project directory; this
PR removes the fragile relative bind mount from the shipped compose file so the
failure mode can't recur. See "Fix applied" below.

**Severity:** High for local sensor labs — when it triggers, *all* local-lab
provisioning silently hangs (requests queue up but never drain). CML labs and
the rest of the app are unaffected.

## Symptom

- Adding a Local Lab (Agents hub → Local Labs → New Local Lab → Build) hangs
  forever in "provisioning".
- `docker compose ps` shows `packetarch-host-agent` in `Restarting (1)` —
  a crash loop.
- `docker compose logs host-agent` is a wall of:
  ```
  /usr/bin/python3: Error while finding module specification for 'app.watcher'
  (ModuleNotFoundError: No module named 'app')
  ```

## Root cause

The `host-agent` service in `docker-compose.yml` (line ~206) bind-mounts the
watcher source for live-editing without a rebuild:

```yaml
volumes:
  - ./docker/packetarch-host-agent:/app:ro   # live-edit watcher w/o rebuild
```

This **relative** path is resolved against the Compose *project directory*,
which is fixed at the moment the container is created (stored in the
`com.docker.compose.project.working_dir` label).

On the affected instance the whole stack had originally been `up`'d from
`/repo` (the path used by the OVA / release deploy). Later the working tree
lived at `/home/rocky/packetarch`, and `/repo` no longer existed. So:

1. The container kept its stale mount source `/repo/docker/packetarch-host-agent`.
2. That path doesn't exist on the host → Docker **silently creates an empty
   directory** and mounts it at `/app`.
3. The empty mount **shadows** the image's real code at `/app/app/`, so
   `python3 -m app.watcher` (CMD, WORKDIR `/app`) can't find the `app` package.
4. Crash → restart → crash. The watcher never runs, so the file-queue at
   `host_agent_state:/hostagent/local-labs/requests/` never drains.

Confirmed via:
```
docker inspect packetarch-host-agent \
  --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
# => /repo        (but /repo/docker/packetarch-host-agent/app does not exist)
```

The backend & celery containers were *also* created from `/repo` but survive
because they run from the baked image with no live-edit bind mount over their
code. **The host-agent is the only service with a source bind mount over its
own code**, so it's uniquely fragile to a moved/renamed project directory.

## Immediate recovery (already applied in prod)

Recreate just the host-agent from the correct project directory:

```bash
docker compose -f /home/rocky/packetarch/docker-compose.yml \
  --project-directory /home/rocky/packetarch \
  up -d --force-recreate host-agent
```

`COMPOSE_PROJECT_NAME=packetarch` is set in `.env`, so this adopts the existing
project rather than spawning a parallel one. After recreate the watcher booted,
drained the stuck request, created the veth, trusted the registry, and
provisioned the lab (`state=running`). Lab containers `packetarch-agent-<slug>`
and `ccv-sensor-<slug>` came up.

## Fix applied

The live-edit bind mount was a dev affordance and should never have shipped in
a deploy-target compose file. This change:

1. **Removes** the `./docker/packetarch-host-agent:/app:ro` mount from
   `docker-compose.yml`. The host-agent now runs purely from its baked image
   (`COPY app /app/app` in the Dockerfile) — exactly like the backend and every
   other service. With no source mount, there is nothing to go stale and
   nothing that can shadow `/app/app`, so the crash-loop failure mode is gone.

2. **Adds** an opt-in `docker-compose.host-agent-dev.yml` overlay that re-adds
   the mount for watcher development. It is deliberately a separate,
   *non-auto-loaded* file (not `docker-compose.override.yml`, which Compose
   loads automatically), so the default deploy can never pick it up:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.host-agent-dev.yml \
     up -d host-agent
   ```

### Rejected alternatives

- **Absolute-path mount via env var** (`${PACKETARCH_ROOT}/...:/app:ro`) — still
  ships a code bind mount in prod and depends on the installer/OVA setting the
  var consistently; one missed var reintroduces the shadowing.
- **Fail-loud guard in `watcher.py`** — improves the *diagnosis* but keeps the
  fragile mount. Worth adding independently, but it doesn't remove the failure
  mode the way dropping the mount does.

## Why it likely surfaced now

The stack was deployed once from `/repo`, then the working copy moved to
`/home/rocky/packetarch`. Any `docker compose up` from the new path that
*didn't* recreate the host-agent (e.g. a targeted `up -d --build backend`) left
the host-agent on its stale `/repo` mount until something restarted it.
