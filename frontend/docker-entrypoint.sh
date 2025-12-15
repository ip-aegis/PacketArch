#!/bin/sh
set -e

# Generate self-signed SSL certificate if it doesn't exist
if [ ! -f /etc/nginx/ssl/server.crt ] || [ ! -f /etc/nginx/ssl/server.key ]; then
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/server.key \
        -out /etc/nginx/ssl/server.crt \
        -subj "/CN=packetarch/O=PacketArch/C=US" \
        2>/dev/null
    echo "SSL certificate generated successfully."
else
    echo "SSL certificate already exists, skipping generation."
fi

# Execute the main command (nginx)
exec "$@"
