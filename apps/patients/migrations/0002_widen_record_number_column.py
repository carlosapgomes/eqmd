"""Widen record_number so consolidation markers fit their originals.

Correction 2: the amended per-row void marker
``<original>::voided::<plan_ref>:<pk-token>`` costs 33 fixed characters
plus ``len(plan_ref)`` over the original value. Live collisions include
18-character originals, so no marker fits ``VarChar(50)``. ``VarChar(120)``
is a metadata-only change on PostgreSQL; human input stays capped at 50
by the explicit form fields and the service validator.
"""

from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    """Metadata-only column widening (the reverse restores the 50 limit)."""

    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("patients", "0001_initial"),
    ]

    operations: ClassVar[list[migrations.AlterField]] = [
        migrations.AlterField(
            model_name="patientrecordnumber",
            name="record_number",
            field=models.CharField(
                max_length=120,
                verbose_name="Número do Prontuário",
                help_text="Número do prontuário do paciente no hospital",
            ),
        ),
    ]
