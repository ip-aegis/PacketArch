# PacketArch self-upgrade runner image.
#
# A one-off container launched (detached) by the backend via the Docker socket
# to run scripts/upgrade.sh against the host install. Needs the Docker CLI +
# compose plugin (to drive the host daemon over the mounted socket), git (to
# check out release tags), and the coreutils the scripts use. NOT a long-running
# service — see the `updater` profile in docker-compose.yml.
FROM docker:27-cli

# docker:cli already bundles the compose plugin; add the rest upgrade.sh +
# packetarch-backup.sh rely on.
RUN apk add --no-cache git bash curl tar coreutils

# The bind-mounted /repo is owned by the host user but this container runs as
# root; without this git refuses every command with "dubious ownership".
RUN git config --global --add safe.directory '*'

WORKDIR /repo

# No CMD: the backend supplies the command
# (scripts/upgrade.sh --to <tag> --status-file /state/upgrade_status.json).
