from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport
from apps.dischargereports.utils import clean_text_field, clean_discharge_report_text_fields
from datetime import date, datetime
from django.utils import timezone

User = get_user_model()


class TextCleaningTests(TestCase):
    """Test text cleaning functionality for discharge reports"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=0  # MEDICAL_DOCTOR
        )
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )

    def test_clean_text_field_removes_word_breaks(self):
        """Test that linebreaks between words are removed"""
        text_with_breaks = 'Paciente apresenta\nsintomas de dor\nabdominal durante\na internação.'
        expected = 'Paciente apresenta sintomas de dor abdominal durante a internação.'
        result = clean_text_field(text_with_breaks)
        self.assertEqual(result, expected)

    def test_clean_text_field_preserves_sentence_breaks(self):
        """Test that linebreaks after periods are preserved"""
        text_with_sentences = 'Diagnóstico principal: diabetes.\nTratamento realizado com sucesso.\nPaciente estável.'
        result = clean_text_field(text_with_sentences)
        self.assertIn('diabetes.\nTratamento', result)
        self.assertIn('sucesso.\nPaciente', result)

    def test_clean_text_field_preserves_paragraph_breaks(self):
        """Test that double linebreaks (paragraphs) are preserved"""
        text_with_paragraphs = 'História clínica:\n\nPaciente internado com quadro agudo.\n\nExames realizados mostram melhora.'
        result = clean_text_field(text_with_paragraphs)
        self.assertIn('clínica:\n\nPaciente', result)
        self.assertIn('agudo.\n\nExames', result)

    def test_clean_text_field_handles_edge_cases(self):
        """Test edge cases for text cleaning"""
        # Empty string
        self.assertEqual(clean_text_field(''), '')
        
        # None value
        self.assertIsNone(clean_text_field(None))
        
        # Just spaces
        self.assertEqual(clean_text_field('   '), '')
        
        # Multiple spaces
        result = clean_text_field('Paciente    apresenta     sintomas  diversos.')
        self.assertEqual(result, 'Paciente apresenta sintomas diversos.')

    def test_clean_text_field_handles_unicode(self):
        """Test that Unicode characters are handled correctly"""
        unicode_text = 'Paciente\napresenta histórico\nde condições\ncardíacas.'
        result = clean_text_field(unicode_text)
        expected = 'Paciente apresenta histórico de condições cardíacas.'
        self.assertEqual(result, expected)

    def test_discharge_report_text_cleaning_on_save(self):
        """Test that discharge report fields are cleaned automatically on save"""
        # Create discharge report with problematic linebreaks
        report = DischargeReport(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now(),
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 7),
            medical_specialty='Medicina Interna',
            admission_history='Paciente internado\ncom quadro de\nfebre alta.',
            problems_and_diagnosis='Diagnóstico principal:\npneumonia.\nQuadro estável.',
            discharge_recommendations='Repouso domiciliar.\nRetorno em 7 dias.'
        )
        
        # Save the report (should trigger cleaning)
        report.save()
        
        # Check that word breaks were removed
        self.assertNotIn('internado\ncom', report.admission_history)
        self.assertIn('internado com', report.admission_history)
        
        # Check that sentence breaks after periods were preserved
        self.assertIn('pneumonia.\nQuadro', report.problems_and_diagnosis)
        
        # Check that sentence breaks after periods were preserved
        self.assertIn('domiciliar.\nRetorno', report.discharge_recommendations)

    def test_clean_discharge_report_text_fields_function(self):
        """Test the clean_discharge_report_text_fields function directly"""
        report = DischargeReport(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now(),
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 7),
            medical_specialty='Medicina Interna',
            exams_list='Exame de\nsangue realizado\ncom sucesso.',
            procedures_list='Procedimento cirúrgico.\nSem intercorrências.'
        )
        
        # Apply cleaning function
        clean_discharge_report_text_fields(report)
        
        # Check results
        self.assertEqual(report.exams_list, 'Exame de sangue realizado com sucesso.')
        self.assertIn('cirúrgico.\nSem', report.procedures_list)

    def test_mixed_content_scenarios(self):
        """Test realistic mixed content scenarios"""
        mixed_text = '''História da internação:

Paciente do sexo masculino,
65 anos, internado com
quadro de dispneia.

Exames realizados:
- Raio-X de tórax.
- Hemograma completo.
- Gasometria arterial.

Evolução favorável durante
o período de internação.'''
        
        result = clean_text_field(mixed_text)
        
        # Should preserve paragraph breaks
        self.assertIn('internação:\n\nPaciente', result)
        self.assertIn('dispneia.\n\nExames', result)
        
        # Should clean word breaks
        self.assertIn('masculino, 65 anos, internado', result)
        self.assertIn('favorável durante o período', result)
        
        # Should preserve breaks after periods in lists
        self.assertIn('tórax.\n-', result)
        self.assertIn('completo.\n-', result)