# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application (skip tsc, vite handles transpilation)
RUN npx vite build

# Runtime stage - nginx for static serving with SSL
FROM nginx:alpine

# openssl for certificate generation; curl for the container healthcheck.
# nginx:alpine happens to ship curl today, but it is a floating tag — relying on
# that would make the healthcheck vanish on a base-image refresh, and a
# healthcheck that cannot run is reported exactly like one that never passed.
RUN apk add --no-cache openssl curl

# Create SSL directories. /etc/nginx/ssl is the live cert location nginx
# reads from; /etc/nginx/custom-certs is the read-only mount point operators
# use to provide a real CA-signed cert (see docker-entrypoint.sh).
RUN mkdir -p /etc/nginx/ssl /etc/nginx/custom-certs

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTPS port. Port 80 is also listened-on for the HTTP→HTTPS redirect
# block in nginx.conf, but we don't publish it by default.
EXPOSE 443 80

# Use custom entrypoint to generate certs if needed
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
