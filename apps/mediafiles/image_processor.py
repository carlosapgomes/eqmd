import os
from pathlib import Path
from PIL import Image
from django.conf import settings


class ImageProcessor:
    """
    Server-side image processing for thumbnails and optimization.
    """
    
    @staticmethod
    def generate_thumbnail(image_path: str, thumbnail_path: str) -> bool:
        """
        Generate thumbnail for image file.
        
        Args:
            image_path: Path to original image
            thumbnail_path: Path for thumbnail
            
        Returns:
            bool: Success status
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                thumbnail_size = getattr(settings, 'MEDIA_THUMBNAIL_SIZE', (300, 300))
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                return True
                
        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
            return False
    
    @staticmethod
    def get_image_metadata(image_path: str) -> dict:
        """
        Extract image metadata.
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': os.path.getsize(image_path)
                }
        except Exception:
            return {}
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """
        Validate image file integrity.
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False