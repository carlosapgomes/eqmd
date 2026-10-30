# Stage 1: Node.js build for static assets
FROM node:18-alpine AS static-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY assets/ ./assets/
COPY apps/ ./apps/
COPY webpack.config.js ./
RUN npm run build

# Stage 2: Python dependency base (runtime + optional dev group from uv.lock)
# Base identity is pinned to the multi-arch python:3.12-slim-trixie index
# (Debian 13) so the Python/Debian series cannot drift silently (ADR-0001).
FROM python:3.12-slim-trixie@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS python-base
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  UV_NO_CACHE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
  # Poppler for PDF processing (required for pdf-forms app)
  poppler-utils \
  # FFmpeg for media processing
  ffmpeg \
  # Image processing libraries
  libjpeg-dev \
  libpng-dev \
  libwebp-dev \
  # Brotli runtime must carry the Debian 13 security fix (CVE-2026-111497)
  libbrotli1 \
  # Database drivers
  libpq-dev \
  default-libmysqlclient-dev \
  # Build tools
  gcc \
  g++ \
  # Git for version control (if needed)
  git \
  # curl for health checks
  curl \
  # Cleanup
  && rm -rf /var/lib/apt/lists/*

# Fail closed if the Debian archive cannot supply the corrected Brotli build.
# dpkg ordering handles the +deb13u1 revision correctly.
RUN dpkg --compare-versions \
    "$(dpkg-query -W -f='${Version}' libbrotli1)" ge '1.1.0-2+deb13u1'

# Install uv (validated 0.12.5 build tool, pinned tag; `latest` is forbidden
# because it breaks deterministic builds, ADR-0001).
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv

# Copy dependency metadata and lockfile; install in frozen mode so Docker
# resolution matches uv.lock exactly (ADR-0001).
COPY pyproject.toml uv.lock ./

# INSTALL_DEV=true installs the dev dependency group (quality tooling) for the
# development target; the production target installs runtime + prod groups only.
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      uv export --frozen --no-emit-project > /tmp/requirements.txt \
      && uv pip install --system --no-cache -r /tmp/requirements.txt \
      && uv pip install --system --no-cache --no-deps --editable .; \
    else \
      uv export --frozen --no-dev --group prod --no-emit-project > /tmp/requirements.txt \
      && uv pip install --system --no-cache -r /tmp/requirements.txt \
      && uv pip install --system --no-cache --no-deps --editable .; \
    fi \
    && rm -f /tmp/requirements.txt

# Stage 3: Production runtime image (derives from the lock-backed base)
FROM python-base AS production

# Copy application code
COPY . .
# Create logs directory for matrix bot audit
RUN mkdir -p /app/logs

# Copy static files from build stage and set www-data ownership
COPY --from=static-builder --chown=33:33 /app/static /app/staticfiles
RUN chmod -R 755 /app/staticfiles

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
