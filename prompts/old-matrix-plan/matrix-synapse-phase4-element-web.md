# Phase 4: Element Web Client Configuration

## Overview
Deploy and configure Element Web client with disabled E2E encryption, custom branding, and optimized interface for medical team collaboration.

## Prerequisites
- Phase 3 Matrix Synapse configuration completed
- Matrix server accessible via internal network
- nginx configuration prepared
- SSL certificates available

## Step 1: Element Web Configuration

### 1.1 Create Comprehensive Element Configuration
Update `element/config.json`:

```json
{
  "default_server_config": {
    "m.homeserver": {
      "base_url": "https://matrix.yourhospital.com",
      "server_name": "matrix.yourhospital.com"
    },
    "m.identity_server": {
      "base_url": ""
    }
  },
  
  "brand": "EquipeMed Chat",
  "branding": {
    "welcomeBackgroundUrl": "",
    "authHeaderLogoUrl": "",
    "authFooterLinks": [
      {
        "text": "Suporte EquipeMed",
        "url": "mailto:suporte@yourhospital.com"
      }
    ]
  },
  
  "defaultCountryCode": "BR",
  "default_theme": "light",
  "disable_custom_urls": true,
  "disable_guests": true,
  "disable_login_language_selector": false,
  "disable_3pid_login": true,
  
  "enable_presence_by_hs_url": {
    "https://matrix.yourhospital.com": false
  },
  
  "features": {
    "feature_pinning": "disable",
    "feature_custom_status": "disable", 
    "feature_custom_tags": "disable",
    "feature_state_counters": "disable",
    "feature_many_integration_managers": "disable",
    "feature_mjolnir": "disable",
    "feature_dnd": "disable",
    "feature_bridge_state": "disable",
    "feature_groups": "disable",
    "feature_communities_v2_prototypes": "disable",
    "feature_pinning": "disable",
    "feature_custom_themes": "disable"
  },
  
  "default_federate": false,
  "default_guest_access": false,
  "default_history_visibility": "invited",
  
  "roomDirectory": {
    "servers": ["matrix.yourhospital.com"]
  },
  
  "welcomeUserId": "",
  "piwik": false,
  
  "enable_presence_by_hs_url": {
    "https://matrix.yourhospital.com": false
  },
  
  "setting_defaults": {
    "UIFeature.urlPreviews": false,
    "UIFeature.feedback": false,
    "UIFeature.voip": false,
    "UIFeature.widgets": false,
    "UIFeature.communities": false,
    "UIFeature.advancedSettings": false,
    "UIFeature.shareQrCode": false,
    "UIFeature.shareSocial": false,
    "breadcrumbs": false,
    "MessageComposerInput.suggestEmoji": false,
    "MessageComposerInput.ctrlEnterToSend": true,
    "MessageComposerInput.autoReplaceEmoji": false,
    "VideoView.flipVideoHorizontally": false,
    "TagPanel.enableTagPanel": false,
    "theme": "light"
  },
  
  "showLabsSettings": false,
  "integrations_ui_url": "",
  "integrations_rest_url": "",
  "integrations_widgets_urls": [],
  "bug_report_endpoint_url": "",
  "uisi_autorageshake_app": "",
  "clean_cache_on_reload": false,
  
  "jitsi": {
    "preferredDomain": ""
  },
  
  "element_call": {
    "url": "",
    "use_exclusively": false,
    "brand": "Element Call"
  },
  
  "map_style_url": "",
  
  "desktop_builds": {
    "available": false,
    "logo": "",
    "url": ""
  },
  
  "mobile_builds": {
    "ios": "",
    "android": "",
    "fdroid": ""
  }
}
```

### 1.2 Create Custom Element Styling
Create `element/custom.css`:

```css
/* EquipeMed Chat Custom Styling */

/* Hide unnecessary UI elements */
.mx_RoomHeader_button_video,
.mx_RoomHeader_button_voice,
.mx_RoomHeader_button_spotlight {
    display: none !important;
}

/* Hide widgets and integrations */
.mx_AddIntegrationButton,
.mx_IntegrationManager {
    display: none !important;
}

/* Simplify room creation dialog */
.mx_CreateRoomDialog_topic_field,
.mx_CreateRoomDialog_advanced,
.mx_CreateRoomDialog_encryption {
    display: none !important;
}

/* Hide encryption warnings and key backup */
.mx_KeyBackupPanel,
.mx_CryptographyPanel,
.mx_EncryptionInfo {
    display: none !important;
}

/* Medical-themed color scheme */
:root {
    --accent-color: #2d5aa0; /* Medical blue */
    --primary-color: #2d5aa0;
    --warning-color: #e17055; /* Medical orange */
    --alert-color: #d63031; /* Medical red */
    --success-color: #00b894; /* Medical green */
    --sidebar-color: #f8f9fa;
}

/* Custom header styling */
.mx_MatrixToolbar {
    background-color: var(--accent-color) !important;
    color: white !important;
}

/* Room list styling for medical context */
.mx_RoomTile_name {
    font-weight: 500;
}

.mx_RoomTile_avatar .mx_BaseAvatar {
    border: 2px solid var(--accent-color);
}

/* Message composition area */
.mx_MessageComposer_wrapper {
    border-top: 2px solid var(--accent-color);
}

/* Hide community/space features */
.mx_SpacePanel,
.mx_SpaceButton {
    display: none !important;
}

/* Simplify user settings */
.mx_UserSettingsDialog .mx_TabbedView_tabLabel:nth-child(n+6) {
    display: none !important;
}

/* Medical file type indicators */
.mx_MFileBody[title*=".pdf"] .mx_MFileBody_info_filename:before {
    content: "📄 ";
}

.mx_MFileBody[title*=".jpg"] .mx_MFileBody_info_filename:before,
.mx_MFileBody[title*=".jpeg"] .mx_MFileBody_info_filename:before,
.mx_MFileBody[title*=".png"] .mx_MFileBody_info_filename:before {
    content: "🖼️ ";
}

.mx_MFileBody[title*=".mp3"] .mx_MFileBody_info_filename:before,
.mx_MFileBody[title*=".wav"] .mx_MFileBody_info_filename:before,
.mx_MFileBody[title*=".ogg"] .mx_MFileBody_info_filename:before {
    content: "🎵 ";
}

/* Hide encryption padlock icons */
.mx_EventTile_e2eIcon {
    display: none !important;
}

/* Responsive design for tablets */
@media (max-width: 1024px) {
    .mx_LeftPanel {
        width: 280px;
    }
}

/* Print styles for medical documentation */
@media print {
    .mx_RoomHeader,
    .mx_MessageComposer,
    .mx_RightPanel {
        display: none !important;
    }
    
    .mx_EventTile_line {
        page-break-inside: avoid;
    }
}
```

### 1.3 Update Element Docker Configuration
Update the Element service in `docker-compose.yml`:

```yaml
  # Element Web Client
  element-web:
    image: vectorim/element-web:v1.11.46  # Pin to specific stable version
    container_name: ${CONTAINER_PREFIX:-eqmd}_element_web
    restart: unless-stopped
    volumes:
      - ./element/config.json:/app/config.json:ro
      - ./element/custom.css:/app/bundles/[hash]/theme-light.css:ro
      - ./element/welcome.html:/app/welcome.html:ro
    ports:
      - "127.0.0.1:8080:80"  # Internal access only
    networks:
      - matrix-network
    depends_on:
      - matrix-synapse
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    environment:
      - ELEMENT_WEB_CONFIG=/app/config.json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 1.4 Create Custom Welcome Page
Create `element/welcome.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EquipeMed Chat - Comunicação Segura da Equipe Médica</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #2d5aa0 0%, #4a69bd 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .welcome-container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            max-width: 500px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .hospital-logo {
            width: 80px;
            height: 80px;
            background: #2d5aa0;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 32px;
        }
        
        h1 {
            color: #2d5aa0;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        
        .login-button {
            background: #2d5aa0;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s ease;
        }
        
        .login-button:hover {
            background: #1e3a6f;
        }
        
        .features {
            text-align: left;
            margin: 30px 0;
        }
        
        .feature {
            display: flex;
            align-items: center;
            margin: 10px 0;
            color: #444;
        }
        
        .feature-icon {
            width: 20px;
            margin-right: 12px;
            color: #2d5aa0;
        }
        
        .footer {
            margin-top: 30px;
            font-size: 14px;
            color: #888;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <div class="welcome-container">
        <div class="hospital-logo">🏥</div>
        <h1>EquipeMed Chat</h1>
        <p class="subtitle">Comunicação segura e eficiente para a equipe médica</p>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">💬</div>
                <div>Mensagens diretas entre profissionais</div>
            </div>
            <div class="feature">
                <div class="feature-icon">📎</div>
                <div>Compartilhamento seguro de documentos</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🔒</div>
                <div>Integração com sistema EquipeMed</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🤖</div>
                <div>Assistente para elaboração de documentos</div>
            </div>
        </div>
        
        <a href="/#/login" class="login-button">Entrar com EquipeMed</a>
        
        <div class="footer">
            <p>Acesso restrito à equipe médica autorizada</p>
            <p><a href="mailto:suporte@yourhospital.com">Suporte Técnico</a></p>
        </div>
    </div>
</body>
</html>
```

## Step 2: Nginx Configuration for Element and Matrix

### 2.1 Create Production Nginx Configuration
Create `nginx/matrix/matrix.conf`:

```nginx
# Matrix Synapse Server Configuration
server {
    listen 80;
    server_name matrix.yourhospital.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name matrix.yourhospital.com;

    # SSL Configuration (update paths for your certificates)
    ssl_certificate /path/to/ssl/fullchain.pem;
    ssl_private_key /path/to/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Matrix client-server API
    location ~ ^(\/_matrix|\/_synapse\/client) {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        
        # File upload settings for medical documents
        client_max_body_size 50M;
        client_body_timeout 60s;
        
        # Proxy timeouts
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
        proxy_connect_timeout 60s;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Well-known files for Matrix
    location /.well-known/matrix/server {
        return 200 '{"m.server": "matrix.yourhospital.com:443"}';
        default_type application/json;
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, OPTIONS";
        add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
    }

    location /.well-known/matrix/client {
        return 200 '{
            "m.homeserver": {
                "base_url": "https://matrix.yourhospital.com"
            },
            "m.identity_server": {
                "base_url": ""
            },
            "io.element.e2ee": {
                "default": false,
                "force_disable": true
            },
            "im.vector.riot.e2ee": {
                "default": false
            }
        }';
        default_type application/json;
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, OPTIONS";
        add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept, Authorization";
    }

    # Health check endpoint
    location /_matrix/client/versions {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
    }

    # Block unwanted endpoints
    location ~ ^/(_matrix/federation|_matrix/key) {
        return 404;
    }
}

# Element Web Client Configuration
server {
    listen 80;
    server_name chat.yourhospital.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name chat.yourhospital.com;

    # SSL Configuration (same as Matrix server)
    ssl_certificate /path/to/ssl/fullchain.pem;
    ssl_private_key /path/to/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security headers for web application
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Content Security Policy for Element
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://matrix.yourhospital.com wss://matrix.yourhospital.com; media-src 'self' https://matrix.yourhospital.com; object-src 'none'; frame-ancestors 'self';";

    # Root location
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        
        # WebSocket support for Element
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Caching for static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            proxy_pass http://127.0.0.1:8080;
        }
    }

    # Custom welcome page
    location = /welcome {
        proxy_pass http://127.0.0.1:8080/welcome.html;
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 2.2 Create SSL Certificate Check Script
Create `nginx/scripts/check_ssl.sh`:

```bash
#!/bin/bash
# Check SSL certificate validity for Matrix domains

DOMAINS=("matrix.yourhospital.com" "chat.yourhospital.com")

echo "Checking SSL certificates for Matrix domains..."
echo "================================================"

for domain in "${DOMAINS[@]}"; do
    echo "Checking $domain..."
    
    # Check if domain resolves
    if ! nslookup "$domain" > /dev/null 2>&1; then
        echo "❌ $domain does not resolve"
        continue
    fi
    
    # Check SSL certificate
    if ssl_info=$(echo | openssl s_client -connect "$domain:443" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null); then
        echo "✅ $domain SSL certificate is valid"
        echo "   $ssl_info"
    else
        echo "❌ $domain SSL certificate is invalid or not accessible"
    fi
    echo
done

echo "SSL check complete."
```

## Step 3: Docker Configuration Updates

### 3.1 Update Element Service with Custom Assets
Update `docker-compose.yml` Element service:

```yaml
  # Element Web Client with custom configuration
  element-web:
    image: vectorim/element-web:v1.11.46
    container_name: ${CONTAINER_PREFIX:-eqmd}_element_web
    restart: unless-stopped
    volumes:
      - ./element/config.json:/app/config.json:ro
      - ./element/custom.css:/app/custom.css:ro
      - ./element/welcome.html:/app/welcome.html:ro
      # Mount custom theme over default
      - ./element/custom.css:/app/bundles/[hash]/theme-light.css:ro
    ports:
      - "127.0.0.1:8080:80"
    networks:
      - matrix-network
    depends_on:
      - matrix-synapse
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    environment:
      # Custom Element configuration
      - ELEMENT_WEB_CONFIG_FILE=/app/config.json
      - ELEMENT_WEB_CUSTOM_CSS=/app/custom.css
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### 3.2 Add Environment Variables
Add to `.env`:

```bash
# Element Web Configuration
ELEMENT_WEB_VERSION=v1.11.46
ELEMENT_WEB_BRAND="EquipeMed Chat"
ELEMENT_WEB_WELCOME_URL=https://chat.yourhospital.com/welcome
ELEMENT_DEFAULT_THEME=light

# Matrix Well-known Configuration
MATRIX_WELL_KNOWN_CLIENT_URL=https://matrix.yourhospital.com
MATRIX_WELL_KNOWN_SERVER=matrix.yourhospital.com:443
```

## Step 4: E2E Encryption Disable Configuration

### 4.1 Create Matrix Client Policy
Create `matrix/client_policies/e2ee_disabled.json`:

```json
{
  "policies": {
    "encryption": {
      "default_enabled": false,
      "force_disabled": true,
      "allow_toggle": false
    },
    "room_creation": {
      "default_encryption": false,
      "allow_encryption_toggle": false
    },
    "device_verification": {
      "required": false,
      "auto_accept": true
    }
  },
  "ui_features": {
    "encryption_settings": false,
    "device_management": false,
    "key_backup": false,
    "cross_signing": false
  }
}
```

### 4.2 Update Matrix Configuration for E2E Disable
Add to `matrix/homeserver.yaml`:

```yaml
# Additional E2E encryption controls
encryption:
  enabled: true
  default: false
  require_encryption: false

# Client feature controls
client_config:
  encryption:
    default: false
    force_disable: true
  ui_features:
    encryption_panel: false
    key_backup_panel: false
    device_verification: false

# Room encryption defaults
room_defaults:
  encryption: false
  allow_encryption_toggle: false
```

## Step 5: Testing and Validation

### 5.1 Create Element Configuration Test Script
Create `element/scripts/test_element.py`:

```python
#!/usr/bin/env python3
"""Test Element web client configuration."""

import json
import requests
import time
from urllib.parse import urljoin

def test_element_config():
    """Test Element configuration endpoint."""
    base_url = "https://chat.yourhospital.com"
    
    try:
        # Test main Element page
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("✅ Element web client accessible")
        else:
            print(f"❌ Element web client error: {response.status_code}")
            return False
        
        # Test config.json
        config_url = urljoin(base_url, "/config.json")
        response = requests.get(config_url, timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("✅ Element configuration loaded")
            print(f"   Brand: {config.get('brand')}")
            print(f"   Homeserver: {config.get('default_server_config', {}).get('m.homeserver', {}).get('base_url')}")
            return True
        else:
            print(f"❌ Element configuration error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Element test error: {e}")
        return False

def test_matrix_wellknown():
    """Test Matrix well-known endpoints."""
    base_url = "https://matrix.yourhospital.com"
    
    endpoints = [
        "/.well-known/matrix/client",
        "/.well-known/matrix/server"
    ]
    
    for endpoint in endpoints:
        try:
            url = urljoin(base_url, endpoint)
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint} working")
                if endpoint == "/.well-known/matrix/client":
                    e2ee_setting = data.get("io.element.e2ee", {}).get("force_disable", False)
                    print(f"   E2E encryption disabled: {e2ee_setting}")
            else:
                print(f"❌ {endpoint} error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {endpoint} test error: {e}")
            return False
    
    return True

def test_matrix_health():
    """Test Matrix server health."""
    try:
        response = requests.get("https://matrix.yourhospital.com/_matrix/client/versions", timeout=10)
        if response.status_code == 200:
            versions = response.json()
            print("✅ Matrix server health check passed")
            print(f"   Supported versions: {', '.join(versions.get('versions', []))}")
            return True
        else:
            print(f"❌ Matrix server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Matrix health check error: {e}")
        return False

if __name__ == "__main__":
    print("Element Web Client Configuration Test")
    print("=" * 40)
    
    element_ok = test_element_config()
    wellknown_ok = test_matrix_wellknown()
    health_ok = test_matrix_health()
    
    print("\n" + "=" * 40)
    if element_ok and wellknown_ok and health_ok:
        print("✅ All Element tests passed!")
    else:
        print("❌ Some Element tests failed.")
```

### 5.2 Create Complete Integration Test
Create `scripts/test_matrix_integration.sh`:

```bash
#!/bin/bash
# Complete integration test for Matrix setup

echo "Matrix Integration Test Suite"
echo "============================="

# Test 1: Docker services
echo "1. Testing Docker services..."
if docker compose ps matrix-synapse | grep -q "Up"; then
    echo "✅ Matrix Synapse running"
else
    echo "❌ Matrix Synapse not running"
    exit 1
fi

if docker compose ps element-web | grep -q "Up"; then
    echo "✅ Element Web running"
else
    echo "❌ Element Web not running"
    exit 1
fi

# Test 2: Database connectivity
echo -e "\n2. Testing database..."
if docker compose exec postgres psql -U matrix_user -d matrix_db -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Matrix database accessible"
else
    echo "❌ Matrix database connection failed"
fi

# Test 3: OIDC endpoints
echo -e "\n3. Testing OIDC endpoints..."
if curl -s "https://yourhospital.com/.well-known/openid_configuration" > /dev/null; then
    echo "✅ OIDC discovery endpoint accessible"
else
    echo "❌ OIDC discovery endpoint failed"
fi

# Test 4: Matrix endpoints
echo -e "\n4. Testing Matrix endpoints..."
if curl -s "https://matrix.yourhospital.com/_matrix/client/versions" > /dev/null; then
    echo "✅ Matrix client API accessible"
else
    echo "❌ Matrix client API failed"
fi

# Test 5: Element configuration
echo -e "\n5. Testing Element configuration..."
if curl -s "https://chat.yourhospital.com/config.json" | jq '.brand' | grep -q "EquipeMed"; then
    echo "✅ Element configuration correct"
else
    echo "❌ Element configuration incorrect"
fi

# Test 6: E2E encryption disabled
echo -e "\n6. Testing E2E encryption settings..."
if curl -s "https://matrix.yourhospital.com/.well-known/matrix/client" | jq '.["io.element.e2ee"].force_disable' | grep -q "true"; then
    echo "✅ E2E encryption properly disabled"
else
    echo "❌ E2E encryption not properly disabled"
fi

echo -e "\nIntegration test complete!"
```

## Step 6: Production Deployment Verification

### 6.1 SSL Certificate Installation
```bash
# Check SSL certificate validity
chmod +x nginx/scripts/check_ssl.sh
./nginx/scripts/check_ssl.sh

# If certificates need installation/renewal
# (Example for Let's Encrypt - adjust for your setup)
# certbot certonly --nginx -d matrix.yourhospital.com -d chat.yourhospital.com
```

### 6.2 Start Services in Order
```bash
# Start Matrix Synapse first
docker compose up -d matrix-synapse

# Wait for Matrix to be ready
sleep 30

# Check Matrix health
curl -f https://matrix.yourhospital.com/_matrix/client/versions

# Start Element Web
docker compose up -d element-web

# Verify both services
docker compose ps matrix-synapse element-web
```

### 6.3 Configure Nginx
```bash
# Copy nginx configuration
sudo cp nginx/matrix/matrix.conf /etc/nginx/sites-available/matrix

# Enable the site
sudo ln -sf /etc/nginx/sites-available/matrix /etc/nginx/sites-enabled/matrix

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Verification Commands

### Check Element Configuration
```bash
# Test Element web interface
curl -s https://chat.yourhospital.com/config.json | jq '.'

# Test custom styling
curl -s https://chat.yourhospital.com/custom.css | head -10

# Test welcome page
curl -s https://chat.yourhospital.com/welcome.html | grep -i "EquipeMed"
```

### Test E2E Encryption Disable
```bash
# Check Matrix client well-known
curl -s https://matrix.yourhospital.com/.well-known/matrix/client | jq '.["io.element.e2ee"]'

# Expected output: {"force_disable": true}
```

### Test Matrix-Element Integration
```bash
# Run comprehensive test
chmod +x scripts/test_matrix_integration.sh
./scripts/test_matrix_integration.sh

# Run Element-specific tests
cd element/scripts
python3 test_element.py
```

## File Structure Check

After Phase 4, you should have:
```
├── element/
│   ├── config.json             # Element configuration
│   ├── custom.css              # Custom styling
│   ├── welcome.html            # Custom welcome page
│   └── scripts/
│       └── test_element.py     # Element testing script
├── matrix/
│   └── client_policies/
│       └── e2ee_disabled.json  # E2E encryption policy
├── nginx/
│   ├── matrix/
│   │   └── matrix.conf         # Production nginx config
│   └── scripts/
│       └── check_ssl.sh        # SSL verification script
└── scripts/
    └── test_matrix_integration.sh # Integration testing
```

## Next Steps

1. ✅ **Complete Phase 4** Element web client setup
2. ➡️ **Proceed to Phase 5** for user management integration
3. 🌐 **Test web interface** at `https://chat.yourhospital.com`
4. 🔒 **Verify E2E encryption is disabled**

## Troubleshooting

### Common Element Issues
- **Config not loading**: Check Element container logs and volume mounts
- **CORS errors**: Verify nginx configuration and allowed origins
- **Custom CSS not applied**: Check file paths and container restart

### Debug Commands
```bash
# Check Element container logs
docker compose logs element-web

# Test Element configuration loading
docker compose exec element-web cat /app/config.json

# Check nginx proxy headers
curl -I https://chat.yourhospital.com

# Test Matrix connectivity from Element perspective
curl -s "https://matrix.yourhospital.com/_matrix/client/versions" -H "Origin: https://chat.yourhospital.com"
```

---

**Status**: Element Web client configured with disabled E2E encryption and ready for user management integration