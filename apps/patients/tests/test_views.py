from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.accounts.tests.helpers import create_navigation_user

from ..models import Patient, PatientRecordNumber

User = get_user_model()

LOGIN_URL = "/accounts/login/"


class PatientViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user with lifecycle gates cleared
        cls.user = create_navigation_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            profession_type=0,  # MEDICAL_DOCTOR — clinical role for these tests
        )

        # Add permissions
        content_type = ContentType.objects.get_for_model(Patient)
        permissions = Permission.objects.filter(content_type=content_type)
        cls.user.user_permissions.add(*permissions)

        # Create test data
        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username="testuser", password="testpassword")

    def test_patient_list_view(self):
        response = self.client.get(reverse("patients:patient_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Patient")
        self.assertTemplateUsed(response, "patients/patient_list.html")

    def test_patient_detail_view(self):
        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Patient")
        self.assertTemplateUsed(response, "patients/patient_detail.html")

    def test_patient_create_view(self):
        response = self.client.get(reverse("patients:patient_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "patients/patient_create.html")

        # Test form submission
        response = self.client.post(
            reverse("patients:patient_create"),
            {
                "name": "New Patient",
                "birthday": "1990-01-01",
                "gender": Patient.GenderChoices.FEMALE,
                "initial_record_number": "REC001",
            },
        )
        self.assertEqual(Patient.objects.filter(name="New Patient").count(), 1)

        # Verify gender was saved correctly
        new_patient = Patient.objects.get(name="New Patient")
        self.assertEqual(new_patient.gender, Patient.GenderChoices.FEMALE)
        self.assertEqual(new_patient.current_record_number, "REC001")

    def test_patient_update_view(self):
        response = self.client.get(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "patients/patient_update.html")

        # Test form submission
        response = self.client.post(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk}),
            {
                "name": "Updated Patient",
                "birthday": "1980-01-01",
                "gender": Patient.GenderChoices.MALE,
            },
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "Updated Patient")
        self.assertEqual(self.patient.gender, Patient.GenderChoices.MALE)

    # --- Slice 02: initial_record_number view tests ---

    def test_patient_create_with_initial_record_number(self):
        """Creating a patient with initial_record_number succeeds and creates PatientRecordNumber"""
        initial_count = PatientRecordNumber.objects.count()

        self.client.post(
            reverse("patients:patient_create"),
            {
                "name": "Record Number Patient",
                "birthday": "1995-05-15",
                "gender": Patient.GenderChoices.MALE,
                "initial_record_number": "REC123",
            },
        )

        self.assertEqual(
            Patient.objects.filter(name="Record Number Patient").count(), 1
        )
        new_patient = Patient.objects.get(name="Record Number Patient")
        self.assertEqual(new_patient.current_record_number, "REC123")
        self.assertEqual(PatientRecordNumber.objects.count(), initial_count + 1)
        record = PatientRecordNumber.objects.get(patient=new_patient)
        self.assertTrue(record.is_current)
        self.assertEqual(record.record_number, "REC123")

    def test_patient_update_ignores_initial_record_number(self):
        """Updating a patient with unexpected initial_record_number does not create/change record number"""
        record_count_before = PatientRecordNumber.objects.filter(
            patient=self.patient
        ).count()

        self.client.post(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk}),
            {
                "name": "Updated Record Patient",
                "birthday": "1980-01-01",
                "gender": Patient.GenderChoices.MALE,
                "initial_record_number": "EVIL999",
            },
        )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "Updated Record Patient")
        self.assertNotEqual(self.patient.current_record_number, "EVIL999")

        record_count_after = PatientRecordNumber.objects.filter(
            patient=self.patient
        ).count()
        self.assertEqual(record_count_after, record_count_before)

    def test_patient_delete_view(self):
        """Doctor POST is rejected: clinical deletion is superuser-only."""
        response = self.client.post(
            reverse("patients:patient_delete", kwargs={"pk": self.patient.pk}),
            {"deletion_reason": "Test deletion"},
        )
        self.assertEqual(response.status_code, 403)
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_deleted)
        self.assertIsNone(self.patient.deleted_at)
        self.assertEqual(self.patient.deletion_reason, "")

    def test_permission_required(self):
        # Create a user without permissions (lifecycle gates cleared)
        create_navigation_user(
            username="noperms", email="noperms@example.com", password="testpassword"
        )

        # Log in as the user without permissions
        self.client.logout()
        self.client.login(username="noperms", password="testpassword")

        # Test create view
        response = self.client.get(reverse("patients:patient_create"))
        self.assertEqual(response.status_code, 403)  # Permission denied

        # Test update view
        response = self.client.get(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk})
        )
        self.assertEqual(response.status_code, 403)  # Permission denied

        # Test delete view (POST-only; non-superuser should get 403)
        response = self.client.post(
            reverse("patients:patient_delete", kwargs={"pk": self.patient.pk}),
            {"deletion_reason": "Test"},
        )
        self.assertEqual(response.status_code, 403)  # Superuser required

    def test_patient_create_with_explicit_gender(self):
        """Test patient creation with explicit NOT_INFORMED gender"""
        self.client.post(
            reverse("patients:patient_create"),
            {
                "name": "Default Gender Patient",
                "birthday": "1990-01-01",
                "gender": Patient.GenderChoices.NOT_INFORMED,
                "initial_record_number": "REC001",
            },
        )
        self.assertEqual(
            Patient.objects.filter(name="Default Gender Patient").count(), 1
        )

        # Verify gender was saved correctly
        patient = Patient.objects.get(name="Default Gender Patient")
        self.assertEqual(patient.gender, Patient.GenderChoices.NOT_INFORMED)

    def test_patient_create_with_all_gender_choices(self):
        """Test patient creation with all valid gender choices"""
        gender_choices = [
            Patient.GenderChoices.MALE,
            Patient.GenderChoices.FEMALE,
            Patient.GenderChoices.OTHER,
            Patient.GenderChoices.NOT_INFORMED,
        ]

        for i, gender in enumerate(gender_choices):
            patient_name = f"Gender Test Patient {i}"
            self.client.post(
                reverse("patients:patient_create"),
                {
                    "name": patient_name,
                    # Distinct birthdays avoid the name-and-birthday advisory
                    # review, keeping this test focused on gender storage.
                    "birthday": f"1990-01-{i + 1:02d}",
                    "gender": gender,
                    "initial_record_number": f"REC00{i + 1}",
                },
            )

            # Check patient was created successfully
            self.assertEqual(Patient.objects.filter(name=patient_name).count(), 1)

            # Verify gender was saved correctly
            patient = Patient.objects.get(name=patient_name)
            self.assertEqual(patient.gender, gender)

    def test_patient_update_gender_change(self):
        """Test updating patient gender"""
        # Start with default gender
        self.assertEqual(self.patient.gender, Patient.GenderChoices.NOT_INFORMED)

        # Update to male
        self.client.post(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk}),
            {
                "name": self.patient.name,
                "birthday": self.patient.birthday,
                "gender": Patient.GenderChoices.MALE,
                "status": self.patient.status,
            },
        )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.gender, Patient.GenderChoices.MALE)

        # Update to female
        self.client.post(
            reverse("patients:patient_update", kwargs={"pk": self.patient.pk}),
            {
                "name": self.patient.name,
                "birthday": self.patient.birthday,
                "gender": Patient.GenderChoices.FEMALE,
                "status": self.patient.status,
            },
        )

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.gender, Patient.GenderChoices.FEMALE)

    def test_patient_detail_view_displays_gender(self):
        """Test that patient detail view displays gender information"""
        # Update patient to have a specific gender
        self.patient.gender = Patient.GenderChoices.MALE
        self.patient.save()

        response = self.client.get(
            reverse("patients:patient_detail", kwargs={"pk": self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Check that gender information is in the response
        self.assertContains(response, "Masculino")  # Portuguese label for male


class PatientDeleteRouteSuperuserOnlyTests(TestCase):
    """S1: the clinical delete route accepts superuser POSTs only.

    Authorization is enforced inside ``post()`` so the route stays POST-only:
    an authenticated GET keeps returning 405 instead of rendering a
    confirmation page, while anonymous callers keep the pre-existing login
    redirect for both methods.
    """

    REASON = "Duplicate record created in error"

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="delete_doctor",
            email="delete_doctor@example.com",
            password="testpassword",
            profession_type=0,  # MEDICAL_DOCTOR
        )
        content_type = ContentType.objects.get_for_model(Patient)
        cls.doctor.user_permissions.add(
            *Permission.objects.filter(content_type=content_type)
        )
        cls.staff = create_navigation_user(
            username="delete_staff",
            email="delete_staff@example.com",
            password="testpassword",
            is_staff=True,
        )
        cls.superuser = create_navigation_user(
            username="delete_superuser",
            email="delete_superuser@example.com",
            password="testpassword",
            is_staff=True,
            is_superuser=True,
        )
        cls.patient = Patient.objects.create(
            name="Delete Route Patient",
            birthday="1985-03-04",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.delete_url = reverse(
            "patients:patient_delete", kwargs={"pk": self.patient.pk}
        )

    def _post_delete(self, user, deletion_reason):
        self.client.force_login(user)
        return self.client.post(self.delete_url, {"deletion_reason": deletion_reason})

    def _patient_record(self):
        return Patient.all_objects.get(pk=self.patient.pk)

    def test_doctor_post_is_forbidden(self):
        """R1: a doctor holding patients.delete_patient still gets 403."""
        response = self._post_delete(self.doctor, self.REASON)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self._patient_record().is_deleted)
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())

    def test_staff_non_superuser_post_is_forbidden(self):
        """R1: staff-but-not-superuser is also rejected."""
        response = self._post_delete(self.staff, self.REASON)

        self.assertEqual(response.status_code, 403)
        record = self._patient_record()
        self.assertFalse(record.is_deleted)
        self.assertIsNone(record.deleted_by)
        self.assertEqual(record.deletion_reason, "")

    def test_superuser_post_soft_deletes(self):
        """R2: superuser POST with a reason keeps the soft-delete behavior."""
        response = self._post_delete(self.superuser, self.REASON)

        self.assertRedirects(
            response,
            reverse("patients:patient_list"),
            fetch_redirect_response=False,
        )
        record = self._patient_record()
        self.assertTrue(record.is_deleted)
        self.assertEqual(record.deleted_by, self.superuser)
        self.assertEqual(record.deletion_reason, self.REASON)
        self.assertIsNotNone(record.deleted_at)
        self.assertFalse(Patient.objects.filter(pk=self.patient.pk).exists())

    def test_superuser_post_without_reason_deletes_nothing(self):
        """R3: empty or whitespace-only reasons keep the patient active."""
        for deletion_reason in ("", "   ", "\n\t "):
            with self.subTest(deletion_reason=deletion_reason):
                response = self._post_delete(self.superuser, deletion_reason)

                self.assertRedirects(
                    response,
                    reverse("patients:patient_detail", kwargs={"pk": self.patient.pk}),
                    fetch_redirect_response=False,
                )
                messages = [str(m) for m in get_messages(response.wsgi_request)]
                self.assertIn("Deletion reason is required.", messages)
                record = self._patient_record()
                self.assertFalse(record.is_deleted)
                self.assertIsNone(record.deleted_by)
                self.assertEqual(record.deletion_reason, "")

    def test_anonymous_post_redirects_to_login(self):
        """R4: anonymous POST keeps the login redirect."""
        response = self.client.post(self.delete_url, {"deletion_reason": self.REASON})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(LOGIN_URL))
        self.assertFalse(self._patient_record().is_deleted)

    def test_anonymous_get_redirects_to_login(self):
        """R5/R4: anonymous GET keeps the login redirect, not a 405 or 200."""
        response = self.client.get(self.delete_url)

        self.assertRedirects(
            response,
            f"{LOGIN_URL}?next={self.delete_url}",
            fetch_redirect_response=False,
        )
        record = self._patient_record()
        self.assertFalse(record.is_deleted)
        self.assertIsNone(record.deleted_by)
        self.assertEqual(record.deletion_reason, "")

    def test_get_is_not_allowed_for_authenticated_callers(self):
        """R5: no confirmation page; GET stays 405 for every session role."""
        for user in (self.doctor, self.staff, self.superuser):
            with self.subTest(username=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.delete_url).status_code, 405)


class CatalogueViewAuthorityTests(TestCase):
    """S2 R4: catalogue mutation routes require administrator authority."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = create_navigation_user(
            username="catalogue_route_admin",
            email="croute@example.com",
            password="testpassword",
            is_staff=True,
            is_superuser=True,
        )
        cls.staff = create_navigation_user(
            username="catalogue_route_staff",
            email="cstaff@example.com",
            password="testpassword",
            is_staff=True,
        )
        from ..models import AllowedTag

        cls.tag = AllowedTag.objects.create(
            name="Route Tag", created_by=cls.admin, updated_by=cls.admin
        )

    def test_ordinary_staff_denied_on_every_catalogue_route(self):
        self.client.force_login(self.staff)
        urls = [
            reverse("patients:tag_create"),
            reverse("patients:tag_update", kwargs={"pk": self.tag.pk}),
            reverse("patients:tag_delete", kwargs={"pk": self.tag.pk}),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_can_open_catalogue_routes(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("patients:tag_create")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("patients:tag_update", kwargs={"pk": self.tag.pk})
            ).status_code,
            200,
        )


class PatientDeleteUiAffordanceTests(TestCase):
    """S2: the clinical UI exposes no Excluir control toward patient_delete.

    Clinical deletion is superuser-only (S1) and the supported deletion
    surface is Django admin, so neither the patient detail nor the patient
    list page renders a link or form targeting the clinical delete route for
    any session role.
    """

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="ui_doctor",
            email="ui_doctor@example.com",
            password="testpassword",
            profession_type=0,  # MEDICAL_DOCTOR
        )
        content_type = ContentType.objects.get_for_model(Patient)
        cls.doctor.user_permissions.add(
            *Permission.objects.filter(content_type=content_type)
        )
        cls.superuser = create_navigation_user(
            username="ui_superuser",
            email="ui_superuser@example.com",
            password="testpassword",
            is_staff=True,
            is_superuser=True,
        )
        cls.patient = Patient.objects.create(
            name="UI Affordance Patient",
            birthday="1990-06-15",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.detail_url = reverse(
            "patients:patient_detail", kwargs={"pk": self.patient.pk}
        )
        self.list_url = reverse("patients:patient_list")
        self.delete_url = reverse(
            "patients:patient_delete", kwargs={"pk": self.patient.pk}
        )

    def _get_as(self, user, url):
        self.client.force_login(user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response

    def _assert_no_delete_control(self, response):
        html = response.content.decode()
        self.assertNotIn(self.delete_url, html)
        self.assertNotIn('name="deletion_reason"', html)
        self.assertNotIn("Excluir", html)

    def test_non_superuser_detail_has_no_delete_control(self):
        """R1: the detail page renders no control toward patient_delete."""
        response = self._get_as(self.doctor, self.detail_url)

        self.assertTemplateUsed(response, "patients/patient_detail.html")
        self._assert_no_delete_control(response)

    def test_superuser_detail_has_no_delete_control(self):
        """R1: even a superuser deletes through Django admin, not this page."""
        response = self._get_as(self.superuser, self.detail_url)

        self._assert_no_delete_control(response)

    def test_non_superuser_list_has_no_delete_control(self):
        """R2: the list page renders no control toward patient_delete."""
        response = self._get_as(self.doctor, self.list_url)

        self.assertTemplateUsed(response, "patients/patient_list.html")
        self.assertContains(response, self.patient.name)
        self._assert_no_delete_control(response)

    def test_superuser_list_has_no_delete_control(self):
        """R2: the list page offers no delete control to a superuser either."""
        response = self._get_as(self.superuser, self.list_url)

        self._assert_no_delete_control(response)

    def test_detail_keeps_timeline_and_edit_controls(self):
        """R4: Timeline and Editar stay on the detail page."""
        response = self._get_as(self.doctor, self.detail_url)

        timeline_url = reverse(
            "patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        update_url = reverse("patients:patient_update", kwargs={"pk": self.patient.pk})
        self.assertContains(response, f'href="{timeline_url}"')
        self.assertContains(response, "Timeline")
        self.assertContains(response, f'href="{update_url}"')
        self.assertContains(response, "Editar")

    def test_list_keeps_detail_and_edit_controls(self):
        """R4: the list row keeps Ver detalhes and Editar actions."""
        response = self._get_as(self.doctor, self.list_url)

        update_url = reverse("patients:patient_update", kwargs={"pk": self.patient.pk})
        self.assertContains(response, f'href="{self.patient.get_absolute_url()}"')
        self.assertContains(response, f'href="{update_url}"')
        self.assertContains(response, 'title="Editar"')
