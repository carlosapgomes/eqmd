# Full Text Search Algorithm Details

## Search Query Processing

### PostgreSQL Full Text Search Configuration

```python
# Language configuration for Portuguese
SEARCH_CONFIG = 'portuguese'

# Create search vector from content
SearchVector('content', config=SEARCH_CONFIG)

# Create search query
SearchQuery(query_text, config=SEARCH_CONFIG)
```

### Search Vector Population

```python
# Initial population command
python manage.py populate_search_vectors --batch-size=1000

# Signal-based updates
@receiver(post_save, sender=DailyNote)
def update_search_vector(sender, instance, **kwargs):
    instance.search_vector = SearchVector('content', config='portuguese')
    sender.objects.filter(pk=instance.pk).update(
        search_vector=instance.search_vector
    )
```

## Core Search Algorithm

### Step 1: Query Matching Notes

```python
def get_matching_notes(query_text):
    query = SearchQuery(query_text, config='portuguese')

    return DailyNote.objects.annotate(
        rank=SearchRank('search_vector', query),
        headline=SearchHeadline(
            'content',
            query,
            config='portuguese',
            max_words=30,
            min_words=10,
            start_sel='<b>',
            stop_sel='</b>'
        )
    ).filter(
        search_vector=query
    ).select_related('patient').order_by('-rank')
```

### Step 2: Group by Patient

```python
from collections import defaultdict

def group_notes_by_patient(matching_notes):
    patient_groups = defaultdict(list)

    for note in matching_notes:
        patient_groups[note.patient].append({
            'note': note,
            'rank': note.rank,
            'headline': note.headline,
            'note_date': note.event_datetime
        })

    return patient_groups
```

### Step 3: Build Patient Results

```python
def build_patient_results(patient_groups):
    results = []

    for patient, notes in patient_groups.items():
        # Get the most recent note date for age calculation
        last_note_date = max(n['note_date'].date() for n in notes)

        # Calculate age at last note date
        age_at_last_note = calculate_age_at_date(patient.birthday, last_note_date)

        # Get top 5 matches per patient, sorted by rank
        top_matches = sorted(notes, key=lambda x: x['rank'], reverse=True)[:5]

        results.append({
            'patient': patient,
            'registration_number': patient.current_record_number,
            'initials': get_patient_initials(patient.name),
            'gender': patient.get_gender_display(),
            'birthday': patient.birthday,
            'age_at_last_note': age_at_last_note,
            'matching_notes': top_matches,
            'highest_rank': max(n['rank'] for n in notes),
            'total_matches': len(notes)
        })

    return results
```

### Step 4: Sort and Paginate

```python
def sort_and_paginate_results(results, page=1, per_page=25):
    # Sort by highest rank (best matches first)
    sorted_results = sorted(results, key=lambda x: x['highest_rank'], reverse=True)

    # Implement pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    paginated_results = sorted_results[start_idx:end_idx]

    return {
        'patients': paginated_results,
        'total_patients': len(sorted_results),
        'current_page': page,
        'per_page': per_page,
        'total_pages': math.ceil(len(sorted_results) / per_page),
        'has_next': end_idx < len(sorted_results),
        'has_previous': page > 1
    }
```

## Utility Functions

### Patient Initials Extraction

```python
def get_patient_initials(full_name):
    """
    Extract initials from patient name.
    Example: "João da Silva Santos" -> "J.S.S."
    """
    if not full_name:
        return ""

    # Split name into words, filter out common prepositions
    words = full_name.strip().split()
    prepositions = {'da', 'de', 'do', 'das', 'dos', 'e'}

    initials = []
    for word in words:
        if word.lower() not in prepositions and word:
            initials.append(word[0].upper())

    return '.'.join(initials) + '.' if initials else ""
```

### Age Calculation

```python
def calculate_age_at_date(birthday, reference_date):
    """
    Calculate age at a specific reference date.
    """
    if not birthday or not reference_date:
        return None

    # Ensure reference_date is a date object
    if hasattr(reference_date, 'date'):
        reference_date = reference_date.date()

    age = reference_date.year - birthday.year

    # Adjust if birthday hasn't occurred yet in the reference year
    if (reference_date.month, reference_date.day) < (birthday.month, birthday.day):
        age -= 1

    return age
```

## Search Performance Optimization

### Database Indexing

```python
# In DailyNote model Meta class
class Meta:
    indexes = [
        GinIndex(fields=['search_vector']),  # For full text search
        models.Index(fields=['patient', 'event_datetime']),  # For patient grouping
        models.Index(fields=['event_datetime']),  # For date sorting
    ]
```

### Query Optimization

```python
def optimized_search_query(query_text):
    """
    Optimized query with minimal database hits
    """
    query = SearchQuery(query_text, config='portuguese')

    # Single query with all needed data
    return DailyNote.objects.select_related(
        'patient'
    ).annotate(
        rank=SearchRank('search_vector', query),
        headline=SearchHeadline(
            'content',
            query,
            config='portuguese',
            max_words=30
        )
    ).filter(
        search_vector=query
    ).order_by('-rank')
```

### Batch Processing for Initial Population

```python
def populate_search_vectors_batch(batch_size=1000):
    """
    Populate search vectors in batches to handle 160k records
    """
    total_notes = DailyNote.objects.count()
    processed = 0

    while processed < total_notes:
        notes_batch = DailyNote.objects.filter(
            search_vector__isnull=True
        )[:batch_size]

        if not notes_batch:
            break

        # Update search vectors for batch
        for note in notes_batch:
            note.search_vector = SearchVector('content', config='portuguese')

        # Bulk update
        DailyNote.objects.bulk_update(notes_batch, ['search_vector'])

        processed += len(notes_batch)
        print(f"Processed {processed}/{total_notes} notes")
```

## Frontend Integration

### Search Result Highlighting

```html
<!-- In search results template -->
{% for patient in patients %}
<tr>
  <td>{{ patient.registration_number }}</td>
  <td>{{ patient.initials }}</td>
  <td>{{ patient.gender }}</td>
  <td>{{ patient.birthday|date:"d/m/Y" }}</td>
  <td>{{ patient.age_at_last_note }} anos</td>
  <td>
    {% for match in patient.matching_notes %}
    <div class="search-snippet">
      {{ match.headline|safe }}
      <small class="text-muted">({{ match.note_date|date:"d/m/Y" }})</small>
    </div>
    {% endfor %}
  </td>
</tr>
{% endfor %}
```

### CSS for Search Highlighting

```css
.search-snippet {
  margin-bottom: 0.5rem;
  padding: 0.25rem;
  background-color: #f8f9fa;
  border-left: 3px solid #007bff;
}

.search-snippet b {
  background-color: #ffeb3b;
  padding: 0.1rem 0.2rem;
  border-radius: 0.2rem;
}
```

## Error Handling and Edge Cases

### Search Query Validation

```python
def validate_search_query(query_text):
    """
    Validate and sanitize search query
    """
    if not query_text or not query_text.strip():
        return None, "Query cannot be empty"

    # Remove excessive whitespace
    query_text = ' '.join(query_text.split())

    # Minimum length check
    if len(query_text) < 3:
        return None, "Query must be at least 3 characters"

    # Maximum length check
    if len(query_text) > 200:
        return None, "Query too long (maximum 200 characters)"

    return query_text, None
```

### No Results Handling

```python
def handle_empty_results(query_text):
    return {
        'patients': [],
        'total_patients': 0,
        'message': f'Nenhum resultado encontrado para "{query_text}"',
        'suggestions': [
            'Verifique a ortografia dos termos de busca',
            'Tente usar palavras-chave mais gerais',
            'Use apenas palavras essenciais da busca'
        ]
    }
```

## Performance Benchmarks

### Expected Performance

- **Search Query Time**: < 100ms for typical queries
- **Result Processing**: < 50ms for grouping and sorting
- **Total Response Time**: < 200ms for 25 results
- **Memory Usage**: < 50MB for processing 1000 matches

### Monitoring Points

1. PostgreSQL query execution time
2. Python processing time for grouping
3. Template rendering time
4. Total HTTP response time
5. Memory usage during search processing

