# PacketArch host-agent image.
#
# A LONG-RUNNING privileged sibling that owns all host-level operations for
# local sensor labs: per-lab veth crossovers, /etc/docker/daemon.json registry
# trust, and per-lab CV-sensor + traffic-agent containers. The unprivileged
# backend never touches the host — it drops request files on a shared volume and
# this watcher acts on them (see app/state.py for the file-queue contract).
#
# Based on docker:cli (bundles the compose plugin) like packetarch-updater, plus
# iproute2 + ethtool for veth management and python3 + pyyaml for the watcher.
FROM docker:27-cli

RUN apk add --no-cache python3 py3-yaml iproute2 ethtool curl bash coreutils

WORKDIR /app
COPY app /app/app

# Unbuffered so logs stream to `docker logs` in real time.
ENV PYTHONUNBUFFERED=1

CMD ["python3", "-m", "app.watcher"]
