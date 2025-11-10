from django.core.management.base import BaseCommand, CommandError
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.db.models import Value
from apps.dailynotes.models import DailyNote
from apps.dailynotes.signals import sanitize_content_for_search

class Command(BaseCommand):
    help = 'Populate search vectors for existing DailyNote records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        # Count total records needing update
        total_notes = DailyNote.objects.filter(search_vector__isnull=True).count()

        if total_notes == 0:
            self.stdout.write(
                self.style.SUCCESS('All DailyNote records already have search vectors.')
            )
            return

        self.stdout.write(f'Found {total_notes} DailyNote records to update')

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {total_notes} records in batches of {batch_size}')
            )
            return

        processed = 0
        failed = 0

        self.stdout.write('Starting search vector population...')

        while True:
            # Get next batch
            notes_batch = list(
                DailyNote.objects.filter(search_vector__isnull=True)[:batch_size]
            )

            if not notes_batch:
                break

            # Process each note individually
            batch_processed = 0
            for note in notes_batch:
                try:
                    # Sanitize content before creating search vector
                    sanitized_content = sanitize_content_for_search(note.content)
                    
                    # Update the note with the sanitized search vector
                    note.search_vector = SearchVector(Value(sanitized_content), config='portuguese')
                    note.save(update_fields=['search_vector'])
                    batch_processed += 1
                    
                except Exception as note_error:
                    # Skip problematic notes and log them
                    self.stdout.write(
                        self.style.WARNING(f'Skipped note {note.pk}: {note_error}')
                    )
                    failed += 1
                    
                    # Force update to mark as processed even if failed
                    try:
                        note.search_vector = SearchVector(Value(''), config='portuguese')
                        note.save(update_fields=['search_vector'])
                    except:
                        pass

            processed += batch_processed

            # Progress update
            self.stdout.write(
                f'Processed {processed}/{total_notes} records '
                f'({(processed/total_notes)*100:.1f}%)'
            )

        if failed > 0:
            self.stdout.write(
                self.style.WARNING(f'Completed with {failed} failed records')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {processed} DailyNote records')
            )