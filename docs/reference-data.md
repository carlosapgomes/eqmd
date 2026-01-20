# Reference Data Management Guide

This guide explains how to import and manage reference data (ICD-10 diagnosis codes and medical procedures) in the EquipeMed application.

## Overview

EquipeMed uses reference data for standardized medical coding and searching:

- **ICD-10 Codes** (Códigos CID): International Classification of Diseases for diagnoses
- **Medical Procedures** (Procedimentos Médicos): Standardized procedure codes for hospital operations

**Important Distinction:** Reference data is **production data** used across all hospitals, while sample data is for development/testing only.

## Quick Start

```bash
# Import ICD-10 codes (14,242 codes)
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv

# Import medical procedures
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv

# Preview imports without making changes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --dry-run
```

---

## ICD-10 Codes (Códigos CID)

ICD-10 (International Statistical Classification of Diseases and Related Health Problems) is used for diagnosis coding and searching.

### Data File

- **Location**: `fixtures/cid.csv`
- **Total Codes**: 14,242
- **Code Range**: A00 - Z999
- **File Size**: 856 KB
- **Format**: CSV with Portuguese headers

#### CSV Format

```csv
codigo,descricao
A00,Cólera
A000,"Cólera devida a Vibrio Cholerae 01, biótipo Cholerae"
A001,"Cólera devida a Vibrio Cholerae 01, biótipo El Tor"
A009,Cólera não especificada
```

**Columns:**
- `codigo`: ICD-10 code (e.g., A00, B001)
- `descricao`: Description in Portuguese

### Import Command

```bash
# Basic import
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv

# Preview without importing
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --dry-run

# Verbose output
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --verbose

# Update existing codes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --update

# Deactivate codes not in import file
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --deactivate-missing

# Custom batch size (for memory constraints)
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --batch-size=500
```

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--file` | Path to CSV or JSON file (required) | - |
| `--format` | File format: csv or json (auto-detected) | Auto-detect |
| `--batch-size` | Records per batch | 1000 |
| `--dry-run` | Validate without saving | False |
| `--update` | Update existing codes instead of skipping | False |
| `--deactivate-missing` | Mark codes as inactive if not in import file | False |
| `--verbose` | Show detailed progress | False |

### Model Structure

```python
class Icd10Code(models.Model):
    id = UUIDField(primary_key=True)
    code = CharField(max_length=20, unique=True)  # e.g., A00, B001
    description = TextField()  # Full description
    is_active = BooleanField(default=True)  # Available for use
    search_vector = SearchVectorField()  # Full-text search
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Features

- **Full-Text Search**: PostgreSQL tsvector for Portuguese text search
- **Code Auto-Uppercase**: Codes automatically converted to uppercase
- **Active/Inactive**: Soft delete with `is_active` flag
- **Search API**: `/api/icd10/search/?q=query` endpoint

### Verification

```bash
# Check total count
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
print(f'Total codes: {Icd10Code.objects.count()}')
"

# Check active codes
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
print(f'Active codes: {Icd10Code.objects.filter(is_active=True).count()}')
"

# Check search vectors
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
print(f'Vectored: {Icd10Code.objects.filter(search_vector__isnull=False).count()}')
"

# Test search functionality
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
results = Icd10Code.simple_search('cólera')
print(f'Found {results.count()} codes')
for code in results:
    print(f'  {code.code}: {code.description}')
"
```

### Common Use Cases

#### Initial Setup (New Installation)

```bash
# Run migrations first
uv run python manage.py migrate

# Import all ICD-10 codes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --verbose
```

#### Update Reference Data

```bash
# Download updated CID codes (from official sources)
# Replace fixtures/cid.csv with new file

# Preview changes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --dry-run --verbose

# Apply updates (will update descriptions, keep existing codes)
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --update
```

#### Clean Up Deprecated Codes

```bash
# Mark codes not in new file as inactive
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --deactivate-missing
```

#### Troubleshooting Memory Issues

```bash
# Use smaller batch sizes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --batch-size=100 --verbose
```

---

## Medical Procedures (Procedimentos Médicos)

Medical procedures are standardized codes for hospital operations, procedures, and treatments.

### Data File

- **Location**: `fixtures/procedimentos.csv`
- **Format**: CSV with Portuguese headers
- **Code Format**: Variable length procedure codes

#### CSV Format

```csv
codigo,descricao
0301010012,Consulta em ambulatório de especialidade
0301010020,Consulta em pronto socorro
0301010039,Consulta no domicílio
```

**Columns:**
- `codigo`: Procedure code (e.g., 0301010012)
- `descricao`: Description in Portuguese

### Import Command

```bash
# Basic import
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv

# Preview without importing
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv --dry-run

# Verbose output
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv --verbose

# Update existing procedures
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv --update

# Deactivate procedures not in import file
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv --deactivate-missing

# Custom batch size
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv --batch-size=500
```

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--file` | Path to CSV or JSON file (required) | - |
| `--format` | File format: csv or json (auto-detected) | Auto-detect |
| `--batch-size` | Records per batch | 1000 |
| `--dry-run` | Validate without saving | False |
| `--update` | Update existing procedures instead of skipping | False |
| `--deactivate-missing` | Mark procedures as inactive if not in import file | False |
| `--verbose` | Show detailed progress | False |

### Model Structure

```python
class MedicalProcedure(models.Model):
    id = UUIDField(primary_key=True)
    code = CharField(max_length=20, unique=True)  # Procedure code
    description = TextField()  # Full description
    is_active = BooleanField(default=True)  # Available for use
    search_vector = SearchVectorField()  # Full-text search
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Features

- **Full-Text Search**: PostgreSQL tsvector for Portuguese text search
- **Active/Inactive**: Soft delete with `is_active` flag
- **Search API**: `/api/procedures/search/?q=query` endpoint

### Verification

```bash
# Check total count
uv run python manage.py shell -c "
from apps.core.models import MedicalProcedure
print(f'Total procedures: {MedicalProcedure.objects.count()}')
"

# Check active procedures
uv run python manage.py shell -c "
from apps.core.models import MedicalProcedure
print(f'Active procedures: {MedicalProcedure.objects.filter(is_active=True).count()}')
"

# Test search functionality
uv run python manage.py shell -c "
from apps.core.models import MedicalProcedure
results = MedicalProcedure.simple_search('consulta')
print(f'Found {results.count()} procedures')
for proc in results[:5]:
    print(f'  {proc.code}: {proc.description}')
"
```

---

## Advanced Features

### JSON Format Support

Both import commands support JSON format in addition to CSV:

```json
{
  "codes": [
    {
      "code": "A00",
      "description": "Cólera",
      "is_active": true
    },
    {
      "code": "A01",
      "description": "Febres tifóide e paratifóide",
      "is_active": true
    }
  ]
}
```

```bash
# Import JSON file
uv run python manage.py import_icd10_codes --file=fixtures/cid.json --format=json
```

### Search API Endpoints

Both reference data types provide search API endpoints:

#### ICD-10 Search

```bash
# Search for ICD-10 codes
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/icd10/search/?q=cólera"

# Requires at least 2 characters
# Returns JSON with code, description, and short_description fields
```

#### Medical Procedure Search

```bash
# Search for procedures
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/procedures/search/?q=consulta"
```

### Full-Text Search

Both models support PostgreSQL full-text search:

```python
from apps.core.models import Icd10Code, MedicalProcedure

# Simple search (case-insensitive, works on SQLite too)
results = Icd10Code.simple_search('diabetes')

# Full-text search (PostgreSQL only, more accurate)
results = Icd10Code.search('diabetes mellitus')
```

Search operators supported:
- `diabetes mellitus`: Both terms required (AND)
- `diabetes | hipertensão`: Either term (OR)
- `diabetes & !gestacional`: Diabetes but not gestational (NOT)
- `medicaç*`: Prefix matching (medicação, medicamentos, etc.)

### Batch Processing Performance

For large datasets, adjust batch size based on available memory:

| Dataset Size | Recommended Batch Size | Memory Usage | Processing Time |
|--------------|----------------------|--------------|-----------------|
| < 1,000 | 1000 (default) | Low | < 1 minute |
| 1,000 - 10,000 | 500 | Medium | 1-5 minutes |
| 10,000 - 20,000 | 250 | High | 5-10 minutes |
| > 20,000 | 100 | Very High | 10+ minutes |

---

## Docker Compose Usage

### Import in Production

```bash
# Import ICD-10 codes
docker compose run eqmd python manage.py import_icd10_codes --file=fixtures/cid.csv

# Import medical procedures
docker compose run eqmd python manage.py import_procedures --file=fixtures/procedimentos.csv
```

### Background Processing

```bash
# Run import in background with logging
docker compose run -d eqmd bash -c "
  python manage.py import_icd10_codes --file=fixtures/cid.csv --verbose 2>&1 |
  tee /app/logs/icd10-import-$(date +%Y%m%d-%H%M%S).log
"

# Monitor logs
docker compose logs -f
```

---

## Maintenance and Updates

### Regular Updates Strategy

1. **Subscribe to Updates**: Monitor official ICD-10 and procedure code updates
2. **Test in Development**: Always test imports with `--dry-run` first
3. **Schedule Updates**: Plan for low-traffic periods
4. **Backup Database**: Always backup before major updates

### Update Workflow

```bash
# 1. Backup database
docker compose exec db pg_dump -U postgres eqmd > backup-$(date +%Y%m%d).sql

# 2. Preview changes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --dry-run --verbose

# 3. Apply updates
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --update --verbose

# 4. Verify import
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
print(f'Total: {Icd10Code.objects.count()}')
print(f'Active: {Icd10Code.objects.filter(is_active=True).count()}')
print(f'Vectored: {Icd10Code.objects.filter(search_vector__isnull=False).count()}')
"

# 5. Run tests
uv run pytest apps/core/tests/test_icd10_codes.py
```

---

## Troubleshooting

### Common Issues

#### Import Fails with "File Not Found"

```bash
# Use absolute path or check relative path
ls -la fixtures/cid.csv

# Use absolute path
uv run python manage.py import_icd10_codes --file=/path/to/fixtures/cid.csv
```

#### Memory Error During Import

```bash
# Reduce batch size
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --batch-size=100 --verbose
```

#### Search Not Working After Import

```bash
# Check search vectors
uv run python manage.py shell -c "
from apps.core.models import Icd10Code
missing = Icd10Code.objects.filter(search_vector__isnull=False).count()
print(f'Vectored: {missing}')
"

# Re-run import (it updates search vectors automatically)
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --update
```

#### Duplicate Code Errors

```bash
# Check for duplicates in CSV
cut -d',' -f1 fixtures/cid.csv | sort | uniq -d

# Use --update flag to handle existing codes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --update
```

#### CSV Format Issues

```bash
# Check CSV format
head -5 fixtures/cid.csv

# Expected format:
# codigo,descricao
# A00,Cólera
# A001,Febre tifóide

# If headers are in English (code,description), the command handles both
```

### Performance Issues

#### Slow Search Performance

```bash
# Check if search indexes exist
docker compose exec db psql -U postgres -d eqmd -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename LIKE '%icd10%';
"

# Re-create indexes if needed
uv run python manage.py migrate core 0003_icd10code --fake
```

#### Database Lock During Import

```bash
# Use smaller batch sizes to reduce lock duration
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --batch-size=50
```

---

## Testing

### Unit Tests

```bash
# Run ICD-10 tests
uv run pytest apps/core/tests/test_icd10_codes.py -v

# Run specific test
uv run pytest apps/core/tests/test_icd10_codes.py::Icd10CodeModelTest -v
```

### Integration Tests

```bash
# Test import command
uv run pytest apps/core/tests/test_icd10_codes.py::ImportIcd10CodesCommandTest -v

# Test API endpoints
uv run pytest apps/core/tests/test_icd10_codes.py::Icd10CodesAPITest -v
```

### Manual Testing

```python
# In Django shell
from apps.core.models import Icd10Code, MedicalProcedure

# Create test code
code = Icd10Code.objects.create(code='TEST01', description='Test code', is_active=True)

# Test search
results = Icd10Code.simple_search('test')
print(f'Found: {results.count()} codes')

# Test full-text search (PostgreSQL only)
results = Icd10Code.search('test')
print(f'Found: {results.count()} codes')

# Clean up
code.delete()
```

---

## Data Sources and Updates

### ICD-10 Codes

**Official Source:** World Health Organization (WHO)
- **URL**: https://icd.who.int/
- **Brazilian Version**: DATASUS (http://datasus.saude.gov.br/cid-10)

**Update Frequency:** As needed (WHO updates periodically)

### Medical Procedures

**Official Source:** Brazilian Health Ministry
- **URL**: http://www.saude.gov.br/sigtap
- **Table**: SIGTAP (Sistema de Gerenciamento da Tabela de Procedimentos)

**Update Frequency:** Annually (usually January)

---

## Best Practices

### Before Importing

1. **Backup Database**: Always backup before production imports
2. **Validate File**: Check CSV format and encoding
3. **Preview Import**: Use `--dry-run` to preview changes
4. **Schedule Downtime**: Plan for potential performance impact
5. **Test in Development**: Verify import works in non-production environment

### During Import

1. **Monitor Logs**: Watch for errors or warnings
2. **Check Progress**: Use `--verbose` for detailed output
3. **Verify Resources**: Monitor memory and CPU usage
4. **Allow Time**: Large imports may take several minutes

### After Importing

1. **Verify Counts**: Check expected vs actual record counts
2. **Test Search**: Verify search functionality works
3. **Run Tests**: Execute test suite to catch issues
4. **Monitor Performance**: Check application performance
5. **Document Changes**: Record import details and any issues

---

## Related Documentation

- [Sample Data Population](sample-data-population.md) - Test data for development
- [Full-Text Search](fts-vector-indexation.md) - Search vector management
- [Database Reset](database-reset.md) - Database operations and migration
- [API Reference](apps/core/docs/api-reference.md) - Core API endpoints

---

## Summary Checklist

### Initial Setup

- [ ] Run migrations: `uv run python manage.py migrate`
- [ ] Import ICD-10 codes: `uv run python manage.py import_icd10_codes --file=fixtures/cid.csv`
- [ ] Import medical procedures: `uv run python manage.py import_procedures --file=fixtures/procedimentos.csv`
- [ ] Verify imports: Check record counts and search functionality
- [ ] Run tests: `uv run pytest apps/core/tests/`

### Regular Maintenance

- [ ] Subscribe to update notifications from official sources
- [ ] Test new reference data files in development
- [ ] Backup database before updates
- [ ] Use `--dry-run` to preview changes
- [ ] Apply updates with `--update` flag
- [ ] Verify search vectors are populated
- [ ] Run test suite after updates

---

**Remember**: Reference data is production data used across all hospitals. Always backup before importing and test in development first!
