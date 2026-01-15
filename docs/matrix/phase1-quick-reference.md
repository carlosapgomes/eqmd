# Matrix Phase 1 - Quick Reference

## 🚀 Fast Setup (TL;DR)

### Prerequisites Check
```bash
docker --version && docker compose version && uv --version
```

### 1. Update Environment
Edit `.env` and add:
```bash
EQMD_DOMAIN=yourdomain.com
MATRIX_FQDN=matrix.yourdomain.com
CHAT_FQDN=chat.yourdomain.com
MATRIX_DATABASE_PASSWORD=secure_password_here
EQMD_UID=1000
EQMD_GID=1000
```

### 2. Execute Setup Commands (In Order)
```bash
# Generate configs
uv run python scripts/generate_matrix_configs.py

# Start PostgreSQL
docker compose up -d postgres

# Bootstrap database
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=eqmd_user \
POSTGRES_PASSWORD=eqmd_dev_password_123 POSTGRES_DB=eqmd_dev \
MATRIX_DATABASE_PASSWORD=secure_password_here \
uv run python scripts/bootstrap_matrix_db.py

# Generate signing keys
docker run --rm -v $(pwd)/matrix:/data -u 1000:1000 \
-e SYNAPSE_SERVER_NAME=matrix.yourdomain.com \
-e SYNAPSE_REPORT_STATS=no matrixdotorg/synapse:v1.99.0 generate

# Start Matrix services
docker compose up -d matrix-synapse element-web
```

### 3. Verify
```bash
curl http://localhost:8008/_matrix/client/versions
curl -I http://localhost:8080
```

## 🔧 Troubleshooting Commands

### Fix Permissions
```bash
sudo ./scripts/setup_matrix_permissions.sh
```

### Check Logs
```bash
docker compose logs matrix-synapse
```

### Restart Services
```bash
docker compose restart matrix-synapse element-web
```

### Re-generate Configs
```bash
uv run python scripts/generate_matrix_configs.py
```

## 📁 Key Files Created

- `matrix/homeserver.yaml` - Main Synapse config
- `matrix/signing.key` - Crypto keys (auto-generated)
- `element/config.json` - Element Web config  
- `nginx/*.conf` - Production nginx configs

## 🔗 Next Steps

After Phase 1 completion:
1. Phase 2: Configure EquipeMed OIDC Provider
2. Phase 3: Enable Synapse OIDC integration
3. Phase 4: Set up well-known endpoints
4. Phase 5: Policy bot and room management
5. Phase 6: Production deployment and testing

## 📖 Full Documentation

See `docs/matrix/phase1-infrastructure-setup.md` for detailed instructions and troubleshooting.