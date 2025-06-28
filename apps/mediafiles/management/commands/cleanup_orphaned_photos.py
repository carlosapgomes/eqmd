"""
Management command to clean up orphaned Photo records without file_id.

These are likely old records that existed before the FilePond migration
and don't have associated files anymore.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.mediafiles.models import Photo


class Command(BaseCommand):
    help = 'Clean up orphaned Photo records without file_id'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete orphaned records without confirmation',
        )

    def handle(self, *args, **options):
        # Find orphaned photos
        orphaned_photos = Photo.objects.filter(
            file_id__isnull=True
        ).select_related('patient', 'created_by')

        if not orphaned_photos.exists():
            self.stdout.write(
                self.style.SUCCESS('No orphaned photos found.')
            )
            return

        self.stdout.write(
            f'Found {orphaned_photos.count()} orphaned photo(s):'
        )

        for photo in orphaned_photos:
            patient_name = photo.patient.name if photo.patient else 'Unknown'
            creator_name = photo.created_by.get_full_name() if photo.created_by else 'Unknown'
            
            self.stdout.write(
                f'  - Photo {photo.pk}: Patient "{patient_name}", '
                f'Created by "{creator_name}" on {photo.created_at.strftime("%Y-%m-%d %H:%M")}'
            )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No records were deleted.')
            )
            return

        # Confirm deletion
        if not options['force']:
            confirm = input(
                f'\nAre you sure you want to delete {orphaned_photos.count()} orphaned photo(s)? '
                'This action cannot be undone. Type "yes" to continue: '
            )
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled.')
                return

        # Delete orphaned photos
        with transaction.atomic():
            deleted_count, _ = orphaned_photos.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} orphaned photo(s).'
            )
        )