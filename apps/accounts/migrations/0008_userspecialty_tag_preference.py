from collections.abc import Sequence
from typing import ClassVar

import django.db.models.deletion
from django.db import migrations, models
from django.db.migrations.operations.base import Operation


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("accounts", "0007_medicalspecialty_principal_tag"),
        ("patients", "0005_allowedtag_lifecycle_responsibility"),
    ]

    operations: ClassVar[Sequence[Operation]] = [
        migrations.CreateModel(
            name="UserSpecialtyTagPreference",
            fields=[
                (
                    "membership",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="tag_preference",
                        serialize=False,
                        to="accounts.userspecialty",
                        verbose_name="Vínculo com a especialidade",
                    ),
                ),
                (
                    "mode",
                    models.CharField(
                        choices=[("any", "Qualquer tag"), ("all", "Todas as tags")],
                        default="any",
                        max_length=8,
                        verbose_name="Modo de correspondência",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Criada em"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Atualizada em"),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        blank=True,
                        related_name="specialty_preferences",
                        to="patients.allowedtag",
                        verbose_name="Tags selecionadas",
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferência de Tags da Especialidade",
                "verbose_name_plural": "Preferências de Tags das Especialidades",
            },
        ),
        migrations.AddConstraint(
            model_name="userspecialtytagpreference",
            constraint=models.CheckConstraint(
                condition=models.Q(("mode__in", ["any", "all"])),
                name="userspecialtytagpreference_mode_valid",
            ),
        ),
    ]
