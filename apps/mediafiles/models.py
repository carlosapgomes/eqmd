# MediaFiles Models - Database Schema Documentation
#
# This file documents the planned database schema for the MediaFiles app.
# The actual model implementations will be created in subsequent phases.
#
# Database Schema Plan:
# =====================
#
# Tables to be created:
# 1. mediafiles_mediafile - Core file storage and metadata
# 2. mediafiles_photo - Single photo events (inherits from Event)
# 3. mediafiles_photoseries - Photo series events (inherits from Event)
# 4. mediafiles_videoclip - Video clip events (inherits from Event)
# 5. mediafiles_photoseriesfile - Through table for photo series ordering
#
# File Storage Structure:
# ======================
#
# media/
# ├── photos/
# │   ├── 2024/01/
# │   │   ├── originals/
# │   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
# │   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
# │   │   ├── large/
# │   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
# │   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
# │   │   ├── medium/
# │   │   └── thumbnails/
# ├── photo_series/
# │   └── 2024/01/
# │       ├── originals/
# │       │   ├── series1-uuid1.jpg
# │       │   └── series1-uuid2.jpg
# │       └── thumbnails/
# └── videos/
#     ├── 2024/01/
#     │   ├── originals/
#     │   │   └── video-uuid.mp4
#     │   └── thumbnails/
#     │       └── video-uuid.jpg
#
# Security Features:
# ==================
# - UUID-based filenames prevent enumeration attacks
# - Original filenames stored in database only
# - No patient information in file paths
# - File extension validation enforced
# - File hash calculation for deduplication
# - MIME type validation
# - File size limits enforced
# - Path traversal protection
# - Secure file serving through Django views
#
# Model Relationships:
# ===================
#
# Event (base model)
# ├── Photo (1:1 with MediaFile)
# ├── PhotoSeries (1:M with MediaFile through PhotoSeriesFile)
# └── VideoClip (1:1 with MediaFile)
#
# MediaFile (core file storage)
# ├── file_path (secure UUID-based path)
# ├── original_filename (user's original filename)
# ├── file_hash (SHA-256 for deduplication)
# ├── file_size (in bytes)
# ├── mime_type (validated MIME type)
# ├── width/height (for images/videos)
# ├── duration (for videos)
# ├── thumbnail_path (generated thumbnail)
# └── metadata (JSON field for additional data)
#
# PhotoSeriesFile (through model for ordering)
# ├── photo_series (FK to PhotoSeries)
# ├── media_file (FK to MediaFile)
# ├── order (PositiveIntegerField for sequence)
# └── caption (optional description)

from django.db import models

# Models will be implemented in Phase 2 vertical slices:
# - Phase 2A: Photo model (single images)
# - Phase 2B: PhotoSeries model (image series)
# - Phase 2C: VideoClip model (short videos)
#
# Each phase will follow the pattern:
# Slice 1: Model and Admin
# Slice 2: Forms and Views
# Slice 3: Templates and Testing
