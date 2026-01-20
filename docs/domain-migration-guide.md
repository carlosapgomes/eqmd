# Domain Migration Guide: equipemed.app → equipehgrs.com

This guide provides step-by-step instructions for migrating your EquipeMed deployment from `equipemed.app` to `equipehgrs.com`.

## Overview

Based on a comprehensive search of the codebase, this migration requires updating configuration files, Matrix integration settings, and external infrastructure components.

## Pre-Migration Checklist

- [ ] **DNS Setup**: Configure DNS records for the new domain
- [ ] **SSL Certificates**: Obtain SSL certificates for:
  - `equipehgrs.com`
  - `matrix.equipehgrs.com` 
  - `chat.equipehgrs.com`
- [ ] **Backup**: Create full backup of current deployment
- [ ] **Maintenance Window**: Schedule downtime for the migration

## Migration Steps

### 1. Environment Configuration (.env file)

Update your `.env` file with the following changes:

```bash
# Main domain configuration
ALLOWED_HOSTS=equipehgrs.com,www.equipehgrs.com,localhost,127.0.0.1
SITE_DOMAIN=equipehgrs.com
SITE_NAME=Your Hospital Name

# Email configuration
DEFAULT_FROM_EMAIL=noreply@equipehgrs.com
EMAIL_HOST_USER=noreply@equipehgrs.com
SERVER_EMAIL=server@equipehgrs.com

# Matrix Integration
EQMD_DOMAIN=equipehgrs.com
MATRIX_FQDN=matrix.equipehgrs.com
CHAT_FQDN=chat.equipehgrs.com
MATRIX_PUBLIC_BASEURL=https://matrix.equipehgrs.com/

# OIDC Provider configuration
OIDC_ISSUER=https://equipehgrs.com/o

# Matrix admin users (update domain part)
MATRIX_ADMIN_USERS=@<localpart>:matrix.equipehgrs.com
MATRIX_BOT_USER_ID=@rzero_bot:matrix.equipehgrs.com
```

**Optional**: Add CSRF trusted origins if needed:
```bash
DJANGO_CSRF_TRUSTED_ORIGINS=https://equipehgrs.com,https://www.equipehgrs.com
```

### 2. Matrix Configuration Files

#### Update matrix/homeserver.yaml

**Line 9**: Change server name
```yaml
server_name: "matrix.equipehgrs.com"
```

#### Update element/config.json

Replace all occurrences of `sispep.com` with `equipehgrs.com`:

```json
{
    "default_server_config": {
        "m.homeserver": {
            "base_url": "https://matrix.equipehgrs.com/",
            "server_name": "matrix.equipehgrs.com"
        }
    },
    "roomDirectory": {
        "servers": ["matrix.equipehgrs.com"]
    },
    "enable_presence_by_hs_url": {
        "https://matrix.equipehgrs.com/": false
    },
    "terms_and_conditions_links": [
        {
            "url": "https://equipehgrs.com/privacy-policy",
            "text": "Privacy Policy"
        },
        {
            "url": "https://equipehgrs.com/terms-of-service", 
            "text": "Terms of Service"
        }
    ],
    "embedded_pages": {
        "home_url": "https://equipehgrs.com/",
        "login_for_welcome": false
    },
    "default_server_name": "matrix.equipehgrs.com",
    "welcomeUserId": "@welcome:matrix.equipehgrs.com",
    "privacy_policy_url": "https://equipehgrs.com/privacy-policy",
    "cookie_policy_url": "https://equipehgrs.com/privacy-policy"
}
```

### 3. Nginx Configuration Files

#### Update nginx/matrix.conf

**Lines 6 and 14**: Change server name
```nginx
server {
    listen 80;
    server_name matrix.equipehgrs.com;
    # ...
}

server {
    listen 443 ssl http2;
    server_name matrix.equipehgrs.com;
    # ...
}
```

**Line 76**: Update well-known matrix client configuration
```nginx
location /.well-known/matrix/client {
    return 200 '{"m.homeserver":{"base_url":"https://matrix.equipehgrs.com/"},"io.element.e2ee":{"default":false,"force_disable":true},"m.identity_server":{"base_url":""}}';
    # ...
}
```

#### Update nginx/element.conf

**Lines 6 and 14**: Change server name
```nginx
server {
    listen 80;
    server_name chat.equipehgrs.com;
    # ...
}

server {
    listen 443 ssl http2;
    server_name chat.equipehgrs.com;
    # ...
}
```

**Line 29**: Update CSP connect-src URLs
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://matrix.equipehgrs.com wss://matrix.equipehgrs.com; font-src 'self'; form-action 'self'; frame-ancestors 'none';" always;
```

### 4. External Infrastructure Updates

#### DNS Configuration
Configure the following DNS records to point to your server IP:

```
A       equipehgrs.com           → YOUR_SERVER_IP
A       www.equipehgrs.com       → YOUR_SERVER_IP
A       matrix.equipehgrs.com    → YOUR_SERVER_IP
A       chat.equipehgrs.com      → YOUR_SERVER_IP
```

#### SSL/TLS Certificates

**If using Let's Encrypt with certbot:**
```bash
# Obtain certificates for all domains
certbot certonly --nginx -d equipehgrs.com -d www.equipehgrs.com
certbot certonly --nginx -d matrix.equipehgrs.com
certbot certonly --nginx -d chat.equipehgrs.com
```

**Update nginx SSL certificate paths in your nginx configurations:**
```nginx
ssl_certificate /etc/letsencrypt/live/equipehgrs.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/equipehgrs.com/privkey.pem;
```

### 5. Deployment Steps

1. **Stop services:**
   ```bash
   docker compose down
   ```

2. **Update configuration files** as described above

3. **Restart services:**
   ```bash
   docker compose up -d
   ```

4. **Verify Matrix integration:**
   ```bash
   # Check Matrix homeserver is accessible
   curl https://matrix.equipehgrs.com/_matrix/client/versions
   
   # Check Element web client
   curl https://chat.equipehgrs.com/
   ```

5. **Update Matrix database** (if needed):
   ```bash
   # Connect to Matrix database and update server references
   # This may be required for existing rooms and user data
   ```

### 6. Post-Migration Verification

- [ ] Main application accessible at `https://equipehgrs.com`
- [ ] Matrix homeserver accessible at `https://matrix.equipehgrs.com`
- [ ] Element web client accessible at `https://chat.equipehgrs.com`
- [ ] SSL certificates valid for all domains
- [ ] Matrix OIDC authentication working
- [ ] Email functionality working with new domain
- [ ] All existing user accounts accessible

### 7. Optional Updates

#### PWA Manifest (if desired)
Update `assets/manifest.json` to reflect new branding:
```json
{
  "name": "EquipeHGRS - Plataforma Médica",
  "short_name": "EquipeHGRS",
  "description": "Plataforma de colaboração médica para HGRS"
}
```

#### Email Templates
Review Django email templates for any hardcoded domain references that may need updating.

## Rollback Plan

If issues occur during migration:

1. **Restore configuration files** from backup
2. **Update DNS records** back to original domain
3. **Restart services:**
   ```bash
   docker compose down && docker compose up -d
   ```

## Troubleshooting

### Common Issues

**Matrix authentication fails:**
- Verify OIDC_ISSUER matches the main domain
- Check Matrix homeserver.yaml server_name
- Ensure MATRIX_FQDN environment variable is correct

**Element client cannot connect:**
- Verify element/config.json has correct Matrix homeserver URL
- Check nginx configuration for chat subdomain
- Verify SSL certificates are valid

**Email functionality broken:**
- Update email DNS records (SPF, DKIM) for new domain
- Verify EMAIL_HOST_USER and DEFAULT_FROM_EMAIL in .env

### Verification Commands

```bash
# Test Django ALLOWED_HOSTS
curl -H "Host: equipehgrs.com" http://localhost:8778/

# Test Matrix homeserver
curl https://matrix.equipehgrs.com/_matrix/client/versions

# Test Element web client
curl https://chat.equipehgrs.com/

# Check SSL certificates
openssl s_client -connect equipehgrs.com:443 -servername equipehgrs.com
```

## Security Considerations

- **Update CSRF_TRUSTED_ORIGINS** if using CSRF protection
- **Review CORS settings** if applicable
- **Update security headers** in nginx configuration
- **Verify SSL certificate chain** is complete
- **Test all authentication flows** after migration

---

**Note**: This migration affects both the main EquipeMed application and the Matrix chat integration. Plan for adequate testing time to ensure all components work correctly with the new domain.