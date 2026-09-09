# Release Bundles (Multi-Lab Deploys)

> Moved out of `CLAUDE.md` on 2026-09-09 so the always-loaded file stays a map. Content unchanged.


Releases are built as self-contained offline tarballs suitable for
air-gapped lab deployment.

- `scripts/build-release.sh` — builds backend/frontend/agent images,
  pulls postgres/redis, `docker save`s everything, stages compose +
  install script + docs + licenses, produces
  `dist/packetarch-<version>-offline.tar.gz`. Set `PCAP_ONLY=1` to
  produce the PCAP-only variant (`...-pcap-offline.tar.gz`): forces
  `SKIP_AGENT=1`, stamps `BUILD_VARIANT=pcap-only` into the bundle's
  `VERSION` file, and `install.sh` reads that to write
  `LIVE_TRAFFIC_ENABLED=false` into the generated `.env`.
- `scripts/release-bundle/` — the source-of-truth for everything that
  goes INTO the bundle: `install.sh`, `README_SITE.md`,
  `docker-compose.offline.yml`, `.env.example`.
- `.github/workflows/release.yml` — tag `v*` to trigger a CI build.
  Matrix builds both `full` and `pcap-only` variants in parallel; both
  tarballs are attached to the draft GitHub Release.
- Site operators use the bundle's `install.sh` (generates `.env` with
  fresh secrets), then `packetarch-backup.sh` / `packetarch-restore.sh`
  for snapshot/restore across the install's Postgres DB + PCAP volumes.

# Cert injection (custom TLS)

Frontend container's `docker-entrypoint.sh` checks
`/etc/nginx/custom-certs/server.{crt,key}` on every boot; if present,
copies to live cert path. Compose mounts `./certs` as the source. Drop
real cert/key there + `docker compose restart frontend` to swap.
