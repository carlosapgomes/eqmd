# Container Registry Setup

**Complete guide for setting up container registries for EquipeMed deployment**

## Overview

EquipeMed uses a registry-based deployment approach where Docker images are built once and pushed to a container registry, then pulled for deployment. This eliminates the need to rebuild images on production servers.

## Supported Registries

### GitHub Container Registry (Recommended)

**Benefits:**

- Free for public repositories
- Integrated with GitHub Actions
- Automatic authentication with GITHUB_TOKEN
- Good security and access controls

**Setup:**

1. **Enable GitHub Actions** in your repository settings
2. **Configure package permissions** in repository settings > Actions > General
3. **Update workflow file** (already included in `.github/workflows/build-and-push.yml`)
4. **Set repository visibility** for packages in Settings > Actions > General

**Authentication:**

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Or set environment variables for scripts
export REGISTRY="ghcr.io"
export REGISTRY_USER="your-github-username"
export REGISTRY_TOKEN="your-github-token"
```

**Image naming:**

- Format: `ghcr.io/username/repository:tag`
- Example: `ghcr.io/yourorg/eqmd:latest`

### Docker Hub Alternative

**Benefits:**

- Most widely used registry
- Good free tier
- Easy setup and management

**Setup:**

1. **Create Docker Hub account** at <https://hub.docker.com>
2. **Create repository** for your project
3. **Generate access token** in Account Settings > Security
4. **Update image references** in deployment scripts

**Authentication:**

```bash
# Login to Docker Hub
echo $DOCKER_TOKEN | docker login -u $DOCKER_USERNAME --password-stdin

# Set environment variables
export REGISTRY="docker.io"
export REGISTRY_USER="your-dockerhub-username"
export REGISTRY_TOKEN="your-access-token"
```

**Image naming:**

- Format: `username/repository:tag`
- Example: `yourorg/eqmd:latest`

### Private Registry

**Benefits:**

- Full control over infrastructure
- No external dependencies
- Can be hosted on-premise

**Setup:**

1. **Set up registry server:**

```bash
# Using Docker Registry
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Or using Harbor for advanced features
# See: https://goharbor.io/docs/2.9.0/install-config/
```

1. **Configure TLS** (recommended for production):

```bash
# Generate certificates
openssl req -newkey rsa:4096 -nodes -sha256 -keyout certs/domain.key -x509 -days 365 -out certs/domain.crt

# Run registry with TLS
docker run -d -p 5000:5000 --restart=always --name registry \
  -v "$(pwd)"/certs:/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
  registry:2
```

1. **Configure authentication:**

```bash
# Create password file
htpasswd -Bbn username password > auth/htpasswd

# Run registry with auth
docker run -d -p 5000:5000 --restart=always --name registry \
  -v "$(pwd)"/auth:/auth \
  -e "REGISTRY_AUTH=htpasswd" \
  -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
  registry:2
```

**Client Configuration:**

```bash
# Add registry to Docker daemon configuration
echo '{"insecure-registries": ["your-registry:5000"]}' > /etc/docker/daemon.json
systemctl restart docker

# Login to private registry
docker login your-registry:5000

# Set environment variables
export REGISTRY="your-registry:5000"
export REGISTRY_USER="your-username"
export REGISTRY_TOKEN="your-password"
```

## CI/CD Integration

### GitHub Actions (Included)

The repository includes `.github/workflows/build-and-push.yml` that:

- Builds Docker images on push/PR
- Pushes to GitHub Container Registry
- Performs security scanning
- Tags images appropriately

**Trigger conditions:**

- Push to `main` or `dev` branches
- Pull requests to `main`

**Image tags created:**

- `latest` (for main branch)
- `dev` (for dev branch)
- `pr-123` (for pull requests)
- `sha-abcd123` (for specific commits)

### Manual Build and Push

```bash
# Build image locally
docker build -t eqmd:latest .

# Tag for registry
docker tag eqmd:latest ghcr.io/yourorg/eqmd:latest

# Push to registry
docker push ghcr.io/yourorg/eqmd:latest
```

### Custom CI/CD

For other CI/CD systems, adapt the workflow:

```bash
#!/bin/bash
# build-and-push.sh

# Build image
docker build -t $IMAGE_NAME:$TAG .

# Login to registry
echo $REGISTRY_TOKEN | docker login $REGISTRY -u $REGISTRY_USER --password-stdin

# Push image
docker push $IMAGE_NAME:$TAG

# Logout for security
docker logout $REGISTRY
```

## Environment Configuration

### Registry Environment Variables

Create or update your `.env` file:

```bash
# Registry configuration
REGISTRY=ghcr.io                    # Registry hostname
REGISTRY_USER=your-github-username  # Registry username
REGISTRY_TOKEN=your-github-token    # Registry authentication token

# Image configuration
EQMD_IMAGE=ghcr.io/yourorg/eqmd:latest  # Full image name with tag

# User configuration (for building)
EQMD_UID=1001                      # User ID for eqmd user
EQMD_GID=1001                      # Group ID for eqmd user
```

### Script Integration

Update deployment scripts to use registry:

```bash
# In install.sh or upgrade.sh
source .env

# Login to registry
if [ -n "$REGISTRY_TOKEN" ]; then
    echo "$REGISTRY_TOKEN" | docker login $REGISTRY -u "$REGISTRY_USER" --password-stdin
fi

# Pull image
docker pull $EQMD_IMAGE
export EQMD_IMAGE

# Deploy
docker compose up -d eqmd
```

## Security Considerations

### Authentication Security

1. **Use access tokens** instead of passwords
2. **Limit token permissions** to minimum required
3. **Rotate tokens regularly** (quarterly recommended)
4. **Never commit tokens** to version control

### Image Security

1. **Scan images** for vulnerabilities (included in GitHub workflow)
2. **Sign images** using Docker Content Trust (optional)
3. **Use specific tags** instead of `latest` in production
4. **Regularly update base images**

### Access Control

1. **Limit who can push** images to registry
2. **Use separate registries** for dev/staging/production if needed
3. **Monitor registry access** logs
4. **Implement image approval** process for production

## Troubleshooting

### Authentication Issues

```bash
# Check if logged in
docker system info | grep Registry

# Manual login test
docker login ghcr.io

# Check credentials
cat ~/.docker/config.json
```

### Image Push/Pull Issues

```bash
# Check image exists locally
docker images | grep eqmd

# Test registry connectivity
curl -v https://ghcr.io/v2/

# Check image manifest
docker manifest inspect ghcr.io/yourorg/eqmd:latest
```

### Deployment Issues

```bash
# Check if image can be pulled
docker pull $EQMD_IMAGE

# Verify image contents
docker run --rm $EQMD_IMAGE ls -la /app/staticfiles

# Check docker compose configuration
docker compose config
```

## Migration from Build-based Deployment

### Step-by-Step Migration

1. **Set up registry** (choose from options above)
2. **Build and push** current version to registry
3. **Update environment variables** on production server
4. **Test pull** from registry on production server
5. **Update deployment scripts** (already done in this repository)
6. **Perform test deployment** on staging environment
7. **Execute production migration** during maintenance window

### Rollback Plan

If registry deployment fails:

```bash
# Fallback to local build
unset EQMD_IMAGE
docker compose build eqmd
docker compose up -d eqmd
```

## Best Practices

### Image Management

1. **Use semantic versioning** for tags (v1.0.0, v1.1.0)
2. **Maintain multiple tags** (latest, stable, specific versions)
3. **Clean up old images** regularly to save space
4. **Document image contents** and changes

### Deployment Strategy

1. **Test registry deployment** in staging first
2. **Use health checks** to verify deployments
3. **Implement rollback procedures** for failed deployments
4. **Monitor deployment metrics** and success rates
5. **Schedule regular registry maintenance**

### Development Workflow

1. **Use feature branches** for development
2. **Build images automatically** on PR/merge
3. **Test with registry images** before production
4. **Maintain development/staging/production** image variants

This registry setup provides a robust foundation for scalable, consistent deployments while maintaining security and operational efficiency.
