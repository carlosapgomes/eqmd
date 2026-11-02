"""Stable catalogue references attached to patient tag timeline events."""

from __future__ import annotations

from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models


class TagEventReference(models.Model):
    """Action-time catalogue identity and snapshot for one tag audit action.

    A reference keeps the catalogue identity of the acted-on tag independent of
    the legacy event snapshot fields. Renames, responsibility transfers,
    archival and association removal never rewrite it, so a requester-aware
    reader can resolve today's visibility from stable data.
    """

    class Action(models.TextChoices):
        ADDED = "added", "Adicionada"
        REMOVED = "removed", "Removida"

    event: ClassVar[models.ForeignKey] = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="tag_references",
        verbose_name="Evento",
    )
    tag: ClassVar[models.ForeignKey] = models.ForeignKey(
        "patients.AllowedTag",
        on_delete=models.PROTECT,
        related_name="event_references",
        verbose_name="Tag do catálogo",
        help_text="Identidade estável da tag no momento da ação",
    )
    action: ClassVar[models.CharField] = models.CharField(
        max_length=16, choices=Action.choices, verbose_name="Ação"
    )
    tag_name: ClassVar[models.CharField] = models.CharField(
        max_length=100, verbose_name="Nome na ação"
    )
    tag_color: ClassVar[models.CharField] = models.CharField(
        max_length=7, verbose_name="Cor na ação"
    )
    tag_notes: ClassVar[models.TextField] = models.TextField(
        blank=True, verbose_name="Notas na ação"
    )
    tag_visibility: ClassVar[models.CharField] = models.CharField(
        max_length=16, verbose_name="Visibilidade na ação"
    )
    specialty: ClassVar[models.ForeignKey] = models.ForeignKey(
        "accounts.MedicalSpecialty",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tag_event_references",
        verbose_name="Equipe na ação",
    )
    specialty_abbreviation: ClassVar[models.CharField] = models.CharField(
        max_length=10, blank=True, verbose_name="Sigla da equipe na ação"
    )
    created_at: ClassVar[models.DateTimeField] = models.DateTimeField(
        auto_now_add=True, verbose_name="Criada em"
    )

    class Meta:
        db_table = "events_tageventreference"
        ordering: ClassVar[list[str]] = ["event", "pk"]
        verbose_name = "Referência de Tag em Evento"
        verbose_name_plural = "Referências de Tag em Eventos"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["event", "tag"],
                name="events_tageventreference_unique_event_tag",
            )
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["tag", "event"]),
        ]

    def __str__(self) -> str:
        return f"{self.action}: {self.tag_name}"

    def save(self, *args: object, **kwargs: object) -> None:
        """Reject updates: action-time audit references are append-only."""
        if self.pk is not None:
            raise ValidationError(
                "Tag event references are immutable and cannot be changed."
            )
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        """Reject deletion: references must survive association removal."""
        raise ValidationError(
            "Tag event references are immutable and cannot be deleted."
        )
