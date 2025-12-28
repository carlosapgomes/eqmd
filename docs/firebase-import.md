# Firebase Data Import

## Incremental Data Sync from Firebase

Incrementally sync patients and dailynotes from Firebase Realtime Database to EQMD in a single command. The sync process automatically handles both patients and dailynotes in the correct order (patients first, then dailynotes) with intelligent draft filtering. Requires `firebase-admin` package (already installed).

### Prerequisites

1. Firebase service account credentials JSON file
2. Valid user account for import attribution

### Basic Usage

```bash
# Initial sync with dry run (recommended first step)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-01 \
  --dry-run

# Initial sync for real
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-01 \
  --user-email admin@yourcompany.com

# Daily incremental sync (recommended approach)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date $(date -d "yesterday" +%Y-%m-%d) \
  --user-email admin@yourcompany.com

# Test sync with limits
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-20 \
  --limit 10 \
  --dry-run

# Sync only patients (skip dailynotes)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --no-sync-dailynotes \
  --user-email admin@yourcompany.com

# Sync only dailynotes (skip patients)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --no-sync-patients \
  --user-email admin@yourcompany.com
```

### Docker Usage

#### Docker Compose

**Option 1: Temporary Mount (Recommended - Most Secure)**

```bash
# Initial sync with dry run
docker-compose run --rm \
  -v /path/to/firebase-key.json:/app/firebase-key.json:ro \
  eqmd uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date 2025-08-01 \
    --user-email admin@yourcompany.com \
    --dry-run

# Daily sync (automatic date calculation)
docker-compose run --rm \
  -v /path/to/firebase-key.json:/app/firebase-key.json:ro \
  eqmd uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --user-email admin@yourcompany.com \
    --chunk-size 500
```

**Option 2: Copy with Cleanup**

```bash
# Daily sync with copy and cleanup
docker-compose cp firebase-key.json eqmd:/app/firebase-key.json && \
docker-compose exec eqmd uv run python manage.py sync_firebase_data \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date $(date -d "yesterday" +%Y-%m-%d) \
  --user-email admin@yourcompany.com \
  --chunk-size 500 && \
docker-compose exec eqmd rm /app/firebase-key.json
```

**Option 3: Manual Copy with Shell Cleanup**

```bash
# Copy credentials
docker-compose cp firebase-key.json eqmd:/app/firebase-key.json

# Run with cleanup in single command
docker-compose exec eqmd bash -c "
  uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date \$(date -d 'yesterday' +%Y-%m-%d) \
    --user-email admin@yourcompany.com \
    --chunk-size 500 && \
  rm firebase-key.json
"
```

#### Standalone Docker

**Secure Mount (Recommended)**

```bash
# Daily sync with secure mount
docker run --rm -it \
  -v /path/to/firebase-key.json:/app/firebase-key.json:ro \
  -v /path/to/db:/app/db \
  your-eqmd-image \
  uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --user-email admin@yourcompany.com \
    --chunk-size 500
```

#### Production Docker (Using Secrets)

**Docker Swarm Secrets**

```bash
# Create secret from credentials file
echo "$(cat firebase-key.json)" | docker secret create firebase-creds -

# Run daily sync with secret
docker service create --rm \
  --secret firebase-creds \
  --mount type=tmpfs,destination=/tmp \
  your-eqmd-image sh -c "
    cp /run/secrets/firebase-creds /tmp/firebase-key.json && \
    uv run python manage.py sync_firebase_data \
      --credentials-file /tmp/firebase-key.json \
      --database-url https://your-project.firebaseio.com \
      --project-name your-project \
      --since-date 2025-08-25 \
      --user-email admin@yourcompany.com
  "

# Clean up secret after use
docker secret rm firebase-creds
```

**Kubernetes Secrets**

```bash
# Create secret
kubectl create secret generic firebase-creds \
  --from-file=firebase-key.json

# Run daily sync job with secret mount
kubectl run firebase-sync --rm -i --restart=Never \
  --image=your-eqmd-image \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "firebase-sync",
        "image": "your-eqmd-image",
        "command": ["uv", "run", "python", "manage.py", "sync_firebase_data"],
        "args": [
          "--credentials-file", "/tmp/firebase-key.json",
          "--database-url", "https://your-project.firebaseio.com",
          "--project-name", "your-project",
          "--since-date", "2025-08-25",
          "--user-email", "admin@yourcompany.com"
        ],
        "volumeMounts": [{
          "name": "firebase-creds",
          "mountPath": "/tmp",
          "readOnly": true
        }]
      }],
      "volumes": [{
        "name": "firebase-creds",
        "secret": {
          "secretName": "firebase-creds",
          "items": [{"key": "firebase-key.json", "path": "firebase-key.json"}]
        }
      }]
    }
  }'

# Clean up secret
kubectl delete secret firebase-creds
```

### Automated Daily Sync with Cron

**Linux Cron Example**

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/eqmd && docker-compose run --rm \
  -v /path/to/firebase-key.json:/app/firebase-key.json:ro \
  eqmd uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +\%Y-\%m-\%d) \
    --user-email admin@yourcompany.com \
    --chunk-size 500 >> /var/log/firebase-sync.log 2>&1
```

### Command Options

- `--credentials-file`: Firebase service account JSON (required)
- `--database-url`: Firebase Realtime Database URL (required)
- `--project-name`: Firebase project name (required)
- `--since-date`: Sync data from this date YYYY-MM-DD (required)
- `--patients-reference`: Database reference path for patients (default: "patients")
- `--dailynotes-reference`: Database reference path for dailynotes (default: "dailynotes")
- `--user-email`: User email for import attribution (uses first superuser if not provided)
- `--dry-run`: Preview without importing
- `--limit`: Import only N records per type (useful for testing)
- `--no-sync-patients`: Skip patient sync (default: sync both patients and dailynotes)
- `--no-sync-dailynotes`: Skip dailynotes sync (default: sync both patients and dailynotes)

### Sync Process (Automatic Ordering)

The `sync_firebase_data` command automatically syncs in the correct order:

1. **Patient Sync First**:
   - Filters patients by `registrationDt` >= since-date timestamp
   - Creates dual PatientRecordNumbers (Firebase key + ptRecN)
   - Skips test patients containing "teste" or "paciente" (case-insensitive)
   - Skips existing patients (by either Firebase key or ptRecN)
   - Maps Firebase fields to EQMD Patient model with proper admission handling

2. **Dailynote Sync Second**:
   - Filters dailynotes by `datetime` >= since-date timestamp
   - **Automatically excludes draft dailynotes** by checking currentdailynotekey references
   - Matches patients using Firebase `patient` field against `PatientRecordNumber.record_number`
   - Skips duplicate dailynotes (by patient, datetime, and Firebase ID)
   - Formats content with Firebase ID reference for traceability

3. **Output**: Displays next cutoff date for subsequent sync runs

**Key Benefits:**
- **Single command** replaces manual two-step process
- **Automatic ordering** ensures patients exist before dailynotes
- **Draft filtering** prevents importing incomplete/draft notes
- **Optimized performance** with intelligent chunking (default: 1000 records)

### Patient Field Mapping

| Firebase Field                  | EQMD Field                    | Notes                                                         |
| ------------------------------- | ----------------------------- | ------------------------------------------------------------- |
| Object Key                      | PatientRecordNumber (old)     | Firebase key, non-current                                     |
| `ptRecN`                        | PatientRecordNumber (current) | Hospital number, current                                      |
| `birthDt`                       | Patient.birthday              | Epoch milliseconds → date                                     |
| `gender`                        | Patient.gender                | 1→M, 2→F, 9→O, ""→NOT_INFORMED                                |
| `name`                          | Patient.name                  |                                                               |
| `registrationDt`                | Patient.created_at            | Epoch milliseconds → datetime                                 |
| `address`                       | Patient.address               |                                                               |
| `city`                          | Patient.city                  |                                                               |
| `phone`                         | Patient.phone                 |                                                               |
| `state`                         | Patient.state                 |                                                               |
| `zip`                           | Patient.zip_code              |                                                               |
| `unifiedHealthCareSystemNumber` | Patient.healthcard_number     |                                                               |
| `lastAdmissionDate`             | Patient.last_admission_date   | Epoch milliseconds → date                                     |
| `status`                        | Patient.status                | inpatient→INPATIENT, outpatient→OUTPATIENT, deceased→DECEASED |

### Security Best Practices

**Credential Handling Priority:**

1. **🥇 Temporary Mounts** - Credentials never persist in container (Options 1)
2. **🥈 Docker Secrets** - Enterprise-grade secret management (Production)
3. **🥉 Copy with Cleanup** - Manual cleanup required (Options 2-3)

**Environment Recommendations:**

- **Development**: Use temporary mount (Option 1)
- **CI/CD Pipelines**: Use Docker/Kubernetes secrets
- **Production**: Always use secrets management systems + automated cron
- **Quick Testing**: Copy with cleanup (Option 2)

### Troubleshooting

**Patient Import Issues:**

- Check Firebase patient structure matches expected fields
- Verify patient names don't contain test data keywords ("teste", "paciente")
- Test patients are automatically skipped
- Use `--dry-run` to preview what will be synced

**Dailynote Import Issues:**

- Ensure patients are synced first (automatic when using both syncs)
- Check Firebase `patient` field matches PatientRecordNumber values
- Draft dailynotes are automatically excluded (currentdailynotekey filtering)

**Date/Time Issues:**

- Firebase timestamps are in epoch milliseconds
- EQMD stores in local timezone
- Use `--dry-run` to verify date parsing
- For daily sync, use `$(date -d "yesterday" +%Y-%m-%d)` for automatic date calculation

**Performance Issues:**

- Adjust `--chunk-size` parameter (default: 1000, try 500 for slower networks)
- Use `--limit` parameter for testing with smaller datasets
- Monitor Docker container resources during large syncs

## Production Deployment Examples

### Recommended Single-Command Approach

**For production deployments, use the single `sync_firebase_data` command that automatically handles both patients and dailynotes in the correct order:**

```bash
# Production daily sync (cron-ready)
docker-compose run --rm \
  -v ./firebase-key.json:/app/firebase-key.json:ro \
  eqmd python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --chunk-size 500
```

### Cron Job Setup

**Simple Daily Sync (2 AM)**
```bash
# Add to crontab
0 2 * * * cd /path/to/your/project && docker-compose run --rm \
  -v ./firebase-key.json:/app/firebase-key.json:ro \
  eqmd python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +%Y-%m-%d) \
    --chunk-size 500 >> /var/log/firebase-sync.log 2>&1
```

**Advanced Cron with Error Handling**
```bash
# Cron with email alerts on failure
0 2 * * * cd /path/to/your/project && (
  docker-compose run --rm \
    -v ./firebase-key.json:/app/firebase-key.json:ro \
    eqmd python manage.py sync_firebase_data \
      --credentials-file firebase-key.json \
      --database-url https://your-project.firebaseio.com \
      --project-name your-project \
      --since-date $(date -d "yesterday" +%Y-%m-%d) \
      --chunk-size 500 \
  || echo "Firebase sync failed at $(date)" | mail -s "Firebase Sync Error" admin@yourcompany.com
) >> /var/log/firebase-sync.log 2>&1
```

### Security Best Practices

**Credential Handling:**

- **Always use read-only mounts** (`:ro` flag) for credential files
- **Never commit** Firebase credentials to version control
- **Use secrets management** for production environments
- **Rotate credentials** regularly following security best practices
- **Use single command approach** to minimize credential exposure time
- **Monitor sync logs** for successful completion and error detection

**Production Recommendations:**

- **Use the production cron examples** above for automated daily syncing
- **Monitor disk space** and log rotation for sync logs
- **Set up email alerts** for failed sync attempts
- **Verify sync success** by checking the daily output logs
- **Keep firebase credentials secure** and accessible only to authorized systems
