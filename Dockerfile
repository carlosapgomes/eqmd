# Stage 1: Node.js build for static assets
FROM node:18-alpine AS static-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY assets/ ./assets/
COPY apps/ ./apps/
COPY webpack.config.js ./
RUN npm run build

# Stage 2: Python application  
FROM python:3.12-slim
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user with configurable UID/GID
ARG USER_ID=1001
ARG GROUP_ID=1001
RUN groupadd -r -g ${GROUP_ID} eqmd && \
    useradd -r -u ${USER_ID} -g eqmd eqmd

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

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy Python dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN uv pip install --system --editable .
# Install production server explicitly
RUN uv pip install --system gunicorn

# Copy application code
COPY . .
RUN chown -R eqmd:eqmd /app

# Copy static files from build stage and set www-data ownership
COPY --from=static-builder --chown=33:33 /app/static /app/staticfiles
RUN chmod -R 755 /app/staticfiles

# Switch to eqmd user for runtime
USER eqmd

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
