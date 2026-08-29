"""End-to-end duplicate-review flow during patient creation (slice 001)."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Patient, PatientRecordNumber
from ..services.patient_identity import (
    NAME_SIMILARITY_THRESHOLD,
    DuplicateCandidate,
    find_duplicate_candidates,
)

User = get_user_model()


def _grant_permission(user, codename, model):
    content_type = ContentType.objects.get_for_model(model)
    permission, _ = Permission.objects.get_or_create(
        codename=codename,
        content_type=content_type,
        defaults={"name": codename},
    )
    user.user_permissions.add(permission)


def _create_user(username, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpassword",
        password_change_required=False,
        terms_accepted=True,
        **extra,
    )


class DuplicateReviewFlowTests(TestCase):
    """Server-side review of name-and-birthday candidates on patient creation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="reviewuser",
            email="review@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )
        _grant_permission(cls.user, "add_patient", Patient)
        _grant_permission(cls.user, "view_patient", Patient)
        cls.birthday = date(1990, 5, 10)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("patients:patient_create")

    def _create_patient(self, name, **overrides):
        data = {
            "name": name,
            "birthday": self.birthday,
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "created_by": self.user,
            "updated_by": self.user,
        }
        data.update(overrides)
        return Patient.objects.create(**data)

    def _post(self, name, birthday=None, confirmed=False, **overrides):
        data = {
            "name": name,
            "birthday": (birthday or self.birthday).isoformat(),
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "initial_record_number": "REC001",
        }
        data.update(overrides)
        if confirmed:
            data["duplicate_review_confirmed"] = "1"
        return self.client.post(self.url, data)

    def test_exact_normalized_name_with_same_birthday_warns(self):
        """Case/accent/punctuation-equivalent name plus birthday warns."""
        self._create_patient("MARIA DA SILVA")
        response = self._post("maria, da silva!")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_similar_name_at_or_above_threshold_warns(self):
        """Different normalized name with trigram similarity >= 0.80 warns."""
        self._create_patient("Ana Carolina Souza")
        response = self._post("ana caroline souza")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertContains(response, "Nome semelhante")
        self.assertEqual(Patient.objects.count(), 1)

    def test_different_birthday_does_not_warn(self):
        """Similar name with a different birthday preserves normal creation."""
        self._create_patient("Maria da Silva")
        other_birthday = date(1985, 1, 2)
        response = self._post("maria da silva", birthday=other_birthday)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(PatientRecordNumber.objects.filter(is_current=True).count(), 1)

    def test_soft_deleted_match_is_returned_and_marked_deleted(self):
        """Soft-deleted patients appear as candidates and are flagged."""
        patient = self._create_patient("MARIA DA SILVA")
        patient.delete(deleted_by=self.user, reason="review test")

        response = self._post("maria, da silva!")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertContains(response, "Excluído")
        self.assertEqual(Patient.all_objects.count(), 1)

    def test_first_post_creates_zero_patient_and_record_rows(self):
        """An unconfirmed matching submission persists nothing."""
        self._create_patient("MARIA DA SILVA")

        response = self._post("maria da silva")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_confirmed_post_reruns_search_and_creates_single_patient(self):
        """Explicit confirmation permits the homonym with one patient/record."""
        existing = self._create_patient("MARIA DA SILVA")

        first = self._post("maria da silva")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(Patient.objects.count(), 1)

        confirmed = self._post("maria da silva", confirmed=True)

        self.assertEqual(confirmed.status_code, 302)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(PatientRecordNumber.objects.filter(is_current=True).count(), 1)
        new_patient = Patient.objects.exclude(pk=existing.pk).get()
        self.assertEqual(new_patient.current_record_number, "REC001")

    def test_confirmed_post_reruns_fresh_server_search(self):
        """Mock-proven: the confirmed POST executes a fresh server search."""
        self._create_patient("MARIA DA SILVA")

        with patch(
            "apps.patients.forms.find_duplicate_candidates",
            wraps=find_duplicate_candidates,
        ) as spy:
            first = self._post("maria da silva")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(spy.call_count, 1)

            confirmed = self._post("maria da silva", confirmed=True)
            self.assertEqual(confirmed.status_code, 302)
            self.assertEqual(spy.call_count, 2)

        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(PatientRecordNumber.objects.filter(is_current=True).count(), 1)

    def test_direct_confirmation_still_queries_and_creates_once(self):
        """Sending the hidden confirmation field directly never skips search."""
        self._create_patient("MARIA DA SILVA")

        with patch(
            "apps.patients.forms.find_duplicate_candidates",
            wraps=find_duplicate_candidates,
        ) as spy:
            response = self._post("maria da silva", confirmed=True)

        self.assertEqual(spy.call_count, 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 2)
        self.assertEqual(PatientRecordNumber.objects.filter(is_current=True).count(), 1)

    def test_diacritic_normalization_warns(self):
        """A real diacritic (e acute) is ignored by exact normalization."""
        self._create_patient("JOSÉ CARLOS PEREIRA")
        response = self._post("jose carlos pereira")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_csrf_is_enforced_on_creation_posts(self):
        """Real CSRF enforcement rejects token-less POSTs and accepts tokens."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        create_url = reverse("patients:patient_create")
        token = client.get(create_url).cookies["csrftoken"].value
        data = {
            "name": "Paciente CSRF",
            "birthday": self.birthday.isoformat(),
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "initial_record_number": "REC001",
        }

        without_token = client.post(create_url, data)
        self.assertEqual(without_token.status_code, 403)
        self.assertEqual(Patient.objects.count(), 0)

        with_token = client.post(create_url, {**data, "csrfmiddlewaretoken": token})
        self.assertEqual(with_token.status_code, 302)
        self.assertEqual(Patient.objects.count(), 1)

    def test_add_only_user_gets_generic_warning_without_candidate_data(self):
        """add_patient-only users see no candidate data or detail links."""
        patient = self._create_patient("MARIA DA SILVA")
        add_only = _create_user("addonly")
        _grant_permission(add_only, "add_patient", Patient)
        self.client.force_login(add_only)

        response = self._post("maria da silva")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertContains(response, "duplicate_review_confirmed")
        self.assertNotContains(response, "MARIA DA SILVA")
        self.assertNotContains(
            response,
            reverse("patients:patient_detail", kwargs={"pk": patient.pk}),
        )

    def test_add_and_view_user_sees_minimal_candidate_and_link(self):
        """view_patient users see minimal candidate fields and the link."""
        patient = self._create_patient(
            "MARIA DA SILVA",
            current_record_number="REC900",
            fiscal_number="123.456.789-00",
            healthcard_number="123456789012345",
            address="Rua Secreta 42",
            phone="(11) 99999-9999",
        )
        viewer = _create_user("addview")
        _grant_permission(viewer, "add_patient", Patient)
        _grant_permission(viewer, "view_patient", Patient)
        self.client.force_login(viewer)

        response = self._post("maria da silva")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertContains(response, "MARIA DA SILVA")
        self.assertContains(response, "REC900")
        self.assertContains(
            response,
            reverse("patients:patient_detail", kwargs={"pk": patient.pk}),
        )
        self.assertNotContains(response, "123.456.789-00")
        self.assertNotContains(response, "123456789012345")
        self.assertNotContains(response, "Rua Secreta 42")
        self.assertNotContains(response, "(11) 99999-9999")

    def test_soft_deleted_candidate_link_only_for_superuser(self):
        """Soft-deleted rows show the badge but link only for superusers."""
        patient = self._create_patient("MARIA DA SILVA")
        patient.delete(deleted_by=self.user, reason="review test")
        detail_url = reverse("patients:patient_detail", kwargs={"pk": patient.pk})

        viewer = _create_user("softview")
        _grant_permission(viewer, "add_patient", Patient)
        _grant_permission(viewer, "view_patient", Patient)
        self.client.force_login(viewer)

        response = self._post("maria da silva")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Excluído")
        self.assertNotContains(response, detail_url)

        superuser = _create_user("supersoft", is_superuser=True)
        self.client.force_login(superuser)

        response = self._post("maria da silva")

        self.assertContains(response, "Excluído")
        self.assertContains(response, detail_url)

    def test_warning_omits_raw_cpf_cns_address_and_phone(self):
        """The warning panel discloses only the minimal candidate data."""
        self._create_patient(
            "MARIA DA SILVA",
            fiscal_number="123.456.789-00",
            healthcard_number="123456789012345",
            address="Rua Secreta 42",
            phone="(11) 99999-9999",
        )

        response = self._post("maria da silva")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertContains(response, "MARIA DA SILVA")
        self.assertNotContains(response, "123.456.789-00")
        self.assertNotContains(response, "123456789012345")
        self.assertNotContains(response, "Rua Secreta 42")
        self.assertNotContains(response, "(11) 99999-9999")

    def test_permission_denial_still_enforced(self):
        """Users without add_patient cannot reach the creation flow."""
        other = User.objects.create_user(
            username="nopermission",
            email="noperm@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )
        self.client.force_login(other)

        response = self._post("Maria Nova")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Patient.objects.count(), 0)

    def test_no_candidate_creation_proceeds_unchanged(self):
        """Without candidates the existing atomic creation flow is preserved."""
        response = self._post("Paciente Novo")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.filter(is_current=True).count(), 1)


class PatientIdentityServiceTests(TestCase):
    """Unit coverage for the advisory candidate service (R1/R2/R5)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="serviceuser",
            email="service@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )
        cls.birthday = date(1990, 5, 10)

    def _create_patient(self, name, **overrides):
        data = {
            "name": name,
            "birthday": self.birthday,
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "current_record_number": "REC900",
            "created_by": self.user,
            "updated_by": self.user,
        }
        data.update(overrides)
        return Patient.objects.create(**data)

    def test_threshold_constant_is_defined_once_as_0_80(self):
        """The similarity threshold has a single authoritative value."""
        self.assertEqual(NAME_SIMILARITY_THRESHOLD, 0.80)

    def test_candidate_dto_exposes_only_minimal_fields(self):
        """The DTO never carries raw CPF, CNS, address, or phone values."""
        patient = self._create_patient(
            "MARIA DA SILVA",
            fiscal_number="123.456.789-00",
            healthcard_number="123456789012345",
            address="Rua Secreta 42",
            phone="(11) 99999-9999",
        )

        candidates = find_duplicate_candidates("maria, da silva!", self.birthday)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertIsInstance(candidate, DuplicateCandidate)
        self.assertEqual(candidate.patient_id, patient.pk)
        self.assertEqual(candidate.name, "MARIA DA SILVA")
        self.assertEqual(candidate.birthday, self.birthday)
        self.assertEqual(candidate.current_record_number, "REC900")
        self.assertFalse(candidate.is_deleted)
        self.assertEqual(candidate.evidence_type, "exact")
        for hidden in ("fiscal_number", "healthcard_number", "address", "phone"):
            self.assertFalse(hasattr(candidate, hidden))

    def test_soft_deleted_candidate_is_marked(self):
        """Soft-deleted patients keep flowing through all_objects."""
        patient = self._create_patient("MARIA DA SILVA")
        patient.delete(deleted_by=self.user, reason="review test")

        candidates = find_duplicate_candidates("maria da silva", self.birthday)

        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].is_deleted)

    def test_different_birthday_excludes_candidate(self):
        """Birthday filters the cohort before name comparison."""
        self._create_patient("MARIA DA SILVA")

        candidates = find_duplicate_candidates("maria da silva", date(1985, 1, 2))

        self.assertEqual(candidates, [])

    def test_similar_name_evidence_and_deterministic_order(self):
        """Fuzzy matches get similar evidence and a stable name ordering."""
        self._create_patient("Ana Carolina Souza")
        self._create_patient("Ana Caroline Souza")

        candidates = find_duplicate_candidates("ana caroline souza", self.birthday)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            [candidate.evidence_type for candidate in candidates],
            ["similar", "exact"],
        )
        self.assertEqual(
            [candidate.name for candidate in candidates],
            ["Ana Carolina Souza", "Ana Caroline Souza"],
        )
        self.assertGreaterEqual(candidates[0].similarity, NAME_SIMILARITY_THRESHOLD)
