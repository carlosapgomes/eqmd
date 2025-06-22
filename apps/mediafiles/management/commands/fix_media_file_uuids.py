"""
Management command to fix UUID mismatches in media files.

This command addresses the issue where original files and thumbnails
use different UUIDs, causing 404 errors in file serving.
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.mediafiles.models import MediaFile


class Command(BaseCommand):
    help = 'Fix UUID mismatches between original files and MediaFile IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the files (default is dry-run)',
        )
        parser.add_argument(
            '--delete-orphaned',
            action='store_true',
            help='Delete files that cannot be matched to MediaFile records',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        self.fix_mode = options.get('fix', False)
        self.delete_orphaned = options.get('delete_orphaned', False)

        if self.fix_mode:
            self.stdout.write(
                self.style.WARNING('Running in FIX mode - files will be renamed!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Running in DRY-RUN mode - no changes will be made')
            )

        self.fix_uuid_mismatches()

    def fix_uuid_mismatches(self):
        """Fix UUID mismatches in media files."""
        self.stdout.write('Checking for UUID mismatches in media files...')
        
        media_root = Path(settings.MEDIA_ROOT)
        fixed_count = 0
        error_count = 0
        
        for media_file in MediaFile.objects.all():
            try:
                result = self.process_media_file(media_file, media_root)
                if result == 'fixed':
                    fixed_count += 1
                elif result == 'error':
                    error_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {media_file.id}: {str(e)}')
                )
                error_count += 1

        # Report results
        self.stdout.write('\n' + '='*60)
        self.stdout.write('UUID MISMATCH FIX RESULTS')
        self.stdout.write('='*60)
        self.stdout.write(f'Total MediaFile records processed: {MediaFile.objects.count()}')
        self.stdout.write(f'Files fixed: {fixed_count}')
        self.stdout.write(f'Errors encountered: {error_count}')

        if not self.fix_mode and fixed_count > 0:
            self.stdout.write('\n' + self.style.WARNING(
                'To actually fix the files, run with --fix flag'
            ))

    def process_media_file(self, media_file, media_root):
        """Process a single MediaFile for UUID mismatch."""
        if not media_file.file:
            if self.verbose:
                self.stdout.write(f'Skipping {media_file.id}: No file field')
            return 'skipped'

        current_file_path = media_root / media_file.file.name

        # Extract UUID from current filename
        current_filename = current_file_path.name
        current_file_uuid = current_filename.split('.')[0]  # Get UUID part before extension

        # Check if UUID matches MediaFile.id
        if str(media_file.id) == current_file_uuid:
            if self.verbose:
                self.stdout.write(f'✓ {media_file.id}: UUID already consistent')
            return 'ok'

        # UUID mismatch detected - need to rename file
        if self.verbose:
            self.stdout.write(f'UUID MISMATCH: MediaFile.id={media_file.id}, File UUID={current_file_uuid}')

        # Check if current file exists (with old UUID naming)
        if not current_file_path.exists():
            if self.verbose:
                self.stdout.write(f'✗ {media_file.id}: File does not exist: {current_file_path}')
            return 'error'

        # Calculate the new filename using MediaFile.id
        file_extension = current_file_path.suffix
        new_filename = f"{media_file.id}{file_extension}"
        new_file_path = current_file_path.parent / new_filename

        if self.verbose:
            self.stdout.write(f'Need to rename: {current_filename} -> {new_filename}')

        if self.fix_mode:
            try:
                # Rename the file to use MediaFile.id
                shutil.move(str(current_file_path), str(new_file_path))

                # Update the MediaFile.file field to point to the new filename
                old_file_name = media_file.file.name
                new_file_name = old_file_name.replace(current_filename, new_filename)
                media_file.file.name = new_file_name
                media_file.save(update_fields=['file'])

                self.stdout.write(f'✓ Fixed: {current_filename} -> {new_filename}')
                return 'fixed'
            except Exception as e:
                self.stdout.write(f'✗ Error renaming {current_filename}: {str(e)}')
                return 'error'
        else:
            self.stdout.write(f'Would fix: {current_filename} -> {new_filename}')
            return 'fixed'

    def find_orphaned_files(self):
        """Find files that don't match any MediaFile record."""
        media_root = Path(settings.MEDIA_ROOT)
        orphaned_files = []
        
        # Get all MediaFile IDs
        media_file_ids = set(str(mf.id) for mf in MediaFile.objects.all())
        
        # Scan for files in originals directories
        for originals_dir in media_root.rglob('originals'):
            for file_path in originals_dir.iterdir():
                if file_path.is_file():
                    # Extract UUID from filename
                    filename_uuid = file_path.stem
                    if filename_uuid not in media_file_ids:
                        orphaned_files.append(file_path)
        
        return orphaned_files
