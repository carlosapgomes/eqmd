"""WMX-S2: the named endpoint exports the map's resolved result as XLSX.

The endpoint inherits the map's context resolution and its login and
permission gates (design D1), so every parity test compares the exported
rows with the rows the map itself renders for the same query string.
Contract values (the XLSX content type, the attachment filename pattern)
are asserted as literals, mirroring the WMX-S1 policy of never importing
the module's own constants.

Split plan if this module grows further (it passed the 300-line soft
limit): the constants, the row readers (``cell_text`` …
``exported_names``) and ``WardMapExportViewFixture`` are fixture seams
that can move to a shared ward-map-export fixture module, and each
behavior class (Access, Attachment, Ajax, Refusal, Parity) can become
its own ``test_ward_map_export_*`` module without changing a single
assertion.

WMX-S3 adds ``WardMapExportButtonTests`` here: the same fixtures render
the map page's button beside the endpoint it links to.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, Tag
from django.template import loader
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from apps.accounts.tests.helpers import create_navigation_user
from apps.core.models import WardMappingCache
from apps.patients.models import AllowedTag, Patient, Ward
from apps.patients.tests.test_ward_map_tag_filters import (
    assign,
    make_patient,
    make_tag,
    make_user,
    seed_warm_cache,
)
from apps.patients.views_ward_map_filters import WardMapFilterActionsView

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REFUSAL_CONTENT_TYPE = "text/plain; charset=utf-8"
REFUSAL_WORDING = "Nenhum paciente"
LOGIN_PATH = "/accounts/login/"
FILENAME_PATTERN = r'attachment; filename="(mapa_pacientes_\d{8}_\d{6}\.xlsx)"'
FILE_STAMP_FORMAT = "mapa_pacientes_%Y%m%d_%H%M%S.xlsx"
FIRST_DATA_ROW = 2
# One minute past the 20-minute staleness window the cache reader enforces.
CACHE_STALENESS = timedelta(minutes=21)
EXPORT_LABEL = "Exportar xlsx"
EXPORT_DISABLED_TITLE = "Nenhum paciente no resultado da busca"


def create_ward(owner: Any, name: str, abbreviation: str) -> Ward:
    """One ward row in the cache's own shape."""
    return Ward.objects.create(
        name=name, abbreviation=abbreviation, created_by=owner, updated_by=owner
    )


def cell_text(sheet: Worksheet, row: int, column: int) -> str:
    """Return one cell as text, the same reader the WMX-S1 tests use."""
    value = sheet.cell(row=row, column=column).value
    return "" if value is None else str(value)


def sheet_rows(sheet: Worksheet) -> list[tuple[str, str]]:
    """Return each data row as (bed, Nome line) in row order."""
    return [
        (cell_text(sheet, row, 1), cell_text(sheet, row, 2).split("\n")[0])
        for row in range(FIRST_DATA_ROW, sheet.max_row + 1)
    ]


def sheet_listings(workbook: Workbook) -> list[tuple[str, list[tuple[str, str]]]]:
    """Return every sheet as (title, rows) in workbook order."""
    return [(sheet.title, sheet_rows(sheet)) for sheet in workbook.worksheets]


def exported_names(workbook: Workbook) -> set[str]:
    """Return the patient names written into the workbook's rows."""
    return {
        nome.removeprefix("Nome: ")
        for _title, rows in sheet_listings(workbook)
        for _bed, nome in rows
    }


def export_rows(body: str) -> list[Tag]:
    """Return the export anchors one rendered map body carries (design D4)."""
    page = BeautifulSoup(body, "html.parser")
    rows: list[Tag] = []
    for marker in ("data-map-export", "data-map-export-disabled"):
        rows += page.find_all("a", attrs={marker: True})
    return rows


class WardMapExportViewFixture(TestCase):
    """Two wards, two public tags and the warm cache the map expects."""

    owner: Any
    member: Any
    ward_a: Ward
    ward_b: Ward
    tag_a: AllowedTag
    tag_b: AllowedTag
    patient_both: Patient
    patient_a: Patient
    patient_b: Patient
    patient_untagged: Patient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.owner = make_user("map-export-owner", is_staff=True, is_superuser=True)
        cls.member = make_user("map-export-member")
        cls.ward_a = create_ward(cls.owner, "Ala A", "ALA")
        cls.ward_b = create_ward(cls.owner, "Ala B", "ALB")
        cls.tag_a = make_tag(cls.owner, "Filtro A")
        cls.tag_b = make_tag(cls.owner, "Filtro B")
        cls.patient_both = cls.inpatient("Paciente Ambas", cls.ward_a, "101")
        cls.patient_a = cls.inpatient("Paciente Filtro A", cls.ward_a, "102")
        cls.patient_b = cls.inpatient("Paciente Filtro B", cls.ward_b, "201")
        cls.patient_untagged = cls.inpatient("Paciente Sem Tag", cls.ward_b, "202")
        assign(cls.owner, cls.patient_both, cls.tag_a)
        assign(cls.owner, cls.patient_both, cls.tag_b)
        assign(cls.owner, cls.patient_a, cls.tag_a)
        assign(cls.owner, cls.patient_b, cls.tag_b)

    @classmethod
    def inpatient(cls, name: str, ward: Ward, bed: str) -> Patient:
        """One inpatient of the fixture's owner, placed in a ward."""
        return make_patient(
            cls.owner, name, status=Patient.Status.INPATIENT, ward=ward, bed=bed
        )

    def setUp(self) -> None:
        seed_warm_cache(
            [
                (self.ward_a, [self.patient_both, self.patient_a]),
                (self.ward_b, [self.patient_b, self.patient_untagged]),
            ]
        )
        self.client.force_login(self.member)

    # -- helpers ---------------------------------------------------------

    def export_url(self) -> str:
        return reverse("patients:patient_map_export")

    def map_url(self) -> str:
        return reverse("patients:patient_map")

    def export_response(self, **params: Any) -> Any:
        """Request the export for one query string."""
        return self.client.get(self.export_url(), params)

    def workbook_from(self, response: Any) -> Workbook:
        """Reopen the response body as the spreadsheet it claims to be."""
        return load_workbook(io.BytesIO(response.content))

    def map_rows(self, **params: Any) -> list[tuple[str, list[tuple[str, str]]]]:
        """Return the rows the map renders as (abbreviation, (bed, name))."""
        response = self.client.get(self.map_url(), params)
        return [
            (
                str(ward_info["ward"]["abbreviation"]),
                [
                    (str(row["bed"]), f"Nome: {row['patient']['name']}")
                    for row in ward_info["patients"]
                ],
            )
            for ward_info in response.context["ward_data"]
        ]

    def assert_export_mirrors_the_map(self, **params: Any) -> Workbook:
        """Assert the export equals the map's rows for one query string."""
        expected = self.map_rows(**params)
        response = self.export_response(**params)
        self.assertEqual(response.status_code, 200)
        workbook = self.workbook_from(response)
        self.assertEqual(sheet_listings(workbook), expected)
        return workbook

    def assert_refused(self, response: Any) -> None:
        """Assert the single refusal rule: 409, plain text, no file."""
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response["Content-Type"], REFUSAL_CONTENT_TYPE)
        self.assertNotIn("Content-Disposition", response)
        self.assertIn(REFUSAL_WORDING, response.content.decode("utf-8"))


class WardMapExportAccessTests(WardMapExportViewFixture):
    """The endpoint keeps the map's inherited login and permission gates."""

    def test_anonymous_request_is_redirected_to_login(self) -> None:
        self.client.logout()
        requested = self.export_url() + f"?q=Filtro&ward={self.ward_a.pk}"
        response = self.client.get(requested)
        self.assertEqual(response.status_code, 302)
        location = urlsplit(response["Location"])
        self.assertEqual(location.path, LOGIN_PATH)
        self.assertEqual(parse_qs(location.query).get("next"), [requested])
        self.assertNotIn("Content-Disposition", response)

    def test_authenticated_without_permission_is_refused_403(self) -> None:
        plain = create_navigation_user(
            username="map-export-plain",
            email="map-export-plain@example.com",
            password="map-export-plain-pass",
        )
        self.client.force_login(plain)
        response = self.export_response()
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Content-Disposition", response)


class WardMapExportAttachmentTests(WardMapExportViewFixture):
    """A warm result answers with one valid, timestamped XLSX attachment."""

    def test_warm_result_exports_a_valid_workbook(self) -> None:
        response = self.export_response()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], XLSX_CONTENT_TYPE)
        self.assertEqual(
            dict(sheet_listings(self.workbook_from(response))),
            {
                "ALA": [
                    ("101", "Nome: Paciente Ambas"),
                    ("102", "Nome: Paciente Filtro A"),
                ],
                "ALB": [
                    ("201", "Nome: Paciente Filtro B"),
                    ("202", "Nome: Paciente Sem Tag"),
                ],
            },
        )

    def test_attachment_filename_carries_the_local_export_moment(self) -> None:
        before = timezone.localtime() - timedelta(seconds=1)
        response = self.export_response()
        after = timezone.localtime()
        match = re.fullmatch(FILENAME_PATTERN, response["Content-Disposition"])
        if match is None:
            self.fail(f"unexpected disposition: {response['Content-Disposition']!r}")
        filename = match.group(1)
        self.assertTrue(filename.isascii())
        moment = datetime.strptime(filename, FILE_STAMP_FORMAT).replace(
            tzinfo=timezone.get_current_timezone()
        )
        self.assertLessEqual(moment, after)
        self.assertGreaterEqual(moment, before)


class WardMapExportAjaxTests(WardMapExportViewFixture):
    """An AJAX request still receives the file, not the map's tree partial."""

    def test_ajax_header_still_receives_the_workbook(self) -> None:
        response = self.client.get(
            self.export_url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], XLSX_CONTENT_TYPE)
        self.assertEqual(
            [title for title, _rows in sheet_listings(self.workbook_from(response))],
            ["ALA", "ALB"],
        )


class WardMapExportRefusalTests(WardMapExportViewFixture):
    """One refusal rule: an empty applied result answers 409 with no file."""

    def test_filters_matching_nothing_are_refused(self) -> None:
        self.assert_refused(self.export_response(q="NadaDisponivel"))

    def test_an_expired_cache_is_refused(self) -> None:
        WardMappingCache.objects.update(updated_at=timezone.now() - CACHE_STALENESS)
        map_response = self.client.get(self.map_url())
        self.assertTrue(map_response.context["updating"])
        self.assert_refused(self.export_response())

    def test_a_missing_cache_is_refused(self) -> None:
        WardMappingCache.objects.all().delete()
        map_response = self.client.get(self.map_url())
        self.assertTrue(map_response.context["updating"])
        self.assert_refused(self.export_response())

    def test_retained_empty_wards_at_zero_patients_are_refused(self) -> None:
        params = {"q": "NadaDisponivel", "show_empty_wards": "true"}
        map_response = self.client.get(self.map_url(), params)
        self.assertEqual(len(map_response.context["ward_data"]), 2)
        self.assertEqual(map_response.context["total_patients"], 0)
        self.assert_refused(self.export_response(**params))


class WardMapExportParityTests(WardMapExportViewFixture):
    """The export equals the rows the map renders for the same query."""

    def test_export_equals_the_unfiltered_map_rows(self) -> None:
        self.assert_export_mirrors_the_map()

    def test_export_equals_the_search_filtered_map_rows(self) -> None:
        self.assert_export_mirrors_the_map(q="Filtro")

    def test_export_equals_the_ward_filtered_map_rows(self) -> None:
        self.assert_export_mirrors_the_map(ward=str(self.ward_b.pk))

    def test_export_equals_the_tag_filtered_map_rows(self) -> None:
        workbook = self.assert_export_mirrors_the_map(tags=[self.tag_a.pk])
        self.assertEqual(
            exported_names(workbook),
            {"Paciente Ambas", "Paciente Filtro A"},
        )

    def test_export_equals_the_map_rows_for_repeated_parameters(self) -> None:
        params = {"tags": [self.tag_a.pk, self.tag_b.pk], "tag_mode": "all"}
        workbook = self.assert_export_mirrors_the_map(**params)
        self.assertEqual(exported_names(workbook), {"Paciente Ambas"})

    def test_export_equals_the_rows_of_a_retained_empty_ward(self) -> None:
        params = {"q": "Filtro B", "show_empty_wards": "true"}
        workbook = self.assert_export_mirrors_the_map(**params)
        self.assertEqual(dict(sheet_listings(workbook))["ALA"], [])

    def test_context_is_resolved_exactly_once(self) -> None:
        original = WardMapFilterActionsView.get_context_data
        with patch.object(
            WardMapFilterActionsView,
            "get_context_data",
            autospec=True,
            side_effect=original,
        ) as resolver:
            response = self.export_response()
        self.assertEqual(response.status_code, 200)
        resolver.assert_called_once()


class WardMapExportButtonTests(WardMapExportViewFixture):
    """WMX-S3: the map page's export row; the AJAX fragment never has one."""

    def single_row(self, body: str) -> Tag:
        """Return the page's single export anchor (design D4)."""
        rows = export_rows(body)
        self.assertEqual(len(rows), 1)
        return rows[0]

    def map_body(self, **params: Any) -> str:
        """Render the full map page and return its decoded body."""
        return self.client.get(self.map_url(), params).content.decode("utf-8")

    def assert_disabled_anchor(self, response: Any) -> None:
        """Assert the empty-result disabled anchor: no href, inert, titled."""
        row = self.single_row(response.content.decode("utf-8"))
        self.assertIn("data-map-export-disabled", row.attrs)
        self.assertIsNone(row.get("href"))
        self.assertIn("disabled", row.get("class", []))
        self.assertEqual(row.get("aria-disabled"), "true")
        self.assertEqual(row.get("tabindex"), "-1")
        self.assertEqual(row.get("title"), EXPORT_DISABLED_TITLE)
        self.assertEqual(row.get_text(strip=True), EXPORT_LABEL)

    def test_the_row_sits_above_results_outside_the_filter_form(self) -> None:
        body = self.map_body()
        row = self.single_row(body)
        self.assertIn("data-map-export", row.attrs)
        self.assertIn("btn-medical-outline-primary", row.get("class", []))
        self.assertIsNotNone(row.find("i", class_="bi-file-earmark-excel"))
        self.assertEqual(row.get_text(strip=True), EXPORT_LABEL)
        self.assertIsNone(row.find_parent("form"))
        self.assertIsNone(row.find_parent(attrs={"data-patient-filter-panel": True}))
        row_at = body.index("data-map-export")
        results_at = body.index('<div class="card">', body.index("</form>"))
        self.assertTrue(body.index("</form>") < row_at < results_at)

    def test_the_enabled_href_carries_the_exact_query_string(self) -> None:
        ward = str(self.ward_a.pk)
        for query, suffix in (
            ({"q": "Filtro", "ward": ward}, f"?q=Filtro&ward={ward}"),
            ({"q": "", "ward": ward}, f"?q=&ward={ward}"),
            ({}, ""),
        ):
            with self.subTest(params=query):
                self.assertEqual(
                    self.single_row(self.map_body(**query)).get("href"),
                    self.export_url() + suffix,
                )

    def test_the_enabled_href_preserves_repeated_parameters(self) -> None:
        params = {"tags": [str(self.tag_a.pk), str(self.tag_b.pk)], "tag_mode": "all"}
        row = self.single_row(self.map_body(**params))
        href = row.get("href")
        self.assertEqual(
            href,
            f"{self.export_url()}?tags={self.tag_a.pk}"
            f"&tags={self.tag_b.pk}&tag_mode=all",
        )
        followed = self.client.get(href)
        self.assertEqual(followed.status_code, 200)
        self.assertEqual(followed["Content-Type"], XLSX_CONTENT_TYPE)

    def test_empty_results_render_the_disabled_anchor(self) -> None:
        for params, retained_wards in (
            ({"q": "NadaDisponivel"}, 0),
            ({"q": "NadaDisponivel", "show_empty_wards": "true"}, 2),
        ):
            with self.subTest(params=params):
                response = self.client.get(self.map_url(), params)
                self.assertEqual(response.context["total_patients"], 0)
                self.assertEqual(len(response.context["ward_data"]), retained_wards)
                self.assert_disabled_anchor(response)
        WardMappingCache.objects.update(updated_at=timezone.now() - CACHE_STALENESS)
        cold = self.client.get(self.map_url())
        self.assertTrue(cold.context["updating"])
        self.assert_disabled_anchor(cold)

    def test_the_row_block_is_placed_and_keyed_independently_of_updating(self) -> None:
        source = loader.get_template("patients/ward_patient_map.html").template.source
        start = source.index("{% if total_patients %}")
        end = source.index("{% endif %}", source.rindex("data-map-export-disabled"))
        block = source[start:end]
        self.assertIn("data-map-export", block)
        self.assertNotIn("updating", block)
        self.assertLess(source.index("data-map-updating"), start)
        self.assertLess(end, source.index("<!-- Tree View Section -->"))
        for body in (self.map_body(), self.map_body(q="NadaDisponivel")):
            for row in export_rows(body):
                self.assertNotIn("updating", str(row.attrs))

    def test_the_ajax_fragment_never_renders_the_export_row(self) -> None:
        for params in ({}, {"q": "NadaDisponivel"}):
            with self.subTest(params=params):
                ajax = self.client.get(
                    self.map_url(), params, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
                )
                self.assertTemplateUsed(
                    ajax, "patients/ward_patient_map_tree_only.html"
                )
                self.assertEqual(export_rows(ajax.content.decode("utf-8")), [])
                self.assertNotContains(ajax, EXPORT_LABEL)
