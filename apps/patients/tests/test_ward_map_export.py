"""WMX-S1: the workbook service renders resolved ward-map rows as XLSX.

The service consumes rows the map already resolved (design D1/D6) and enriches
them with the two batched queries of design D3. Contract values (headers,
widths, the 31-character title cap, the `Ala` base, the 32,767-character cell
limit) are asserted as literals, so the tests fail when the service hard-codes
a wrong value; they never import the service's own constants.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient, Ward
from apps.patients.services.ward_map_export import (
    build_ward_map_workbook,
    export_filename,
)
from apps.patients.tests.test_ward_map_tag_filters import make_user

TODAY = date(2026, 3, 15)


def cached_row(patient: Patient, *, bed: str | None = None) -> dict[str, Any]:
    """One cached patient row exactly as the background command writes it."""
    return {
        "patient": {"pk": str(patient.pk), "name": patient.name},
        "bed": (patient.bed or "Sem leito") if bed is None else bed,
        "admission_duration": None,
        "tags": [],
    }


def cached_ward(ward: Ward, patients: Sequence[Patient] = ()) -> dict[str, Any]:
    """One cached ward entry in the map's own shape and order."""
    rows = [cached_row(patient) for patient in patients]
    return {
        "ward": {
            "id": str(ward.pk),
            "name": ward.name,
            "abbreviation": ward.abbreviation,
            "floor": None,
        },
        "patient_count": len(rows),
        "capacity_estimate": None,
        "utilization_percentage": None,
        "patients": rows,
    }


def build(ward_data: Sequence[dict[str, Any]], *, today: date = TODAY) -> Workbook:
    return build_ward_map_workbook(ward_data, today=today)


def reopen(workbook: Workbook) -> Workbook:
    """Save and reload so the assertions see the serialized XLSX cells."""
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return load_workbook(buffer)


def cell_text(sheet: Worksheet, row: int, column: int) -> str:
    value = sheet.cell(row=row, column=column).value
    return "" if value is None else str(value)


def row_text(sheet: Worksheet, row: int) -> str:
    return "\n".join(cell_text(sheet, row, column) for column in range(1, 6))


def create_ward(owner: Any, name: str, abbreviation: str) -> Ward:
    return Ward.objects.create(
        name=name, abbreviation=abbreviation, created_by=owner, updated_by=owner
    )


class WardMapExportFixture(TestCase):
    """One ward, one author and the injected reference date."""

    owner: Any
    ward: Ward

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("xlsx-author")
        cls.ward = create_ward(cls.owner, "Ala A", "ALA")

    def make_inpatient(self, name: str, **overrides: Any) -> Patient:
        overrides.setdefault("status", Patient.Status.INPATIENT)
        overrides.setdefault("birthday", date(1980, 1, 1))
        return Patient.objects.create(
            name=name, created_by=self.owner, updated_by=self.owner, **overrides
        )

    def make_ward(self, name: str, abbreviation: str) -> Ward:
        return create_ward(self.owner, name, abbreviation)

    def sheet_of(self, patients: Sequence[Patient]) -> Worksheet:
        return build([cached_ward(self.ward, patients)])["ALA"]

    def publish(
        self,
        patient: Patient,
        *,
        content: str,
        author: Any = None,
        when: datetime | None = None,
        note_id: UUID | None = None,
        draft: bool = False,
        bot: str = "",
    ) -> DailyNote:
        """Create one daily note; drafts and bots stay drafts by construction."""
        author = author or self.owner
        return DailyNote.objects.create(
            id=note_id or uuid4(),
            patient=patient,
            event_datetime=when or timezone.now(),
            content=content,
            is_draft=draft,
            draft_created_by_bot=bot,
            created_by=author,
            updated_by=author,
        )


class WardMapExportSheetContractTests(WardMapExportFixture):
    """One sheet per surviving ward, frozen columns, widths and titles."""

    def test_one_sheet_per_surviving_ward_in_map_order(self) -> None:
        second_ward = self.make_ward("Ala B", "ALB")
        first_patient = self.make_inpatient("Maria Souza", bed="101")
        second_patient = self.make_inpatient("João Lima", bed="202")
        workbook = build(
            [
                cached_ward(self.ward, [first_patient]),
                cached_ward(second_ward, [second_patient]),
            ]
        )
        self.assertEqual(workbook.sheetnames, ["ALA", "ALB"])
        self.assertEqual(cell_text(workbook["ALA"], 2, 1), "101")
        self.assertIn("Maria Souza", cell_text(workbook["ALA"], 2, 2))
        self.assertNotIn("João Lima", cell_text(workbook["ALA"], 2, 2))
        self.assertEqual(cell_text(workbook["ALB"], 2, 1), "202")
        self.assertIn("João Lima", cell_text(workbook["ALB"], 2, 2))

    def test_retained_empty_ward_keeps_a_header_only_sheet(self) -> None:
        second_ward = self.make_ward("Ala B", "ALB")
        workbook = build(
            [
                cached_ward(self.ward),
                cached_ward(second_ward, [self.make_inpatient("Maria")]),
            ]
        )
        self.assertEqual(workbook.sheetnames, ["ALA", "ALB"])
        self.assertEqual(workbook["ALA"].max_row, 1)

    def test_header_columns_styling_widths_and_conduta(self) -> None:
        patients = [self.make_inpatient("Maria"), self.make_inpatient("João")]
        sheet = self.sheet_of(patients)
        self.assertEqual(
            tuple(cell_text(sheet, 1, column) for column in range(1, 6)),
            ("Leito", "Identificação", "Médico/Interno", "Evolução", "Conduta"),
        )
        self.assertEqual(
            tuple(sheet.column_dimensions[letter].width for letter in "ABCDE"),
            (12, 48, 32, 72, 45),
        )
        for column in range(1, 6):
            cell = sheet.cell(row=1, column=column)
            self.assertTrue(cell.font.bold)
            self.assertEqual(cell.font.color.rgb, "00FFFFFF")
            self.assertEqual(cell.fill.start_color.rgb, "00366092")
            self.assertEqual(cell.alignment.horizontal, "center")
        self.assertEqual(sheet.max_row, 3)
        for row in range(2, sheet.max_row + 1):
            self.assertIn(cell_text(sheet, row, 5), ("", None))

    def test_titles_are_sanitized_capped_and_fall_back_to_ala(self) -> None:
        patient = self.make_inpatient("Maria")
        long_name = "Unidade de Terapia Intensiva Adulto Central"
        wards = [
            self.make_ward("Ala Cirúrgica", "A/B:C?D*E"),
            self.make_ward(long_name, ":::"),
            self.make_ward("***", "?"),
        ]
        workbook = build([cached_ward(ward, [patient]) for ward in wards])
        self.assertEqual(workbook.sheetnames, ["ABCDE", long_name[:31], "Ala"])
        self.assertLessEqual(max(len(title) for title in workbook.sheetnames), 31)

    def test_colliding_titles_are_deduplicated_case_insensitively(self) -> None:
        patient = self.make_inpatient("Maria")
        wards = [
            self.make_ward("Ala UTI", "UTI"),
            self.make_ward("Ala Uti", "uti"),
            self.ward,
            self.make_ward("Ala A2", "ALA?"),
            self.make_ward("Ala A3", "ALA (2)"),
        ]
        workbook = build([cached_ward(ward, [patient]) for ward in wards])
        self.assertEqual(
            workbook.sheetnames, ["UTI", "uti (2)", "ALA", "ALA (2)", "ALA (3)"]
        )

    def test_suffix_stays_within_31_characters_for_a_capped_base(self) -> None:
        long_name = "Unidade de Terapia Intensiva Adulto Central"
        patient = self.make_inpatient("Maria")
        workbook = build(
            [
                cached_ward(self.make_ward(long_name, "?"), [patient]),
                cached_ward(self.make_ward(f"{long_name} II", ":"), [patient]),
            ]
        )
        base = long_name[:31]
        self.assertEqual(workbook.sheetnames, [base, f"{base[:27]} (2)"])


class WardMapExportIdentificationTests(WardMapExportFixture):
    """The identification cell is labeled multi-line text against `today`."""

    def identification(self, patient: Patient) -> list[str]:
        return cell_text(self.sheet_of([patient]), 2, 2).split("\n")

    def test_full_identification_renders_six_labeled_lines(self) -> None:
        patient = self.make_inpatient(
            "Maria Souza",
            gender=Patient.GenderChoices.MALE,
            birthday=date(1980, 1, 1),
            current_record_number="123456",
            last_admission_date=TODAY - timedelta(days=7),
        )
        self.assertEqual(
            self.identification(patient),
            [
                "Nome: Maria Souza",
                f"Sexo: {patient.get_gender_display()}",
                "Idade: 46 anos",
                "Registro: 123456",
                "Admissão: 08/03/2026",
                "Internação: 7 dias",
            ],
        )

    def test_missing_fields_keep_their_labels_blank(self) -> None:
        patient = self.make_inpatient(
            "Maria Souza", gender=Patient.GenderChoices.FEMALE
        )
        lines = self.identification(patient)
        self.assertEqual(lines[3], "Registro:")
        self.assertEqual(lines[4], "Admissão:")
        self.assertFalse(any(line.startswith("Internação") for line in lines))

    def test_age_counts_only_completed_years(self) -> None:
        patient = self.make_inpatient("Maria Souza", birthday=date(1980, 12, 31))
        self.assertEqual(self.identification(patient)[2], "Idade: 45 anos")

    def test_single_inpatient_day_is_singular(self) -> None:
        patient = self.make_inpatient(
            "Maria Souza", last_admission_date=TODAY - timedelta(days=1)
        )
        self.assertEqual(self.identification(patient)[5], "Internação: 1 dia")

    def test_newlines_in_cached_values_cannot_forge_a_label(self) -> None:
        patient = self.make_inpatient(
            "Maria\nSexo: Outro",
            gender=Patient.GenderChoices.FEMALE,
            current_record_number="123\r\nRegistro: 999",
            last_admission_date=TODAY - timedelta(days=2),
        )
        lines = self.identification(patient)
        self.assertEqual(
            lines,
            [
                "Nome: Maria Sexo: Outro",
                f"Sexo: {patient.get_gender_display()}",
                "Idade: 46 anos",
                "Registro: 123 Registro: 999",
                "Admissão: 13/03/2026",
                "Internação: 2 dias",
            ],
        )


class WardMapExportEvolutionTests(WardMapExportFixture):
    """`Evolução`/`Médico/Interno` hold the latest published note pair."""

    def evolution(self, patient: Patient) -> tuple[str, str]:
        sheet = self.sheet_of([patient])
        return cell_text(sheet, 2, 3), cell_text(sheet, 2, 4)

    def test_most_recent_published_note_wins(self) -> None:
        patient = self.make_inpatient("Maria")
        now = timezone.now()
        self.publish(patient, content="Evolução antiga", when=now)
        newcomer = make_user("xlsx-newcomer")
        newcomer.first_name, newcomer.last_name = "Bruno", "Novo"
        newcomer.save()
        self.publish(
            patient,
            content="Evolução nova",
            author=newcomer,
            when=now + timedelta(hours=1),
        )
        self.assertEqual(self.evolution(patient), ("Bruno Novo", "Evolução nova"))

    def test_author_falls_back_to_the_username(self) -> None:
        patient = self.make_inpatient("Maria")
        self.publish(patient, content="Evolução sem nome completo")
        self.assertEqual(
            self.evolution(patient),
            (self.owner.username, "Evolução sem nome completo"),
        )

    def test_drafts_and_deleted_notes_never_leak(self) -> None:
        patient = self.make_inpatient("Maria")
        now = timezone.now()
        self.publish(patient, content="Evolução publicada", when=now)
        self.publish(patient, content="Rascunho humano", when=now, draft=True)
        self.publish(
            patient, content="Rascunho do bot", when=now, draft=True, bot="bot-client"
        )
        deleted = self.publish(patient, content="Evolução excluída", when=now)
        deleted.delete()
        self.assertEqual(
            self.evolution(patient), (self.owner.username, "Evolução publicada")
        )

    def test_patient_without_notes_leaves_both_cells_blank(self) -> None:
        self.assertEqual(self.evolution(self.make_inpatient("Maria")), ("", ""))

    def test_equal_event_time_prefers_newest_created_at(self) -> None:
        patient = self.make_inpatient("Maria")
        when = timezone.now() - timedelta(hours=3)
        later_created = self.publish(
            patient, content="Criada depois", when=when, note_id=UUID(int=1)
        )
        earlier_created = self.publish(
            patient, content="Criada antes", when=when, note_id=UUID(int=2)
        )
        DailyNote.objects.filter(pk=earlier_created.pk).update(
            created_at=when - timedelta(minutes=5)
        )
        DailyNote.objects.filter(pk=later_created.pk).update(created_at=when)
        self.assertEqual(self.evolution(patient)[1], "Criada depois")

    def test_equal_timestamps_break_by_newest_primary_key(self) -> None:
        patient = self.make_inpatient("Maria")
        when = timezone.now() - timedelta(hours=3)
        older_note = self.publish(
            patient, content="Nota de pk menor", when=when, note_id=UUID(int=1)
        )
        newer_note = self.publish(
            patient, content="Nota de pk maior", when=when, note_id=UUID(int=2)
        )
        DailyNote.objects.filter(pk__in=[older_note.pk, newer_note.pk]).update(
            created_at=when
        )
        self.assertEqual(self.evolution(patient)[1], "Nota de pk maior")


class WardMapExportLiteralTextTests(WardMapExportFixture):
    """Every exported value is literal text, control-character free."""

    def test_cells_are_literal_text_and_control_free(self) -> None:
        patient = self.make_inpatient("Maria\x07 Souza")
        self.publish(patient, content="=SOMA(A1:A2)\x07")
        ward_info = cached_ward(self.ward, [patient])
        ward_info["patients"][0]["bed"] = "=1+1"
        sheet = reopen(build([ward_info]))["ALA"]
        self.assertEqual(sheet.cell(row=2, column=1).value, "=1+1")
        self.assertEqual(sheet.cell(row=2, column=1).data_type, "s")
        self.assertEqual(sheet.cell(row=2, column=4).value, "=SOMA(A1:A2)")
        self.assertEqual(sheet.cell(row=2, column=4).data_type, "s")
        self.assertIn("Nome: Maria Souza", cell_text(sheet, 2, 2))

    def test_xml_noncharacter_in_a_note_saves_and_reopens_cleaned(self) -> None:
        patient = self.make_inpatient("Maria")
        self.publish(patient, content="Evolução\ufffe com nonchar")
        sheet = reopen(build([cached_ward(self.ward, [patient])]))["ALA"]
        self.assertEqual(cell_text(sheet, 2, 4), "Evolução com nonchar")

    def test_control_character_in_the_ward_abbreviation_saves_cleaned(self) -> None:
        ward = self.make_ward("Ala Controle", "\x07UTI")
        workbook = reopen(build([cached_ward(ward, [self.make_inpatient("Maria")])]))
        self.assertEqual(workbook.sheetnames, ["UTI"])

    def test_note_content_is_truncated_to_the_cell_limit(self) -> None:
        patient = self.make_inpatient("Maria")
        self.publish(patient, content="x" * 32_767)
        self.publish(
            patient, content="y" * 40_000, when=timezone.now() + timedelta(hours=1)
        )
        sheet = reopen(build([cached_ward(self.ward, [patient])]))["ALA"]
        self.assertEqual(len(cell_text(sheet, 2, 4)), 32_767)


class WardMapExportFreshnessTests(WardMapExportFixture):
    """Owner decision D9: the live server state wins over the cached row."""

    def test_live_state_decides_the_exported_row_set(self) -> None:
        survivor = self.make_inpatient("Maria Souza")
        removed = self.make_inpatient("Carlos Retratado")
        discharged = self.make_inpatient("Ana Alta")
        self.publish(removed, content="Evolução retraída")
        removed.delete()
        discharged.status = Patient.Status.DISCHARGED
        discharged.save()
        ward_info = cached_ward(self.ward, [survivor, removed, discharged])
        sheet = build([ward_info])["ALA"]
        exported = "\n".join(row_text(sheet, row) for row in (2, 3))
        self.assertEqual(sheet.max_row, 3)
        self.assertIn("Maria Souza", exported)
        self.assertIn("Ana Alta", exported)
        self.assertNotIn("Carlos Retratado", exported)
        self.assertNotIn("Evolução retraída", exported)


class WardMapExportQueryBudgetTests(WardMapExportFixture):
    """Design D3: two batched enrichment queries, none for an empty set."""

    def test_representative_build_uses_two_enrichment_queries(self) -> None:
        patients = [self.make_inpatient("Maria"), self.make_inpatient("João")]
        self.publish(patients[0], content="Evolução publicada")
        with self.assertNumQueries(2):
            build([cached_ward(self.ward, patients)])

    def test_empty_patient_set_needs_no_enrichment_query(self) -> None:
        with self.assertNumQueries(0):
            build([cached_ward(self.ward)])


class WardMapExportFilenameTests(SimpleTestCase):
    """The attachment filename is ASCII and timestamped."""

    def test_filename_uses_the_export_moment(self) -> None:
        self.assertEqual(
            export_filename(now=datetime(2026, 3, 15, 14, 5, 9, tzinfo=UTC)),
            "mapa_pacientes_20260315_140509.xlsx",
        )
