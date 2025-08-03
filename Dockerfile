# Multi-stage build for EquipeMed Django application
FROM node:18-slim AS frontend-builder

# Install frontend dependencies and build assets
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY assets/ ./assets/
COPY apps/ ./apps/
COPY webpack.config.js ./
RUN npm run build

# Main application stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

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
  # Cleanup
  && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create application directory
WORKDIR /app

# Copy Python dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml
# Install production server
RUN uv pip install --system gunicorn

# Copy built frontend assets from frontend-builder stage
COPY --from=frontend-builder /app/static/ ./static/

# Copy application code
COPY . .

# Create directories for media and static files
RUN mkdir -p /app/media /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Create non-root user for security
# Allow customizing user ID to match host user
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID appuser && \
  useradd -u $USER_ID -g $GROUP_ID --create-home --shell /bin/bash appuser && \
  chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8778

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python manage.py check --deploy || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8778", "--workers", "3", "config.wsgi:application"]
