FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /extension

RUN uv venv /opt/venv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH=/opt/venv/bin:$PATH

FROM base AS build-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

FROM build-base AS build

COPY backend/ .

RUN uv sync --frozen --no-cache --no-dev

# Builds the frontend static assets that the backend SDK mounts and serves.
# The frontend is parked while frontend/src/modules has no entrypoints: the
# stage detects that and skips npm entirely, emitting an empty static tree.
# Adding a module makes the image build it automatically, with no build-arg, so
# a plain `docker build` behaves the same as `make` (see FRONTEND_HAS_CODE in
# make/common.mk).
FROM node:26-bookworm-slim AS frontend-build

WORKDIR /frontend

COPY frontend/ ./
RUN if [ -n "$(find src/modules -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null)" ]; then \
        npm ci && npm run build; \
    fi \
    && mkdir -p /static

FROM build AS dev

COPY --from=frontend-build /static ./static
RUN uv sync --frozen --no-cache --dev

CMD ["mpt-ext", "run"]

FROM base AS prod

COPY --from=build /opt/venv /opt/venv
COPY --from=build /extension/mpt_installation_extension ./mpt_installation_extension
COPY --from=build /extension/migrations ./migrations
COPY --from=frontend-build /static ./static

RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser && \
    mkdir -p /home/appuser/.cache/uv && \
    chown -R appuser:appuser /extension /opt/venv /home/appuser

ENV UV_CACHE_DIR=/home/appuser/.cache/uv

USER appuser

CMD ["mpt-ext", "run"]
