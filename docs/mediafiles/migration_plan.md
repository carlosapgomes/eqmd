# MediaFiles Database Migration Plan

## Overview

This document outlines the step-by-step database migration plan for implementing the MediaFiles app models. The migration strategy ensures data integrity, minimal downtime, and rollback capabilities.

## Migration Strategy

### Phase-Based Approach

The migration will be implemented in phases to minimize risk and ensure proper testing:

1. **Phase 1**: Core MediaFile model
2. **Phase 2**: Photo model (single images)
3. **Phase 3**: PhotoSeries and PhotoSeriesFile models
4. **Phase 4**: VideoClip model
5. **Phase 5**: Indexes and constraints optimization

### Migration Principles

- **Backward Compatibility**: Each migration maintains compatibility with existing data
- **Atomic Operations**: Each migration is atomic and can be rolled back
- **Data Validation**: Comprehensive validation before and after migrations
- **Performance Monitoring**: Track migration performance and database impact
- **Testing First**: All migrations tested in development and staging environments

## Phase 1: Core MediaFile Model

### Migration 0001_initial.py

```python
# Generated migration for MediaFile model
from django.db import migrations, models
import uuid
import apps.mediafiles.utils

class Migration(migrations.Migration):
    initial = True
    
    dependencies = [
        ('events', '0002_alter_event_event_type'),  # Ensure VIDEO_CLIP_EVENT exists
    ]
    
    operations = [
        migrations.CreateModel(
            name='MediaFile',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4, 
                    editable=False, 
                    primary_key=True, 
                    serialize=False
                )),
                ('file_path', models.CharField(
                    max_length=500, 
                    unique=True,
                    help_text="Secure UUID-based file path"
                )),
                ('original_filename', models.CharField(
                    max_length=255,
                    help_text="User's original filename"
                )),
                ('file_hash', models.CharField(
                    max_length=64, 
                    unique=True, 
                    null=True, 
                    blank=True,
                    help_text="SHA-256 hash for deduplication"
                )),
                ('file_size', models.BigIntegerField(
                    help_text="File size in bytes"
                )),
                ('mime_type', models.CharField(
                    max_length=100,
                    help_text="Validated MIME type"
                )),
                ('file_type', models.CharField(
                    max_length=20, 
                    choices=[
                        ('image', 'Image'),
                        ('video', 'Video'),
                    ],
                    help_text="Media file type"
                )),
                ('width', models.PositiveIntegerField(
                    null=True, 
                    blank=True,
                    help_text="Image/video width in pixels"
                )),
                ('height', models.PositiveIntegerField(
                    null=True, 
                    blank=True,
                    help_text="Image/video height in pixels"
                )),
                ('duration', models.DecimalField(
                    max_digits=10, 
                    decimal_places=3, 
                    null=True, 
                    blank=True,
                    help_text="Video duration in seconds"
                )),
                ('thumbnail_path', models.CharField(
                    max_length=500, 
                    null=True, 
                    blank=True,
                    help_text="Generated thumbnail path"
                )),
                ('metadata', models.JSONField(
                    default=dict, 
                    blank=True,
                    help_text="Additional file metadata"
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True
                )),
                ('updated_at', models.DateTimeField(
                    auto_now=True
                )),
            ],
            options={
                'verbose_name': 'Media File',
                'verbose_name_plural': 'Media Files',
                'ordering': ['-created_at'],
            },
        ),
    ]
```

### Post-Migration Validation

```python
# Validation script for Phase 1
def validate_mediafile_model():
    """Validate MediaFile model after migration"""
    from apps.mediafiles.models import MediaFile
    
    # Test model creation
    assert MediaFile._meta.get_field('id').primary_key
    assert MediaFile._meta.get_field('file_hash').unique
    assert MediaFile._meta.get_field('file_path').unique
    
    print("✓ MediaFile model validation passed")
```

## Phase 2: Photo Model

### Migration 0002_photo.py

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0001_initial'),
        ('events', '0002_alter_event_event_type'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('event_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='events.event'
                )),
                ('media_file', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='mediafiles.mediafile',
                    help_text="Associated media file"
                )),
            ],
            options={
                'verbose_name': 'Photo',
                'verbose_name_plural': 'Photos',
                'ordering': ['-event_datetime'],
            },
            bases=('events.event',),
        ),
    ]
```

### Data Migration for Existing Photos

```python
# Data migration to handle existing photo events
from django.db import migrations

def migrate_existing_photos(apps, schema_editor):
    """
    Migrate existing photo events to new Photo model.
    This is a placeholder - actual implementation depends on existing data.
    """
    Event = apps.get_model('events', 'Event')
    Photo = apps.get_model('mediafiles', 'Photo')
    
    # Find existing photo events
    photo_events = Event.objects.filter(event_type=3)  # PHOTO_EVENT
    
    print(f"Found {photo_events.count()} existing photo events")
    # Note: Actual migration would require creating MediaFile records
    # for existing photos if any exist

def reverse_photo_migration(apps, schema_editor):
    """Reverse migration for photos"""
    # Implementation for rollback
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0002_photo'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_existing_photos,
            reverse_photo_migration
        ),
    ]
```

## Phase 3: PhotoSeries Models

### Migration 0004_photoseries.py

```python
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0003_migrate_photos'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='PhotoSeries',
            fields=[
                ('event_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='events.event'
                )),
                ('total_images', models.PositiveIntegerField(
                    default=0,
                    help_text="Total number of images in series"
                )),
                ('series_description', models.TextField(
                    blank=True,
                    help_text="Optional description of the photo series"
                )),
            ],
            options={
                'verbose_name': 'Photo Series',
                'verbose_name_plural': 'Photo Series',
                'ordering': ['-event_datetime'],
            },
            bases=('events.event',),
        ),
        migrations.CreateModel(
            name='PhotoSeriesFile',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False
                )),
                ('order_index', models.PositiveIntegerField(
                    help_text="Order of image in series (1-based)"
                )),
                ('caption', models.TextField(
                    blank=True,
                    help_text="Optional caption for this image"
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('photo_series', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='series_files',
                    to='mediafiles.photoseries'
                )),
                ('media_file', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='mediafiles.mediafile'
                )),
            ],
            options={
                'verbose_name': 'Photo Series File',
                'verbose_name_plural': 'Photo Series Files',
                'ordering': ['photo_series', 'order_index'],
            },
        ),
        migrations.AddConstraint(
            model_name='photoseriesfile',
            constraint=models.UniqueConstraint(
                fields=['photo_series', 'media_file'],
                name='unique_series_file'
            ),
        ),
        migrations.AddConstraint(
            model_name='photoseriesfile',
            constraint=models.UniqueConstraint(
                fields=['photo_series', 'order_index'],
                name='unique_series_order'
            ),
        ),
    ]
```

## Phase 4: VideoClip Model

### Migration 0005_videoclip.py

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0004_photoseries'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='VideoClip',
            fields=[
                ('event_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='events.event'
                )),
                ('media_file', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='mediafiles.mediafile',
                    help_text="Associated video file"
                )),
            ],
            options={
                'verbose_name': 'Video Clip',
                'verbose_name_plural': 'Video Clips',
                'ordering': ['-event_datetime'],
            },
            bases=('events.event',),
        ),
    ]
```

## Phase 5: Indexes and Optimization

### Migration 0006_indexes.py

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0005_videoclip'),
    ]
    
    operations = [
        # MediaFile indexes
        migrations.AddIndex(
            model_name='mediafile',
            index=models.Index(
                fields=['file_hash'],
                name='mediafile_hash_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='mediafile',
            index=models.Index(
                fields=['file_type', '-created_at'],
                name='mediafile_type_created_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='mediafile',
            index=models.Index(
                fields=['mime_type'],
                name='mediafile_mime_idx'
            ),
        ),
        
        # PhotoSeriesFile indexes
        migrations.AddIndex(
            model_name='photoseriesfile',
            index=models.Index(
                fields=['photo_series', 'order_index'],
                name='series_file_order_idx'
            ),
        ),
        
        # Performance optimization indexes
        migrations.AddIndex(
            model_name='mediafile',
            index=models.Index(
                fields=['created_at'],
                name='mediafile_created_idx'
            ),
        ),
    ]
```

## Migration Execution Plan

### Pre-Migration Checklist

1. **Database Backup**
   ```bash
   # Create full database backup
   pg_dump eqmd_db > backup_pre_mediafiles_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Environment Validation**
   ```bash
   # Verify Django environment
   python manage.py check --deploy
   
   # Check migration status
   python manage.py showmigrations mediafiles
   ```

3. **Dependency Verification**
   ```bash
   # Ensure all dependencies are installed
   pip install Pillow ffmpeg-python
   
   # Verify ffmpeg system installation
   ffmpeg -version
   ```

### Migration Execution

```bash
# Phase 1: Core MediaFile model
python manage.py makemigrations mediafiles
python manage.py migrate mediafiles 0001

# Validate Phase 1
python manage.py shell -c "from apps.mediafiles.models import MediaFile; print('MediaFile model ready')"

# Phase 2: Photo model
python manage.py migrate mediafiles 0002
python manage.py migrate mediafiles 0003  # Data migration

# Phase 3: PhotoSeries models
python manage.py migrate mediafiles 0004

# Phase 4: VideoClip model
python manage.py migrate mediafiles 0005

# Phase 5: Indexes and optimization
python manage.py migrate mediafiles 0006

# Final validation
python manage.py check
```

### Post-Migration Validation

```python
# Comprehensive validation script
def validate_all_models():
    """Validate all MediaFiles models after migration"""
    from apps.mediafiles.models import MediaFile, Photo, PhotoSeries, VideoClip
    from django.db import connection
    
    # Test model imports
    assert MediaFile
    assert Photo
    assert PhotoSeries
    assert VideoClip
    
    # Test database tables exist
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'mediafiles_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'mediafiles_mediafile',
            'mediafiles_photo',
            'mediafiles_photoseries',
            'mediafiles_photoseriesfile',
            'mediafiles_videoclip'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
    
    print("✓ All MediaFiles models validated successfully")

# Run validation
validate_all_models()
```

## Rollback Plan

### Emergency Rollback Procedure

```bash
# Rollback to specific migration
python manage.py migrate mediafiles 0003  # Rollback to before VideoClip

# Complete rollback (if necessary)
python manage.py migrate mediafiles zero

# Restore from backup (last resort)
psql eqmd_db < backup_pre_mediafiles_YYYYMMDD_HHMMSS.sql
```

### Rollback Testing

Each migration includes reverse operations tested in development:

```python
# Test rollback capability
def test_migration_rollback():
    """Test that migrations can be safely rolled back"""
    from django.core.management import call_command
    
    # Apply migration
    call_command('migrate', 'mediafiles', '0001')
    
    # Rollback migration
    call_command('migrate', 'mediafiles', 'zero')
    
    # Verify clean rollback
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name LIKE 'mediafiles_%'
        """)
        assert len(cursor.fetchall()) == 0
    
    print("✓ Migration rollback test passed")
```

## Performance Monitoring

### Migration Performance Tracking

```python
import time
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """Monitor migration performance"""
    
    def handle(self, *args, **options):
        start_time = time.time()
        
        # Run migration
        call_command('migrate', 'mediafiles')
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Migration completed in {duration:.2f} seconds'
            )
        )
```

### Database Impact Assessment

```sql
-- Monitor table sizes after migration
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename LIKE 'mediafiles_%';

-- Check index usage
SELECT 
    indexrelname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE indexrelname LIKE 'mediafile%';
```

## Success Criteria

### Migration Success Validation

- [ ] All migrations execute without errors
- [ ] All expected tables created with correct schema
- [ ] All indexes created and functional
- [ ] All constraints properly enforced
- [ ] Model imports work correctly
- [ ] Admin interface accessible
- [ ] No data loss during migration
- [ ] Performance within acceptable limits
- [ ] Rollback capability verified
- [ ] Full test suite passes

### Ready for Phase 2 Implementation

After successful completion of Step 7 (Database Preparation), the foundation will be ready for Phase 2 vertical slice implementations:

1. **Phase 2A**: Photo model implementation
2. **Phase 2B**: PhotoSeries model implementation  
3. **Phase 2C**: VideoClip model implementation

Each phase will build upon this solid database foundation with proper security, validation, and performance optimization.
