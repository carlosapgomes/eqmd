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
docker compose run eqmd python manage.py populate_search_vectors --dry-run

# Full indexation for production system
docker compose run eqmd python manage.py populate_search_vectors

# Large dataset with smaller batches (more memory efficient)
docker compose run eqmd python manage.py populate_search_vectors --batch-size 100
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
          command:
            ["uv", "run", "python", "manage.py", "populate_search_vectors"]
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
  schedule: "0 2 * * 0" # Weekly at 2 AM Sunday
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: maintenance
              image: your-eqmd-image
              command:
                ["uv", "run", "python", "manage.py", "populate_search_vectors"]
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

| Dataset Size    | Recommended Batch Size | Memory Usage | Processing Time |
| --------------- | ---------------------- | ------------ | --------------- |
| < 1,000 notes   | 1000 (default)         | Low          | < 1 minute      |
| 1,000 - 10,000  | 500                    | Medium       | 5-15 minutes    |
| 10,000 - 50,000 | 100-250                | High         | 30-60 minutes   |
| > 50,000        | 50-100                 | Very High    | 1+ hours        |

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

## Advanced Search Capabilities

### Search Syntax and Operators

EquipeMed supports PostgreSQL's advanced full-text search operators for precise medical research:

#### Automatic Optimization

The system automatically enhances simple queries for better performance:

- **Single words**: `diabetes` → `diabetes*` (finds diabetes, diabética, diabético)
- **Multiple words**: `diabetes dor` → `diabetes & dor` (both terms must be present)

#### Manual Operators

Users can specify advanced operators for precise control:

##### Exact Phrases

```
"diabetes mellitus"        # Finds exact phrase
"insuficiência cardíaca"   # Exact cardiac insufficiency phrase
"dor abdominal aguda"      # Exact phrase for acute abdominal pain
```

##### Boolean Logic

```
diabetes & hipertensão     # Both terms required (AND)
diabetes | hipertensão     # Either term acceptable (OR)
diabetes & !gestacional    # Diabetes but not gestational (NOT)
```

##### Prefix Matching  

```
medicaç*                   # Finds medicação, medicamentos, medicamentosa
hiperten*                  # Finds hipertensão, hipertensivo, hipertensiva
cardio*                    # Finds cardiologia, cardiomegalia, cardiovascular
```

##### Complex Combinations

```
diabetes & (medicaç* | insulin*)           # Diabetes with any medication
"dor torácica" & !(muscular | costal)      # Chest pain excluding muscular/costal
cardio* & (insuficien* | arritmia)         # Cardiac conditions with specific terms
```

### Search Examples by Medical Specialty

#### Cardiology

```
"insuficiência cardíaca"                    # Exact heart failure phrase
cardio* & (sopro | arritmia | fibrilação)   # Cardiac findings
"dor torácica" & !muscular                  # Non-muscular chest pain
```

#### Endocrinology

```
diabetes & (tipo1 | tipo2)                 # Diabetes classification
glicemi* & (jejum | pós-prandial)          # Glycemic measurements
"cetoacidose diabética"                     # Exact DKA phrase
```

#### Gastroenterology

```
"dor abdominal" & (aguda | crônica)        # Abdominal pain classification
gastro* & (sangramento | hemorragia)       # GI bleeding terms
"síndrome do intestino irritável"          # Exact IBS phrase
```

#### Pneumology

```
"dispneia aos esforços"                    # Exact dyspnea phrase
pneumo* & (derrame | consolidação)         # Lung findings
"insuficiência respiratória" & !crônica    # Acute respiratory failure
```

### Performance Tips

#### Query Optimization Guidelines

1. **Use specific terms**: `"fibrilação atrial"` vs `fibrilação`
2. **Combine operators**: `diabetes & medicaç*` vs `diabetes medicação`
3. **Exclude common terms**: `dor & !leve` vs `dor`
4. **Use prefixes for variants**: `hiperten*` vs multiple OR terms

#### Search Strategy Recommendations

**For Literature Reviews:**

```
# Broad initial search
diabetes*

# Refined search
diabetes & (complicaç* | nefropatia | retinopatia)

# Very specific
"diabetes mellitus tipo 2" & medicaç*
```

**For Case Finding:**

```
# Symptom-based
"dor torácica" & (aguda | súbita)

# Diagnosis-based  
"infarto agudo do miocárdio"

# Treatment-based
"angioplastia" & (primária | emergência)
```

### User Interface Integration

#### Form Help Text

The search form automatically shows available operators:

> "Digite pelo menos 3 caracteres. Use: "frase exata", diabetes & hipertensão, medicaç* para busca avançada"

#### Search Tips for Users

**Beginner Level:**

- Type medical terms normally: `diabetes hipertensão`
- Use quotes for exact phrases: `"dor abdominal"`

**Advanced Level:**

- Combine with AND: `diabetes & nefropatia`
- Use wildcards: `cardio* medicaç*`
- Exclude terms: `pneumonia & !viral`

### API and Integration

#### Programmatic Search

```python
from apps.research.utils import perform_fulltext_search_queryset

# Simple search
results = perform_fulltext_search_queryset("diabetes", max_patients=100)

# Advanced search
results = perform_fulltext_search_queryset(
    'diabetes & medicaç* & !"tipo 1"', 
    max_patients=500
)

# Medical specialty search
results = perform_fulltext_search_queryset(
    '"insuficiência cardíaca" & (betabloqueador* | inibidor*)',
    max_patients=200
)
```

#### Excel Export Enhancement

Search results exported to Excel maintain:

- Original search query in filename
- Relevance scores for ranking
- Match counts per patient
- Optimized column widths for medical data

### Troubleshooting Search Queries

#### Common Query Errors

**Syntax Error: Invalid tsquery**

```
# Problem: Unmatched quotes
"diabetes mellitus

# Solution: Close quotes
"diabetes mellitus"
```

**No Results Found**

```
# Problem: Too restrictive
diabetes & hipertensão & nefropatia & retinopatia

# Solution: Use OR for alternatives  
diabetes & (nefropatia | retinopatia)
```

**Too Many Results**

```
# Problem: Too broad
dor

# Solution: Add specificity
"dor torácica" & aguda
```

#### Performance Optimization

**Query Performance Guidelines:**

- Shorter queries execute faster
- Exact phrases (`"termo"`) are faster than wildcards (`termo*`)
- Boolean operators add minimal overhead
- Complex nested queries may be slower

**Best Practices:**

1. Start with broad terms, then refine
2. Use exact phrases for established medical terms
3. Combine boolean operators strategically
4. Monitor search performance in production

The enhanced full-text search system provides powerful tools for medical research while maintaining simplicity for everyday use.
