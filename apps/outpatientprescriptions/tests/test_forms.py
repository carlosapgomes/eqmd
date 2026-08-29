from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.drugtemplates.models import DrugTemplate
from apps.outpatientprescriptions.forms.prescription_forms import (
    OutpatientPrescriptionForm,
    PrescriptionItemForm,
    PrescriptionItemFormSet,
    PrescriptionItemFormSetHelper,
)
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.patients.models import Patient

User = get_user_model()


class OutpatientPrescriptionFormTest(TestCase):
    """Test cases for OutpatientPrescriptionForm."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=0,  # Doctor
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription for patient",
            "instructions": "Take all medications as prescribed",
            "status": "draft",
            "prescription_date": timezone.now().date(),
        }

        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())

        # Check that required fields are in errors.
        # description is not a form field (Meta.fields) and instructions is
        # explicitly optional (required=False in __init__), so neither can be
        # in form.errors.
        self.assertIn("patient", form.errors)
        self.assertIn("event_datetime", form.errors)
        self.assertIn("prescription_date", form.errors)
        self.assertIn("status", form.errors)
        self.assertNotIn("description", form.errors)
        self.assertNotIn("instructions", form.errors)

    def test_form_default_prescription_date(self):
        """Test that form sets default prescription date for new instances.

        The initial value is a 'YYYY-MM-DD' string because the field uses an
        HTML5 date input; the view renders it directly into the input value.
        """
        form = OutpatientPrescriptionForm(user=self.user)
        initial = form.fields["prescription_date"].initial
        self.assertIsInstance(initial, str)
        self.assertEqual(date.fromisoformat(initial), timezone.localdate())

    def test_form_save_sets_creator(self):
        """Test that form save method sets creator correctly."""
        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription",
            "instructions": "Test instructions",
            "status": "draft",
            "prescription_date": timezone.now().date(),
        }

        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

        prescription = form.save(commit=False)
        prescription.updated_by = self.user  # Set updated_by field
        prescription.save()
        self.assertEqual(prescription.created_by, self.user)
        self.assertEqual(prescription.patient, self.patient)

    def test_form_widget_classes(self):
        """Test that form widgets have correct CSS classes."""
        form = OutpatientPrescriptionForm(user=self.user)

        # EventForm.__init__ applies 'form-control' to every field widget,
        # including the status RadioSelect.
        for field_name in [
            "patient",
            "event_datetime",
            "instructions",
            "status",
            "prescription_date",
        ]:
            self.assertIn("form-control", form.fields[field_name].widget.attrs["class"])
        self.assertIsInstance(form.fields["status"].widget, forms.RadioSelect)

    def test_form_field_labels(self):
        """Test that form fields have correct labels."""
        form = OutpatientPrescriptionForm(user=self.user)

        self.assertEqual(form.fields["patient"].label, "Paciente")
        self.assertEqual(form.fields["event_datetime"].label, "Data e Hora da Receita")
        self.assertEqual(form.fields["instructions"].label, "Instruções Gerais")
        self.assertEqual(form.fields["status"].label, "Status")
        self.assertEqual(form.fields["prescription_date"].label, "Data da Receita")

    def test_form_help_texts(self):
        """Test that form fields have the current help-text contract.

        The help texts are commented out in the form (instructions/description
        guidance is carried by labels and placeholders), so the contract is an
        empty help text for the instructions field.
        """
        form = OutpatientPrescriptionForm(user=self.user)

        self.assertEqual(form.fields["instructions"].help_text, "")
        self.assertEqual(form.fields["patient"].help_text, "")
        self.assertNotIn("description", form.fields)

    def test_form_status_choices(self):
        """Test that status field has correct choices."""
        form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription",
            "instructions": "Test instructions",
            "status": "finalized",
            "prescription_date": timezone.now().date(),
        }

        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

        # Event.updated_by is NOT NULL, so the caller must set it before save.
        prescription = form.save(commit=False)
        prescription.updated_by = self.user
        prescription.save()
        self.assertEqual(prescription.status, "finalized")


class PrescriptionItemFormTest(TestCase):
    """Test cases for PrescriptionItemForm."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=0,  # Doctor
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.drug_template = DrugTemplate.objects.create(
            name="Test Drug",
            concentration="10mg",
            pharmaceutical_form="tablet",
            usage_instructions="Take 1 tablet daily",
            creator=cls.user,
            is_public=True,
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "drug_name": "Paracetamol",
            "presentation": "500mg comprimidos",
            "usage_instructions": "Tomar 1 comprimido de 8 em 8 horas",
            "quantity": "21 comprimidos",
            "order": 1,
            "source_template": "",  # Empty source template
        }

        form = PrescriptionItemForm(data=form_data, user=self.user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = PrescriptionItemForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())

        # Check that required fields are in errors
        self.assertIn("drug_name", form.errors)
        self.assertIn("presentation", form.errors)
        self.assertIn("usage_instructions", form.errors)
        self.assertIn("quantity", form.errors)

    def test_form_field_labels(self):
        """Test that form fields have correct labels."""
        form = PrescriptionItemForm(user=self.user)

        self.assertEqual(form.fields["drug_name"].label, "Medicamento")
        self.assertEqual(form.fields["presentation"].label, "Apresentação")
        self.assertEqual(form.fields["usage_instructions"].label, "Instruções de Uso")
        self.assertEqual(form.fields["quantity"].label, "Quantidade")

    def test_form_widget_classes(self):
        """Test that form widgets have correct CSS classes."""
        form = PrescriptionItemForm(user=self.user)

        # Check that widgets have Bootstrap classes
        self.assertIn("form-control", form.fields["drug_name"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["presentation"].widget.attrs["class"])
        self.assertIn(
            "form-control", form.fields["usage_instructions"].widget.attrs["class"]
        )
        self.assertIn("form-control", form.fields["quantity"].widget.attrs["class"])

    def test_clean_order_method(self):
        """Test clean_order method sets minimum value to 1."""
        form_data = {
            "drug_name": "Test Drug",
            "presentation": "10mg tablet",
            "usage_instructions": "Take daily",
            "quantity": "30",
            "order": 0,  # Valid for PositiveIntegerField; clean_order -> 1
            "source_template": "",
        }

        form = PrescriptionItemForm(data=form_data, user=self.user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["order"], 1)

    def test_clean_order_none_value(self):
        """Test that a missing order fails validation.

        The order field is a required PositiveIntegerField, so an absent value
        is rejected by field validation before clean_order can run.
        """
        form_data = {
            "drug_name": "Test Drug",
            "presentation": "10mg tablet",
            "usage_instructions": "Take daily",
            "quantity": "30",
            "source_template": "",
            # order not provided
        }

        form = PrescriptionItemForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("order", form.errors)

    def test_drug_template_field_with_user(self):
        """Test that drug_template field is updated with user context."""
        form = PrescriptionItemForm(user=self.user)

        # Check that drug_template field exists
        self.assertIn("drug_template", form.fields)
        self.assertEqual(form.fields["drug_template"].label, "Template de Medicamento")

    def test_form_widget_placeholders(self):
        """Test that form widgets have correct placeholders."""
        form = PrescriptionItemForm(user=self.user)

        self.assertEqual(
            form.fields["drug_name"].widget.attrs["placeholder"], "Nome do medicamento"
        )
        self.assertEqual(
            form.fields["presentation"].widget.attrs["placeholder"],
            "Ex: 500mg comprimidos, 120ml xarope",
        )
        self.assertEqual(
            form.fields["usage_instructions"].widget.attrs["placeholder"],
            "Ex: Tomar 1 comprimido de 8 em 8 horas por 7 dias",
        )
        self.assertEqual(
            form.fields["quantity"].widget.attrs["placeholder"],
            "Ex: 21 comprimidos, 1 frasco",
        )


class PrescriptionItemFormSetTest(TestCase):
    """Test cases for PrescriptionItemFormSet."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=0,  # Doctor
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_formset_creation(self):
        """Test creating a formset."""
        formset = PrescriptionItemFormSet(instance=self.prescription)

        # Check formset properties (extra=0, min_num=1 per the inline factory)
        self.assertEqual(formset.model, PrescriptionItem)
        self.assertTrue(formset.can_delete)
        self.assertEqual(formset.min_num, 1)
        self.assertEqual(formset.extra, 0)

    def test_formset_valid_data(self):
        """Test formset with valid data."""
        # The inline formset prefix derives from the FK related_name ('items').
        formset_data = {
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Paracetamol",
            "items-0-presentation": "500mg comprimidos",
            "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas",
            "items-0-quantity": "21 comprimidos",
            "items-0-order": "1",
            "items-1-drug_name": "Ibuprofeno",
            "items-1-presentation": "400mg comprimidos",
            "items-1-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas se dor",
            "items-1-quantity": "20 comprimidos",
            "items-1-order": "2",
        }

        formset = PrescriptionItemFormSet(data=formset_data, instance=self.prescription)

        self.assertTrue(formset.is_valid())
        formset.save()
        self.assertEqual(self.prescription.items.count(), 2)

    def test_formset_minimum_forms_validation(self):
        """Test that formset requires at least one form."""
        formset_data = {
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            # Empty form data - should fail validation
            "items-0-drug_name": "",
            "items-0-presentation": "",
            "items-0-usage_instructions": "",
            "items-0-quantity": "",
            "items-0-order": "1",
        }

        formset = PrescriptionItemFormSet(data=formset_data, instance=self.prescription)

        self.assertFalse(formset.is_valid())

    def test_formset_delete_functionality(self):
        """Test formset delete functionality with min_num=1."""
        # Create two existing items so one can be deleted without violating
        # the min_num=1 constraint.
        item1 = PrescriptionItem.objects.create(
            prescription=self.prescription,
            drug_name="Test Drug",
            presentation="10mg tablet",
            usage_instructions="Take daily",
            quantity="30",
            order=1,
        )
        item2 = PrescriptionItem.objects.create(
            prescription=self.prescription,
            drug_name="Keep Drug",
            presentation="20mg tablet",
            usage_instructions="Take twice daily",
            quantity="60",
            order=2,
        )

        formset_data = {
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "2",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(item1.pk),
            "items-0-drug_name": "Test Drug",
            "items-0-presentation": "10mg tablet",
            "items-0-usage_instructions": "Take daily",
            "items-0-quantity": "30",
            "items-0-order": "1",
            "items-0-DELETE": "on",  # Mark for deletion
            "items-1-id": str(item2.pk),
            "items-1-drug_name": "Keep Drug",
            "items-1-presentation": "20mg tablet",
            "items-1-usage_instructions": "Take twice daily",
            "items-1-quantity": "60",
            "items-1-order": "2",
        }

        formset = PrescriptionItemFormSet(data=formset_data, instance=self.prescription)

        self.assertTrue(formset.is_valid())
        self.assertIn(formset.forms[0], formset.deleted_forms)
        formset.save()

        # Only the deleted item is removed
        self.assertFalse(PrescriptionItem.objects.filter(pk=item1.pk).exists())
        self.assertTrue(PrescriptionItem.objects.filter(pk=item2.pk).exists())


class PrescriptionItemFormSetHelperTest(TestCase):
    """Test cases for PrescriptionItemFormSetHelper."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=0,  # Doctor
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description="Test Prescription",
            instructions="Test instructions",
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_get_formset_with_user(self):
        """Test get_formset_with_user method."""
        formset = PrescriptionItemFormSetHelper.get_formset_with_user(
            self.user, instance=self.prescription
        )

        # Check that formset was created
        self.assertIsNotNone(formset)

        # Check that user was passed to forms
        for form in formset:
            self.assertEqual(form.user, self.user)

    def test_prepare_formset_data(self):
        """Test prepare_formset_data method."""
        formset = PrescriptionItemFormSet(instance=self.prescription)
        formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)

        # Check that all expected keys are present
        expected_keys = ["formset", "management_form", "empty_form", "can_delete"]
        for key in expected_keys:
            self.assertIn(key, formset_data)

        # Check values
        self.assertEqual(formset_data["formset"], formset)
        self.assertEqual(formset_data["management_form"], formset.management_form)
        self.assertEqual(formset_data["can_delete"], formset.can_delete)
        # empty_form is rebuilt on each property access, so compare the field
        # contract instead of instance identity.
        self.assertEqual(
            list(formset_data["empty_form"].fields.keys()),
            list(formset.empty_form.fields.keys()),
        )


class FormIntegrationTest(TestCase):
    """Integration tests for forms working together."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            profession_type=0,  # Doctor
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_complete_prescription_creation_workflow(self):
        """Test complete workflow of creating prescription with items."""
        # Create prescription form
        prescription_form_data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now(),
            "description": "Test prescription for complete workflow",
            "instructions": "Take all medications as prescribed",
            "status": "draft",
            "prescription_date": timezone.now().date(),
        }

        prescription_form = OutpatientPrescriptionForm(
            data=prescription_form_data, user=self.user
        )

        self.assertTrue(prescription_form.is_valid())
        prescription = prescription_form.save(commit=False)
        prescription.updated_by = self.user
        prescription.save()

        # Create formset with items (inline formset prefix: 'items')
        formset_data = {
            "items-TOTAL_FORMS": "2",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-drug_name": "Paracetamol",
            "items-0-presentation": "500mg comprimidos",
            "items-0-usage_instructions": "Tomar 1 comprimido de 8 em 8 horas",
            "items-0-quantity": "21 comprimidos",
            "items-0-order": "1",
            "items-1-drug_name": "Ibuprofeno",
            "items-1-presentation": "400mg comprimidos",
            "items-1-usage_instructions": "Tomar 1 comprimido se dor",
            "items-1-quantity": "10 comprimidos",
            "items-1-order": "2",
        }

        formset = PrescriptionItemFormSet(data=formset_data, instance=prescription)

        self.assertTrue(formset.is_valid())
        formset.save()

        # Verify everything was created correctly
        self.assertEqual(prescription.items.count(), 2)

        items = prescription.items.all().order_by("order")
        item1 = items[0]
        self.assertEqual(item1.drug_name, "Paracetamol")
        self.assertEqual(item1.order, 1)

        item2 = items[1]
        self.assertEqual(item2.drug_name, "Ibuprofeno")
        self.assertEqual(item2.order, 2)
