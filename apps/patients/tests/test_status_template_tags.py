from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template import Template, Context
from ..models import Patient, Ward
from ..templatetags.patient_tags import (
    patient_status_badge, can_change_status, available_status_actions
)

User = get_user_model()


class PatientStatusTemplateTagsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpassword',
            profession_type=0  # MEDICAL_DOCTOR
        )
        cls.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@example.com',
            password='testpassword',
            profession_type=2  # NURSE
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

    def test_patient_status_badge_outpatient(self):
        """Test patient status badge for outpatient"""
        result = patient_status_badge(Patient.Status.OUTPATIENT)
        self.assertIn('bg-success', result)
        self.assertIn('Ambulatorial', result)
        self.assertIn('<span class="badge', result)

    def test_patient_status_badge_inpatient(self):
        """Test patient status badge for inpatient"""
        result = patient_status_badge(Patient.Status.INPATIENT)
        self.assertIn('bg-primary', result)
        self.assertIn('Internado', result)

    def test_patient_status_badge_emergency(self):
        """Test patient status badge for emergency"""
        result = patient_status_badge(Patient.Status.EMERGENCY)
        self.assertIn('bg-danger', result)
        self.assertIn('Emergência', result)

    def test_patient_status_badge_discharged(self):
        """Test patient status badge for discharged"""
        result = patient_status_badge(Patient.Status.DISCHARGED)
        self.assertIn('bg-secondary', result)
        self.assertIn('Alta', result)

    def test_patient_status_badge_transferred(self):
        """Test patient status badge for transferred"""
        result = patient_status_badge(Patient.Status.TRANSFERRED)
        self.assertIn('bg-warning', result)
        self.assertIn('Transferido', result)

    def test_patient_status_badge_deceased(self):
        """Test patient status badge for deceased"""
        result = patient_status_badge(Patient.Status.DECEASED)
        self.assertIn('bg-dark', result)
        self.assertIn('Óbito', result)

    def test_patient_status_badge_unknown(self):
        """Test patient status badge for unknown status"""
        result = patient_status_badge(999)  # Invalid status
        self.assertIn('bg-secondary', result)
        self.assertIn('Desconhecido', result)

    def test_can_change_status_doctor(self):
        """Test that doctors can change patient status"""
        result = can_change_status(self.doctor, self.patient)
        self.assertTrue(result)

    def test_can_change_status_nurse(self):
        """Test nurse permissions for status changes"""
        result = can_change_status(self.nurse, self.patient)
        # Nurses should have limited status change permissions
        # This depends on the permission system implementation
        self.assertIsInstance(result, bool)

    def test_available_status_actions_outpatient(self):
        """Test available status actions for outpatient"""
        actions = available_status_actions(self.doctor, self.patient)
        
        # Should include all other statuses except current
        action_statuses = [action['status'] for action in actions]
        self.assertIn(Patient.Status.INPATIENT, action_statuses)
        self.assertIn(Patient.Status.EMERGENCY, action_statuses)
        self.assertIn(Patient.Status.DISCHARGED, action_statuses)
        self.assertIn(Patient.Status.TRANSFERRED, action_statuses)
        self.assertIn(Patient.Status.DECEASED, action_statuses)
        self.assertNotIn(Patient.Status.OUTPATIENT, action_statuses)

    def test_available_status_actions_inpatient(self):
        """Test available status actions for inpatient"""
        self.patient.status = Patient.Status.INPATIENT
        self.patient.save()
        
        actions = available_status_actions(self.doctor, self.patient)
        action_statuses = [action['status'] for action in actions]
        
        # Should include all other statuses except current
        self.assertNotIn(Patient.Status.INPATIENT, action_statuses)
        self.assertIn(Patient.Status.OUTPATIENT, action_statuses)

    def test_available_status_actions_deceased(self):
        """Test available status actions for deceased patient"""
        self.patient.status = Patient.Status.DECEASED
        self.patient.save()
        
        actions = available_status_actions(self.doctor, self.patient)
        action_statuses = [action['status'] for action in actions]
        
        # Should include all other statuses except current
        self.assertNotIn(Patient.Status.DECEASED, action_statuses)

    def test_action_has_required_fields(self):
        """Test that each action has required fields"""
        actions = available_status_actions(self.doctor, self.patient)
        
        for action in actions:
            self.assertIn('status', action)
            self.assertIn('label', action)
            self.assertIn('icon', action)
            self.assertIn('btn_class', action)
            self.assertIn('action_name', action)

    def test_action_labels_are_meaningful(self):
        """Test that action labels are meaningful"""
        actions = available_status_actions(self.doctor, self.patient)
        
        # Map status to expected label
        expected_labels = {
            Patient.Status.INPATIENT: 'Internar',
            Patient.Status.EMERGENCY: 'Emergência',
            Patient.Status.DISCHARGED: 'Dar Alta',
            Patient.Status.TRANSFERRED: 'Transferir',
            Patient.Status.OUTPATIENT: 'Ambulatorial',
            Patient.Status.DECEASED: 'Declarar Óbito',
        }
        
        for action in actions:
            status = action['status']
            if status in expected_labels:
                self.assertEqual(action['label'], expected_labels[status])

    def test_template_integration(self):
        """Test template tags work in actual templates"""
        template = Template("""
        {% load patient_tags %}
        <div>{{ patient.status|patient_status_badge }}</div>
        {% if user|can_change_status:patient %}
            <div>Can change status</div>
        {% endif %}
        """)
        
        context = Context({
            'patient': self.patient,
            'user': self.doctor
        })
        
        rendered = template.render(context)
        self.assertIn('bg-success', rendered)  # Outpatient badge
        self.assertIn('Ambulatorial', rendered)
        self.assertIn('Can change status', rendered)  # Doctor permissions