"""
Medical procedures model for national forms (APAC/AIH).
Stores procedures and codes from national health system.
"""

import uuid
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class MedicalProcedure(models.Model):
    """
    National medical procedures and codes for APAC/AIH forms.
    
    Stores the complete national procedures table with full-text search
    capabilities for dynamic form field population.
    """

    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=20, 
        unique=True,
        verbose_name="Código do Procedimento",
        help_text="Código oficial do procedimento (ex: 0301010012)"
    )
    description = models.TextField(
        verbose_name="Descrição do Procedimento",
        help_text="Descrição completa do procedimento"
    )

    # Status and tracking
    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Procedimento disponível para uso"
    )
    
    # Full-text search field
    search_vector = SearchVectorField(
        null=True, 
        blank=True,
        help_text="Campo de busca textual (preenchido automaticamente)"
    )

    # Audit fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    # Custom manager
    objects = models.Manager()  # Default manager
    
    class Meta:
        db_table = 'core_medicalprocedure'
        ordering = ['code']
        verbose_name = "Procedimento Médico"
        verbose_name_plural = "Procedimentos Médicos"
        
        indexes = [
            # Standard indexes for common queries
            models.Index(fields=['is_active'], name='medicalprocedure_active_idx'),
            models.Index(fields=['code'], name='medicalprocedure_code_idx'),
            
            # Full-text search index
            GinIndex(fields=['search_vector'], name='medicalprocedure_search_idx'),
        ]
        
        constraints = [
            # Ensure code follows expected format (basic validation)
            models.CheckConstraint(
                condition=models.Q(code__regex=r'^[0-9A-Za-z]{4,20}$'),
                name='medicalprocedure_code_format'
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.description[:50]}{'...' if len(self.description) > 50 else ''}"

    def save(self, *args, **kwargs):
        """Override save to ensure code is uppercase and clean."""
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def short_description(self):
        """Return truncated description for UI display."""
        if len(self.description) <= 100:
            return self.description
        return self.description[:97] + "..."

    def get_display_text(self):
        """Get formatted text for form dropdowns and API responses."""
        return f"{self.code} - {self.short_description}"

    @classmethod
    def active(cls):
        """Return only active procedures."""
        return cls.objects.filter(is_active=True)

    @classmethod
    def search(cls, query):
        """
        Perform full-text search on procedures.
        
        Args:
            query (str): Search query
            
        Returns:
            QuerySet: Filtered procedures ordered by search rank
        """
        if not query:
            return cls.objects.none()

        # Use PostgreSQL full-text search on search_vector
        from django.contrib.postgres.search import SearchQuery, SearchRank
        
        search_query = SearchQuery(query)
        return (
            cls.active()
            .filter(search_vector=search_query)
            .annotate(rank=SearchRank('search_vector', search_query))
            .order_by('-rank', 'code')
        )

    @classmethod
    def simple_search(cls, query):
        """
        Simple search fallback using icontains for compatibility.
        
        Args:
            query (str): Search query
            
        Returns:
            QuerySet: Filtered procedures
        """
        if not query:
            return cls.objects.none()

        return (
            cls.active()
            .filter(
                models.Q(code__icontains=query) |
                models.Q(description__icontains=query)
            )
            .order_by('code')
        )