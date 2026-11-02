"""Read-only preflight for the namespaced tag catalogue (S2).

Runs against schema states before and after the additive S2 migrations by
introspecting database columns instead of assuming the new model fields.
It never writes, merges, renames or deletes catalogue rows.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import DatabaseError, connection
from django.db.models import Count, F, Q
from django.db.models.functions import Lower, Trim

from apps.accounts.models import MedicalSpecialty
from apps.patients.models import AllowedTag

TAG_TABLE = "patients_allowedtag"
SPECIALTY_TABLE = "accounts_medicalspecialty"
CLASSIFICATION_COLUMNS = frozenset({"origin", "visibility", "specialty_id"})


class Command(BaseCommand):
    """Report S2 catalogue hazards without changing any data."""

    help = (
        "Read-only preflight: normalized-name collisions, invalid "
        "associations and principal mappings."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        tag_columns = _table_columns(TAG_TABLE)
        specialty_columns = _table_columns(SPECIALTY_TABLE)
        has_classification = CLASSIFICATION_COLUMNS <= tag_columns
        has_principal = "principal_tag_id" in specialty_columns

        self.stdout.write(f"schema={'additive' if has_classification else 'legacy'}")
        detected = sorted(CLASSIFICATION_COLUMNS & tag_columns)
        self.stdout.write(f"fields={','.join(detected) if detected else 'none'}")

        collisions, details = self._name_collisions(has_classification)
        self.stdout.write(f"normalized_name_collisions={collisions}")
        for line in details:
            self.stdout.write(line)

        self._invalid_associations(has_classification, has_principal)
        self.stdout.write("legacy_event_resolution=deferred_s4")
        self.stdout.write("read_only=yes")

    def _name_collisions(self, has_specialty: bool) -> tuple[int, list[str]]:
        group_fields = ["canonical"]
        if has_specialty:
            group_fields.append("specialty_id")
        groups = (
            AllowedTag.all_objects.annotate(canonical=Lower(Trim("name")))
            .values(*group_fields)
            .annotate(row_count=Count("pk"))
            .filter(row_count__gt=1)
            .order_by(*group_fields)
        )
        details: list[str] = []
        total = 0
        for group in groups:
            total += 1
            namespace = "global"
            specialty_id = group.get("specialty_id")
            if specialty_id is not None:
                namespace = str(specialty_id)
            ids = _collision_ids(group["canonical"], specialty_id, has_specialty)
            details.append(
                "collision "
                f"namespace={namespace} canonical={group['canonical']!r} "
                f"rows={group['row_count']} ids={ids}"
            )
        return total, details

    def _invalid_associations(
        self, has_classification: bool, has_principal: bool
    ) -> None:
        if not has_classification:
            self.stdout.write("invalid_associations=not_checked_legacy_schema")
            return
        restricted_without_team = AllowedTag.all_objects.filter(
            visibility="restricted", specialty__isnull=True
        ).count()
        invalid_principals = 0
        if has_principal:
            invalid_principals = (
                MedicalSpecialty.objects.filter(principal_tag__isnull=False)
                .filter(
                    ~Q(principal_tag__visibility="public")
                    | ~Q(principal_tag__specialty_id=F("pk"))
                )
                .count()
            )
        total = restricted_without_team + invalid_principals
        self.stdout.write(f"invalid_associations={total}")
        self.stdout.write(
            f"invalid_restricted_without_specialty={restricted_without_team}"
        )
        if has_principal:
            self.stdout.write(f"invalid_principal_mappings={invalid_principals}")
        else:
            self.stdout.write("invalid_principal_mappings=not_checked_legacy_schema")


def _table_columns(table: str) -> set[str]:
    """Return the live database columns, tolerating a missing table."""
    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table)
    except DatabaseError:
        return set()
    return {column.name for column in description}


def _collision_ids(canonical: str, specialty_id: object, has_specialty: bool) -> str:
    """Return the catalogue ids in one collision group, read-only."""
    rows = AllowedTag.all_objects.annotate(canonical=Lower(Trim("name"))).filter(
        canonical=canonical
    )
    if has_specialty:
        rows = rows.filter(specialty_id=specialty_id)
    return ",".join(str(pk) for pk in rows.values_list("pk", flat=True))
