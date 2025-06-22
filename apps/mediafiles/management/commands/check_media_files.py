"""
Management command to check and repair media files.

This command helps identify and fix issues with MediaFile records,
particularly those created with the broken save process.
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.mediafiles.models import MediaFile, Photo


class Command(BaseCommand):
    help = 'Check media files for integrity and repair broken records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix broken records (default is dry-run)',
        )
        parser.add_argument(
            '--delete-broken',
            action='store_true',
            help='Delete broken MediaFile records that cannot be repaired',
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
        self.delete_broken = options.get('delete_broken', False)

        if self.fix_mode:
            self.stdout.write(
                self.style.WARNING('Running in FIX mode - changes will be made!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Running in DRY-RUN mode - no changes will be made')
            )

        self.check_media_files()

    def check_media_files(self):
        """Check all MediaFile records for integrity."""
        self.stdout.write('Checking MediaFile records...')
        
        total_files = MediaFile.objects.count()
        broken_files = []
        missing_files = []
        orphaned_thumbnails = []
        
        self.stdout.write(f'Found {total_files} MediaFile records to check')

        for media_file in MediaFile.objects.all():
            issues = self.check_single_file(media_file)
            if issues:
                if 'missing_original' in issues:
                    missing_files.append((media_file, issues))
                if 'broken_record' in issues:
                    broken_files.append((media_file, issues))
                if 'orphaned_thumbnail' in issues:
                    orphaned_thumbnails.append((media_file, issues))

        # Report findings
        self.stdout.write('\n' + '='*60)
        self.stdout.write('INTEGRITY CHECK RESULTS')
        self.stdout.write('='*60)
        
        self.stdout.write(f'Total MediaFile records: {total_files}')
        self.stdout.write(f'Missing original files: {len(missing_files)}')
        self.stdout.write(f'Broken records: {len(broken_files)}')
        self.stdout.write(f'Orphaned thumbnails: {len(orphaned_thumbnails)}')

        if missing_files:
            self.stdout.write('\n' + self.style.ERROR('MISSING ORIGINAL FILES:'))
            for media_file, issues in missing_files:
                self.stdout.write(f'  - {media_file.id}: {media_file.original_filename}')
                if self.verbose:
                    self.stdout.write(f'    File path: {media_file.file.name}')
                    self.stdout.write(f'    Issues: {", ".join(issues)}')

        if broken_files:
            self.stdout.write('\n' + self.style.ERROR('BROKEN RECORDS:'))
            for media_file, issues in broken_files:
                self.stdout.write(f'  - {media_file.id}: {media_file.original_filename}')
                if self.verbose:
                    self.stdout.write(f'    Issues: {", ".join(issues)}')

        # Handle fixes if requested
        if self.fix_mode and (missing_files or broken_files):
            self.handle_fixes(missing_files, broken_files)

    def check_single_file(self, media_file):
        """Check a single MediaFile for issues."""
        issues = []
        
        # Check if original file exists
        if media_file.file:
            try:
                file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
                if not file_path.exists():
                    issues.append('missing_original')
                elif not file_path.is_file():
                    issues.append('not_a_file')
            except (ValueError, AttributeError):
                issues.append('invalid_file_path')
        else:
            issues.append('no_file_field')

        # Check if thumbnail exists when it should
        if media_file.thumbnail:
            try:
                thumbnail_path = Path(settings.MEDIA_ROOT) / media_file.thumbnail.name
                if not thumbnail_path.exists():
                    issues.append('missing_thumbnail')
            except (ValueError, AttributeError):
                issues.append('invalid_thumbnail_path')
        elif media_file.file and media_file.mime_type and media_file.mime_type.startswith('image/'):
            # Should have a thumbnail but doesn't
            issues.append('missing_expected_thumbnail')

        # Check for orphaned thumbnails (thumbnail exists but original doesn't)
        if media_file.thumbnail and 'missing_original' in issues:
            issues.append('orphaned_thumbnail')

        # Check for broken records (no file but has metadata)
        if not media_file.file and (media_file.width or media_file.height):
            issues.append('broken_record')

        return issues

    def handle_fixes(self, missing_files, broken_files):
        """Handle fixing broken records."""
        self.stdout.write('\n' + self.style.WARNING('APPLYING FIXES...'))
        
        fixed_count = 0
        deleted_count = 0

        with transaction.atomic():
            # Handle missing files
            for media_file, issues in missing_files:
                if self.delete_broken:
                    # Check if this MediaFile is referenced by any Photo
                    try:
                        photo = Photo.objects.get(media_file=media_file)
                        self.stdout.write(
                            f'Deleting broken Photo {photo.id} and MediaFile {media_file.id}'
                        )
                        photo.delete()  # This will cascade delete the MediaFile
                        deleted_count += 1
                    except Photo.DoesNotExist:
                        self.stdout.write(
                            f'Deleting orphaned MediaFile {media_file.id}'
                        )
                        media_file.delete()
                        deleted_count += 1
                else:
                    self.stdout.write(
                        f'Would delete MediaFile {media_file.id} (use --delete-broken to actually delete)'
                    )

            # Handle broken records
            for media_file, issues in broken_files:
                if self.delete_broken:
                    self.stdout.write(f'Deleting broken MediaFile {media_file.id}')
                    media_file.delete()
                    deleted_count += 1
                else:
                    self.stdout.write(
                        f'Would delete MediaFile {media_file.id} (use --delete-broken to actually delete)'
                    )

        self.stdout.write('\n' + self.style.SUCCESS('FIX SUMMARY:'))
        self.stdout.write(f'Records fixed: {fixed_count}')
        self.stdout.write(f'Records deleted: {deleted_count}')

        if not self.delete_broken and (missing_files or broken_files):
            self.stdout.write('\n' + self.style.WARNING(
                'To actually delete broken records, run with --delete-broken flag'
            ))
