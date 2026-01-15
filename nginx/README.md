# Nginx Configuration for Matrix Integration

This directory contains nginx configuration templates for Matrix Synapse and Element Web.

## Template Files

- `matrix.conf.template` - Synapse homeserver configuration
- `element.conf.template` - Element Web client configuration

## Production Setup

1. **Process templates** with your actual domain values:
   ```bash
   # Generate configs from templates
   uv run python scripts/generate_matrix_configs.py
   ```

2. **Copy to nginx sites**:
   ```bash
   # Copy generated configs to nginx sites-available
   sudo cp nginx/matrix.conf /etc/nginx/sites-available/matrix-${MATRIX_FQDN}
   sudo cp nginx/element.conf /etc/nginx/sites-available/element-${CHAT_FQDN}
   
   # Enable sites
   sudo ln -sf /etc/nginx/sites-available/matrix-${MATRIX_FQDN} /etc/nginx/sites-enabled/
   sudo ln -sf /etc/nginx/sites-available/element-${CHAT_FQDN} /etc/nginx/sites-enabled/
   ```

3. **Update SSL certificates** in the config files with your actual certificate paths.

4. **Test and reload nginx**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Key Features

### Matrix Configuration (`matrix.conf`)
- Proxies `/_matrix/*` to Synapse container on port 8008
- Blocks federation endpoints (security)
- Handles file uploads (50MB limit)
- Serves `.well-known/matrix/client` for autodiscovery

### Element Configuration (`element.conf`)
- Proxies all requests to Element Web container on port 8080
- Optimized caching for static assets
- CSP headers for security
- Optional well-known delegation

## Security Considerations

- Federation endpoints are explicitly blocked
- Security headers are added
- File upload limits are enforced
- CSP prevents XSS attacks

## Testing

After setup, test these endpoints:

- `https://${MATRIX_FQDN}/_matrix/client/versions` - Should return JSON
- `https://${CHAT_FQDN}/` - Should load Element Web
- `https://${MATRIX_FQDN}/.well-known/matrix/client` - Should return homeserver info
- `https://${MATRIX_FQDN}/_matrix/federation/` - Should return 404 (blocked)