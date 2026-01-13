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
            deleted_count = expired_drafts.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} expired draft(s)')
            )
            logger.info(f'Cleaned up {deleted_count} expired drafts')