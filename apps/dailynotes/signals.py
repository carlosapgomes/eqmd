import re
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from django.db.models import Value
from django.contrib.postgres.search import SearchVectorField
from .models import DailyNote

def sanitize_content_for_search(content):
    """
    Sanitize content to remove characters that cause PostgreSQL text search issues.
    
    Args:
        content: Raw text content
        
    Returns:
        Sanitized content safe for PostgreSQL text search
    """
    if not content:
        return ""
    
    # Remove or replace problematic characters that cause "unrecognized token" errors
    sanitized = content
    
    # Replace colons with spaces (main issue)
    sanitized = sanitized.replace(':', ' ')
    
    # Remove other potentially problematic characters
    # Keep only letters, numbers, spaces, and common punctuation
    sanitized = re.sub(r'[^\w\s\.\,\!\?\(\)\-]', ' ', sanitized)
    
    # Clean up multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized

@receiver(post_save, sender=DailyNote)
def update_search_vector(sender, instance, created, **kwargs):
    """
    Update search vector when DailyNote is saved.
    """
    # Avoid recursion by checking if search_vector was already updated
    if hasattr(instance, '_search_vector_updated'):
        return

    try:
        # Sanitize content before creating search vector
        sanitized_content = sanitize_content_for_search(instance.content)
        
        # Update the search vector with sanitized content
        sender.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector(Value(sanitized_content), config='portuguese')
        )
    except Exception as e:
        # Log the error but don't fail the save operation
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to update search vector for DailyNote {instance.pk}: {e}")

    # Mark as updated to avoid recursion
    instance._search_vector_updated = True