# Full Text Search Implementation Plan

## Overview

Implementation of PostgreSQL full text search for DailyNotes clinical research functionality.

**✅ USER PREFERENCES APPLIED:**

- **Boolean field**: Use `is_researcher` boolean field instead of Django groups
- **New menu section**: Add "Pesquisa Clínica" under new section visible only to researchers
- **Initials format**: First letter of each word (e.g., "João da Silva Santos" → "J.D.S.S.")
- **Age calculation**: Age at the most recent matching dailynote date (not last overall note)

## Architecture Summary

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   DailyNote     │────▶│   SearchVector   │────▶│  Research App   │
│   + tsvector    │     │   (GIN Index)    │     │   + Views       │
│   + signals     │     │   + Portuguese   │     │   + Templates   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Step-by-Step Implementation

### Phase 0: User Model Extension (NEW)

#### 0.1 Add `is_researcher` Field to User Model

**File**: `apps/accounts/models.py`

- Add `is_researcher = models.BooleanField(default=False, verbose_name="Pesquisador Clínico")`
- Update help text for clinical research access

#### 0.2 Create Migration for User Model

**File**: `apps/accounts/migrations/XXXX_add_is_researcher.py`

- Add `is_researcher` boolean field
- Default to False for existing users

#### 0.3 Update User Admin Interface

**File**: `apps/accounts/admin.py`

- Add `is_researcher` to fieldsets in user admin
- Allow superusers to grant/revoke researcher access

### Phase 1: Database Schema and Search Infrastructure

#### 1.1 Update DailyNote Model

**File**: `apps/dailynotes/models.py`

- Add `search_vector = SearchVectorField(null=True, blank=True)`
- Add GIN index for search_vector field in Meta class
- Configure for Portuguese language search

#### 1.2 Create Migration for DailyNote Search Vector

**File**: `apps/dailynotes/migrations/XXXX_add_search_vector.py`

- Add search_vector field
- Create GIN index
- Populate initial search vectors (via data migration)

#### 1.3 Create Management Command for Search Vector Population

**File**: `apps/dailynotes/management/commands/populate_search_vectors.py`

- Command to populate existing DailyNote records with search vectors
- Support for batch processing (160k records)
- Progress reporting
- Portuguese language configuration

#### 1.4 Create Signal Handler for Ongoing Updates

**File**: `apps/dailynotes/signals.py`

- post_save signal to update search_vector when DailyNote.content changes
- Use SearchVector with Portuguese configuration

### Phase 2: Research App Creation

#### 2.1 Create Research App Structure

```
apps/research/
├── __init__.py
├── apps.py
├── models.py          # Empty for now
├── views.py          # Search view with patient grouping
├── urls.py           # URL patterns
├── forms.py          # Search form
├── utils.py          # Helper functions for search (UPDATED)
├── permissions.py    # is_researcher checks (UPDATED)
└── templates/research/
    ├── search.html   # Main search interface
    └── access_denied.html  # Access denied page
```

#### 2.2 Create Researcher Permission System (UPDATED)

**File**: `apps/research/permissions.py`

- Function to check if `user.is_researcher` is True
- Integration with existing permission system

#### 2.3 ~~Create Django Group Management Command~~ (REMOVED)

- Not needed - using boolean field instead

### Phase 3: Search Implementation

#### 3.1 Search Utility Functions (UPDATED)

**File**: `apps/research/utils.py`

- `get_patient_initials(full_name)` - Extract ALL word initials (J.D.S.S.)
- `calculate_age_at_most_recent_match()` - Age at most recent matching note
- `perform_fulltext_search(query_text)` - Core search function with patient grouping

#### 3.2 Search Form

**File**: `apps/research/forms.py`

- Simple form with search query field
- Basic validation

#### 3.3 Search View (UPDATED)

**File**: `apps/research/views.py`

- Permission check for `is_researcher` field
- Handle search form submission
- Pagination (25 patients per page)
- Results sorting by relevance

### Phase 4: Frontend Implementation

#### 4.1 Search Interface Template

**File**: `apps/research/templates/research/search.html`

- Extends `base_app.html`
- Bootstrap 5.3 styling consistent with project
- Search form with input field and submit button
- Results display area with researcher badge

#### 4.2 Access Denied Template (NEW)

**File**: `apps/research/templates/research/access_denied.html`

- Clear access denied message
- Instructions for getting researcher access
- Link back to dashboard

#### 4.3 Navigation Menu Update (UPDATED)

**File**: `templates/base_app.html`

- Add NEW "Pesquisa Clínica" section visible only to researchers
- Permission check for `user.is_researcher` field

### Phase 5: URL Configuration

#### 5.1 Research App URLs

**File**: `apps/research/urls.py`

- Search view URL pattern
- App namespace configuration

#### 5.2 Main URL Configuration

**File**: `config/urls.py`

- Include research app URLs

### Phase 6: Search Algorithm Implementation

#### 6.1 Core Search Logic

**Location**: `apps/research/utils.py`

```python
def perform_fulltext_search(query_text, limit=25, offset=0):
    """
    Perform full text search and return patient-grouped results

    Returns:
    {
        'patients': [
            {
                'registration_number': str,
                'initials': str,
                'gender': str,
                'birthday': date,
                'age_at_last_note': int,
                'matching_notes': [
                    {
                        'headline': str,  # Search snippet
                        'rank': float,
                        'note_date': datetime
                    }
                ],
                'highest_rank': float
            }
        ],
        'total_patients': int,
        'has_next': bool,
        'has_previous': bool
    }
    """
```

#### 6.2 Search Process Flow (UPDATED)

1. Create SearchQuery with Portuguese config
2. Query DailyNotes with SearchRank and SearchHeadline
3. Group results by patient using defaultdict
4. Calculate age at MOST RECENT MATCHING note date for each patient
5. Generate ALL-WORD initials for each patient name
6. Sort patients by highest match rank
7. Implement pagination
8. Format results for template

### Phase 7: Testing and Optimization

#### 7.1 Database Optimization

- Verify GIN index performance with EXPLAIN ANALYZE
- Test with realistic query loads
- Monitor query performance

#### 7.2 Search Performance Testing

- Test with various query patterns
- Validate search result accuracy
- Test pagination performance

## Configuration Details

### PostgreSQL Search Configuration

- Language: `portuguese`
- Search fields: DailyNote.content
- Index type: GIN
- Update method: Django signals

### Security and Permissions (UPDATED)

- `is_researcher` boolean field required for access
- Integration with existing permission system
- Patient access follows existing rules (universal access)

### UI/UX Considerations

- Consistent with existing EquipeMed design
- Bootstrap 5.3 styling
- Responsive design
- Search result highlighting
- Clear pagination controls

## Database Migration Strategy

### For Existing Data (160k records)

1. Add field with migration (nullable initially)
2. Run management command to populate in batches
3. Create index after population
4. Enable signals for ongoing updates

### Performance Considerations

- Batch processing for initial population
- Efficient signal handlers
- Proper indexing strategy
- Query optimization

## Files to Create/Modify

### New Files

1. `apps/research/` (entire app structure)
2. `apps/dailynotes/signals.py`
3. `apps/dailynotes/management/commands/populate_search_vectors.py`
4. Migration file for search_vector
5. Migration file for is_researcher field (NEW)

### Modified Files

1. `apps/accounts/models.py` - Add is_researcher field (NEW)
2. `apps/accounts/admin.py` - Add field to admin interface (NEW)
3. `apps/dailynotes/models.py` - Add search_vector field
4. `templates/base_app.html` - Add NEW navigation section
5. `config/urls.py` - Include research URLs
6. `apps/dailynotes/apps.py` - Register signals

## Implementation Order (UPDATED)

1. User model extension with is_researcher field (NEW)
2. DailyNote model changes and migration
3. Management command for data population
4. Signal handler for ongoing updates
5. Research app structure
6. Permission system (updated for boolean field)
7. Search functionality (updated algorithms)
8. Frontend templates (updated navigation and results)
9. URL configuration
10. Testing and optimization

## Estimated Timeline (UPDATED)

- Phase 0: User Model Extension (30 minutes) (NEW)
- Phase 1: Database Schema (1-2 hours)
- Phase 2: Research App Structure (1 hour)
- Phase 3: Search Implementation (2-3 hours)
- Phase 4: Frontend (2 hours)
- Phase 5: URL Configuration (30 minutes)
- Phase 6: Search Algorithm (2-3 hours)
- Phase 7: Testing/Optimization (1-2 hours)

**Total: 9.5-13.5 hours**
