# Firebase Data Import

## Incremental Data Sync from Firebase

Incrementally sync patients and dailynotes from Firebase Realtime Database to EQMD. Includes both initial bulk import and ongoing daily sync capabilities. Requires `firebase-admin` package (already installed).

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

# Daily sync (use date from previous sync output)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --user-email admin@yourcompany.com

# Test sync with limits
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-20 \
  --limit 10 \
  --dry-run

# Sync only patients (no dailynotes)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --sync-patients \
  --user-email admin@yourcompany.com

# Sync only dailynotes (no patients)
uv run python manage.py sync_firebase_data \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --sync-dailynotes \
  --user-email admin@yourcompany.com
```

### Docker Usage

#### Docker Compose

**Option 1: Temporary Mount (Recommended - Most Secure)**
```bash
# Initial sync with dry run
docker-compose run --rm --user root \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  web uv run python manage.py sync_firebase_data \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date 2025-08-01 \
    --user-email admin@yourcompany.com \
    --dry-run

# Daily sync
docker-compose run --rm --user root \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  web uv run python manage.py sync_firebase_data \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date 2025-08-25 \
    --user-email admin@yourcompany.com
```

**Option 2: Copy with Cleanup**
```bash
# Daily sync with copy and cleanup
docker-compose cp firebase-key.json web:/app/firebase-key.json && \
docker-compose exec web uv run python manage.py sync_firebase_data \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --since-date 2025-08-25 \
  --user-email admin@yourcompany.com && \
docker-compose exec web rm /app/firebase-key.json
```

**Option 3: Manual Copy with Shell Cleanup**
```bash
# Copy credentials
docker-compose cp firebase-key.json web:/app/firebase-key.json

# Run with cleanup in single command
docker-compose exec web bash -c "
  uv run python manage.py sync_firebase_data \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date 2025-08-25 \
    --user-email admin@yourcompany.com && \
  rm firebase-key.json
"
```

#### Standalone Docker

**Secure Mount (Recommended)**
```bash
# Daily sync with secure mount
docker run --rm -it \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  -v /path/to/db:/app/db \
  your-eqmd-image \
  uv run python manage.py sync_firebase_data \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date 2025-08-25 \
    --user-email admin@yourcompany.com
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
0 2 * * * cd /path/to/eqmd && docker-compose run --rm --user root \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  web uv run python manage.py sync_firebase_data \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --since-date $(date -d "yesterday" +\%Y-\%m-\%d) \
    --user-email admin@yourcompany.com >> /var/log/firebase-sync.log 2>&1
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
- `--sync-patients`: Enable patient sync (default: True)
- `--sync-dailynotes`: Enable dailynotes sync (default: True)

### Sync Process

1. **Patient Import**:
   - Filters patients by `registrationDt` >= since-date timestamp
   - Creates dual PatientRecordNumbers (Firebase key + ptRecN)
   - Skips test patients containing "teste" or "paciente" (case-insensitive)
   - Skips existing patients (by either Firebase key or ptRecN)
   - Maps Firebase fields to EQMD Patient model

2. **Dailynote Import**:
   - Filters dailynotes by `datetime` >= since-date timestamp
   - Matches patients using Firebase `patient` field against `PatientRecordNumber.record_number`
   - Skips duplicate dailynotes (by patient, datetime, and Firebase ID)
   - Formats content with Firebase ID reference for traceability

3. **Output**: Displays next cutoff date for subsequent sync runs

### Patient Field Mapping

| Firebase Field | EQMD Field | Notes |
|---------------|------------|--------|
| Object Key | PatientRecordNumber (old) | Firebase key, non-current |
| `ptRecN` | PatientRecordNumber (current) | Hospital number, current |
| `birthDt` | Patient.birthday | Epoch milliseconds → date |
| `gender` | Patient.gender | 1→M, 2→F, 9→O, ""→NOT_INFORMED |
| `name` | Patient.name | |
| `registrationDt` | Patient.created_at | Epoch milliseconds → datetime |
| `address` | Patient.address | |
| `city` | Patient.city | |
| `phone` | Patient.phone | |
| `state` | Patient.state | |
| `zip` | Patient.zip_code | |
| `unifiedHealthCareSystemNumber` | Patient.healthcard_number | |
| `lastAdmissionDate` | Patient.last_admission_date | Epoch milliseconds → date |
| `status` | Patient.status | inpatient→INPATIENT, outpatient→OUTPATIENT, deceased→DECEASED |

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
- Verify patient names don't contain test data keywords
- Test patients are automatically skipped

**Dailynote Import Issues:**
- Ensure patients exist before importing dailynotes
- Check Firebase `patient` field matches PatientRecordNumber values

**Date/Time Issues:**
- Firebase timestamps are in epoch milliseconds
- EQMD stores in local timezone
- Use `--dry-run` to verify date parsing

## Import Dailynotes from Firebase (Legacy Bulk Import)

Import dailynotes from Firebase Realtime Database to EQMD. Requires `firebase-admin` package (already installed).

### Prerequisites
1. Firebase service account credentials JSON file
2. Patients already imported (command matches using `PatientRecordNumber.record_number`)
3. Valid user account for import attribution

### Basic Usage

```bash
# Dry run to preview import
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --dry-run

# Import with specific user
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --user-email admin@yourcompany.com

# Test import with limited records
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --limit 10

# Large dataset with chunking
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --chunk-size 100

# Resume interrupted import
uv run python manage.py import_firebase_dailynotes \
  --credentials-file /path/to/firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --start-key "firebase-key-from-previous-run"
```

### Docker Usage

#### Docker Compose

**Option 1: Temporary Mount (Recommended - Most Secure)**
```bash
# Mount as read-only temporary volume (auto-cleanup)
docker-compose run --rm --user root \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  web uv run python manage.py import_firebase_dailynotes \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com
```

**Option 2: Copy with Cleanup**
```bash
# Copy, run, and remove in one command
docker-compose cp firebase-key.json web:/app/firebase-key.json && \
docker-compose exec web uv run python manage.py import_firebase_dailynotes \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --project-name your-project \
  --user-email admin@yourcompany.com && \
docker-compose exec web rm /app/firebase-key.json
```

**Option 3: Manual Copy with Shell Cleanup**
```bash
# Copy credentials
docker-compose cp firebase-key.json web:/app/firebase-key.json

# Run with cleanup in single command
docker-compose exec web bash -c "
  uv run python manage.py import_firebase_dailynotes \
    --credentials-file firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com && \
  rm firebase-key.json
"
```

#### Standalone Docker

**Secure Mount (Recommended)**
```bash
# Mount credentials as read-only volume (auto-cleanup)
docker run --rm -it \
  -v /path/to/firebase-key.json:/tmp/firebase-key.json:ro \
  -v /path/to/db:/app/db \
  your-eqmd-image \
  uv run python manage.py import_firebase_dailynotes \
    --credentials-file /tmp/firebase-key.json \
    --database-url https://your-project.firebaseio.com \
    --project-name your-project \
    --user-email admin@yourcompany.com
```

#### Production Docker (Using Secrets)

**Docker Swarm Secrets**
```bash
# Create secret from credentials file
echo "$(cat firebase-key.json)" | docker secret create firebase-creds -

# Run service with secret (auto-cleanup)
docker service create --rm \
  --secret firebase-creds \
  --mount type=tmpfs,destination=/tmp \
  your-eqmd-image sh -c "
    cp /run/secrets/firebase-creds /tmp/firebase-key.json && \
    uv run python manage.py import_firebase_dailynotes \
      --credentials-file /tmp/firebase-key.json \
      --database-url https://your-project.firebaseio.com \
      --project-name your-project \
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

# Run job with secret mount
kubectl run firebase-import --rm -i --restart=Never \
  --image=your-eqmd-image \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "firebase-import",
        "image": "your-eqmd-image",
        "command": ["uv", "run", "python", "manage.py", "import_firebase_dailynotes"],
        "args": [
          "--credentials-file", "/tmp/firebase-key.json",
          "--database-url", "https://your-project.firebaseio.com",
          "--project-name", "your-project",
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

### Command Options

- `--credentials-file`: Firebase service account JSON (required)
- `--database-url`: Firebase Realtime Database URL (required)
- `--project-name`: Firebase project name (required)  
- `--base-reference`: Database reference path (default: "dailynotes")
- `--user-email`: User email for import attribution (uses first superuser if not provided)
- `--dry-run`: Preview without importing
- `--limit`: Import only N records (useful for testing)
- `--chunk-size`: Records per Firebase request (default: 100, max: 1000)
- `--start-key`: Firebase key to start from (useful for resuming interrupted imports)

### Large Dataset Support

The command automatically handles datasets larger than Firebase's 256MB payload limit through chunking:

- **Automatic chunking**: Fetches data in configurable chunks (default: 100 records)
- **Progress tracking**: Shows chunk-by-chunk progress with statistics
- **Resume capability**: Can restart from specific Firebase key if interrupted
- **Memory efficient**: Only loads small chunks at a time, suitable for very large datasets

### Security Best Practices

**Credential Handling Priority:**
1. **🥇 Temporary Mounts** - Credentials never persist in container (Options 1)
2. **🥈 Docker Secrets** - Enterprise-grade secret management (Production)
3. **🥉 Copy with Cleanup** - Manual cleanup required (Options 2-3)

**Environment Recommendations:**
- **Development**: Use temporary mount (Option 1)
- **CI/CD Pipelines**: Use Docker/Kubernetes secrets
- **Production**: Always use secrets management systems
- **Quick Testing**: Copy with cleanup (Option 2)

### Import Process

1. **Patient Matching**: Matches patients using Firebase `patient` field against `PatientRecordNumber.record_number`
2. **Timestamp Conversion**: Converts epoch milliseconds timestamps to Django datetime
3. **Content Formatting**: Formats content as structured sections:
   ```
   Evolução importada do Firebase
   
   [Subjective content]
   
   [Objective content]
   
   [Exams List content]
   
   [Assessment/Plan content]
   
   Médico: [username]
   ```
4. **Duplicate Handling**: Allows duplicate imports (creates additional dailynotes)
5. **Error Reporting**: Provides detailed reporting of unmatched patients and errors

### Troubleshooting

**"Payload is too large" Error:**
- Use `--chunk-size` parameter to reduce chunk size (try 50 or 25)
- The command automatically handles large datasets with chunking

**Permission Errors:**
- Use `--user root` in Docker commands to avoid permission issues with uv cache

**Patient Not Found:**
- Ensure patients are already imported using the patient import command
- Check that Firebase `patient` field matches values in `PatientRecordNumber.record_number`

**Interrupted Import:**
- Use the `--start-key` parameter with the key provided in the final report to resume

### Security Notes

- **Always use read-only mounts** and clean up credentials after import
- **Never commit** Firebase credentials to version control
- **Use secrets management** for production environments
- **Rotate credentials** regularly following security best practices