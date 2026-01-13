"""
Generate audit reports for bot delegation activity.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.botauth.audit import BotAuditLog


class Command(BaseCommand):
    help = 'Generate audit report for bot delegation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=7,
            help='Number of days to include in report'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        since = timezone.now() - timedelta(days=days)
        
        logs = BotAuditLog.objects.filter(timestamp__gte=since)
        
        self.stdout.write(f"\n=== Bot Delegation Audit Report ===")
        self.stdout.write(f"Period: Last {days} days")
        self.stdout.write(f"Total events: {logs.count()}\n")
        
        # Event type breakdown
        self.stdout.write("Events by type:")
        for event_type in logs.values('event_type').distinct():
            count = logs.filter(event_type=event_type['event_type']).count()
            self.stdout.write(f"  {event_type['event_type']}: {count}")
        
        # Failed events
        failed = logs.filter(success=False)
        self.stdout.write(f"\nFailed events: {failed.count()}")
        
        # Top users
        self.stdout.write("\nTop delegating users:")
        from django.db.models import Count
        top_users = logs.values('user_email').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        for u in top_users:
            self.stdout.write(f"  {u['user_email']}: {u['count']}")
        
        # Top bots
        self.stdout.write("\nTop bots:")
        top_bots = logs.values('bot_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        for b in top_bots:
            self.stdout.write(f"  {b['bot_name']}: {b['count']}")