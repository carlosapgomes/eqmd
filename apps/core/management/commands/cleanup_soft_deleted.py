from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from apps.patients.models import Patient
from apps.events.models import Event


class Command(BaseCommand):
    help = 'Clean up old soft-deleted records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete records soft-deleted more than N days ago'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        cutoff_date = datetime.now() - timedelta(days=options['days'])

        # Find old soft-deleted records
        old_patients = Patient.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )

        old_events = Event.all_objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )

        if options['dry_run']:
            self.stdout.write(f"Would delete {old_patients.count()} patients")
            self.stdout.write(f"Would delete {old_events.count()} events")
        else:
            patient_count = old_patients.count()
            event_count = old_events.count()

            # Hard delete old records
            old_patients.hard_delete()
            old_events.hard_delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted {patient_count} patients and {event_count} events '
                    f'that were soft-deleted more than {options["days"]} days ago'
                )
            )