# Dashboard Cache System

## Overview

The Dashboard Cache System eliminates expensive real-time database
queries that were causing 100% CPU spikes when accessing the dashboard
and ward mapping pages. Instead, background management commands run
every 5 minutes to pre-compute and cache the data.

## Performance Impact

### Before (Real-time queries)

- Dashboard load: ~2-5 seconds with complex JOINs
- CPU spikes to 100% on each dashboard access
- Multiple expensive queries per page load
- Ward mapping caused server slowdowns

### After (Cached approach)

- Dashboard load: ~200-500ms (simple SELECT from cache)
- Background processing: ~10-30 seconds every 5 minutes
- No impact on user-facing performance
- Predictable server load pattern

## Architecture

### Cache Models

```python
# apps/core/models/cache.py

class DashboardCache(models.Model):
    """General dashboard statistics cache"""
    key = models.CharField(max_length=100, primary_key=True)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

class WardMappingCache(models.Model):
    """Ward mapping data cache"""
    cache_key = models.CharField(max_length=100, primary_key=True)
    ward_data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)
```

### Cache Keys

**Dashboard Cache:**

- `patient_counts` - Total, inpatient, outpatient counts
- `recent_patients` - 30 most recent patients with latest event

**Ward Mapping Cache:**

- `ward_mapping_full` - Complete ward structure with patient assignments
- `ward_filters` - Ward and tag dropdown data

## Management Commands

### update_dashboard_stats

Updates patient statistics and recent patients list.

```bash
# Manual execution
uv run python manage.py update_dashboard_stats

# Docker Compose
docker compose exec web python manage.py update_dashboard_stats

# With force flag
docker compose exec web python manage.py update_dashboard_stats --force
```

**Data collected:**

- Patient counts (total, inpatients, outpatients)
- 30 most recent patients ordered by latest event datetime
- Execution time and success/error logging

### update_ward_mapping_cache

Updates complete ward/bed mapping with patient assignments.

```bash
# Manual execution
uv run python manage.py update_ward_mapping_cache

# Docker Compose
docker compose exec web python manage.py update_ward_mapping_cache

# With force flag
docker compose exec web python manage.py update_ward_mapping_cache --force
```

**Data collected:**

- All wards with patient assignments
- Patient details (name, bed, admission duration, tags)
- Ward utilization calculations
- Filter dropdown data (wards and tags)

### check_cache_health

Monitors cache freshness and health status.

```bash
# Basic health check
docker compose exec web python manage.py check_cache_health

# Detailed information
docker compose exec web python manage.py check_cache_health --verbose
```

**Output example:**

```text
✓ dashboard_stats: Healthy (2.3 minutes old)
✓ recent_patients: Healthy (2.3 minutes old)
✓ ward_mapping: Healthy (1.8 minutes old)
✓ ward_filters: Healthy (1.8 minutes old)
All caches are healthy!
```

## Cron Job Setup

### Production Schedule (Docker Compose)

Create cron jobs that run every 5 minutes with 2-minute offset to
distribute server load:

```bash
# Add to crontab for eqmd user
sudo crontab -u eqmd -e

<!-- markdownlint-disable MD013 -- crontab lines cannot be wrapped -->
# Dashboard stats - runs every 5 minutes (:00, :05, ... :55)
*/5 * * * * cd /home/carlos/projects/eqmd && docker compose exec -T web python manage.py update_dashboard_stats >> /var/log/eqmd/dashboard_cache.log 2>&1

# Ward mapping - runs every 5 minutes offset by 2 minutes (:02, :07, ... :57)
2-59/5 * * * * cd /home/carlos/projects/eqmd && docker compose exec -T web python manage.py update_ward_mapping_cache >> /var/log/eqmd/ward_cache.log 2>&1
<!-- markdownlint-enable MD013 -->
```

### Alternative: Docker Compose Run

If services are not always running, use `run --rm` instead:

```bash
<!-- markdownlint-disable MD013 -- crontab lines cannot be wrapped -->
# Dashboard stats - runs every 5 minutes
*/5 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_dashboard_stats

# Ward mapping - runs every 5 minutes offset by 2 minutes
2-59/5 * * * * cd /home/carlos/projects/eqmd && docker compose run --rm web python manage.py update_ward_mapping_cache
<!-- markdownlint-enable MD013 -->
```

### Log Management

Create log directory:

```bash
sudo mkdir -p /var/log/eqmd
sudo chown $USER:$USER /var/log/eqmd
```

Log rotation with logrotate:

```bash
# /etc/logrotate.d/eqmd-cache
/var/log/eqmd/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## Cache Utility Functions

### get_cached_dashboard_stats()

```python
from apps.core.utils.cache import get_cached_dashboard_stats

dashboard_data = get_cached_dashboard_stats()

if dashboard_data['from_cache']:
    # Use cached data
    stats = dashboard_data['stats']
    total_patients = stats['total_patients']
    recent_patients = dashboard_data['recent_patients']
else:
    # Show updating message
    show_updating_indicator = dashboard_data['updating']
```

### get_cached_ward_mapping()

```python
from apps.core.utils.cache import get_cached_ward_mapping
from apps.patients.services import tag_filters, ward_tag_overlay

# Resolve the shared filter state (same contract as the patient list)
filters = ward_tag_overlay.WardMapFilters(
    selection=tag_filters.TagFilterSelection(),
    search_query=search_query,
    ward_id=ward_id,
    show_empty_wards=show_empty_wards,
)

# Requester-aware projection + filtering; totals come from the returned rows
ward_data = get_cached_ward_mapping(filters, viewer=request.user)

ward_list = ward_data['ward_data']
all_wards = ward_data['all_wards']  # For dropdowns
available_tags = ward_data['available_tags']  # Requester-visible TagBadge list
total_patients = ward_data['total_patients']  # Filtered result, not global
total_wards = ward_data['total_wards']  # Filtered result, not global
```

### Map filters, tag overlay and stale states

The ward-mapping cache is a **structural base only**: ward, bed, patient
identity and admission duration. It is never an authorization or filtering
decision.

- `apps.patients.services.ward_tag_overlay.project_patients()` rehydrates tag
  names, colours, identifiers, lifecycle labels and patient associations from
  the current catalogue for the bounded patient set of the cached base, using
  one batched projection per request (no query per patient or per ward).
  Requester visibility is applied before serialization, so a revocation, a
  reclassification or a rename is effective on the very next response without
  waiting for the 20-minute expiry.
- `apply_filters()` then applies the same `TagFilterSelection` (ANY/ALL,
  manual/clear/default precedence, legacy `tag=` compatibility) used by the
  patient list, together with the search and ward predicates. A tag
  association added or removed after the base was built is reflected
  immediately, because associations are re-read rather than trusted from the
  payload.
- `map_totals()` recomputes the page totals from the rows actually rendered,
  so the header can never disagree with the filtered tree. Empty wards are
  included only when the request asks for them.

The empty states are deliberately distinguishable in the page:

- **Empty result** — the filters match no inpatient: "Nenhum paciente
  encontrado" plus a clear-filters action.
- **Invalid automatic default** — the saved or principal tag is unavailable: a
  generic warning, no tag predicate, patients still listed.
- **Invalid manual filter** — a forged, unknown or inaccessible `tags`/`tag`
  value: `Filtro de tag inválido.`, no rows, no metadata.
- **Stale base data** — the cache is missing or older than 20 minutes: "Dados
  sendo atualizados" plus the updating fallback.

Map eligibility stays **INPATIENT with a ward**, as written by the background
command. A tag associated only with outpatients therefore yields zero map rows
with matching totals while the patient list can still return those patients.
Refreshing the map is a plain GET reload that retains the query parameters; it
never triggers a cache rebuild or a management command.

### get_cache_status()

```python
from apps.core.utils.cache import get_cache_status

status = get_cache_status()
for cache_name, cache_info in status.items():
    if cache_info['stale']:
        print(f"Warning: {cache_name} is stale")
```

## View Integration

### Dashboard View

The dashboard view now uses cached data with automatic fallback:

```python
@login_required
def dashboard_view(request):
    from apps.core.utils.cache import get_cached_dashboard_stats

    dashboard_data = get_cached_dashboard_stats()

    if dashboard_data['from_cache']:
        # Use cached data - fast response
        context = {
            'total_patients': dashboard_data['stats']['total_patients'],
            'recent_patients': dashboard_data['recent_patients'][:5]
        }
    else:
        # Show updating indicator
        context = {
            'updating': True,
            'total_patients': '...'
        }
```

### Ward Patient Map View

The ward mapping view resolves the shared tag filter state and hands a
`WardMapFilters` object to the cache utility:

```python
class WardPatientMapView(TemplateView):
    def get_context_data(self, **kwargs):
        from apps.core.utils.cache import get_cached_ward_mapping

        preference = tag_preferences.resolve_request_state(
            self.request.user, self.request.GET
        )
        filters = ward_tag_overlay.WardMapFilters(
            selection=preference.selection,
            search_query=self.request.GET.get('q', '').strip(),
            ward_id=self.request.GET.get('ward', '').strip(),
            show_empty_wards=self.request.GET.get('show_empty_wards') == 'true',
        )

        ward_data = get_cached_ward_mapping(filters, viewer=self.request.user)
        return {
            'ward_data': ward_data['ward_data'],
            'total_patients': ward_data['total_patients'],
            'total_wards': ward_data['total_wards'],
            'updating': ward_data.get('updating', False),
        }
```

## Template Updates

### Dashboard Template

Add updating indicators to dashboard templates:

```html
<!-- Show updating indicator -->
{% if updating %}
<div class="alert alert-info">
  <i class="bi bi-arrow-clockwise me-2"></i>
  Dados sendo atualizados... Recarregue a página em alguns minutos.
</div>
{% endif %}

<!-- Patient counts -->
<div class="col">
  <div class="h4 mb-0 text-medical-primary">{{ total_patients }}</div>
  <small class="text-muted">Pacientes</small>
</div>
```

### Ward Mapping Template

Add refresh functionality:

```html
<!-- Refresh button -->
<button
  type="button"
  class="btn btn-outline-primary"
  id="refresh-data"
  title="Atualizar dados"
>
  <i class="bi bi-arrow-clockwise"></i>
  {% if updating %}Atualizando...{% endif %}
</button>

<!-- Auto-refresh script -->
<script>
  {% if updating %}
  // Auto refresh every 5 minutes if showing "updating" state
  setTimeout(() => location.reload(), 300000);
  {% endif %}
</script>
```

## Monitoring and Troubleshooting

### Health Monitoring

Set up automated health checks:

```bash
<!-- markdownlint-disable MD013 -- crontab line cannot be wrapped -->
# Add to cron for monitoring
*/15 * * * * cd /home/carlos/projects/eqmd && docker compose exec web python manage.py check_cache_health --verbose >> /var/log/eqmd/cache_health.log 2>&1
<!-- markdownlint-enable MD013 -->
```

### Manual Cache Refresh

Force immediate cache refresh:

```bash
# Refresh both caches immediately
docker compose exec web python manage.py update_dashboard_stats --force
docker compose exec web python manage.py update_ward_mapping_cache --force
```

### Cache Reset

If cache becomes corrupted, clear and rebuild:

```bash
# Clear cache tables (will show "updating" until next cron run)
docker compose exec web python manage.py shell -c "
from apps.core.models import DashboardCache, WardMappingCache
DashboardCache.objects.all().delete()
WardMappingCache.objects.all().delete()
print('Cache cleared')
"

# Force immediate rebuild
docker compose exec web python manage.py update_dashboard_stats --force
docker compose exec web python manage.py update_ward_mapping_cache --force
```

### Troubleshooting Common Issues

**1. Cache showing as stale:**

- Check cron jobs are running: `sudo crontab -l`
- Check log files: `tail -f /var/log/eqmd/dashboard_cache.log`
- Verify Docker containers are healthy: `docker compose ps`

**2. "Updating" message persists:**

- Run health check:
  `docker compose exec web python manage.py check_cache_health`
- Force refresh:
  `docker compose exec web python manage.py update_dashboard_stats --force`
- Check command logs for errors

**3. Performance not improved:**

- Verify views are using cached data (check for `from_cache: True` in context)
- Monitor CPU usage during cache refresh vs. page access
- Check that old real-time queries have been removed

## Development and Testing

### Local Development

For development, you can run cache commands manually:

```bash
# Update caches locally
uv run python manage.py update_dashboard_stats
uv run python manage.py update_ward_mapping_cache

# Check health
uv run python manage.py check_cache_health --verbose
```

### Testing Cache Functions

```python
# Test in Django shell
python manage.py shell

from apps.core.utils.cache import get_cached_dashboard_stats, get_cached_ward_mapping

# Test dashboard cache
dashboard_data = get_cached_dashboard_stats()
print(f"From cache: {dashboard_data['from_cache']}")
print(f"Total patients: {dashboard_data['stats']['total_patients']}")

# Test ward mapping cache
ward_data = get_cached_ward_mapping()
print(f"Total wards: {ward_data['total_wards']}")

# Test filtering
from apps.patients.services import tag_filters, ward_tag_overlay
filters = ward_tag_overlay.WardMapFilters(selection=tag_filters.TagFilterSelection())
filtered_data = get_cached_ward_mapping(filters, viewer=user)
print(f"Filtered patients: {filtered_data['total_patients']}")
```

## Data Staleness Policy

- **Maximum staleness:** 20 minutes (cache refresh attempts every 5 minutes)
- **Fallback behavior:** Show "Dados sendo atualizados..." message
- **User experience:** Clear indication when data is being refreshed
- **Manual refresh:** Available for immediate updates when needed

## Security Considerations

- Cache contains patient data - ensure proper database access controls
- Log files may contain patient information - configure log rotation and access
- Management commands require proper Django permissions
- Cache refresh operations are not authenticated - run via secure cron environment

## Migration and Deployment

### Initial Setup

1. Deploy code with cache models
2. Run migrations: `docker compose exec web python manage.py migrate`
3. Set up cron jobs for cache refresh
4. Run initial cache population:
   `docker compose exec web python manage.py update_dashboard_stats --force &&
docker compose exec web python manage.py update_ward_mapping_cache --force`
5. Verify health: `docker compose exec web python manage.py check_cache_health`

### Rolling Updates

When updating the cache system:

1. Deploy new code
2. Run any new migrations
3. Update cron jobs if needed
4. Force cache refresh to ensure compatibility
5. Monitor cache health after deployment

## Future Enhancements

**Potential improvements:**

- Redis integration for even faster access
- Cache warming on database changes via signals
- Real-time cache invalidation
- Cache compression for large datasets
- Metrics and analytics on cache performance
- Multiple cache refresh frequencies for different data types
