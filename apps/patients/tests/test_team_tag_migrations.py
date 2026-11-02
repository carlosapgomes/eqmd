"""S2 additive migration tests: preservation, backfill and schema states."""

from __future__ import annotations

import threading
from io import StringIO
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.models import MedicalSpecialty
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Tag

GLOBAL_NAME_INDEX = "patients_allowedtag_global_name_unique"
BEFORE = [
    ("patients", "0003_patient_record_number_lifetime_unique"),
    ("accounts", "0006_userspecialty_team_membership"),
]
AFTER = [
    ("patients", "0005_allowedtag_lifecycle_responsibility"),
    ("accounts", "0007_medicalspecialty_principal_tag"),
]
S3_BEFORE = [
    ("patients", "0004_allowedtag_catalogue_governance"),
    ("accounts", "0007_medicalspecialty_principal_tag"),
]
S3_AFTER = [
    ("patients", "0005_allowedtag_lifecycle_responsibility"),
    ("accounts", "0007_medicalspecialty_principal_tag"),
]


def make_tag(actor: Any, name: str, **kwargs: object) -> AllowedTag:
    """Create a catalogue row without form validation (database path)."""
    return AllowedTag.objects.create(
        name=name, created_by=actor, updated_by=actor, **kwargs
    )


def migrate_to(targets: list[tuple[str, str]]) -> Any:
    """Migrate only the catalogue apps and return the historical app registry."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


class AdditiveCatalogueMigrationTests(TransactionTestCase):
    """R1: existing rows survive and backfill to public/custom global."""

    def test_legacy_row_identity_association_and_history_are_preserved(self) -> None:
        legacy: dict[str, Any] = {}
        try:
            old_apps = migrate_to(BEFORE)
            legacy = self._create_legacy_rows(old_apps)
            preflight_before = self._preflight()
        finally:
            migrate_to(AFTER)

        tag = AllowedTag.all_objects.get(pk=legacy["tag_pk"])
        self.assertEqual(tag.name, "Legado")
        self.assertEqual(tag.created_by_id, legacy["user_pk"])
        self.assertEqual(tag.updated_by_id, legacy["user_pk"])
        self.assertEqual(tag.origin, AllowedTag.Origin.CUSTOM)
        self.assertEqual(tag.visibility, AllowedTag.Visibility.PUBLIC)
        self.assertIsNone(tag.specialty_id)
        self.assertIn("schema=legacy", preflight_before)

        association = Tag.objects.get(pk=legacy["association_pk"])
        self.assertEqual(association.allowed_tag_id, tag.pk)
        self.assertEqual(association.patient_id, legacy["patient_pk"])

        history_model = AllowedTag.history.model
        self.assertTrue(history_model.objects.filter(pk=legacy["history_pk"]).exists())
        specialty = MedicalSpecialty.objects.get(pk=legacy["specialty_pk"])
        self.assertIsNone(specialty.principal_tag_id)

        self.assertEqual(
            AllowedTag.all_objects.filter(specialty__isnull=False).count(), 0
        )
        self.assertIn("schema=additive", self._preflight())

    def test_preflight_runs_before_and_after_additive_fields(self) -> None:
        try:
            migrate_to(BEFORE)
            before = self._preflight()
            self.assertIn("schema=legacy", before)
            self.assertIn("read_only=yes", before)
        finally:
            migrate_to(AFTER)
        after = self._preflight()
        self.assertIn("schema=additive", after)
        self.assertIn("normalized_name_collisions=", after)

    def _create_legacy_rows(self, old_apps: Any) -> dict[str, Any]:
        user_model = old_apps.get_model("accounts", "EqmdCustomUser")
        user = user_model.objects.create(username="legacy-owner", password="x")
        specialty_model = old_apps.get_model("accounts", "MedicalSpecialty")
        specialty = specialty_model.objects.create(
            name="Equipe Legada", abbreviation="LEG"
        )
        tag_model = old_apps.get_model("patients", "AllowedTag")
        tag = tag_model.objects.create(
            name="Legado",
            description="legacy",
            color="#101010",
            is_active=True,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        patient_model = old_apps.get_model("patients", "Patient")
        patient = patient_model.objects.create(
            name="Paciente Legado",
            birthday="1980-01-01",
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        association_model = old_apps.get_model("patients", "Tag")
        association = association_model.objects.create(
            allowed_tag_id=tag.pk,
            patient_id=patient.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        history_model = old_apps.get_model("patients", "HistoricalAllowedTag")
        history = history_model.objects.create(
            id=tag.pk,
            name="Legado",
            description="legacy",
            color="#101010",
            is_active=True,
            created_by_id=user.pk,
            updated_by_id=user.pk,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            history_date=timezone.now(),
            history_type="+",
            history_user_id=user.pk,
        )
        return {
            "user_pk": user.pk,
            "specialty_pk": specialty.pk,
            "tag_pk": tag.pk,
            "patient_pk": patient.pk,
            "association_pk": association.pk,
            "history_pk": history.pk,
        }

    def _preflight(self) -> str:
        output = StringIO()
        call_command("preflight_team_tags", stdout=output)
        return output.getvalue()


class CatalogueSchemaConstraintTests(TestCase):
    """R1/R2/R3: PostgreSQL constraints exist after the additive migration."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = create_navigation_user(
            username="schema-admin",
            email="schema@example.com",
            password="schema-pass",
        )

    def test_additive_columns_and_indexes_exist(self) -> None:
        columns = {
            field.name
            for field in AllowedTag._meta.get_fields()
            if getattr(field, "concrete", False)
        }
        self.assertTrue({"origin", "visibility", "specialty"} <= columns)
        self.assertIn(
            "principal_tag",
            {field.name for field in MedicalSpecialty._meta.get_fields()},
        )
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, AllowedTag._meta.db_table
            )
        self.assertIn("patients_allowedtag_global_name_unique", constraints)
        self.assertIn("patients_allowedtag_team_name_unique", constraints)
        self.assertIn("patients_allowedtag_restricted_requires_specialty", constraints)

    def test_archived_namespaced_name_still_occupied_in_database(self) -> None:
        specialty = MedicalSpecialty.objects.create(
            name="Equipe Arquivo", abbreviation="ARQ"
        )
        AllowedTag.all_objects.create(
            name="Arquivada",
            specialty=specialty,
            is_active=False,
            is_deleted=True,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(IntegrityError):
            AllowedTag.all_objects.create(
                name=" arquivada ",
                specialty=specialty,
                created_by=self.admin,
                updated_by=self.admin,
            )

    def test_principal_mapping_round_trips_in_database(self) -> None:
        specialty = MedicalSpecialty.objects.create(
            name="Equipe Principal", abbreviation="PRIN"
        )
        tag = AllowedTag.all_objects.create(
            name="Principal",
            specialty=specialty,
            created_by=self.admin,
            updated_by=self.admin,
        )
        MedicalSpecialty.objects.filter(pk=specialty.pk).update(principal_tag_id=tag.pk)
        specialty.refresh_from_db()
        self.assertEqual(specialty.principal_tag_id, tag.pk)


class NamespaceReservationTests(TestCase):
    """R2: normalized names reserved per namespace in every lifecycle state."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = create_navigation_user(
            username="namespace-admin",
            email="namespace@example.com",
            password="namespace-pass",
        )
        cls.cirger = MedicalSpecialty.objects.create(
            name="Equipe Namespace A", abbreviation="NSACIR"
        )
        cls.cardio = MedicalSpecialty.objects.create(
            name="Equipe Namespace B", abbreviation="NSBCAR"
        )

    def test_same_normalized_name_allowed_in_two_team_namespaces(self) -> None:
        first = make_tag(self.admin, "Reavaliar", specialty=self.cirger)
        second = make_tag(self.admin, "reavaliar", specialty=self.cardio)
        global_tag = make_tag(self.admin, " REAVALIAR ")
        self.assertEqual(
            {first.pk, second.pk, global_tag.pk},
            set(AllowedTag.all_objects.values_list("pk", flat=True)),
        )

    def test_team_namespace_duplicate_case_and_space_variant_rejected(self) -> None:
        make_tag(self.admin, "Reavaliar", specialty=self.cirger)
        duplicate = AllowedTag(
            name="  reavaliar  ",
            specialty=self.cirger,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_global_namespace_duplicate_rejected(self) -> None:
        make_tag(self.admin, "Prioridade")
        duplicate = AllowedTag(
            name="PRIORIDADE ",
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_archived_and_inactive_names_remain_reserved(self) -> None:
        archived = make_tag(
            self.admin,
            "Reavaliar",
            specialty=self.cirger,
            is_active=False,
            is_deleted=True,
        )
        self.assertFalse(AllowedTag.objects.filter(pk=archived.pk).exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_tag(self.admin, " reavaliar ", specialty=self.cirger)
        self.assertEqual(AllowedTag.all_objects.filter(name="Reavaliar").count(), 1)


class ConcurrentNamespaceConstraintTests(TransactionTestCase):
    """R2: PostgreSQL uniqueness survives concurrent creates."""

    def test_concurrent_same_name_in_one_namespace_allows_one_row(self) -> None:
        admin = create_navigation_user(
            username="race-admin",
            email="race@example.com",
            password="race-pass",
        )
        specialty = MedicalSpecialty.objects.create(
            name="Equipe Corrida", abbreviation="RACE"
        )
        barrier = threading.Barrier(2)
        outcomes: list[str] = []

        def worker() -> None:
            barrier.wait()
            try:
                with transaction.atomic():
                    AllowedTag.objects.create(
                        name="Corrida",
                        specialty_id=specialty.pk,
                        created_by_id=admin.pk,
                        updated_by_id=admin.pk,
                    )
                outcomes.append("created")
            except IntegrityError:
                outcomes.append("conflict")
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(sorted(outcomes), ["conflict", "created"])
        self.assertEqual(
            AllowedTag.all_objects.filter(
                specialty_id=specialty.pk, name="Corrida"
            ).count(),
            1,
        )


class PreflightCommandTests(TestCase):
    """R2/R3: read-only preflight across catalogue schema states."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = create_navigation_user(
            username="preflight-admin",
            email="preflight@example.com",
            password="preflight-pass",
        )
        cls.cirger = MedicalSpecialty.objects.create(
            name="Equipe Preflight", abbreviation="PREFL"
        )

    def test_preflight_reports_legacy_normalized_collisions(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP INDEX IF EXISTS "{GLOBAL_NAME_INDEX}"')
        make_tag(self.admin, "Legado")
        make_tag(self.admin, " legado ")
        output = StringIO()
        call_command("preflight_team_tags", stdout=output)
        report = output.getvalue()
        self.assertIn("normalized_name_collisions=1", report)
        self.assertIn("namespace=global", report)
        self.assertIn("schema=additive", report)

    def test_preflight_reports_invalid_principal_mapping(self) -> None:
        restricted = make_tag(
            self.admin,
            "Restrita",
            specialty=self.cirger,
            visibility=AllowedTag.Visibility.RESTRICTED,
        )
        MedicalSpecialty.objects.filter(pk=self.cirger.pk).update(
            principal_tag_id=restricted.pk
        )
        output = StringIO()
        call_command("preflight_team_tags", stdout=output)
        self.assertIn("invalid_principal_mappings=1", output.getvalue())

    def test_preflight_is_read_only(self) -> None:
        tag = make_tag(self.admin, "Legado", specialty=self.cirger)
        rows_before = AllowedTag.all_objects.count()
        history_before = AllowedTag.history.count()
        output = StringIO()
        call_command("preflight_team_tags", stdout=output)
        self.assertEqual(AllowedTag.all_objects.count(), rows_before)
        self.assertEqual(AllowedTag.history.count(), history_before)
        self.assertTrue(AllowedTag.all_objects.filter(pk=tag.pk).exists())
        self.assertIn("read_only=yes", output.getvalue())


class LifecycleMigrationPreservationTests(TransactionTestCase):
    """S3 R1: additive responsibility/lifecycle migration preserves identity."""

    def test_legacy_archived_row_is_normalized_without_fabricated_history(
        self,
    ) -> None:
        legacy: dict[str, Any] = {}
        try:
            old_apps = migrate_to(S3_BEFORE)
            legacy = self._create_legacy_rows(old_apps)
        finally:
            migrate_to(S3_AFTER)

        tag = AllowedTag.all_objects.get(pk=legacy["tag_pk"])
        self.assertEqual(tag.name, "Arquivada Legada")
        self.assertEqual(tag.created_by_id, legacy["user_pk"])
        self.assertTrue(tag.is_deleted)
        self.assertFalse(tag.is_active)
        self.assertEqual(tag.specialty_id, legacy["specialty_pk"])
        self.assertIsNone(tag.responsible_user_id)
        self.assertIsNone(tag.deactivated_by_id)
        self.assertIsNone(tag.restored_by_id)

        association = Tag.objects.get(pk=legacy["association_pk"])
        self.assertEqual(association.allowed_tag_id, tag.pk)
        self.assertEqual(association.patient_id, legacy["patient_pk"])

        principal = AllowedTag.all_objects.get(pk=legacy["principal_pk"])
        specialty = MedicalSpecialty.objects.get(pk=legacy["specialty_pk"])
        self.assertEqual(specialty.principal_tag_id, principal.pk)

        from apps.patients.models import AllowedTagTransition

        self.assertEqual(AllowedTagTransition.objects.count(), 0)

    def test_lifecycle_columns_constraint_and_history_table_exist(self) -> None:
        columns = {
            field.name
            for field in AllowedTag._meta.get_fields()
            if getattr(field, "concrete", False)
        }
        self.assertTrue(
            {
                "responsible_user",
                "deactivated_at",
                "deactivated_by",
                "reactivated_at",
                "reactivated_by",
                "restored_at",
                "restored_by",
            }
            <= columns
        )
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, AllowedTag._meta.db_table
            )
        self.assertIn("patients_allowedtag_archived_requires_inactive", constraints)
        from apps.patients.models import AllowedTagTransition

        self.assertEqual(
            AllowedTagTransition._meta.db_table, "patients_allowedtagtransition"
        )

    def _create_legacy_rows(self, old_apps: Any) -> dict[str, Any]:
        user_model = old_apps.get_model("accounts", "EqmdCustomUser")
        user = user_model.objects.create(username="legacy-lifecycle", password="x")
        specialty_model = old_apps.get_model("accounts", "MedicalSpecialty")
        specialty = specialty_model.objects.create(
            name="Equipe Legada S3", abbreviation="LEGS3"
        )
        tag_model = old_apps.get_model("patients", "AllowedTag")
        tag = tag_model.objects.create(
            name="Arquivada Legada",
            description="legacy archived",
            color="#202020",
            is_active=True,
            is_deleted=True,
            specialty_id=specialty.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        principal = tag_model.objects.create(
            name="Principal Legada",
            description="legacy principal",
            color="#303030",
            is_active=True,
            specialty_id=specialty.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        specialty_model.objects.filter(pk=specialty.pk).update(
            principal_tag_id=principal.pk
        )
        patient_model = old_apps.get_model("patients", "Patient")
        patient = patient_model.objects.create(
            name="Paciente Legado S3",
            birthday="1980-01-01",
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        association_model = old_apps.get_model("patients", "Tag")
        association = association_model.objects.create(
            allowed_tag_id=tag.pk,
            patient_id=patient.pk,
            created_by_id=user.pk,
            updated_by_id=user.pk,
        )
        return {
            "user_pk": user.pk,
            "specialty_pk": specialty.pk,
            "tag_pk": tag.pk,
            "principal_pk": principal.pk,
            "patient_pk": patient.pk,
            "association_pk": association.pk,
        }
