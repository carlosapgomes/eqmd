# Drug Templates App - Complete Guide

**Drug and prescription template management with import capabilities**

## Overview

The drug templates app provides a comprehensive system for managing medication templates and prescription templates within the hospital information system. It supports both user-created templates and imported reference medications from external sources.

### Key Features

- **Drug Templates**: Individual medication templates with separate concentration and pharmaceutical form fields
- **Prescription Templates**: Reusable multi-drug prescription templates
- **Data Import**: Import medications from CSV files (1,000+ Brazilian medications included)
- **Source Tracking**: Distinguish between user-created and imported reference drugs
- **Public/Private Sharing**: Control template visibility across users
- **Backward Compatibility**: Computed presentation field for legacy code integration

### Models

- **DrugTemplate**: Individual medication templates with import tracking
- **PrescriptionTemplate**: Reusable prescription templates containing multiple drugs
- **PrescriptionTemplateItem**: Individual medications within prescription templates

## Drug Template Model

### Core Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | UUID | Primary key (auto-generated) | Yes |
| `name` | CharField(200) | Medication name (e.g., "Dipirona") | Yes |
| `concentration` | CharField(200) | Dosage concentration (e.g., "500 mg", "40 mg/mL") | Yes* |
| `pharmaceutical_form` | CharField(200) | Form type (e.g., "comprimido", "solução injetável") | Yes* |
| `usage_instructions` | TextField | Detailed usage instructions (markdown supported) | Conditional** |

### Sharing & Tracking Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `creator` | ForeignKey | User who created the template | Required |
| `is_public` | BooleanField | Whether other users can see this template | False |
| `usage_count` | PositiveIntegerField | Number of times used in prescriptions | 0 |
| `is_imported` | BooleanField | Whether imported from external source | False |
| `import_source` | CharField(200) | Source of import (e.g., "MERGED_medications.csv") | Null |
| `created_at` | DateTimeField | Creation timestamp | Auto |
| `updated_at` | DateTimeField | Last update timestamp | Auto |

*Required for user-created templates only
**Required for user-created templates, optional for imported medications

### Computed Properties

```python
@property
def presentation(self):
    """Returns combined concentration and form for backward compatibility."""
    # "500 mg comprimido" or "500 mg" or "comprimido" or ""
```

### Custom Manager Methods

```python
# Filter by source type
DrugTemplate.objects.user_created()     # Only user-created templates
DrugTemplate.objects.imported()         # Only imported templates
DrugTemplate.objects.from_source("MERGED_medications.csv")  # From specific source
```

### Model Validation

The `DrugTemplate` model enforces the following validation rules:

1. **Name**: Required, must not be empty after stripping whitespace
2. **Concentration**: Required for user-created templates
3. **Pharmaceutical Form**: Required for user-created templates
4. **Usage Instructions**: Required for user-created templates, optional for imported drugs
5. **Duplicate Prevention**: Forms prevent duplicate names per user

## Prescription Template Model

### PrescriptionTemplate Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | UUID | Primary key (auto-generated) | Yes |
| `name` | CharField(200) | Template name (e.g., "Hipertensão - Esquema Básico") | Yes |
| `creator` | ForeignKey | User who created the template | Yes |
| `is_public` | BooleanField | Whether other users can see this template | False |
| `created_at` | DateTimeField | Creation timestamp | Auto |
| `updated_at` | DateTimeField | Last update timestamp | Auto |

### PrescriptionTemplateItem Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | UUID | Primary key (auto-generated) | Yes |
| `template` | ForeignKey | Parent prescription template | Yes |
| `drug_name` | CharField(200) | Medication name | Yes |
| `presentation` | CharField(300) | Dosage, form, concentration combined | Yes |
| `usage_instructions` | TextField | Instructions for this medication | Yes |
| `quantity` | CharField(100) | Dispensing quantity (e.g., "30 comprimidos") | Yes |
| `order` | PositiveIntegerField | Display order within template | 0 |

## Data Import System

### CSV Import Command

Import medications from CSV files with automatic duplicate detection and validation.

```bash
# Basic import
uv run python manage.py import_medications_csv fixtures/MERGED_medications.csv

# Dry run to preview without saving
uv run python manage.py import_medications_csv fixtures/MERGED_medications.csv --dry-run

# Import with custom source name
uv run python manage.py import_medications_csv fixtures/MERGED_medications.csv \
  --source "Hospital Database"
```

### CSV Format Requirements

The CSV file must contain the following columns (case-sensitive):

| Column | Description | Example |
|--------|-------------|---------|
| `Denominação Comum Brasileira (DCB)` | Brazilian common name | "Dipirona Sódica" |
| `Concentração/Composição` | Concentration/composition | "500 mg" |
| `Forma Farmacêutica` | Pharmaceutical form | "comprimido" |

### Import Behavior

#### Duplicate Detection

The import system checks for duplicates based on **all three fields**:
- Name (case-insensitive)
- Concentration (case-insensitive)
- Pharmaceutical form (case-insensitive)

If a match is found, the record is **skipped** (not updated) and counted in the statistics.

#### Data Normalization

- **Concentration**: Decimal separators normalized (comma → dot), spacing adjusted
- **Pharmaceutical Form**: Converted to lowercase for consistency
- **Empty Fields**: Invalid records with missing required fields are logged as errors

#### Import Statistics

The command provides detailed statistics:

```
Import Statistics:
Total processed: 1070
Successfully imported: 1050
Skipped (duplicates): 15
Errors: 5
```

#### System User

Imported medications are assigned to a "system" user created automatically:
- Username: `system`
- Email: `system@hospital.internal`
- Name: "Sistema Importação"
- No staff privileges

### Import Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview import without saving data | False |
| `--source` | Custom import source description | "CSV Import" |

## Admin Interface

### Drug Template Admin

#### List Display

- Name
- Concentration
- Pharmaceutical Form
- Import Status (with source)
- Creator
- Public/Private
- Created At

#### Filters

- Public/Private
- Imported/User-Created
- Pharmaceutical Form
- Import Source
- Creator
- Created At

#### Search Fields

- Name
- Concentration
- Pharmaceutical Form
- Import Source

#### Read-Only Fields (for Imported Drugs)

When editing imported drugs, the following fields are read-only:
- Name
- Concentration
- Pharmaceutical Form
- Is Imported
- Import Source

#### Bulk Actions

- **Make Public**: Mark selected templates as public
- **Make Private**: Mark selected templates as private
- **Mark as Imported**: Mark user-created as imported (sets source)
- **Mark as User-Created**: Remove import status from imported drugs

### Prescription Template Admin

#### List Display

- Template Name
- Creator
- Public/Private
- Item Count
- Created At

#### Inline Editing

Prescription items are edited inline within the prescription template using a tabular interface:
- Order (for sorting)
- Drug Name
- Presentation
- Usage Instructions
- Quantity

#### Bulk Actions

- **Make Public**: Mark selected templates as public
- **Make Private**: Mark selected templates as private

## Forms and Validation

### DrugTemplateForm

#### Fields

```python
{
    'name': 'Nome do medicamento (ex: Dipirona)',
    'concentration': 'Concentração (ex: 500 mg, 40 mg/mL)',
    'pharmaceutical_form': 'Forma farmacêutica (ex: comprimido, solução injetável)',
    'usage_instructions': 'Instruções detalhadas de uso (markdown)',
    'is_public': 'Se marcado, outros usuários poderão ver este template'
}
```

#### Validation Rules

1. **Name**: Required, not empty, no duplicates per user
2. **Concentration**: Required, not empty, decimal normalization
3. **Pharmaceutical Form**: Required, not empty, converted to lowercase
4. **Usage Instructions**: 
   - Required for user-created drugs
   - Optional for imported drugs
   - Minimum 10 characters for user-created

### PrescriptionTemplateForm

#### Fields

```python
{
    'name': 'Nome do template (ex: Hipertensão - Esquema Básico)',
    'is_public': 'Se marcado, outros usuários poderão ver este template'
}
```

#### Validation Rules

- **Name**: Required, not empty, no duplicates per user

### PrescriptionTemplateItemForm

#### Fields

```python
{
    'drug_name': 'Nome do medicamento',
    'presentation': 'Apresentação (ex: 500mg, comprimido)',
    'usage_instructions': 'Instruções de uso',
    'quantity': 'Quantidade (ex: 30 comprimidos)',
    'order': 'Ordem de exibição'
}
```

#### Validation Rules

1. **Drug Name**: Required, not empty
2. **Presentation**: Required, not empty
3. **Usage Instructions**: Required, not empty, minimum 5 characters
4. **Quantity**: Required, not empty

## Database Schema

### DrugTemplate Indexes

```sql
-- Single field indexes
CREATE INDEX drugtpl_name_idx ON drugtemplates_drugtemplate (name);
CREATE INDEX drugtpl_creator_idx ON drugtemplates_drugtemplate (creator_id);
CREATE INDEX drugtpl_public_idx ON drugtemplates_drugtemplate (is_public);
CREATE INDEX drugtpl_created_idx ON drugtemplates_drugtemplate (created_at);
CREATE INDEX drugtpl_conc_idx ON drugtemplates_drugtemplate (concentration);
CREATE INDEX drugtpl_form_idx ON drugtemplates_drugtemplate (pharmaceutical_form);
CREATE INDEX drugtpl_imported_idx ON drugtemplates_drugtemplate (is_imported);
CREATE INDEX drugtpl_source_idx ON drugtemplates_drugtemplate (import_source);

-- Composite indexes for common queries
CREATE INDEX drugtpl_imp_name_idx ON drugtemplates_drugtemplate (is_imported, name);
CREATE INDEX drugtpl_name_conc_idx ON drugtemplates_drugtemplate (name, concentration);
```

### PrescriptionTemplate Indexes

```sql
CREATE INDEX presc_tmpl_name_idx ON drugtemplates_prescriptiontemplate (name);
CREATE INDEX presc_tmpl_creator_idx ON drugtemplates_prescriptiontemplate (creator_id);
CREATE INDEX presc_tmpl_public_idx ON drugtemplates_prescriptiontemplate (is_public);
CREATE INDEX presc_tmpl_created_idx ON drugtemplates_prescriptiontemplate (created_at);
```

### PrescriptionTemplateItem Indexes

```sql
CREATE INDEX presc_item_tmpl_idx ON drugtemplates_prescriptiontemplateitem (template_id);
CREATE INDEX presc_item_drug_idx ON drugtemplates_prescriptiontemplateitem (drug_name);
CREATE INDEX presc_item_order_idx ON drugtemplates_prescriptiontemplateitem (order);
```

## Usage Examples

### Creating a Drug Template

```python
from apps.drugtemplates.models import DrugTemplate
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='medico')

# Create a new drug template
drug = DrugTemplate.objects.create(
    name='Dipirona',
    concentration='500 mg',
    pharmaceutical_form='comprimido',
    usage_instructions='1 comprimido via oral a cada 6-8 horas '
                      'se necessário para dor. Máximo 4 comprimidos ao dia.',
    creator=user,
    is_public=True
)
```

### Creating a Prescription Template

```python
from apps.drugtemplates.models import PrescriptionTemplate, PrescriptionTemplateItem

# Create prescription template
prescription = PrescriptionTemplate.objects.create(
    name='Hipertensão - Esquema Básico',
    creator=user,
    is_public=True
)

# Add medications to template
PrescriptionTemplateItem.objects.create(
    template=prescription,
    drug_name='Losartana',
    presentation='50 mg comprimido',
    usage_instructions='1 comprimido via oral 1 vez ao dia, pela manhã.',
    quantity='30 comprimidos',
    order=1
)

PrescriptionTemplateItem.objects.create(
    template=prescription,
    drug_name='Hidroclorotiazida',
    presentation='25 mg comprimido',
    usage_instructions='1 comprimido via oral 1 vez ao dia, pela manhã.',
    quantity='30 comprimidos',
    order=2
)
```

### Querying by Source Type

```python
# Get only user-created templates
user_templates = DrugTemplate.objects.user_created()

# Get only imported templates
imported_templates = DrugTemplate.objects.imported()

# Get templates from specific source
csv_imports = DrugTemplate.objects.from_source('MERGED_medications.csv')

# Get public user-created templates
public_templates = DrugTemplate.objects.filter(is_public=True, is_imported=False)
```

### Using the Computed Presentation Property

```python
drug = DrugTemplate.objects.get(name='Dipirona')

# Access computed presentation (backward compatibility)
print(drug.presentation)  # "500 mg comprimido"
```

### Checking Import Statistics

```bash
# Using management command
uv run python manage.py shell -c "
from apps.drugtemplates.models import DrugTemplate
print(f'Total templates: {DrugTemplate.objects.count()}')
print(f'Imported templates: {DrugTemplate.objects.imported().count()}')
print(f'User created templates: {DrugTemplate.objects.user_created().count()}')
print(f'Public templates: {DrugTemplate.objects.filter(is_public=True).count()}')
"
```

## Testing

### Running Tests

```bash
# All drug templates tests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/drugtemplates/tests/ -v

# Specific test files
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest \
  apps/drugtemplates/tests/test_model_refactoring.py -v

DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest \
  apps/drugtemplates/tests/test_medication_import.py -v

DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest \
  apps/drugtemplates/tests/test_source_tracking.py -v
```

### Test Coverage

The app includes comprehensive test coverage for:

1. **Model Refactoring** (`test_model_refactoring.py`)
   - New field validation
   - Computed presentation property
   - Manager methods (user_created, imported, from_source)
   - Backward compatibility

2. **Medication Import** (`test_medication_import.py`)
   - CSV parsing and validation
   - Duplicate detection
   - Data normalization
   - Error handling
   - Dry run mode

3. **Source Tracking** (`test_source_tracking.py`)
   - Import status management
   - Source filtering
   - Admin permissions for imported drugs

4. **Admin Interface** (`test_admin_interface.py`)
   - Bulk actions
   - Read-only field enforcement
   - Filtering and search

## Permissions and Access Control

### Template Visibility

- **Private Templates**: Only visible to the creator
- **Public Templates**: Visible to all authenticated users
- **Imported Templates**: All imported medications are public by default

### Edit Restrictions

- **User-Created Templates**: Full edit access for the creator
- **Imported Templates**: Core fields (name, concentration, form) are read-only
- **Public Templates**: Only the creator can edit their own templates

### Admin Override

Admin users can:
- Edit any template (including imported drugs)
- Change import status (mark user-created as imported or vice versa)
- Modify public/private settings

## Migrations

The app includes the following key migrations:

1. **0001_initial.py**: Initial model creation with combined `presentation` field
2. **0002_refactor_drugtemplate_fields.py**: Split presentation into separate fields
3. **0003_populate_new_fields.py**: Data migration to populate new fields from existing data
4. **0004_remove_presentation_field_completely.py**: Remove legacy presentation field
5. **0005_increase_field_lengths.py**: Increase concentration and form field lengths to 200

### Running Migrations

```bash
# Apply all pending migrations
uv run python manage.py migrate drugtemplates

# Check migration status
uv run python manage.py showmigrations drugtemplates
```

## URL Structure

```
/drugtemplates/                    # List all drug templates
/drugtemplates/create/             # Create new drug template
/drugtemplates/<uuid>/             # View drug template detail
/drugtemplates/<uuid>/update/      # Update drug template
/drugtemplates/<uuid>/delete/      # Delete drug template

/drugtemplates/prescriptions/               # List prescription templates
/drugtemplates/prescriptions/create/        # Create prescription template
/drugtemplates/prescriptions/<uuid>/        # View prescription template
/drugtemplates/prescriptions/<uuid>/update/ # Update prescription template
/drugtemplates/prescriptions/<uuid>/delete/ # Delete prescription template
```

## Best Practices

### When to Use Drug Templates

- **Individual Medications**: Use `DrugTemplate` for single medications
- **Reusable Prescriptions**: Use `PrescriptionTemplate` for multi-drug regimens
- **Common Medications**: Import from CSV to populate reference database
- **Custom Formulations**: Create user templates for hospital-specific formulations

### Data Quality

- **Normalization**: Import command automatically normalizes concentrations and forms
- **Consistency**: Use standard pharmaceutical form names (e.g., "comprimido" not "cps")
- **Validation**: Forms enforce required fields and prevent duplicates
- **Documentation**: Provide clear usage instructions in markdown format

### Performance

- **Indexes**: All frequently queried fields are indexed
- **Composite Indexes**: Optimized for common query patterns
- **Query Optimization**: Use manager methods for efficient filtering

## Troubleshooting

### Import Issues

**Problem**: Duplicate medications not being detected
- **Solution**: Ensure name, concentration, and form match exactly (case-insensitive)

**Problem**: CSV import fails with encoding errors
- **Solution**: Ensure CSV file is UTF-8 encoded

**Problem**: Imported medications not appearing in admin
- **Solution**: Check that system user exists and has proper permissions

### Form Validation Errors

**Problem**: "Instruções de uso são obrigatórias" for imported drugs
- **Solution**: The drug is marked as `is_imported=False` but should be `True`

**Problem**: Duplicate name error for user-created templates
- **Solution**: Each user can only have one template with the same name

### Backward Compatibility

**Problem**: Code expecting `presentation` field fails
- **Solution**: Use the computed `presentation` property instead

## References

- **OpenSpec Proposal**: `@openspec/changes/refactor-drugtemplate-model/proposal.md`
- **Tasks**: `@openspec/changes/refactor-drugtemplate-model/tasks.md`
- **Spec**: `@openspec/changes/refactor-drugtemplate-model/specs/drugtemplates/spec.md`
- **Sample Data**: `fixtures/MERGED_medications.csv` (1,070+ Brazilian medications)
