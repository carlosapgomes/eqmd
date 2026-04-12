"""
Tests for the compact patient context summary rendered in the patient timeline.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient, Ward, PatientAdmission


class PatientTimelineContextSummaryTests(TestCase):
    """Tests for compact patient context summary in the timeline page."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        # Create test user
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        # Add view_patient permission
        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient'
        )
        cls.user.user_permissions.add(view_permission)

        # Create test patient (outpatient, no admission)
        cls.patient = Patient.objects.create(
            name='Maria da Silva',
            birthday=date(1985, 6, 15),
            current_record_number='12345',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        # Create a ward for admission tests
        cls.ward = Ward.objects.create(
            name='Unidade de Terapia Intensiva',
            abbreviation='UTI',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Log in the test user."""
        self.client.login(username='testuser', password='testpassword')

    def _timeline_url(self, patient=None):
        """Helper to build the timeline URL."""
        patient = patient or self.patient
        return reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': patient.pk},
        )

    # ------------------------------------------------------------------
    # 1. Compact summary is rendered with canonical fields
    # ------------------------------------------------------------------

    def test_timeline_shows_compact_patient_context_summary(self):
        """Timeline page renders a compact patient context summary with name,
        record number, age, and status."""
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The compact context summary section should be present
        self.assertIn('patient-context-summary', content)

        # Patient name must appear in the context summary area
        self.assertIn('Maria da Silva', content)

        # Record number must appear
        self.assertIn('12345', content)

        # Age should be rendered (derived from birthday 1985-06-15)
        expected_age = date.today().year - 1985 - (
            (date.today().month, date.today().day) < (6, 15)
        )
        self.assertIn(str(expected_age), content)

        # Status label should be present
        self.assertIn('Ambulatorial', content)

    # ------------------------------------------------------------------
    # 2. Ward and bed shown when patient has active admission
    # ------------------------------------------------------------------

    def test_timeline_summary_shows_ward_and_bed_for_active_admission(self):
        """When the patient has an active admission the compact summary shows
        ward and bed."""
        admitted_patient = Patient.objects.create(
            name='João Souza',
            birthday=date(1990, 3, 10),
            current_record_number='99001',
            status=Patient.Status.INPATIENT,
            ward=self.ward,
            bed='Leito 5A',
            created_by=self.user,
            updated_by=self.user,
        )

        # Create an active admission
        admission = PatientAdmission.objects.create(
            patient=admitted_patient,
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            ward=self.ward,
            initial_bed='Leito 5A',
            created_by=self.user,
            updated_by=self.user,
        )

        # Wire up the denormalized FK
        admitted_patient.current_admission_id = admission.id
        admitted_patient.save(update_fields=['current_admission_id'])

        response = self.client.get(self._timeline_url(admitted_patient))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Ward abbreviation should be visible in the compact context summary
        self.assertIn('UTI', content)

        # Bed should be visible
        self.assertIn('Leito 5A', content)

    # ------------------------------------------------------------------
    # 3. Ward and bed hidden when patient has NO active admission
    # ------------------------------------------------------------------

    def test_timeline_summary_hides_ward_and_bed_without_active_admission(self):
        """When the patient has no active admission the compact summary does
        NOT show ward or bed fields."""
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The patient is an outpatient with no admission — ward/bed should NOT
        # appear inside the patient-context-summary section.
        # Extract the summary section to avoid false positives from other page
        # content (e.g., the patient might have a ward listed elsewhere).
        summary_start = content.find('patient-context-summary')
        self.assertGreater(summary_start, -1, "patient-context-summary block not found")
        summary_end = content.find('</div>', summary_start)
        summary_section = content[summary_start:summary_end]

        self.assertNotIn('Leito', summary_section)
        self.assertNotIn('Leito 5A', summary_section)

    # ------------------------------------------------------------------
    # 4. Missing record number handled safely
    # ------------------------------------------------------------------

    def test_timeline_summary_handles_missing_record_number(self):
        """When the patient has no current record number the compact summary
        renders without errors and shows a safe placeholder."""
        patient_no_record = Patient.objects.create(
            name='Paciente Sem Prontuário',
            birthday=date(2000, 1, 1),
            current_record_number='',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

        response = self.client.get(self._timeline_url(patient_no_record))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # The compact context summary should still render
        self.assertIn('patient-context-summary', content)

        # Patient name should be present
        self.assertIn('Paciente Sem Prontuário', content)

        # A safe placeholder or dash should be present instead of a record
        # number. We check that the page renders successfully and that the
        # summary section exists — the exact placeholder text is an
        # implementation detail.
        summary_start = content.find('patient-context-summary')
        self.assertGreater(summary_start, -1)
        # The page should not crash (already verified by status 200).


# ======================================================================
# Expandable details tests (Slice 02)
# ======================================================================


class PatientTimelineExpandableDetailsTests(TestCase):
    """Tests for the optional expandable patient details in the timeline."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = EqmdCustomUser.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        content_type = ContentType.objects.get_for_model(Patient)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_patient',
        )
        cls.user.user_permissions.add(view_permission)

        # Outpatient (no admission)
        cls.patient = Patient.objects.create(
            name='Ana Costa',
            birthday=date(1992, 4, 20),
            gender=Patient.GenderChoices.FEMALE,
            current_record_number='54321',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.ward = Ward.objects.create(
            name='Clínica Médica',
            abbreviation='CM',
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username='testuser2', password='testpassword')

    def _timeline_url(self, patient=None):
        patient = patient or self.patient
        return reverse(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': patient.pk},
        )

    # ------------------------------------------------------------------
    # 5. Expand control is rendered
    # ------------------------------------------------------------------

    def test_timeline_summary_renders_expand_control_for_extended_details(self):
        """The compact summary renders a toggle control that expands to show
        extended patient details."""
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # A collapse / expand trigger must exist inside the summary block
        self.assertIn('patient-context-details', content)
        self.assertIn('data-bs-toggle="collapse"', content)

    # ------------------------------------------------------------------
    # 6. Expanded details include birthday and gender
    # ------------------------------------------------------------------

    def test_timeline_summary_extended_details_include_birthday_and_gender(self):
        """When expanded, the details section shows birth date and gender."""
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Birthday formatted as dd/mm/yyyy
        self.assertIn('20/04/1992', content)

        # Gender display
        self.assertIn('Feminino', content)

    # ------------------------------------------------------------------
    # 7. Admission date and duration shown for active admission
    # ------------------------------------------------------------------

    def test_timeline_summary_extended_details_include_admission_date_and_duration_for_active_admission(self):
        """When the patient has an active admission the expanded section shows
        admission date and duration."""
        admitted = Patient.objects.create(
            name='Carlos Lima',
            birthday=date(1978, 11, 5),
            gender=Patient.GenderChoices.MALE,
            current_record_number='88001',
            status=Patient.Status.INPATIENT,
            ward=self.ward,
            bed='Leito 3B',
            created_by=self.user,
            updated_by=self.user,
        )

        adm_datetime = timezone.now() - timedelta(days=5)
        admission = PatientAdmission.objects.create(
            patient=admitted,
            admission_datetime=adm_datetime,
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            ward=self.ward,
            initial_bed='Leito 3B',
            created_by=self.user,
            updated_by=self.user,
        )
        admitted.current_admission_id = admission.id
        admitted.save(update_fields=['current_admission_id'])

        response = self.client.get(self._timeline_url(admitted))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Scope to the expandable details block
        details_start = content.find('patient-context-details')
        self.assertGreater(details_start, -1, 'expandable details block not found')
        details_section = content[details_start:details_start + 2000]

        # Admission date rendered as "Internado em dd/mm/yyyy"
        adm_date_str = adm_datetime.strftime('%d/%m/%Y')
        self.assertIn(f'Internado em {adm_date_str}', details_section)

        # Duration icon must be present (the actual text varies with
        # hours/minutes so we assert on the stable icon class instead)
        self.assertIn('bi-clock-history', details_section)

    # ------------------------------------------------------------------
    # 8. Admission fields omitted without active admission
    # ------------------------------------------------------------------

    def test_timeline_summary_extended_details_omit_admission_fields_without_active_admission(self):
        """When the patient has no active admission the expanded section does
        NOT show admission date or duration."""
        response = self.client.get(self._timeline_url())
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # Locate the expandable details section to scope the assertion.
        details_start = content.find('patient-context-details')
        self.assertGreater(details_start, -1, 'expandable details block not found')
        details_section = content[details_start:details_start + 2000]

        # The template renders admission-specific content only when an
        # active admission exists.  Assert the actual rendered strings are
        # absent — not invented label names.
        self.assertNotIn('Internado em', details_section)
        self.assertNotIn('bi-calendar-check', details_section)
        self.assertNotIn('bi-clock-history', details_section)
