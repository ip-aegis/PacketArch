# Build stage - install dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Poetry goes in its OWN virtualenv, and is used only to READ the lock file.
#
# It used to be `pip install poetry` into the system site-packages, followed by
# `poetry install --virtualenvs.create false` into that same site-packages.
# That puts poetry's own dependencies and the application's pinned dependencies
# in one directory, and our lock pins DOWNGRADES of three of poetry's
# (charset-normalizer, httpx, certifi) — so poetry would uninstall its own
# dependencies from under itself mid-run. Whether that survives is down to the
# order pip happens to process things in, which pip does not guarantee: the
# same commit built here and failed on a cache-less CI runner with
#   pip uninstall charset-normalizer -> FileNotFoundError: certifi-2026.7.22.dist-info
# A build that works only because the layer cache is warm is not a build.
#
# So: poetry exports a requirements file, and the system pip installs from it.
# Poetry never writes to the environment the application will run in, the two
# dependency sets can no longer collide, and poetry (plus its ~45 transitive
# packages) stops being copied into the runtime image, which it was.
#
# Poetry is PINNED. Leaving it floating means an upstream poetry release can
# change what this image resolves, which is how the above surfaced on a day
# poetry's dependencies moved.
# Poetry AND the export plugin are pinned. The whole reason for pinning is that
# an upstream release can change what this image resolves; a plugin release can
# change the exported file just as easily as a poetry release can.
ENV POETRY_VERSION=2.5.1 \
    POETRY_EXPORT_PLUGIN_VERSION=1.10.1 \
    POETRY_HOME=/opt/poetry
RUN python -m venv "${POETRY_HOME}" \
    && "${POETRY_HOME}/bin/pip" install --no-cache-dir \
         "poetry==${POETRY_VERSION}" \
         "poetry-plugin-export==${POETRY_EXPORT_PLUGIN_VERSION}"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Resolve from the lock, then install with pip into the system environment.
#
# WITH hashes, deliberately. `poetry install` verified artifact hashes from the
# lock, and exporting without them would have quietly dropped that — which is
# not a trade to make silently on a security platform. Every entry in
# poetry.lock is a PyPI artifact (no git, directory or file sources, checked),
# so every requirement carries hashes and pip runs in hash-checking mode: a
# tampered or substituted wheel fails the build instead of shipping.
RUN "${POETRY_HOME}/bin/poetry" export \
        --only main --no-interaction --no-ansi \
        -f requirements.txt -o /tmp/requirements.txt \
    && grep -c -- '--hash=' /tmp/requirements.txt > /dev/null \
    && pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create directories for data
RUN mkdir -p /app/data/pcap_uploads /app/output/pcap \
    && chmod +x /app/entrypoint.sh

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Entrypoint applies alembic migrations (when RUN_MIGRATIONS=true) then runs CMD
ENTRYPOINT ["/app/entrypoint.sh"]

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
