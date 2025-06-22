# MediaFiles Database Schema Documentation

## Overview

This document outlines the complete database schema design for the MediaFiles app in EquipeMed. The schema supports three types of media events: single photos, photo series, and short video clips, all extending the base Event model.

## Database Tables

### 1. mediafiles_mediafile (Core File Storage)

The central table for storing file metadata and managing secure file storage.

```sql
CREATE TABLE mediafiles_mediafile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path VARCHAR(500) NOT NULL,           -- Secure UUID-based path
    original_filename VARCHAR(255) NOT NULL,   -- User's original filename
    file_hash VARCHAR(64) UNIQUE,              -- SHA-256 hash for deduplication
    file_size BIGINT NOT NULL,                 -- File size in bytes
    mime_type VARCHAR(100) NOT NULL,           -- Validated MIME type
    file_type VARCHAR(20) NOT NULL,            -- 'image' or 'video'
    width INTEGER,                             -- Image/video width
    height INTEGER,                            -- Image/video height
    duration DECIMAL(10,3),                    -- Video duration in seconds
    thumbnail_path VARCHAR(500),               -- Generated thumbnail path
    metadata JSONB,                            -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_mediafile_hash ON mediafiles_mediafile(file_hash);
CREATE INDEX idx_mediafile_type ON mediafiles_mediafile(file_type);
CREATE INDEX idx_mediafile_created ON mediafiles_mediafile(created_at);
```

### 2. mediafiles_photo (Single Photo Events)

Extends Event model for single photo uploads.

```sql
CREATE TABLE mediafiles_photo (
    event_ptr_id UUID PRIMARY KEY REFERENCES events_event(id) ON DELETE CASCADE,
    media_file_id UUID NOT NULL REFERENCES mediafiles_mediafile(id) ON DELETE PROTECT
);

-- Indexes
CREATE UNIQUE INDEX idx_photo_media_file ON mediafiles_photo(media_file_id);
```

### 3. mediafiles_photoseries (Photo Series Events)

Extends Event model for photo series (multiple related images).

```sql
CREATE TABLE mediafiles_photoseries (
    event_ptr_id UUID PRIMARY KEY REFERENCES events_event(id) ON DELETE CASCADE,
    total_images INTEGER DEFAULT 0,
    series_description TEXT
);
```

### 4. mediafiles_photoseriesfile (Through Table)

Links photo series to multiple media files with ordering.

```sql
CREATE TABLE mediafiles_photoseriesfile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_series_id UUID NOT NULL REFERENCES mediafiles_photoseries(event_ptr_id) ON DELETE CASCADE,
    media_file_id UUID NOT NULL REFERENCES mediafiles_mediafile(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    caption TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_series_file_unique ON mediafiles_photoseriesfile(photo_series_id, media_file_id);
CREATE INDEX idx_series_order ON mediafiles_photoseriesfile(photo_series_id, order_index);
```

### 5. mediafiles_videoclip (Video Clip Events)

Extends Event model for short video clips.

```sql
CREATE TABLE mediafiles_videoclip (
    event_ptr_id UUID PRIMARY KEY REFERENCES events_event(id) ON DELETE CASCADE,
    media_file_id UUID NOT NULL REFERENCES mediafiles_mediafile(id) ON DELETE PROTECT
);

-- Indexes
CREATE UNIQUE INDEX idx_videoclip_media_file ON mediafiles_videoclip(media_file_id);
```

## File Storage Structure

### Directory Organization

```
media/
├── photos/
│   ├── 2024/01/
│   │   ├── originals/
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   ├── large/          # 1200px max dimension
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   ├── medium/         # 800px max dimension
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   └── thumbnails/     # 200px max dimension
│   │       ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │       └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
├── photo_series/
│   └── 2024/01/
│       ├── originals/
│       │   ├── series1-uuid1.jpg
│       │   ├── series1-uuid2.jpg
│       │   └── series1-uuid3.jpg
│       └── thumbnails/
│           ├── series1-uuid1.jpg
│           ├── series1-uuid2.jpg
│           └── series1-uuid3.jpg
└── videos/
    ├── 2024/01/
    │   ├── originals/
    │   │   └── video-uuid.mp4
    │   └── thumbnails/
    │       └── video-uuid.jpg
```

### File Naming Convention

- **UUID-based filenames**: `{uuid4()}.{extension}`
- **Year/Month organization**: `{media_type}/{YYYY}/{MM}/`
- **Size variants**: `originals/`, `large/`, `medium/`, `thumbnails/`
- **Original filenames**: Stored in database only, never in file paths

## Security Features

### File Security

1. **UUID-based filenames** prevent enumeration attacks
2. **Original filenames** stored in database only
3. **No patient information** in file paths
4. **File extension validation** enforced at upload
5. **MIME type validation** with magic number checking
6. **File size limits** enforced per media type
7. **Path traversal protection** in all file operations

### Access Control

1. **Permission-based file access** through Django views
2. **No direct file system access** from web
3. **Secure file serving** with proper headers
4. **Rate limiting** for file downloads
5. **Access logging** for audit trails

### Data Integrity

1. **SHA-256 hash calculation** for deduplication
2. **File corruption detection** through hash verification
3. **Atomic file operations** to prevent partial uploads
4. **Backup-friendly structure** with clear organization

## Model Relationships

```
Event (base model)
├── Photo (1:1 with MediaFile)
│   └── MediaFile
├── PhotoSeries (1:M with MediaFile through PhotoSeriesFile)
│   └── PhotoSeriesFile
│       └── MediaFile
└── VideoClip (1:1 with MediaFile)
    └── MediaFile
```

## Implementation Phases

### Phase 2A: Single Photo Implementation
- MediaFile model
- Photo model
- Basic file upload and validation
- Thumbnail generation
- Admin interface

### Phase 2B: Photo Series Implementation
- PhotoSeries model
- PhotoSeriesFile through model
- Multi-file upload handling
- Series ordering and management
- Bulk operations

### Phase 2C: Video Clip Implementation
- VideoClip model
- Video file validation
- Video thumbnail extraction
- Duration validation
- Video metadata extraction

## Performance Considerations

### Database Indexes

- File hash for deduplication lookups
- File type for filtering
- Creation date for chronological queries
- Series ordering for photo series
- Foreign key relationships

### File System

- Year/month organization for manageable directory sizes
- Separate directories for different image sizes
- Efficient thumbnail serving
- CDN-ready structure for future scaling

## Migration Strategy

1. Create MediaFile model first (foundation)
2. Add Photo model (simplest case)
3. Add PhotoSeries and through model (complex case)
4. Add VideoClip model (video handling)
5. Add indexes and constraints
6. Test data migration scripts

## Backup and Recovery

- Database schema allows for complete reconstruction
- File hash enables integrity verification
- Original filenames preserved for user reference
- Metadata stored for complete file information
- Clear separation between database and file storage
