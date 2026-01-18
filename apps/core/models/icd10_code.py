"""
ICD-10 (CID) codes model for diagnoses.
Stores codes and descriptions for search and selection.
"""

import uuid
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Icd10Code(models.Model):
    """
    ICD-10 (CID) diagnosis codes.

    Stores the full ICD-10 code list with full-text search support.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Codigo ICD-10",
        help_text="Codigo oficial do CID-10 (ex: A00)"
    )
    description = models.TextField(
        verbose_name="Descricao",
        help_text="Descricao completa do CID-10"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Codigo disponivel para uso"
    )

    search_vector = SearchVectorField(
        null=True,
        blank=True,
        help_text="Campo de busca textual (preenchido automaticamente)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    objects = models.Manager()

    class Meta:
        db_table = 'core_icd10code'
        ordering = ['code']
        verbose_name = "Codigo ICD-10"
        verbose_name_plural = "Codigos ICD-10"

        indexes = [
            models.Index(fields=['is_active'], name='icd10code_active_idx'),
            models.Index(fields=['code'], name='icd10code_code_idx'),
            GinIndex(fields=['search_vector'], name='icd10code_search_idx'),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=r'^[0-9A-Za-z]{2,20}$'),
                name='icd10code_code_format'
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.description[:50]}{'...' if len(self.description) > 50 else ''}"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def short_description(self):
        if len(self.description) <= 100:
            return self.description
        return self.description[:97] + "..."

    def get_display_text(self):
        return f"{self.code} - {self.short_description}"

    @classmethod
    def active(cls):
        return cls.objects.filter(is_active=True)

    @classmethod
    def search(cls, query):
        if not query:
            return cls.objects.none()

        from django.db import connection
        if connection.vendor != 'postgresql':
            return cls.simple_search(query)

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
