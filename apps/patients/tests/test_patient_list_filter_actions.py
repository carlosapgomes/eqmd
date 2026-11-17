"""PLFA-S1: distinct list actions with genuine saved-specialty defaults."""

import re
from html import unescape
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import parse_qs, urlsplit

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    EqmdCustomUser,
    MedicalSpecialty,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient, Tag

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse


class PatientListFilterActionsTests(TestCase):
    """A real preference X/ALL must not reappear after explicit clear-all."""

    viewer: ClassVar[EqmdCustomUser]
    specialty: ClassVar[MedicalSpecialty]
    preference: ClassVar[UserSpecialtyTagPreference]
    x: ClassVar[AllowedTag]
    y: ClassVar[AllowedTag]
    untagged: ClassVar[Patient]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.viewer = create_navigation_user(
            username="plfa-viewer",
            email="plfa-viewer@example.com",
            password="isolated-plfa-test",
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
        )
        EmailAddress.objects.create(
            user=cls.viewer, email=cls.viewer.email, verified=True, primary=True
        )
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_patient"))
        cls.specialty = MedicalSpecialty.objects.create(
            name="Equipe PLFA", abbreviation="PLFA"
        )
        membership = UserSpecialty.objects.create(
            user=cls.viewer, specialty=cls.specialty
        )
        cls.x = cls.create_tag("PLFA X")
        cls.y = cls.create_tag("PLFA Y")
        cls.specialty.principal_tag = cls.x
        cls.specialty.save(update_fields=["principal_tag"])
        profile = cls.viewer.profile
        profile.current_specialty = cls.specialty
        profile.save(update_fields=["current_specialty"])
        cls.preference = UserSpecialtyTagPreference.objects.create(
            membership=membership, mode="all"
        )
        cls.preference.tags.add(cls.x)
        cls.create_population()

    @classmethod
    def create_population(cls) -> None:
        for suffix, tags in (
            ("X", [cls.x]),
            ("Y", [cls.y]),
            ("XY", [cls.x, cls.y]),
            ("Sem tag", []),
        ):
            patient = cls.create_patient("Ana " + suffix)
            for tag in tags:
                Tag.objects.create(
                    patient=patient,
                    allowed_tag=tag,
                    created_by=cls.viewer,
                    updated_by=cls.viewer,
                )
            if not tags:
                cls.untagged = patient
        for index in range(24):
            cls.create_patient(f"Extra PLFA {index:02}")

    @classmethod
    def create_tag(cls, name: str) -> AllowedTag:
        return AllowedTag.objects.create(
            name=name,
            specialty=cls.specialty,
            created_by=cls.viewer,
            updated_by=cls.viewer,
        )

    @classmethod
    def create_patient(cls, name: str) -> Patient:
        return Patient.objects.create(
            name=name,
            birthday="1980-01-01",
            status=Patient.Status.INPATIENT,
            created_by=cls.viewer,
            updated_by=cls.viewer,
        )

    def setUp(self) -> None:
        self.client.force_login(self.viewer)

    def response(self, **params: str) -> "_MonkeyPatchedWSGIResponse":
        response = self.client.get(reverse("patients:patient_list"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def action_href(self, response: "_MonkeyPatchedWSGIResponse", label: str) -> str:
        pattern = (
            r'<a\b[^>]*href="([^"]+)"[^>]*>\s*(?:<i[^>]*>[^<]*</i>)?\s*'
            + re.escape(label)
            + r"\s*</a>"
        )
        found = re.findall(pattern, response.content.decode(), re.DOTALL)
        self.assertEqual(len(found), 1, f"expected one action: {label}")
        return unescape(found[0])

    def snapshot(self) -> tuple[str, tuple[int, ...], int]:
        self.preference.refresh_from_db()
        return (
            self.preference.mode,
            tuple(self.preference.tags.values_list("pk", flat=True)),
            UserSpecialty.objects.count(),
        )

    def test_clear_all_drops_every_predicate_and_preserves_preferences(self) -> None:
        before = self.snapshot()
        response = self.response(
            q="Ana", status="2", admission="not_admitted", tags=str(self.y.pk), page="1"
        )
        href = self.action_href(response, "Limpar todos os filtros")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {"tag_filter": ["manual"], "tag_mode": ["any"]},
        )
        cleared = self.client.get(href)
        self.assertFalse(cleared.context["tag_selection"].has_predicate)
        self.assertTrue(cleared.context["tag_filter_is_manual"])
        self.assertEqual(cleared.context["search_query"], "")
        self.assertEqual(cleared.context["status_filter"], "")
        self.assertEqual(cleared.context["admission_filter"], "")
        self.assertEqual(cleared.context["paginator"].count, 28)
        self.assertEqual(cleared.context["page_obj"].number, 1)
        for url in (href, href + "&page=2"):
            refreshed = self.client.get(url)
            self.assertFalse(refreshed.context["tag_selection"].has_predicate)
            self.assertEqual(refreshed.context["paginator"].count, 28)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.response().context["tag_selection"].tag_ids, (self.x.pk,))

    def test_restore_preserves_applied_non_tag_predicates(self) -> None:
        response = self.response(
            q="Ana",
            status="2",
            admission="not_admitted",
            tags=str(self.y.pk),
            tag_mode="any",
            page="1",
        )
        href = self.action_href(response, "Usar padrão de tags da especialidade")
        self.assertEqual(
            parse_qs(urlsplit(href).query),
            {"q": ["Ana"], "status": ["2"], "admission": ["not_admitted"]},
        )
        before = self.snapshot()
        restored = self.client.get(href)
        self.assertEqual(restored.context["tag_selection"].tag_ids, (self.x.pk,))
        self.assertEqual(restored.context["tag_selection"].mode, "all")
        self.assertFalse(restored.context["tag_filter_is_manual"])
        self.assertEqual(restored.context["paginator"].count, 2)
        self.assertEqual(self.snapshot(), before)

    def test_manual_and_empty_results_have_no_duplicate_controls(self) -> None:
        for q in ("Ana", "Sem-correspondencia"):
            body = self.response(q=q, tags=str(self.y.pk)).content.decode()
            self.assertEqual(body.count("Limpar todos os filtros</a>"), 1)
            self.assertEqual(body.count("Usar padrão de tags da especialidade</a>"), 1)
            self.assertNotIn("Remover filtro de tags", body)
            self.assertNotIn("Restaurar padrão da especialidade", body)
            self.assertNotIn('aria-label="Limpar filtros"', body)
            self.assertNotIn("Limpar seleção", body)
            summary = body.split("Filtros ativos:", 1)[1].split(
                "data-tag-preference-panel", 1
            )[0]
            self.assertNotIn("<a ", summary)

    def test_restore_is_absent_on_automatic_entry(self) -> None:
        response = self.response()
        self.assertNotContains(response, "Usar padrão de tags da especialidade")
        self.assertContains(response, "Padrão salvo da especialidade aplicado")

    def test_manual_label_does_not_claim_saved_default_is_in_use(self) -> None:
        response = self.response(tags=str(self.y.pk))
        self.assertContains(response, "Filtros personalizados em uso")
        self.assertNotContains(response, "Preferência salva em uso")

    def test_native_apply_has_an_explicit_manual_submitter(self) -> None:
        body = self.response().content.decode()
        self.assertRegex(
            body, r'<button[^>]*type="submit"[^>]*name="tag_filter"[^>]*value="manual"'
        )
        # HTML submission orders selector's initial hidden marker before Apply.
        response = self.client.get(
            reverse("patients:patient_list")
            + "?tag_filter=&tag_mode=all&tag_filter=manual"
        )
        self.assertFalse(response.context["tag_selection"].has_predicate)
        self.assertTrue(response.context["tag_filter_is_manual"])

    def test_saved_empty_and_principal_fallback_are_distinguished(self) -> None:
        self.preference.tags.clear()
        response = self.response()
        self.assertContains(response, "Padrão salvo sem filtro de tags aplicado")
        self.assertEqual(response.context["paginator"].count, 28)
        self.preference.delete()
        response = self.response()
        self.assertContains(response, "Padrão inicial da especialidade aplicado")
        self.assertEqual(response.context["tag_selection"].tag_ids, (self.x.pk,))

    def test_restore_is_hidden_without_a_specialty_or_configured_default(self) -> None:
        profile = self.viewer.profile
        profile.current_specialty = None
        profile.save(update_fields=["current_specialty"])
        self.assertNotContains(
            self.response(tags=str(self.y.pk)), "Usar padrão de tags da especialidade"
        )
        profile.current_specialty = self.specialty
        profile.save(update_fields=["current_specialty"])
        self.preference.delete()
        self.specialty.principal_tag = None
        self.specialty.save(update_fields=["principal_tag"])
        response = self.response(tags=str(self.y.pk))
        self.assertNotContains(response, "Usar padrão de tags da especialidade")
        self.assertContains(self.response(), "Sem padrão de tags aplicado")

    def test_unavailable_defaults_and_invalid_tags_are_not_successes(self) -> None:
        self.preference.tags.add(self.y)
        AllowedTag.objects.filter(pk=self.y.pk).update(is_active=False)
        partial = self.response()
        self.assertContains(partial, "aplicado parcialmente")
        self.assertEqual(partial.context["tag_selection"].tag_ids, (self.x.pk,))
        AllowedTag.objects.filter(pk=self.x.pk).update(is_active=False)
        response = self.response()
        self.assertContains(response, "Sem filtro de tags: padrão indisponível")
        self.assertTrue(response.context["tag_preference_warning"])
        invalid = self.response(tags="999999999")
        self.assertContains(invalid, "Filtro de tag inválido")
        self.assertContains(invalid, "Não foi possível aplicar os filtros")
        self.assertEqual(invalid.context["paginator"].count, 0)

    def test_map_keeps_its_existing_clear_restore_and_applied_links(self) -> None:
        response = self.client.get(reverse("patients:patient_map"), {"tags": self.y.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remover filtro de tags")
        self.assertContains(response, "Restaurar padrão da especialidade")
        self.assertNotContains(response, "Usar padrão de tags da especialidade")
        self.assertNotContains(response, "Limpar todos os filtros")

    def test_legacy_scoped_clear_still_preserves_non_tag_predicates(self) -> None:
        response = self.response(q="Ana", status="2", tag=str(self.y.pk))
        self.assertEqual(response.context["tag_selection"].tag_ids, (self.y.pk,))
        cleared = self.client.get(
            reverse("patients:patient_list")
            + "?"
            + response.context["clear_tags_querystring"]
        )
        self.assertFalse(cleared.context["tag_selection"].has_predicate)
        self.assertEqual(cleared.context["search_query"], "Ana")
        self.assertEqual(cleared.context["status_filter"], "2")
        self.assertEqual(cleared.context["paginator"].count, 4)
        self.assertNotContains(self.response(admission="banana"), "Sem admissão ativa")

    def test_genuine_unfiltered_empty_keeps_first_patient_explanation(self) -> None:
        Patient.objects.filter(created_by=self.viewer).delete()
        response = self.response(tag_filter="manual", tag_mode="any")
        self.assertContains(response, "Comece adicionando o primeiro paciente")
        self.assertNotContains(
            response, "Nenhum paciente corresponde aos filtros atuais"
        )

    def test_anonymous_and_unprivileged_requests_keep_their_gates(self) -> None:
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("patients:patient_list")).status_code, 302
        )
        user = create_navigation_user(
            username="plfa-denied", email="plfa-denied@example.com"
        )
        self.client.force_login(user)
        self.assertEqual(
            self.client.get(reverse("patients:patient_list")).status_code, 403
        )
