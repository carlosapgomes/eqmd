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
    EVIDENCE_CNS,
    EVIDENCE_CPF,
    NAME_SIMILARITY_THRESHOLD,
    DuplicateCandidate,
    find_duplicate_candidates,
    find_strong_identifier_conflicts,
)
from ..validators import is_valid_cns, is_valid_cpf, normalize_cns, normalize_cpf

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


# --- Slice 002: strong CPF/CNS evidence ---

_CPF_FIRST_WEIGHTS = (10, 9, 8, 7, 6, 5, 4, 3, 2)
_CPF_SECOND_WEIGHTS = (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
_CNS_PIS_WEIGHTS = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNS_PROVISORY_WEIGHTS = (4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
_CNS_DEFINITIVE_SUFFIX = "0001"


def _cpf_check_digit(digits: list[int], weights: tuple[int, ...]) -> int:
    """Compute one CPF check digit using the official weighted rule."""
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def _valid_cpf(base: str = "123456789") -> str:
    """Generate a deterministic valid synthetic CPF from a fixed base."""
    digits = [int(char) for char in base]
    first = _cpf_check_digit(digits, _CPF_FIRST_WEIGHTS)
    second = _cpf_check_digit([*digits, first], _CPF_SECOND_WEIGHTS)
    return base + str(first) + str(second)


def _valid_cns(base: str = "1000000000") -> str:
    """Generate a deterministic officially valid synthetic CNS from a base.

    Definitive bases are 10 digits (PIS check digit + "0001" suffix);
    provisory bases are 14 digits starting with 7 (last digit searched so
    the official weighted sum is divisible by 11).
    """
    if len(base) == 10:
        digits = [int(char) for char in base]
        remainder = (
            sum(digit * weight for digit, weight in zip(digits, _CNS_PIS_WEIGHTS)) % 11
        )
        dv = 11 - remainder
        if dv == 10:
            dv = 0
        return base + str(dv) + _CNS_DEFINITIVE_SUFFIX
    if len(base) == 14 and base.startswith("7"):
        for last in "0123456789":
            candidate = base + last
            total = sum(
                int(char) * weight
                for char, weight in zip(candidate, _CNS_PROVISORY_WEIGHTS)
            )
            if total % 11 == 0:
                return candidate
        raise AssertionError(f"No valid provisory CNS found for base {base}")
    raise AssertionError(
        "CNS base must be 10 digits (definitive) or 14 digits starting "
        "with 7 (provisory)"
    )


class IdentifierValidationTests(TestCase):
    """Canonical CPF/CNS utilities (R1)."""

    def test_cpf_normalization_keeps_only_digits(self):
        self.assertEqual(normalize_cpf("123.456.789-09"), "12345678909")
        self.assertEqual(normalize_cpf(" 123.456.789-09 "), "12345678909")
        self.assertEqual(normalize_cpf(""), "")

    def test_cpf_checksum_rules(self):
        self.assertTrue(is_valid_cpf(_valid_cpf()))
        self.assertTrue(is_valid_cpf("12345678909"))
        self.assertFalse(is_valid_cpf("12345678900"))  # wrong second check digit
        self.assertFalse(is_valid_cpf("11111111111"))  # repeated digits
        self.assertFalse(is_valid_cpf("1234567890"))  # too short
        self.assertFalse(is_valid_cpf(""))  # blank is not a strong identifier

    def test_cns_normalization_and_checksum_rules(self):
        self.assertEqual(normalize_cns("100 0000 0008 0001"), "100000000080001")
        self.assertTrue(is_valid_cns(_valid_cns()))
        self.assertTrue(is_valid_cns("700000000000008"))  # valid provisory
        self.assertTrue(is_valid_cns("100000000080001"))  # valid definitive
        self.assertFalse(is_valid_cns("100000000080003"))  # wrong suffix
        self.assertFalse(is_valid_cns("100000000090001"))  # wrong check digit
        self.assertFalse(is_valid_cns("300000000000003"))  # invalid prefix
        self.assertFalse(is_valid_cns("20000000000003"))  # 14 digits
        self.assertFalse(is_valid_cns("200000000000003"))  # old fake-valid sample
        self.assertFalse(is_valid_cns(""))  # blank is not a strong identifier


class StrongIdentifierServiceTests(TestCase):
    """Strong-conflict discovery in the identity service (R3/R4)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _create_user("strongservice")
        cls.birthday = date(1990, 5, 10)

    def _create_owner(self, **overrides):
        data = {
            "name": "Titular CPF",
            "birthday": self.birthday,
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "fiscal_number": _valid_cpf(),
            "healthcard_number": _valid_cns(),
            "created_by": self.user,
            "updated_by": self.user,
        }
        data.update(overrides)
        return Patient.objects.create(**data)

    def test_conflict_dto_exposes_evidence_but_never_raw_identifiers(self):
        owner = self._create_owner()

        conflicts = find_strong_identifier_conflicts(cpf=_valid_cpf(), cns=_valid_cns())

        self.assertEqual(len(conflicts), 2)
        self.assertEqual(
            {candidate.evidence_type for candidate in conflicts},
            {EVIDENCE_CPF, EVIDENCE_CNS},
        )
        self.assertEqual({candidate.patient_id for candidate in conflicts}, {owner.pk})
        for candidate in conflicts:
            for hidden in ("fiscal_number", "healthcard_number"):
                self.assertFalse(hasattr(candidate, hidden))

    def test_exclude_patient_id_removes_only_that_patient(self):
        owner = self._create_owner()

        conflicts = find_strong_identifier_conflicts(
            cpf=_valid_cpf(), exclude_patient_id=owner.pk
        )

        self.assertEqual(conflicts, [])

    def test_invalid_and_blank_identifiers_are_not_strong(self):
        self._create_owner()

        self.assertEqual(find_strong_identifier_conflicts(cpf="12345678900"), [])
        self.assertEqual(find_strong_identifier_conflicts(cpf=""), [])
        self.assertEqual(find_strong_identifier_conflicts(cns="300000000000003"), [])
        self.assertEqual(find_strong_identifier_conflicts(cns=""), [])

    def test_soft_deleted_owner_is_still_a_strong_conflict(self):
        owner = self._create_owner()
        owner.delete(deleted_by=self.user, reason="strong conflict test")

        conflicts = find_strong_identifier_conflicts(cpf=_valid_cpf())

        self.assertEqual(len(conflicts), 1)
        self.assertTrue(conflicts[0].is_deleted)


class StrongIdentifierCreateFlowTests(TestCase):
    """Create-flow strong conflicts and CNS interface wording (R2/R3/R5/R6)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _create_user("strongcreate")
        _grant_permission(cls.user, "add_patient", Patient)
        _grant_permission(cls.user, "view_patient", Patient)
        cls.birthday = date(1990, 5, 10)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("patients:patient_create")
        self.owner = Patient.objects.create(
            name="Titular Existente",
            birthday=self.birthday,
            gender=Patient.GenderChoices.NOT_INFORMED,
            fiscal_number=_valid_cpf(),
            healthcard_number=_valid_cns(),
            current_record_number="REC900",
            created_by=self.user,
            updated_by=self.user,
        )

    def _post(self, confirmed: bool = False, **overrides):
        data = {
            "name": "Paciente Novo",
            "birthday": self.birthday.isoformat(),
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "initial_record_number": "REC001",
        }
        data.update(overrides)
        if confirmed:
            data["duplicate_review_confirmed"] = "1"
        return self.client.post(self.url, data)

    def test_invalid_new_cpf_is_rejected_and_creates_no_rows(self):
        response = self._post(fiscal_number="12345678900")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF inválido")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_invalid_new_cns_is_rejected_and_creates_no_rows(self):
        response = self._post(healthcard_number="300000000000003")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CNS inválido")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_valid_formatted_inputs_are_stored_canonically(self):
        response = self._post(
            fiscal_number="987.654.321-00",
            healthcard_number="700 0000 0000 0008",
        )

        self.assertEqual(response.status_code, 302)
        created = Patient.objects.exclude(pk=self.owner.pk).get()
        self.assertEqual(created.fiscal_number, "98765432100")
        self.assertEqual(created.healthcard_number, "700000000000008")

    def test_exact_valid_cpf_blocks_creation_despite_confirmation(self):
        response = self._post(confirmed=True, fiscal_number=_valid_cpf())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF já cadastrado")
        self.assertContains(response, "CPF coincidente")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_exact_valid_cns_blocks_creation_despite_confirmation(self):
        response = self._post(confirmed=True, healthcard_number=_valid_cns())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CNS já cadastrado")
        self.assertContains(response, "CNS coincidente")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_soft_deleted_owner_still_causes_strong_conflict(self):
        self.owner.delete(deleted_by=self.user, reason="strong conflict test")

        response = self._post(confirmed=True, fiscal_number=_valid_cpf())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Excluído")
        self.assertContains(response, "CPF coincidente")
        self.assertEqual(Patient.all_objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_strong_warning_never_renders_raw_identifier(self):
        response = self._post(confirmed=True, fiscal_number=_valid_cpf())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF coincidente")
        content = response.content.decode()
        self.assertEqual(content.count(_valid_cpf()), 1)  # only the input echo

    def test_strong_conflict_hides_advisory_override_control(self):
        response = self._post(confirmed=True, fiscal_number=_valid_cpf())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "duplicate_review_confirmed")

    def test_advisory_confirmation_still_succeeds_without_strong_conflict(self):
        response = self._post(
            confirmed=True,
            name="Titular Existente",
            fiscal_number=_valid_cpf(base="987654321"),
            healthcard_number=_valid_cns(base="70000000000001"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 2)
        created = Patient.objects.exclude(pk=self.owner.pk).get()
        self.assertEqual(created.fiscal_number, "98765432100")
        self.assertEqual(created.healthcard_number, "700000000000011")

    def test_unconfirmed_advisory_with_identifiers_creates_nothing(self):
        response = self._post(
            name="Titular Existente",
            fiscal_number=_valid_cpf(base="987654321"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possível duplicata")
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(PatientRecordNumber.objects.count(), 0)

    def test_create_page_uses_cns_wording_only(self):
        response = self.client.get(self.url)

        self.assertContains(response, "CNS (Cartão Nacional de Saúde)")
        self.assertContains(response, "Cartão Nacional de Saúde")
        self.assertNotContains(response, "Cartão de Saúde")
        self.assertNotContains(response, "carteirinha")
        self.assertNotContains(response, "plano de saúde")


class StrongIdentifierProfileUpdateTests(TestCase):
    """Profile-update strong conflicts with self-exclusion (R2/R4)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _create_user("strongupdate")
        _grant_permission(cls.user, "change_patient", Patient)
        _grant_permission(cls.user, "view_patient", Patient)
        cls.birthday = date(1990, 5, 10)

    def setUp(self):
        self.client.force_login(self.user)
        self.owner = Patient.objects.create(
            name="Titular Próprio",
            birthday=self.birthday,
            gender=Patient.GenderChoices.NOT_INFORMED,
            fiscal_number=_valid_cpf(),
            healthcard_number=_valid_cns(),
            phone="(11) 91111-1111",
            created_by=self.user,
            updated_by=self.user,
        )
        self.url = reverse("patients:patient_update", kwargs={"pk": self.owner.pk})

    def _post(self, **overrides):
        data = {
            "name": self.owner.name,
            "birthday": self.birthday.isoformat(),
            "gender": Patient.GenderChoices.NOT_INFORMED,
            "fiscal_number": self.owner.fiscal_number,
            "healthcard_number": self.owner.healthcard_number,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_own_unchanged_valid_identifiers_are_accepted(self):
        response = self._post(phone="(11) 92222-2222")

        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.fiscal_number, _valid_cpf())
        self.assertEqual(self.owner.healthcard_number, _valid_cns())
        self.assertEqual(self.owner.phone, "(11) 92222-2222")

    def test_rejecting_another_patients_cpf_persists_no_partial_change(self):
        other = Patient.objects.create(
            name="Outro Titular",
            birthday=self.birthday,
            gender=Patient.GenderChoices.NOT_INFORMED,
            fiscal_number=_valid_cpf(base="987654321"),
            created_by=self.user,
            updated_by=self.user,
        )

        response = self._post(
            name="Nome Alterado",
            phone="(11) 93333-3333",
            fiscal_number=other.fiscal_number,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF já cadastrado")
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, "Titular Próprio")
        self.assertEqual(self.owner.phone, "(11) 91111-1111")
        self.assertEqual(self.owner.fiscal_number, _valid_cpf())

    def test_rejecting_another_patients_cns_persists_no_partial_change(self):
        other = Patient.objects.create(
            name="Outro Titular CNS",
            birthday=self.birthday,
            gender=Patient.GenderChoices.NOT_INFORMED,
            healthcard_number=_valid_cns(base="70000000000001"),
            created_by=self.user,
            updated_by=self.user,
        )

        response = self._post(
            name="Nome Alterado",
            healthcard_number=other.healthcard_number,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CNS já cadastrado")
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, "Titular Próprio")
        self.assertEqual(self.owner.healthcard_number, _valid_cns())

    def test_changed_invalid_cpf_on_update_is_rejected(self):
        response = self._post(fiscal_number="12345678900")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF inválido")
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.fiscal_number, _valid_cpf())

    def test_unchanged_invalid_legacy_identifiers_allow_unrelated_edit(self):
        legacy = Patient.objects.create(
            name="Paciente Legado",
            birthday=self.birthday,
            gender=Patient.GenderChoices.NOT_INFORMED,
            fiscal_number="123",
            healthcard_number="abc",
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse("patients:patient_update", kwargs={"pk": legacy.pk})

        response = self.client.post(
            url,
            {
                "name": "Paciente Legado Renomeado",
                "birthday": self.birthday.isoformat(),
                "gender": Patient.GenderChoices.NOT_INFORMED,
                "fiscal_number": "123",
                "healthcard_number": "abc",
            },
        )

        self.assertEqual(response.status_code, 302)
        legacy.refresh_from_db()
        self.assertEqual(legacy.name, "Paciente Legado Renomeado")
        self.assertEqual(legacy.fiscal_number, "123")
        self.assertEqual(legacy.healthcard_number, "abc")

    def test_update_page_uses_cns_wording_only(self):
        response = self.client.get(self.url)

        self.assertContains(response, "CNS (Cartão Nacional de Saúde)")
        self.assertNotContains(response, "Cartão de Saúde")
        self.assertNotContains(response, "carteirinha")
        self.assertNotContains(response, "plano de saúde")
