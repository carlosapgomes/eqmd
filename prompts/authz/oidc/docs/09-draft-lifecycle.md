# Phase 09 – Draft Lifecycle

## Goal

Add draft support to the Event model, implement automatic expiration, and ensure drafts are clearly separated from definitive documents.

## Prerequisites

- Phase 08 completed (Bot API Layer)
- All existing tests passing

## Tasks

### Task 9.1: Add Draft Fields to Event Model

Edit `apps/events/models.py`, add to Event class:

```python
class Event(SoftDeleteModel):
    # ... existing fields ...
    
    # Draft support
    is_draft = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="É Rascunho",
        help_text="Se True, este evento é um rascunho pendente de revisão"
    )
    
    draft_created_by_bot = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bot que criou",
        help_text="Client ID do bot que criou este rascunho"
    )
    
    draft_delegated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delegated_drafts',
        verbose_name="Delegado por",
        help_text="Médico que delegou a criação deste rascunho"
    )
    
    draft_expires_at = models.DateTimeField(
        null=True, blank=True,
        db_index=True,
        verbose_name="Expira em",
        help_text="Data/hora em que o rascunho expira automaticamente"
    )
    
    draft_promoted_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Promovido em",
        help_text="Data/hora em que o rascunho foi promovido a definitivo"
    )
    
    draft_promoted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='promoted_drafts',
        verbose_name="Promovido por",
        help_text="Usuário que promoveu este rascunho a definitivo"
    )
```

### Task 9.2: Create Custom Manager for Non-Draft Events

Add to `apps/events/models.py`:

```python
class EventManager(SoftDeleteInheritanceManager):
    """Manager that excludes drafts by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_draft=False)
    
    def with_drafts(self):
        """Include drafts in queryset."""
        return SoftDeleteInheritanceQuerySet(self.model, using=self._db).active()
    
    def drafts_only(self):
        """Get only drafts."""
        return SoftDeleteInheritanceQuerySet(self.model, using=self._db).active().filter(is_draft=True)
    
    def expired_drafts(self):
        """Get expired drafts for cleanup."""
        from django.utils import timezone
        return self.drafts_only().filter(draft_expires_at__lt=timezone.now())


class Event(SoftDeleteModel):
    # ... fields ...
    
    objects = EventManager()
    all_objects = SoftDeleteInheritanceManager()  # Access all including drafts
```

### Task 9.3: Create Draft Cleanup Management Command

Create `apps/events/management/commands/cleanup_expired_drafts.py`:

```python
"""
Management command to clean up expired drafts.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.events.models import Event

logger = logging.getLogger('apps.events')


class Command(BaseCommand):
    help = 'Clean up expired draft events'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        expired_drafts = Event.all_objects.filter(
            is_draft=True,
            draft_expires_at__lt=timezone.now()
        ).select_subclasses()
        
        count = expired_drafts.count()
        
        if count == 0:
            self.stdout.write('No expired drafts found.')
            return
        
        if dry_run:
            self.stdout.write(f'Would delete {count} expired draft(s):')
            for draft in expired_drafts[:20]:
                self.stdout.write(f'  - {draft.id}: {draft.description} (expired {draft.draft_expires_at})')
            if count > 20:
                self.stdout.write(f'  ... and {count - 20} more')
        else:
            # Hard delete expired drafts
            deleted_count, _ = expired_drafts.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} expired draft(s)')
            )
            logger.info(f'Cleaned up {deleted_count} expired drafts')
```

### Task 9.4: Create Cron Job Configuration

Create `docs/deployment/draft-cleanup-cron.md`:

```markdown
# Draft Cleanup Cron Configuration

Add to crontab:

```bash
# Run every hour to clean up expired drafts
0 * * * * cd /path/to/eqmd && /path/to/uv run python manage.py cleanup_expired_drafts >> /var/log/eqmd/draft-cleanup.log 2>&1
```

Or use systemd timer:

```ini
# /etc/systemd/system/eqmd-draft-cleanup.service
[Unit]
Description=EQMD Draft Cleanup
After=network.target

[Service]
Type=oneshot
User=eqmd
WorkingDirectory=/path/to/eqmd
ExecStart=/path/to/uv run python manage.py cleanup_expired_drafts
```

```ini
# /etc/systemd/system/eqmd-draft-cleanup.timer
[Unit]
Description=Run EQMD Draft Cleanup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```
```

### Task 9.5: Update Views to Exclude Drafts

Ensure existing views only show definitive documents:

```python
# In dailynotes/views.py (example)
class DailyNoteListView(LoginRequiredMixin, ListView):
    model = DailyNote
    
    def get_queryset(self):
        # objects manager already excludes drafts
        return DailyNote.objects.filter(patient=self.get_patient())
```

### Task 9.6: Create Draft List View for Physicians

Create `apps/botauth/views.py` (add to existing):

```python
class MyDraftsView(LoginRequiredMixin, ListView):
    """View for physicians to see their pending drafts."""
    
    template_name = 'botauth/my_drafts.html'
    context_object_name = 'drafts'
    
    def get_queryset(self):
        from apps.events.models import Event
        return Event.all_objects.filter(
            is_draft=True,
            draft_delegated_by=self.request.user,
            draft_expires_at__gt=timezone.now()
        ).select_subclasses().order_by('-created_at')
```

### Task 9.7: Run Migration

```bash
uv run python manage.py makemigrations events
uv run python manage.py migrate events
```

## Acceptance Criteria

- [x] Event model has `is_draft` and related fields
- [x] Default queryset excludes drafts
- [x] `with_drafts()` and `drafts_only()` managers work
- [x] Cleanup command deletes expired drafts
- [x] Existing views only show definitive documents
- [x] Physicians can see their pending drafts
- [x] All tests pass

## Verification Commands

```bash
# Run migration
uv run python manage.py migrate events

# Test cleanup (dry run)
uv run python manage.py cleanup_expired_drafts --dry-run

# Verify default queryset excludes drafts
uv run python manage.py shell -c "
from apps.dailynotes.models import DailyNote
print('Default count:', DailyNote.objects.count())
print('With drafts:', DailyNote.all_objects.count())
"
```
