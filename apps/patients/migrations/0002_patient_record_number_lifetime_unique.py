"""Lifetime global uniqueness for canonical patient record numbers.

Slice 004: reserves ``Lower(Trim(record_number))`` across every retained
``PatientRecordNumber`` row - current, historical, and soft-deleted patients
alike. A read-only preflight aborts the migration before any schema change
while canonical collisions remain, reporting aggregate counts only.
"""

from typing import ClassVar

from django.db import migrations, models
from django.db.models import Count, Sum
from django.db.models.functions import Lower, Trim


def ensure_no_canonical_collisions(apps, schema_editor) -> None:
    """Abort before schema modification when canonical collisions remain.

    Read-only aggregation: counts collision groups and involved rows without
    selecting, updating, deleting, or merging any record value.
    """
    record_model = apps.get_model("patients", "PatientRecordNumber")
    collisions = (
        record_model.objects.annotate(canonical=Lower(Trim("record_number")))
        .values("canonical")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    group_count = collisions.count()
    row_total = collisions.aggregate(involved=Sum("row_count"))["involved"]
    if group_count:
        raise RuntimeError(
            f"{group_count} canonical record-number collision group(s) "
            f"involving {row_total or 0} row(s). Consolidate colliding "
            "record numbers before applying this migration."
        )


class Migration(migrations.Migration):
    """Preflight (abort on collisions), then the functional unique constraint."""

    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("patients", "0001_initial"),
    ]

    operations: ClassVar[list[migrations.RunPython | migrations.AddConstraint]] = [
        migrations.RunPython(
            ensure_no_canonical_collisions,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            "PatientRecordNumber",
            models.UniqueConstraint(
                Lower(Trim("record_number")),
                name="unique_patient_record_number_lifetime",
            ),
        ),
    ]
