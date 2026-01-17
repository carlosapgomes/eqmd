from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.botauth.models import MatrixUserBinding
from apps.matrix_integration.models import MatrixBotConversationState, MatrixDirectRoom
from apps.patients.models import Patient, PatientAdmission, PatientRecordNumber, Ward

from apps.matrix_integration.bot.processor import BotMessageProcessor


class BotConversationFlowTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.matrix_user_id = "@joao:matrix.test"
        self.room_id = "!room:matrix.test"
        MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id=self.matrix_user_id,
            verified=True,
            delegation_enabled=True,
        )
        MatrixDirectRoom.objects.create(user=self.user, room_id=self.room_id)

        self.ward = Ward.objects.create(
            name="Clinica Medica",
            abbreviation="CM",
            created_by=self.user,
            updated_by=self.user,
        )

        self.patient = Patient.objects.create(
            name="Joao da Silva",
            birthday=timezone.now().date() - timedelta(days=365 * 40),
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.INPATIENT,
            bed="101",
            ward=self.ward,
            current_record_number="12345",
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number="12345",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )
        self.admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="101",
            ward=self.ward,
            created_by=self.user,
            updated_by=self.user,
        )

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_see_patient_in_search", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_access_patient", return_value=True)
    def test_search_then_select_flow(self, *_mocks):
        processor = BotMessageProcessor()
        search_result = processor.handle_message(
            self.room_id,
            self.matrix_user_id,
            "/buscar Joao",
        )

        self.assertTrue(search_result.responses)
        self.assertIn("Joao da Silva", search_result.responses[0])
        self.assertTrue(
            MatrixBotConversationState.objects.filter(room_id=self.room_id).exists()
        )

        selection_result = processor.handle_message(
            self.room_id,
            self.matrix_user_id,
            "1",
        )
        self.assertTrue(selection_result.responses)
        self.assertIn("Joao da Silva", selection_result.responses[0])
        self.assertIn("12345", selection_result.responses[0])
        self.assertFalse(
            MatrixBotConversationState.objects.filter(room_id=self.room_id).exists()
        )

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_see_patient_in_search", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_access_patient", return_value=True)
    def test_state_timeout_clears_pending_selection(self, *_mocks):
        processor = BotMessageProcessor()
        processor.handle_message(self.room_id, self.matrix_user_id, "/buscar Joao")

        MatrixBotConversationState.objects.filter(room_id=self.room_id).update(
            updated_at=timezone.now() - timedelta(minutes=10)
        )

        result = processor.handle_message(self.room_id, self.matrix_user_id, "1")
        self.assertTrue(result.responses)
        self.assertIn("expirada", result.responses[0].lower())
        self.assertFalse(
            MatrixBotConversationState.objects.filter(room_id=self.room_id).exists()
        )


class BotInputValidationTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.matrix_user_id = "@joao:matrix.test"
        self.room_id = "!room:matrix.test"
        MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id=self.matrix_user_id,
            verified=True,
            delegation_enabled=True,
        )
        MatrixDirectRoom.objects.create(user=self.user, room_id=self.room_id)

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=True)
    def test_rejects_oversized_command(self, _mock_perm):
        processor = BotMessageProcessor()
        long_message = "/buscar " + ("x" * 201)
        result = processor.handle_message(self.room_id, self.matrix_user_id, long_message)

        self.assertTrue(result.responses)
        self.assertIn("longo", result.responses[0].lower())

    def test_unknown_command_returns_help(self):
        processor = BotMessageProcessor()
        result = processor.handle_message(self.room_id, self.matrix_user_id, "/foo")

        self.assertTrue(result.responses)
        self.assertIn("!buscar", result.responses[0])


class BotPermissionTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.matrix_user_id = "@joao:matrix.test"
        self.room_id = "!room:matrix.test"
        MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id=self.matrix_user_id,
            verified=True,
            delegation_enabled=True,
        )
        MatrixDirectRoom.objects.create(user=self.user, room_id=self.room_id)

        ward = Ward.objects.create(
            name="Clinica Medica",
            abbreviation="CM",
            created_by=self.user,
            updated_by=self.user,
        )
        patient = Patient.objects.create(
            name="Maria", 
            birthday=timezone.now().date() - timedelta(days=365 * 30),
            gender=Patient.GenderChoices.FEMALE,
            status=Patient.Status.INPATIENT,
            bed="101",
            ward=ward,
            current_record_number="999",
            created_by=self.user,
            updated_by=self.user,
        )
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number="999",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )
        PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="101",
            ward=ward,
            created_by=self.user,
            updated_by=self.user,
        )

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=False)
    def test_search_denied_without_permission(self, _mock_perm):
        processor = BotMessageProcessor()
        result = processor.handle_message(self.room_id, self.matrix_user_id, "/buscar Maria")

        self.assertTrue(result.responses)
        self.assertIn("permiss", result.responses[0].lower())

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_see_patient_in_search", return_value=False)
    def test_search_filters_patients_without_visibility(self, *_mocks):
        processor = BotMessageProcessor()
        result = processor.handle_message(self.room_id, self.matrix_user_id, "/buscar Maria")

        self.assertTrue(result.responses)
        self.assertIn("nenhum", result.responses[0].lower())

    @mock.patch("apps.matrix_integration.bot.processor.can_view_patients", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_see_patient_in_search", return_value=True)
    @mock.patch("apps.matrix_integration.bot.processor.can_access_patient", return_value=False)
    def test_selection_denied_without_access(self, *_mocks):
        processor = BotMessageProcessor()
        processor.handle_message(self.room_id, self.matrix_user_id, "/buscar Maria")
        result = processor.handle_message(self.room_id, self.matrix_user_id, "1")

        self.assertTrue(result.responses)
        self.assertIn("permiss", result.responses[0].lower())
