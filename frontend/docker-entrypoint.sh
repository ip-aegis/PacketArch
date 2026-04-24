#!/bin/sh
# Frontend nginx container entrypoint.
#
# TLS material resolution order on every boot:
#   1. If both /etc/nginx/custom-certs/server.crt and server.key exist,
#      copy them into /etc/nginx/ssl/. This is the "operator-supplied
#      real certificate" path and it is re-applied on every container
#      start so hot-swapping a cert only requires a container restart.
#   2. Otherwise, if /etc/nginx/ssl/ is empty, generate a self-signed
#      cert. This is the out-of-the-box fallback for lab/dev use.
#   3. Otherwise, keep the existing self-signed cert (stable across
#      restarts so the browser-trusted exception doesn't churn).

set -e

CUSTOM_CERT=/etc/nginx/custom-certs/server.crt
CUSTOM_KEY=/etc/nginx/custom-certs/server.key
LIVE_CERT=/etc/nginx/ssl/server.crt
LIVE_KEY=/etc/nginx/ssl/server.key

mkdir -p /etc/nginx/ssl

if [ -f "$CUSTOM_CERT" ] && [ -f "$CUSTOM_KEY" ]; then
    echo "Using operator-supplied TLS certificate from /etc/nginx/custom-certs/"
    cp "$CUSTOM_CERT" "$LIVE_CERT"
    cp "$CUSTOM_KEY"  "$LIVE_KEY"
    chmod 600 "$LIVE_KEY"
elif [ ! -f "$LIVE_CERT" ] || [ ! -f "$LIVE_KEY" ]; then
    echo "No custom certificate found; generating self-signed certificate..."
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$LIVE_KEY" \
        -out    "$LIVE_CERT" \
        -subj "/CN=packetarch/O=PacketArch/C=US" \
        2>/dev/null
    chmod 600 "$LIVE_KEY"
    echo "Self-signed certificate generated. For production, mount a real cert at:"
    echo "  /etc/nginx/custom-certs/server.crt"
    echo "  /etc/nginx/custom-certs/server.key"
else
    echo "Using existing self-signed certificate at /etc/nginx/ssl/."
fi

exec "$@"
