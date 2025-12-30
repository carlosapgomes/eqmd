# Dashboard Cache Implementation Plan

## Overview

This document outlines the implementation of two management commands to cache dashboard and ward mapping data, eliminating expensive real-time queries and improving dashboard performance.

## Commands Structure

### Command 1: `update_dashboard_stats`

- **Purpose**: Cache general patient statistics
- **Frequency**: Every 5 minutes (offset by 2.5 minutes from ward mapping)
- **Data**: Patient counts, recent patients list

### Command 2: `update_ward_mapping_cache`

- **Purpose**: Cache ward/bed mapping data
- **Frequency**: Every 5 minutes (offset by 2.5 minutes from dashboard stats)
- **Data**: Complete ward structure with patient assignments

## Database Schema

### Cache Models

```python
# apps/core/models.py

class DashboardCache(models.Model):
    """General dashboard statistics cache"""
    key = models.CharField(max_length=100, primary_key=True)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_dashboard_cache'

class WardMappingCache(models.Model):
    """Ward mapping data cache"""
    cache_key = models.CharField(max_length=100, primary_key=True)
    ward_data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_ward_mapping_cache'
```

## Command 1: Dashboard Statistics Cache

### File: `apps/core/management/commands/update_dashboard_stats.py`

#### Data Structure

**Key: `patient_counts`**

```json
{
  "total_patients": 150,
  "inpatients": 89,
  "outpatients": 61,
  "updated_at": "2025-08-25T10:30:00Z"
}
```

**Key: `recent_patients`**

```json
{
  "patients": [
    {
      "id": 123,
      "name": "João Silva",
      "status": "inpatient",
      "latest_event_datetime": "2025-08-25T09:45:00Z"
    }
  ],
  "total_count": 30,
  "updated_at": "2025-08-25T10:30:00Z"
}
```

#### Implementation Steps

1. **Query Optimization**

   - Use `select_related()` for patient status
   - Limit to 30 most recent patients
   - Single query for counts using `aggregate()`

2. **Data Collection**

   ```python
   # Patient counts (single query)
   counts = Patient.objects.aggregate(
       total=Count('id'),
       inpatients=Count('id', filter=Q(status='inpatient')),
       outpatients=Count('id', filter=Q(status='outpatient'))
   )

   # Recent patients (single query with subquery)
   recent_patients = Patient.objects.select_related('latest_event').annotate(
       latest_event_datetime=Max('events__datetime')
   ).order_by('-latest_event_datetime')[:30]
   ```

3. **Atomic Updates**
   - Use `update_or_create()` for each cache key
   - Include timestamp for staleness detection

#### Error Handling

- Continue execution if one query fails
- Log errors but don't interrupt the process
- Keep previous cache if new query fails

## Command 2: Ward Mapping Cache

### File: `apps/core/management/commands/update_ward_mapping_cache.py`

#### Data Structure

**Key: `ward_mapping_full`**

```json
{
  "ward_data": [
    {
      "ward": {
        "id": 1,
        "name": "UTI Cirúrgica",
        "abbreviation": "UTIC",
        "floor": "2º Andar"
      },
      "patient_count": 8,
      "capacity_estimate": 12,
      "utilization_percentage": 67,
      "patients": [
        {
          "patient": {
            "pk": 456,
            "name": "Maria Santos"
          },
          "bed": "Leito 201A",
          "admission_duration": "3 dias",
          "tags": [
            {
              "allowed_tag": {
                "id": 1,
                "name": "COVID-19",
                "color": "#ff6b6b"
              }
            }
          ]
        }
      ]
    }
  ],
  "total_patients": 89,
  "total_wards": 6,
  "updated_at": "2025-08-25T10:32:30Z"
}
```

**Key: `ward_filters`** (for search functionality)

```json
{
  "all_wards": [
    { "id": 1, "name": "UTI Cirúrgica", "abbreviation": "UTIC" },
    { "id": 2, "name": "Enfermaria Geral", "abbreviation": "EG" }
  ],
  "available_tags": [
    { "id": 1, "name": "COVID-19", "color": "#ff6b6b" },
    { "id": 2, "name": "Pneumonia", "color": "#4ecdc4" }
  ],
  "updated_at": "2025-08-25T10:32:30Z"
}
```

#### Implementation Steps

1. **Query Optimization**

   ```python
   # Single query for ward data with prefetch
   ward_data = Ward.objects.prefetch_related(
       'patientrecord_set__patient',
       'patientrecord_set__patient__patienttag_set__allowed_tag'
   ).filter(
       patientrecord__current_status='admitted'
   ).annotate(
       patient_count=Count('patientrecord', filter=Q(patientrecord__current_status='admitted'))
   ).order_by('name')
   ```

2. **Data Transformation**

   - Calculate admission duration
   - Format bed information
   - Calculate utilization percentage
   - Serialize tag information

3. **Memory Efficiency**
   - Process wards one by one
   - Use generator expressions where possible
   - Clear large objects after processing

#### Performance Considerations

- Only include patients with active admissions
- Skip wards with no patients (but include in summary)
- Cache expensive calculations (admission duration)

## Cron Job Configuration

### Schedule (alternating every 5 minutes) - Docker Compose

```bash
# Dashboard stats - runs at :00, :10, :20, :30, :40, :50
*/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_dashboard_stats
2-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_dashboard_stats

# Ward mapping - runs at :05, :15, :25, :35, :45, :55
5-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_ward_mapping_cache
7-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_ward_mapping_cache
```

### Alternative: Docker Compose Run (if services are not always running)

```bash
# Dashboard stats - runs at :00, :10, :20, :30, :40, :50
*/10 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_dashboard_stats
2-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_dashboard_stats

# Ward mapping - runs at :05, :15, :25, :35, :45, :55
5-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_ward_mapping_cache
7-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_ward_mapping_cache
```

### Logging Configuration - Docker Compose

```bash
# Add logging to crontab (using exec for running services)
*/5 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1
2-59/5 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1

# Alternative: using run --rm (creates and destroys containers)
*/5 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1
2-59/5 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1
```

### Docker Compose Service-Specific Commands

```bash
# If using specific service names in docker-compose.yml
*/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec django python manage.py update_dashboard_stats
5-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose exec django python manage.py update_ward_mapping_cache

# For production with specific compose file
*/10 * * * * cd /home/carlos/projects/eqmd && docker compose -f docker-compose.prod.yml exec web python manage.py update_dashboard_stats
5-59/10 * * * * cd /home/carlos/projects/eqmd && docker compose -f docker-compose.prod.yml exec web python manage.py update_ward_mapping_cache
```

## View Integration

### Dashboard Views Update

```python
# apps/core/views.py

def get_cached_dashboard_stats():
    """Get dashboard stats from cache with fallback"""
    try:
        # Try to get from cache
        stats_cache = DashboardCache.objects.get(key='patient_counts')
        recent_cache = DashboardCache.objects.get(key='recent_patients')

        # Check staleness (20 minutes max)
        if (timezone.now() - stats_cache.updated_at).seconds < 1200:
            return {
                'stats': stats_cache.data,
                'recent_patients': recent_cache.data['patients'],
                'from_cache': True
            }
    except DashboardCache.DoesNotExist:
        pass

    # Fallback to real-time (show loading message)
    return {
        'stats': {'total_patients': '...', 'inpatients': '...', 'outpatients': '...'},
        'recent_patients': [],
        'from_cache': False,
        'updating': True
    }
```

### Ward Mapping Views Update

```python
# apps/patients/views.py

def get_cached_ward_mapping(filters=None):
    """Get ward mapping from cache with optional filtering"""
    try:
        # Get full ward data from cache
        ward_cache = WardMappingCache.objects.get(cache_key='ward_mapping_full')
        filter_cache = WardMappingCache.objects.get(cache_key='ward_filters')

        # Check staleness
        if (timezone.now() - ward_cache.updated_at).seconds < 1200:
            ward_data = ward_cache.ward_data

            # Apply filters if provided
            if filters:
                ward_data = apply_client_side_filters(ward_data['ward_data'], filters)

            return {
                'ward_data': ward_data['ward_data'],
                'total_patients': ward_data['total_patients'],
                'total_wards': ward_data['total_wards'],
                'all_wards': filter_cache.ward_data['all_wards'],
                'available_tags': filter_cache.ward_data['available_tags'],
                'from_cache': True
            }
    except WardMappingCache.DoesNotExist:
        pass

    # Fallback - show updating message
    return {
        'ward_data': [],
        'total_patients': 0,
        'total_wards': 0,
        'all_wards': [],
        'available_tags': [],
        'from_cache': False,
        'updating': True
    }
```

## Template Updates

### Dashboard Template

```html
<!-- Show updating indicator -->
{% if updating %}
<div class="alert alert-info">
  <i class="bi bi-arrow-clockwise me-2"></i>
  Dados sendo atualizados... Recarregue a página em alguns minutos.
</div>
{% endif %}
```

### Ward Mapping Template

```html
<!-- Add refresh button with auto-refresh -->
<button
  type="button"
  class="btn btn-outline-primary"
  id="refresh-data"
  title="Atualizar dados"
>
  <i class="bi bi-arrow-clockwise"></i>
  {% if updating %}Atualizando...{% endif %}
</button>

<script>
  // Auto refresh every 5 minutes if showing "updating" state
  {% if updating %}
  setTimeout(() => location.reload(), 300000); // 5 minutes
  {% endif %}
</script>
```

## Monitoring and Maintenance

### Health Check

```python
# Add to management commands
class Command(BaseCommand):
    help = 'Check cache health and staleness'

    def handle(self, *args, **options):
        # Check dashboard cache
        try:
            stats = DashboardCache.objects.get(key='patient_counts')
            age = (timezone.now() - stats.updated_at).seconds
            if age > 1800:  # 30 minutes
                self.stdout.write(self.style.WARNING(f'Dashboard cache is stale: {age}s'))
        except DashboardCache.DoesNotExist:
            self.stdout.write(self.style.ERROR('Dashboard cache missing'))
```

### Cache Reset Command - Docker Compose

```bash
# Manual cache refresh (using exec for running services)
docker compose exec web python manage.py update_dashboard_stats --force
docker compose exec web python manage.py update_ward_mapping_cache --force

# Alternative: using run --rm (creates new containers)
docker compose run --rm web python manage.py update_dashboard_stats --force
docker compose run --rm web python manage.py update_ward_mapping_cache --force

# For specific compose files
docker compose -f docker-compose.prod.yml exec web python manage.py update_dashboard_stats --force
docker compose -f docker-compose.prod.yml exec web python manage.py update_ward_mapping_cache --force
```

## Performance Benefits

### Before (Real-time queries)

- Dashboard load: ~2-5 seconds with complex JOINs
- CPU spikes to 100% on each dashboard access
- Multiple expensive queries per page load

### After (Cached approach)

- Dashboard load: ~200-500ms (simple SELECT from cache)
- Background processing: ~10-30 seconds every 5 minutes
- No impact on user-facing performance
- Predictable server load pattern

## Migration Strategy

### Phase 1: Implementation (1 day)

1. Create cache models and migrate
2. Implement management commands
3. Test data accuracy

### Phase 2: Integration (1 day)

1. Update views to use cache
2. Add fallback mechanisms
3. Update templates with loading states

### Phase 3: Deployment (0.5 days)

1. Deploy code changes
2. Set up cron jobs
3. Monitor cache health

## Risk Mitigation

### Data Staleness

- Maximum 20-minute staleness acceptable for dashboard
- Clear indicators when data is updating
- Manual refresh option available

### Command Failures

- Comprehensive error handling
- Preserve previous cache on failure
- Alert logging for monitoring

### Server Load

- Commands run sequentially (not parallel)
- Offset schedules to distribute load
- Can be disabled instantly if needed

This plan provides a robust caching solution that will eliminate dashboard performance issues while maintaining data accuracy and user experience.
