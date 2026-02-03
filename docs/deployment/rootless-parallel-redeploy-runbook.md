# Parallel Rootless Redeploy Runbook (Rootful -> Rootless)

This runbook migrates a rootful Docker deployment (using `upgrade.sh`) to a
parallel **rootless** Docker deployment, so you can validate and cut over
without breaking the existing system.

It assumes:
- Your current deployment is rootful and lives in a separate directory.
- You want the new rootless stack to run **in parallel** (different ports and
  container/volume names).
- You will cut over by changing nginx (or other reverse proxy) to the new port.

---

## Variables (tailored to your host)

```bash
ROOTFUL_DIR=/opt/hgrs
ROOTLESS_USER=eqmdr
ROOTLESS_DIR=/home/${ROOTLESS_USER}/eqmd-app-rootless
BACKUP_DIR=/home/${ROOTLESS_USER}/backup

# Use a distinct prefix and ports so both stacks can run in parallel.
CONTAINER_PREFIX=hgrs-rootless
HOST_PORT=8780
POSTGRES_PORT=5433
MATRIX_SYNAPSE_PORT=8009
MATRIX_ELEMENT_PORT=8081
```

Notes:
- Rootless Docker cannot bind to ports <1024. The defaults above are safe.
- Keep the rootful stack running until you cut over.
- This runbook uses a **new user** (`eqmdr`) to avoid changing the existing
  `eqmd` account shell and to keep rootful and rootless deployments isolated.

---

## Step 1: Back up rootful data (no downtime)

From the **rootful** deployment directory:

```bash
cd "$ROOTFUL_DIR"

sudo -u ${ROOTLESS_USER} -i
# as user eqmdr
mkdir ${$BACKUP_DIR}  && exit

# Database backup (logical, preferred).
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-eqmd_user}" \
  -d "${POSTGRES_DB:-eqmd_db}" -Fc \
  > "$BACKUP_DIR/eqmd_db_$(date +%Y%m%d_%H%M%S).dump"

# Media backup (volume copy).
docker run --rm -v "${CONTAINER_PREFIX:-eqmd}_media_files:/source" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar czf "/backup/eqmd_media_$(date +%Y%m%d_%H%M%S).tar.gz" -C /source .

# Optional: Matrix data if you use it.
docker run --rm -v "${CONTAINER_PREFIX:-eqmd}_matrix_data:/source" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar czf "/backup/eqmd_matrix_data_$(date +%Y%m%d_%H%M%S).tar.gz" -C /source .
docker run --rm -v "${CONTAINER_PREFIX:-eqmd}_matrix_media_store:/source" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar czf "/backup/eqmd_matrix_media_$(date +%Y%m%d_%H%M%S).tar.gz" -C /source .
```

Keep the most recent DB dump for the final cutover.

---

## Step 2: Install rootless Docker for the new `eqmdr` user

As root:

```bash
sudo useradd --create-home --shell /bin/bash ${ROOTLESS_USER} || true
sudo loginctl enable-linger ${ROOTLESS_USER}

# Ensure subuid/subgid entries exist for the new user
echo "${ROOTLESS_USER}:165536:65536" | sudo tee -a /etc/subuid
echo "${ROOTLESS_USER}:165536:65536" | sudo tee -a /etc/subgid

# Rootless prerequisites (needed for uid mappings and networking)
sudo apt-get update
sudo apt-get install -y uidmap slirp4netns fuse-overlayfs
```

As `eqmd` user:

```bash
sudo -u ${ROOTLESS_USER} -i

curl -fsSL https://get.docker.com/rootless | sh

# Set required env vars for rootless usage
echo 'export XDG_RUNTIME_DIR=/home/${ROOTLESS_USER}/.docker/run' >> ~/.bashrc
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
echo 'export DOCKER_HOST=unix:///home/${ROOTLESS_USER}/.docker/run/docker.sock' >> ~/.bashrc
source ~/.bashrc

# Exit the eqmdr shell before enabling the system service
exit

# Run rootless dockerd as a system service (recommended on servers)
sudo tee /etc/systemd/system/docker-rootless@.service > /dev/null << 'EOF'
[Unit]
Description=Rootless Docker for %i
After=network.target

[Service]
User=%i
Environment=PATH=/home/%i/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=XDG_RUNTIME_DIR=/home/%i/.docker/run
Environment=DOCKER_HOST=unix:///home/%i/.docker/run/docker.sock
ExecStart=/home/%i/bin/dockerd-rootless.sh
Restart=on-failure
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now docker-rootless@${ROOTLESS_USER}

# Verify as rootless user
sudo -u ${ROOTLESS_USER} -H env \
  XDG_RUNTIME_DIR=/home/${ROOTLESS_USER}/.docker/run \
  DOCKER_HOST=unix:///home/${ROOTLESS_USER}/.docker/run/docker.sock \
  docker version

# If you see "Permission denied" when starting containers, force cgroupfs:
sudo -u ${ROOTLESS_USER} -H mkdir -p /home/${ROOTLESS_USER}/.config/docker
sudo -u ${ROOTLESS_USER} -H tee /home/${ROOTLESS_USER}/.config/docker/daemon.json > /dev/null << 'EOF'
{
  "exec-opts": ["native.cgroupdriver=cgroupfs"]
}
EOF
sudo systemctl restart docker-rootless@${ROOTLESS_USER}

# Note: rootless without systemd user sessions may report "Cgroup Driver: none".
# That is OK for this migration (no resource limits), but if you need cgroups,
# enable a user systemd session (dbus-user-session + loginctl enable-linger)
# and run rootless dockerd via systemd --user instead.

# If Postgres fails with "failed switching to 'postgres': operation not permitted",
# the uidmap helpers are missing or not in effect. Verify:
#   which newuidmap && which newgidmap
# Then restart the rootless service after installing uidmap.
#
# If uidmap is OK and Postgres still fails, check the `postgres` service in
# docker-compose.rootless.yml and remove restrictive `cap_drop`/`security_opt`
# that prevent chown/setuid in rootless mode.
```

---

## Step 3: Prepare the rootless deployment directory

As `eqmd` user:

```bash
mkdir -p "$ROOTLESS_DIR" "$BACKUP_DIR"
cd "$ROOTLESS_DIR"

# Option A: clone the repo
# git clone <your_repo_url> .

# Option B: copy from rootful deployment (keeps configs)
# rsync -a --exclude=.git "$ROOTFUL_DIR/" "$ROOTLESS_DIR/"
```

Create a **rootless .env** based on your rootful `.env`:

```bash
cp .env .env.rootless

# Ensure parallel identifiers and ports
sed -i \
  -e "s/^CONTAINER_PREFIX=.*/CONTAINER_PREFIX=${CONTAINER_PREFIX}/" \
  -e "s/^HOST_PORT=.*/HOST_PORT=${HOST_PORT}/" \
  -e "s/^POSTGRES_PORT=.*/POSTGRES_PORT=${POSTGRES_PORT}/" \
  -e "s/^MATRIX_SYNAPSE_PORT=.*/MATRIX_SYNAPSE_PORT=${MATRIX_SYNAPSE_PORT}/" \
  -e "s/^MATRIX_ELEMENT_PORT=.*/MATRIX_ELEMENT_PORT=${MATRIX_ELEMENT_PORT}/" \
  .env.rootless

# Remove UID/GID overrides (rootless handles mapping).
sed -i '/^EQMD_UID=/d' .env.rootless
sed -i '/^EQMD_GID=/d' .env.rootless
```

---

## Step 4: Create a rootless compose file

Make a rootless-specific compose file (copy and edit):

```bash
cp docker-compose.deploy.yml docker-compose.rootless.yml
```

Edit `docker-compose.rootless.yml`:
- **Remove** `user:` for `eqmd` and `matrix-synapse`.
- **Remove** `USER_ID` / `GROUP_ID` build args.
- **Remove or disable** the `media-init` service (its `chown` is not needed).
- If using `/srv/eqmd-static`, **remove** the `static-init` service and the
  `eqmd_static_files` named volume; replace with a bind mount on the `eqmd`
  service: `/srv/eqmd-static:/srv/eqmd-static`.
- For `postgres`, remove any `cap_drop: - ALL` and `security_opt: - no-new-privileges:true`
  so the entrypoint can `chown` and switch to the `postgres` user in rootless mode.
- Keep ports, volumes, and services unchanged otherwise.

Optional (cleaner rootless image):
- In `Dockerfile`, remove the `USER_ID`/`GROUP_ID` ARGs and `USER eqmd`
  block so the container runs as root (mapped to host user by rootless).
- If you do this, rebuild the image in the rootless environment.

---

## Step 5: Build or pull the image (rootless)

As `eqmd` user, in `$ROOTLESS_DIR`:

```bash
docker compose -f docker-compose.rootless.yml --env-file .env.rootless pull eqmd
# If you edited Dockerfile, build instead:
# docker compose -f docker-compose.rootless.yml --env-file .env.rootless build eqmd
```

---

## Step 6: Restore data to the rootless volumes

Create volumes by starting postgres once, then stop it:

```bash
docker compose -f docker-compose.rootless.yml --env-file .env.rootless up -d postgres
docker compose -f docker-compose.rootless.yml --env-file .env.rootless stop postgres
```

Restore DB using the latest dump:

```bash
docker compose -f docker-compose.rootless.yml --env-file .env.rootless up -d postgres

cat "$BACKUP_DIR/eqmd_db_YYYYMMDD_HHMMSS.dump" | \
  docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
  exec -T postgres pg_restore -U "${POSTGRES_USER:-eqmd_user}" \
  -d "${POSTGRES_DB:-eqmd_db}" --clean --if-exists
```

Restore media (and optional Matrix) data into volumes:

```bash
docker run --rm -v "${CONTAINER_PREFIX}_media_files:/target" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar xzf "/backup/eqmd_media_YYYYMMDD_HHMMSS.tar.gz" -C /target

# Optional Matrix restores
docker run --rm -v "${CONTAINER_PREFIX}_matrix_data:/target" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar xzf "/backup/eqmd_matrix_data_YYYYMMDD_HHMMSS.tar.gz" -C /target
docker run --rm -v "${CONTAINER_PREFIX}_matrix_media_store:/target" \
  -v "$BACKUP_DIR:/backup" alpine \
  tar xzf "/backup/eqmd_matrix_media_YYYYMMDD_HHMMSS.tar.gz" -C /target
```

---

## Step 7: Run migrations and start the rootless app

```bash
docker compose -f docker-compose.rootless.yml --env-file .env.rootless up -d postgres
docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
  run --rm eqmd python manage.py migrate --noinput

docker compose -f docker-compose.rootless.yml --env-file .env.rootless up -d eqmd
```

Health check:

```bash
curl -f "http://localhost:${HOST_PORT}/health/"
```

---

## Step 8: Static files strategy (choose one)

### Option A (rootless-friendly, recommended)
Bind-mount `/srv/eqmd-static` to `/app/staticfiles` so Django can keep the
default `STATIC_ROOT` without code changes.

1) Create a shared static directory and permissions:
   ```bash
   sudo mkdir -p /srv/eqmd-static
   sudo chown -R ${ROOTLESS_USER}:www-data /srv/eqmd-static
   sudo chmod -R 750 /srv/eqmd-static
   ```
2) In `docker-compose.rootless.yml`, set the `eqmd` service volume to:
   ```yml
   volumes:
     - /srv/eqmd-static:/app/staticfiles
   ```
   Remove the `eqmd_static_files` named volume if it exists.
3) If the `eqmd` service is already running, restart it:
   ```bash
   docker compose -f docker-compose.rootless.yml --env-file .env.rootless up -d eqmd
   ```
4) Update nginx to point to `/srv/eqmd-static/`:
   ```nginx
   location = /static/sw.js {
       alias /srv/eqmd-static/sw.js;
       add_header Content-Type "text/javascript; charset=utf-8";
       add_header Cache-Control "no-cache, must-revalidate";
       add_header Service-Worker-Allowed "/";
       expires off;
   }

   location /static/ {
       alias /srv/eqmd-static/;
       expires 1y;
       add_header Cache-Control "public, immutable";
       add_header X-Served-By "nginx-static";

       gzip on;
       gzip_vary on;
       gzip_types
           text/css
           text/javascript
           text/xml
           text/plain
           application/javascript
           application/xml+rss
           application/json;
   }

   # Switch upstream to the rootless app port
   location /health/ {
       proxy_pass http://localhost:8780;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }

   location / {
       proxy_pass http://localhost:8780;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;

       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";

       proxy_connect_timeout 60s;
       proxy_send_timeout 60s;
       proxy_read_timeout 60s;
   }
   ```
5) Reload nginx after editing:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
6) Run:
   ```bash
   docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
     run --rm eqmd python manage.py collectstatic --noinput
   ```
7) Verify the mount and files:
   ```bash
   docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
     exec eqmd ls -la /app/staticfiles
   ```
8) Verify nginx can serve a static asset (replace host if needed):
   ```bash
   curl -I https://hgrs.equipemed.app/static/manifest.json
   curl -I https://hgrs.equipemed.app/static/sw.js
   ```

### Option B (keep current /var/www flow)
If your nginx expects `/var/www/...`, you can still copy from the container:
1) Collect static in the container (as above).
2) As root, copy from the container to `/var/www/...` similar to `upgrade.sh`.

---

## Step 9: Cutover

1) Pause your daily sync job briefly.
2) Take a **final DB dump** from the old system and restore it into rootless
   (repeat Step 6).
3) Re-run migrations (Step 7).
4) If not already updated in Step 8, update nginx to the new `HOST_PORT`
   (and static alias, if applicable).
5) Verify application behavior.

Rollback is simple: point nginx back to the old port while rootful is still running.

---

## Step 10: Import reference data (drugs, ICD-10, procedures)

Run from `$ROOTLESS_DIR`:

```bash
# Drugs (medications)
docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
  exec -T eqmd python manage.py import_medications_csv fixtures/MERGED_medications.csv

# ICD-10 codes
docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
  exec -T eqmd python manage.py import_icd10_codes --file=fixtures/cid.csv

# Procedures
docker compose -f docker-compose.rootless.yml --env-file .env.rootless \
  exec -T eqmd python manage.py import_procedures --file=fixtures/procedimentos.csv
```

If the `eqmd` service is not running yet, swap `exec -T` for `run --rm`.

---

## Step 11: Decommission (after validation)

Once stable:

```bash
cd "$ROOTFUL_DIR"
sudo docker compose down
```

Keep backups for a few days before cleanup.

---

## Important notes

- Do **not** use `upgrade.sh` for the rootless stack. It assumes rootful Docker
  and performs root-level file operations.
- Rootless Docker uses user namespaces; permissions behave differently. Removing
  `EQMD_UID`/`EQMD_GID` and `user:` directives avoids the common pitfalls.

---

## Nginx updates for your current site

Your current nginx site uses port `8779` and a static alias like:
`/var/www/hgrs_static_ghcr_io_carlosapgomes_eqmd_latest/`.

For the rootless stack:
1) Change `proxy_pass` targets from `http://localhost:8779` to
   `http://localhost:8780`.
2) Update the `/static/` and `/static/sw.js` aliases to the new static path
   you choose in Step 8.
3) Reload nginx:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
