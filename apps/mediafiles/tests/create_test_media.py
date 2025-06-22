#!/usr/bin/env python3
"""
Script to create test media files for the mediafiles app testing.
This script generates various types of test files including valid images,
videos, and malicious files for security testing.
"""

import os
from PIL import Image
import io


def create_test_media_files():
    """Create test media files for testing"""
    
    # Get the test media directory
    test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
    os.makedirs(test_media_dir, exist_ok=True)
    
    # Create valid test images
    create_test_images(test_media_dir)
    
    # Create test video files (mock)
    create_test_videos(test_media_dir)
    
    # Create invalid/malicious test files
    create_malicious_test_files(test_media_dir)
    
    # Create files with dangerous names
    create_dangerous_filename_tests(test_media_dir)
    
    print(f"Test media files created in: {test_media_dir}")


def create_test_images(test_dir):
    """Create valid test image files"""
    
    # Small JPEG image (100x100)
    small_img = Image.new('RGB', (100, 100), color='red')
    small_img.save(os.path.join(test_dir, 'small_image.jpg'), 'JPEG')
    
    # Medium JPEG image (500x500)
    medium_img = Image.new('RGB', (500, 500), color='green')
    medium_img.save(os.path.join(test_dir, 'medium_image.jpg'), 'JPEG')
    
    # Large JPEG image (1920x1080)
    large_img = Image.new('RGB', (1920, 1080), color='blue')
    large_img.save(os.path.join(test_dir, 'large_image.jpg'), 'JPEG')
    
    # PNG image
    png_img = Image.new('RGBA', (300, 300), color=(255, 0, 0, 128))
    png_img.save(os.path.join(test_dir, 'test_image.png'), 'PNG')
    
    # WebP image (if supported)
    try:
        webp_img = Image.new('RGB', (200, 200), color='yellow')
        webp_img.save(os.path.join(test_dir, 'test_image.webp'), 'WEBP')
    except Exception:
        print("WebP format not supported, skipping WebP test file")
    
    # Duplicate image for deduplication testing
    duplicate_img = Image.new('RGB', (100, 100), color='red')
    duplicate_img.save(os.path.join(test_dir, 'duplicate_image.jpg'), 'JPEG')
    
    print("Created test image files")


def create_test_videos(test_dir):
    """Create mock test video files (headers only for testing)"""
    
    # Valid MP4 header
    mp4_header = (
        b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom'
        b'\x00\x00\x00\x08free\x00\x00\x00\x28mdat'
        b'Mock video content for testing purposes. '
        b'This is not a real video file but contains valid MP4 headers.'
    )
    
    with open(os.path.join(test_dir, 'test_video.mp4'), 'wb') as f:
        f.write(mp4_header)
    
    # Valid WebM header (simplified)
    webm_header = (
        b'\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04'
        b'\x42\xf3\x81\x08\x42\x82\x84webm\x42\x87\x81\x02\x42\x85\x81\x02'
        b'Mock WebM content for testing purposes.'
    )
    
    with open(os.path.join(test_dir, 'test_video.webm'), 'wb') as f:
        f.write(webm_header)
    
    # QuickTime MOV header (simplified)
    mov_header = (
        b'\x00\x00\x00\x14ftypqt  \x20\x05\x03\x00qt  '
        b'\x00\x00\x00\x08wide'
        b'Mock QuickTime content for testing purposes.'
    )
    
    with open(os.path.join(test_dir, 'test_video.mov'), 'wb') as f:
        f.write(mov_header)
    
    # Large video file (mock - just repeat content to make it larger)
    large_video_content = mp4_header + (b'x' * (10 * 1024 * 1024))  # ~10MB
    with open(os.path.join(test_dir, 'large_video.mp4'), 'wb') as f:
        f.write(large_video_content)
    
    print("Created test video files")


def create_malicious_test_files(test_dir):
    """Create malicious test files for security testing"""
    
    # Text file disguised as image
    with open(os.path.join(test_dir, 'fake_image.jpg'), 'w') as f:
        f.write("This is just text content, not an image")
    
    # HTML file disguised as image
    html_content = """
    <html>
    <head><title>Malicious</title></head>
    <body>
        <script>alert('XSS');</script>
        <img src="x" onerror="alert('XSS')">
    </body>
    </html>
    """
    with open(os.path.join(test_dir, 'malicious.jpg'), 'w') as f:
        f.write(html_content)
    
    # PHP file disguised as image
    php_content = """<?php
    system($_GET['cmd']);
    echo "Malicious PHP content";
    ?>"""
    with open(os.path.join(test_dir, 'malicious.png'), 'w') as f:
        f.write(php_content)
    
    # JavaScript file disguised as video
    js_content = """
    function maliciousFunction() {
        // Malicious JavaScript code
        eval(atob('YWxlcnQoJ1hTUycpOw=='));
    }
    maliciousFunction();
    """
    with open(os.path.join(test_dir, 'malicious.mp4'), 'w') as f:
        f.write(js_content)
    
    # Binary file with embedded script
    binary_with_script = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG header
        b'<script>alert("XSS")</script>'  # Embedded script
        b'\xff\xd9'  # JPEG footer
    )
    with open(os.path.join(test_dir, 'polyglot.jpg'), 'wb') as f:
        f.write(binary_with_script)
    
    print("Created malicious test files")


def create_dangerous_filename_tests(test_dir):
    """Create files with dangerous names for sanitization testing"""
    
    # Create a subdirectory for dangerous filename tests
    dangerous_dir = os.path.join(test_dir, 'dangerous_names')
    os.makedirs(dangerous_dir, exist_ok=True)
    
    # Files with path traversal attempts
    dangerous_names = [
        'normal_file.jpg',
        'file_with_spaces.jpg',
        'file-with-dashes.jpg',
        'file_with_underscores.jpg',
        'UPPERCASE_FILE.JPG',
        'file.with.dots.jpg',
        'file_with_números_123.jpg',
        'arquivo_com_acentos_àáâãäåæçèéêë.jpg',
    ]
    
    for name in dangerous_names:
        safe_path = os.path.join(dangerous_dir, name.replace('/', '_').replace('\\', '_'))
        try:
            with open(safe_path, 'w') as f:
                f.write(f"Test content for {name}")
        except Exception as e:
            print(f"Could not create file {name}: {e}")
    
    print("Created dangerous filename test files")


if __name__ == '__main__':
    create_test_media_files()
