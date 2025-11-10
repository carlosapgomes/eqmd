# Full-Text Search Vector Indexation

## Initial Vector Population for Deployed Systems

Populate search vectors for existing daily notes to enable full-text search functionality. This command processes all existing daily notes that don't have search vectors and creates PostgreSQL tsvector indexes for Portuguese text search.

### Prerequisites

1. PostgreSQL database with full-text search extensions enabled
2. Existing daily notes in the system
3. Admin access to the deployed system

### Basic Usage

```bash
# Dry run to preview indexation (recommended first step)
uv run python manage.py populate_search_vectors --dry-run

# Full indexation with default batch size
uv run python manage.py populate_search_vectors

# Large dataset with custom batch size
uv run python manage.py populate_search_vectors --batch-size 500
```

### Docker Compose Usage (Production)

#### Standard Deployment

```bash
# Dry run to check how many records need indexation
docker-compose exec web uv run python manage.py populate_search_vectors --dry-run

# Full indexation for production system
docker-compose exec web uv run python manage.py populate_search_vectors

# Large dataset with smaller batches (more memory efficient)
docker-compose exec web uv run python manage.py populate_search_vectors --batch-size 100
```

#### Background Processing (Recommended for Large Datasets)

```bash
# Run indexation in background with logging
docker-compose exec -d web bash -c "
  uv run python manage.py populate_search_vectors --batch-size 500 2>&1 | 
  tee /app/logs/vector-indexation-$(date +%Y%m%d-%H%M%S).log
"

# Monitor progress
docker-compose exec web tail -f /app/logs/vector-indexation-*.log

# Check if process is still running
docker-compose exec web ps aux | grep populate_search_vectors
```

#### One-time Service Run

```bash
# Run as one-time service (auto-cleanup)
docker-compose run --rm web uv run python manage.py populate_search_vectors --batch-size 1000

# With resource limits for large datasets
docker-compose run --rm --memory=2g --cpus=1.0 web \
  uv run python manage.py populate_search_vectors --batch-size 500
```

### Standalone Docker Usage

#### Basic Container Run

```bash
# Run indexation in existing container
docker exec your-eqmd-container \
  uv run python manage.py populate_search_vectors

# Run with custom batch size
docker exec your-eqmd-container \
  uv run python manage.py populate_search_vectors --batch-size 250
```

#### Dedicated Indexation Container

```bash
# Run as dedicated container with volume mounts
docker run --rm -it \
  -v /path/to/db:/app/db \
  --network your-network \
  your-eqmd-image \
  uv run python manage.py populate_search_vectors --batch-size 1000

# With memory limits for large datasets
docker run --rm -it \
  --memory=2g --cpus=1.0 \
  -v /path/to/db:/app/db \
  --network your-network \
  your-eqmd-image \
  uv run python manage.py populate_search_vectors --batch-size 500
```

### Kubernetes Usage

#### Job-based Indexation

```yaml
# Create indexation-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: fts-vector-indexation
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: indexation
        image: your-eqmd-image
        command: ["uv", "run", "python", "manage.py", "populate_search_vectors"]
        args: ["--batch-size", "1000"]
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: eqmd-secrets
              key: database-url
```

```bash
# Apply and monitor job
kubectl apply -f indexation-job.yaml
kubectl logs -f job/fts-vector-indexation

# Clean up after completion
kubectl delete job fts-vector-indexation
```

#### CronJob for Maintenance

```yaml
# Create maintenance-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: fts-vector-maintenance
spec:
  schedule: "0 2 * * 0"  # Weekly at 2 AM Sunday
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: maintenance
            image: your-eqmd-image
            command: ["uv", "run", "python", "manage.py", "populate_search_vectors"]
            args: ["--batch-size", "500"]
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
```

### Command Options

- `--batch-size`: Number of records to process in each batch (default: 1000)
- `--dry-run`: Preview without making changes
- `--help`: Show all available options

### Performance Considerations

#### Batch Size Guidelines

| Dataset Size | Recommended Batch Size | Memory Usage | Processing Time |
|-------------|----------------------|--------------|----------------|
| < 1,000 notes | 1000 (default) | Low | < 1 minute |
| 1,000 - 10,000 | 500 | Medium | 5-15 minutes |
| 10,000 - 50,000 | 100-250 | High | 30-60 minutes |
| > 50,000 | 50-100 | Very High | 1+ hours |

#### Resource Requirements

**Minimum Requirements:**
- RAM: 512MB available
- CPU: 1 core
- Disk: Minimal additional space

**Recommended for Large Datasets:**
- RAM: 1-2GB available
- CPU: 2+ cores
- Disk: 10-20% additional space for indexes

### Monitoring and Troubleshooting

#### Progress Monitoring

```bash
# Check indexation progress
docker-compose exec web uv run python manage.py shell -c "
from apps.dailynotes.models import DailyNote
total = DailyNote.objects.count()
indexed = DailyNote.objects.filter(search_vector__isnull=False).count()
print(f'Progress: {indexed}/{total} ({(indexed/total)*100:.1f}%)')
"

# Monitor database performance during indexation
docker-compose exec db psql -U postgres -d eqmd -c "
SELECT 
  query,
  calls,
  total_time,
  mean_time
FROM pg_stat_statements 
WHERE query LIKE '%search_vector%'
ORDER BY total_time DESC;
"
```

#### Common Issues

**"Out of Memory" Errors:**
```bash
# Reduce batch size
docker-compose exec web uv run python manage.py populate_search_vectors --batch-size 50

# Or add memory limits
docker-compose run --rm --memory=4g web \
  uv run python manage.py populate_search_vectors --batch-size 100
```

**"Database Connection Timeout":**
```bash
# Process in smaller batches with delays
docker-compose exec web bash -c "
  for i in {1..10}; do
    uv run python manage.py populate_search_vectors --batch-size 100
    sleep 30
  done
"
```

**"Permission Denied" (Docker):**
```bash
# Run with proper user permissions
docker-compose exec --user root web \
  uv run python manage.py populate_search_vectors
```

### Production Deployment Checklist

#### Pre-Indexation

- [ ] **Backup database** before starting indexation
- [ ] **Check available disk space** (ensure 20% free space)
- [ ] **Verify PostgreSQL extensions** are installed
- [ ] **Test with dry-run** to estimate processing time
- [ ] **Schedule maintenance window** for large datasets

#### During Indexation

- [ ] **Monitor system resources** (CPU, memory, disk I/O)
- [ ] **Watch database performance** metrics
- [ ] **Keep logs** of the indexation process
- [ ] **Avoid concurrent heavy operations**

#### Post-Indexation

- [ ] **Verify search functionality** works correctly
- [ ] **Check index health** and performance
- [ ] **Update monitoring** to include search metrics
- [ ] **Document completion** and any issues encountered

### Automated Maintenance

#### Weekly Maintenance Script

```bash
#!/bin/bash
# weekly-fts-maintenance.sh

LOG_DIR="/var/log/eqmd"
LOG_FILE="$LOG_DIR/fts-maintenance-$(date +%Y%m%d).log"

echo "Starting FTS vector maintenance at $(date)" >> "$LOG_FILE"

# Run indexation for any missing vectors
docker-compose exec -T web uv run python manage.py populate_search_vectors \
  --batch-size 500 >> "$LOG_FILE" 2>&1

echo "FTS maintenance completed at $(date)" >> "$LOG_FILE"

# Rotate logs older than 30 days
find "$LOG_DIR" -name "fts-maintenance-*.log" -mtime +30 -delete
```

#### Add to Crontab

```bash
# Add to crontab (runs weekly on Sunday at 2 AM)
0 2 * * 0 /path/to/weekly-fts-maintenance.sh

# Or add to docker-compose.yml as a service
services:
  fts-maintenance:
    image: your-eqmd-image
    profiles: ["maintenance"]
    command: >
      bash -c "
        while true; do
          sleep 604800  # 1 week
          uv run python manage.py populate_search_vectors --batch-size 500
        done
      "
    depends_on:
      - db
```

### Security Considerations

- **Database Access**: Ensure indexation runs with appropriate database permissions
- **Resource Limits**: Use container resource limits to prevent system overload
- **Backup Strategy**: Always backup before running on production data
- **Monitoring**: Set up alerts for long-running indexation processes

### Verification

#### Test Search Functionality

```bash
# Verify vectors were created
docker-compose exec web uv run python manage.py shell -c "
from apps.dailynotes.models import DailyNote
from django.contrib.postgres.search import SearchQuery

# Check vector count
total = DailyNote.objects.count()
vectored = DailyNote.objects.filter(search_vector__isnull=False).count()
print(f'Vectored: {vectored}/{total}')

# Test search
results = DailyNote.objects.filter(
    search_vector=SearchQuery('exame', config='portuguese')
).count()
print(f'Search test results: {results}')
"

# Check database indexes
docker-compose exec db psql -U postgres -d eqmd -c "
SELECT indexname, tablename 
FROM pg_indexes 
WHERE indexname LIKE '%search%';
"
```

The full-text search system is now ready for production use with properly indexed search vectors!