from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.pdf_forms.services.field_mapping import DataFieldMapper, FieldMappingUtils
from apps.pdf_forms.tests.factories import PatientFactory, WardFactory
from unittest.mock import Mock


class DataFieldMapperTests(TestCase):
    """Test DataFieldMapper utility functions."""

    def setUp(self):
        pass  # DataFieldMapper is all static methods

    def test_get_available_patient_fields(self):
        """Test getting available patient fields."""
        fields = DataFieldMapper.get_available_patient_fields()
        
        # Should return a dictionary
        self.assertIsInstance(fields, dict)
        
        # Should contain expected fields
        self.assertIn('name', fields)
        self.assertIn('birthday', fields)
        self.assertIn('healthcard_number', fields)
        self.assertIn('gender', fields)
        self.assertIn('ward.name', fields)
        
        # Check structure of field data
        name_field = fields['name']
        self.assertEqual(name_field['type'], 'text')
        self.assertEqual(name_field['label'], 'Nome do Paciente')
        
        gender_field = fields['gender']
        self.assertEqual(gender_field['type'], 'choice')
        self.assertEqual(gender_field['label'], 'Sexo')
        
        ward_field = fields['ward.name']
        self.assertEqual(ward_field['type'], 'text')
        self.assertEqual(ward_field['label'], 'Nome da Ala')

    def test_validate_patient_field_mapping_valid(self):
        """Test validation of valid patient field mappings."""
        # Test valid field paths
        valid_fields = ['name', 'birthday', 'gender', 'ward.name', 'healthcard_number']
        
        for field_path in valid_fields:
            is_valid, error = DataFieldMapper.validate_patient_field_mapping('test_field', field_path)
            self.assertTrue(is_valid)
            self.assertIsNone(error)

    def test_validate_patient_field_mapping_invalid(self):
        """Test validation of invalid patient field mappings."""
        # Test invalid field paths
        invalid_fields = ['invalid_field', 'nonexistent.path', 'ward.invalid_field']
        
        for field_path in invalid_fields:
            is_valid, error = DataFieldMapper.validate_patient_field_mapping('test_field', field_path)
            self.assertFalse(is_valid)
            self.assertIn('Invalid patient field', error)

    def test_validate_patient_field_mapping_empty(self):
        """Test validation with empty field mapping."""
        is_valid, error = DataFieldMapper.validate_patient_field_mapping('test_field', '')
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        is_valid, error = DataFieldMapper.validate_patient_field_mapping('test_field', None)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_get_patient_field_value_simple(self):
        """Test getting simple field values from patient."""
        patient = PatientFactory(
            name='John Doe',
            healthcard_number='HC123456',
            phone='555-1234'
        )
        
        # Test direct field access
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'name'), 'John Doe')
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'healthcard_number'), 'HC123456')
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'phone'), '555-1234')

    def test_get_patient_field_value_related(self):
        """Test getting related field values from patient."""
        ward = WardFactory(name='ICU', abbreviation='ICU', floor=3)
        patient = PatientFactory(ward=ward)
        
        # Test related field access
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'ward.name'), 'ICU')
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'ward.abbreviation'), 'ICU')
        self.assertEqual(DataFieldMapper.get_patient_field_value(patient, 'ward.floor'), 3)

    def test_get_patient_field_value_none_handling(self):
        """Test handling of None values and invalid paths."""
        patient = PatientFactory(name='John Doe')
        
        # Test with None patient
        self.assertIsNone(DataFieldMapper.get_patient_field_value(None, 'name'))
        
        # Test with None field path
        self.assertIsNone(DataFieldMapper.get_patient_field_value(patient, None))
        self.assertIsNone(DataFieldMapper.get_patient_field_value(patient, ''))
        
        # Test with invalid field path
        self.assertIsNone(DataFieldMapper.get_patient_field_value(patient, 'invalid_field'))
        self.assertIsNone(DataFieldMapper.get_patient_field_value(patient, 'ward.invalid_field'))
        
        # Test with None related object
        self.assertIsNone(DataFieldMapper.get_patient_field_value(patient, 'ward.name'))

    def test_get_field_type_compatibility(self):
        """Test field type compatibility checking."""
        # Test compatible types
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('text', 'name'))
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('choice', 'status'))
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('date', 'birthday'))
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('number', 'total_admissions_count'))
        
        # Test incompatible types
        self.assertFalse(DataFieldMapper.get_field_type_compatibility('number', 'name'))
        self.assertFalse(DataFieldMapper.get_field_type_compatibility('date', 'phone'))

    def test_get_field_type_compatibility_edge_cases(self):
        """Test edge cases for field type compatibility."""
        # Test with invalid patient field path
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('text', 'invalid_field'))
        
        # Test with None patient field path
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('text', None))
        self.assertTrue(DataFieldMapper.get_field_type_compatibility('text', ''))


class FieldMappingUtilsTests(TestCase):
    """Test FieldMappingUtils utility functions."""

    def setUp(self):
        self.utils = FieldMappingUtils()

    def test_validate_field_config_valid(self):
        """Test validation of valid field configurations."""
        valid_config = {
            'patient_name': {
                'type': 'text',
                'label': 'Patient Name',
                'x': 5.0,
                'y': 10.0,
                'width': 8.0,
                'height': 0.7,
                'required': True
            },
            'blood_type': {
                'type': 'choice',
                'label': 'Blood Type',
                'choices': ['A+', 'A-', 'B+', 'B-'],
                'x': 15.0,
                'y': 10.0,
                'width': 3.0,
                'height': 0.7
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_field_config_invalid_structure(self):
        """Test validation of invalid field configuration structures."""
        # Test non-dict input
        is_valid, errors = FieldMappingUtils.validate_field_config("invalid")
        self.assertFalse(is_valid)
        self.assertIn("must be a dictionary", errors[0])
        
        # Test field with non-dict config
        invalid_config = {
            'field1': 'not_a_dict'
        }
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("must be a dictionary", errors[0])

    def test_validate_field_config_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_config = {
            'field1': {
                'type': 'text'
                # Missing 'label' field
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("missing required 'label'", errors[0])

    def test_validate_field_config_invalid_type(self):
        """Test validation with invalid field types."""
        invalid_config = {
            'field1': {
                'type': 'invalid_type',
                'label': 'Field 1'
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("invalid type 'invalid_type'", errors[0])

    def test_validate_field_config_invalid_coordinates(self):
        """Test validation with invalid coordinates."""
        invalid_config = {
            'field1': {
                'type': 'text',
                'label': 'Field 1',
                'x': 'invalid_number',
                'y': -5.0,
                'width': 0.0,
                'height': -1.0
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertTrue(any('invalid x coordinate' in error for error in errors))
        self.assertTrue(any('cannot be negative' in error for error in errors))

    def test_validate_field_config_invalid_font_size(self):
        """Test validation with invalid font size."""
        invalid_config = {
            'field1': {
                'type': 'text',
                'label': 'Field 1',
                'font_size': 'invalid'
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("must be an integer", errors[0])
        
        # Test out of range font size
        invalid_config['field1']['font_size'] = 100
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("must be between 6 and 72", errors[0])

    def test_validate_field_config_choice_fields(self):
        """Test validation of choice fields."""
        # Valid choice field
        valid_config = {
            'field1': {
                'type': 'choice',
                'label': 'Choice Field',
                'choices': ['Option 1', 'Option 2']
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Missing choices
        invalid_config = {
            'field1': {
                'type': 'choice',
                'label': 'Choice Field'
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("must have 'choices'", errors[0])
        
        # Empty choices
        invalid_config['field1']['choices'] = []
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("cannot be empty", errors[0])

    def test_validate_field_config_patient_field_mapping(self):
        """Test validation of patient field mapping."""
        # Valid patient field mapping
        valid_config = {
            'field1': {
                'type': 'text',
                'label': 'Patient Name',
                'patient_field_mapping': 'name'
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid patient field mapping
        invalid_config = {
            'field1': {
                'type': 'text',
                'label': 'Field 1',
                'patient_field_mapping': 'invalid_field'
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("invalid patient field mapping", errors[0])
        
        # Incompatible field types
        invalid_config = {
            'field1': {
                'type': 'number',
                'label': 'Number Field',
                'patient_field_mapping': 'name'  # name is text, number is not compatible
            }
        }
        
        is_valid, errors = FieldMappingUtils.validate_field_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertIn("not compatible with patient field type", errors[0])

    def test_get_default_field_config(self):
        """Test getting default field configuration."""
        default_config = FieldMappingUtils.get_default_field_config()
        
        # Should return a dictionary
        self.assertIsInstance(default_config, dict)
        
        # Should contain expected default fields
        self.assertIn('patient_name', default_config)
        self.assertIn('date', default_config)
        self.assertIn('signature', default_config)
        
        # Check structure of default fields
        patient_name_field = default_config['patient_name']
        self.assertEqual(patient_name_field['type'], 'text')
        self.assertEqual(patient_name_field['label'], 'Nome do Paciente')
        self.assertTrue(patient_name_field['required'])

    def test_convert_coordinates(self):
        """Test coordinate conversion from cm to points."""
        # Test basic conversion
        x_points, y_points = FieldMappingUtils.convert_coordinates(
            x_cm=5.0, y_cm=10.0, 
            page_width_pt=595, page_height_pt=842
        )
        
        # 1 cm = 28.35 points
        expected_x = 5.0 * 28.35
        expected_y = 842 - (10.0 * 28.35)  # Y is inverted in PDF
        
        self.assertAlmostEqual(x_points, expected_x, places=1)
        self.assertAlmostEqual(y_points, expected_y, places=1)

    def test_generate_sample_config_generic(self):
        """Test generating sample configuration for generic form."""
        config = FieldMappingUtils.generate_sample_config("generic")
        
        # Should return default configuration
        self.assertIsInstance(config, dict)
        self.assertIn('patient_name', config)
        self.assertIn('date', config)
        self.assertIn('signature', config)

    def test_generate_sample_config_transfusion(self):
        """Test generating sample configuration for transfusion form."""
        config = FieldMappingUtils.generate_sample_config("transfusion")
        
        # Should return transfusion-specific configuration
        self.assertIsInstance(config, dict)
        self.assertIn('patient_name', config)
        self.assertIn('blood_type', config)
        self.assertIn('units_requested', config)
        self.assertIn('urgency', config)
        self.assertIn('clinical_indication', config)
        
        # Check blood type field
        blood_type_field = config['blood_type']
        self.assertEqual(blood_type_field['type'], 'choice')
        self.assertIn('A+', blood_type_field['choices'])

    def test_generate_sample_config_icu_transfer(self):
        """Test generating sample configuration for ICU transfer form."""
        config = FieldMappingUtils.generate_sample_config("icu_transfer")
        
        # Should return ICU transfer-specific configuration
        self.assertIsInstance(config, dict)
        self.assertIn('patient_name', config)
        self.assertIn('current_location', config)
        self.assertIn('requested_icu', config)
        self.assertIn('clinical_condition', config)
        self.assertIn('life_support', config)
        
        # Check ICU choices
        icu_field = config['requested_icu']
        self.assertEqual(icu_field['type'], 'choice')
        self.assertIn('UTI Geral', icu_field['choices'])

    def test_generate_sample_config_unknown_type(self):
        """Test generating sample configuration for unknown form type."""
        config = FieldMappingUtils.generate_sample_config("unknown_type")
        
        # Should return default configuration
        self.assertIsInstance(config, dict)
        self.assertIn('patient_name', config)


class DataFieldMapperGenderTests(TestCase):
    """Test gender-specific functionality in DataFieldMapper."""

    def test_detect_gender_field_type_male_checkbox(self):
        """Test detection of male checkbox field patterns."""
        male_field_names = [
            'masculino',
            'male',
            'homem', 
            'M',
            'masc',
            'check_masculino',
            'masculino_box',
            'male-checkbox'
        ]
        
        for field_name in male_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertEqual(result, 'male_checkbox', 
                           f"Field '{field_name}' should be detected as male_checkbox")

    def test_detect_gender_field_type_female_checkbox(self):
        """Test detection of female checkbox field patterns."""
        female_field_names = [
            'feminino',
            'female',
            'mulher',
            'F',
            'fem',
            'check_feminino',
            'female_box',
            'feminino-checkbox'
        ]
        
        for field_name in female_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertEqual(result, 'female_checkbox', 
                           f"Field '{field_name}' should be detected as female_checkbox")

    def test_detect_gender_field_type_other_checkbox(self):
        """Test detection of other checkbox field patterns."""
        other_field_names = [
            'outro',
            'other',
            'O',
            'check_outro',
            'other_checkbox'
        ]
        
        for field_name in other_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertEqual(result, 'other_checkbox', 
                           f"Field '{field_name}' should be detected as other_checkbox")

    def test_detect_gender_field_type_not_informed_checkbox(self):
        """Test detection of not informed checkbox field patterns."""
        not_informed_field_names = [
            'nao_informado',
            'not_informed',
            'N',
            'nao_info',
            'check_nao_informado'
        ]
        
        for field_name in not_informed_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertEqual(result, 'not_informed_checkbox', 
                           f"Field '{field_name}' should be detected as not_informed_checkbox")

    def test_detect_gender_field_type_text_fields(self):
        """Test detection of gender text field patterns."""
        gender_text_field_names = [
            'sexo',
            'genero',
            'gender',
            'sex',
            'campo_sexo',
            'gender_field'
        ]
        
        for field_name in gender_text_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertEqual(result, 'gender_text', 
                           f"Field '{field_name}' should be detected as gender_text")

    def test_detect_gender_field_type_non_gender_fields(self):
        """Test detection with non-gender field names."""
        non_gender_field_names = [
            'patient_name',
            'birthday', 
            'address',
            'phone',
            'some_random_field',
            'checkbox_other_purpose'
        ]
        
        for field_name in non_gender_field_names:
            result = DataFieldMapper.detect_gender_field_type(field_name)
            self.assertIsNone(result, 
                           f"Field '{field_name}' should not be detected as gender field")

    def test_detect_gender_field_type_edge_cases(self):
        """Test edge cases for gender field detection."""
        # Empty or None field names
        self.assertIsNone(DataFieldMapper.detect_gender_field_type(None))
        self.assertIsNone(DataFieldMapper.detect_gender_field_type(''))
        
        # Case insensitive matching
        self.assertEqual(DataFieldMapper.detect_gender_field_type('MASCULINO'), 'male_checkbox')
        self.assertEqual(DataFieldMapper.detect_gender_field_type('Feminino'), 'female_checkbox')
        
        # Underscore and hyphen handling
        self.assertEqual(DataFieldMapper.detect_gender_field_type('check-masculino'), 'male_checkbox')
        self.assertEqual(DataFieldMapper.detect_gender_field_type('field_feminino'), 'female_checkbox')

    def test_get_gender_checkbox_pairs(self):
        """Test finding gender checkbox pairs in field configuration."""
        field_config = {
            'masculino_check': {
                'type': 'boolean',
                'label': 'Masculino',
                'x': 5.0, 'y': 10.0
            },
            'feminino_check': {
                'type': 'boolean',
                'label': 'Feminino', 
                'x': 8.0, 'y': 10.0
            },
            'patient_name': {
                'type': 'text',
                'label': 'Nome do Paciente'
            },
            'outro_checkbox': {
                'type': 'boolean',
                'label': 'Outro'
            }
        }
        
        gender_checkboxes = DataFieldMapper.get_gender_checkbox_pairs(field_config)
        
        # Should find male and female checkboxes
        self.assertEqual(gender_checkboxes['male_checkbox'], 'masculino_check')
        self.assertEqual(gender_checkboxes['female_checkbox'], 'feminino_check')
        self.assertEqual(gender_checkboxes['other_checkbox'], 'outro_checkbox')
        
        # Should not include text fields
        self.assertNotIn('gender_text', gender_checkboxes)

    def test_get_gender_checkbox_pairs_sectioned_config(self):
        """Test finding gender checkboxes in sectioned field configuration."""
        field_config = {
            'sections': {
                'patient_info': {'name': 'Patient Information', 'order': 1}
            },
            'fields': {
                'masculino': {
                    'type': 'boolean',
                    'label': 'Masculino',
                    'section': 'patient_info'
                },
                'feminino': {
                    'type': 'boolean',
                    'label': 'Feminino',
                    'section': 'patient_info'
                }
            }
        }
        
        gender_checkboxes = DataFieldMapper.get_gender_checkbox_pairs(field_config)
        
        self.assertEqual(gender_checkboxes['male_checkbox'], 'masculino')
        self.assertEqual(gender_checkboxes['female_checkbox'], 'feminino')

    def test_get_gender_text_fields(self):
        """Test finding gender text fields in field configuration."""
        field_config = {
            'sexo': {
                'type': 'text',
                'label': 'Sexo',
                'x': 5.0, 'y': 15.0
            },
            'genero_choice': {
                'type': 'choice',
                'label': 'Gênero',
                'choices': ['M', 'F']
            },
            'patient_name': {
                'type': 'text',
                'label': 'Nome do Paciente'
            },
            'masculino_check': {
                'type': 'boolean',
                'label': 'Masculino'
            }
        }
        
        gender_text_fields = DataFieldMapper.get_gender_text_fields(field_config)
        
        # Should find text and choice gender fields
        self.assertIn('sexo', gender_text_fields)
        self.assertIn('genero_choice', gender_text_fields)
        
        # Should not include non-gender fields or checkboxes
        self.assertNotIn('patient_name', gender_text_fields)
        self.assertNotIn('masculino_check', gender_text_fields)

    def test_process_gender_auto_fill_male(self):
        """Test gender auto-fill processing for male patient."""
        field_config = {
            'masculino': {'type': 'boolean', 'label': 'Masculino'},
            'feminino': {'type': 'boolean', 'label': 'Feminino'},
            'outro': {'type': 'boolean', 'label': 'Outro'},
            'sexo': {'type': 'text', 'label': 'Sexo'},
            'patient_name': {'type': 'text', 'label': 'Nome'}
        }
        
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, 'M')
        
        # Male checkbox should be checked
        self.assertTrue(initial_values['masculino'])
        self.assertFalse(initial_values['feminino'])
        self.assertFalse(initial_values['outro'])
        
        # Text field should have display value
        self.assertEqual(initial_values['sexo'], 'Masculino')
        
        # Non-gender fields should not be affected
        self.assertNotIn('patient_name', initial_values)

    def test_process_gender_auto_fill_female(self):
        """Test gender auto-fill processing for female patient."""
        field_config = {
            'masculino': {'type': 'boolean', 'label': 'Masculino'},
            'feminino': {'type': 'boolean', 'label': 'Feminino'},
            'sexo': {'type': 'text', 'label': 'Sexo'}
        }
        
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, 'F')
        
        # Female checkbox should be checked
        self.assertFalse(initial_values['masculino'])
        self.assertTrue(initial_values['feminino'])
        
        # Text field should have display value
        self.assertEqual(initial_values['sexo'], 'Feminino')

    def test_process_gender_auto_fill_other(self):
        """Test gender auto-fill processing for other gender."""
        field_config = {
            'masculino': {'type': 'boolean', 'label': 'Masculino'},
            'feminino': {'type': 'boolean', 'label': 'Feminino'},
            'outro': {'type': 'boolean', 'label': 'Outro'},
            'genero': {'type': 'choice', 'label': 'Gênero', 'choices': ['M', 'F', 'O']}
        }
        
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, 'O')
        
        # Other checkbox should be checked
        self.assertFalse(initial_values['masculino'])
        self.assertFalse(initial_values['feminino'])
        self.assertTrue(initial_values['outro'])
        
        # Text field should have display value
        self.assertEqual(initial_values['genero'], 'Outro')

    def test_process_gender_auto_fill_not_informed(self):
        """Test gender auto-fill processing for not informed gender."""
        field_config = {
            'masculino': {'type': 'boolean', 'label': 'Masculino'},
            'feminino': {'type': 'boolean', 'label': 'Feminino'},
            'nao_informado': {'type': 'boolean', 'label': 'Não Informado'},
            'sexo': {'type': 'text', 'label': 'Sexo'}
        }
        
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, 'N')
        
        # Not informed checkbox should be checked
        self.assertFalse(initial_values['masculino'])
        self.assertFalse(initial_values['feminino'])
        self.assertTrue(initial_values['nao_informado'])
        
        # Text field should have display value
        self.assertEqual(initial_values['sexo'], 'Não Informado')

    def test_process_gender_auto_fill_no_gender_fields(self):
        """Test gender auto-fill processing when no gender fields exist."""
        field_config = {
            'patient_name': {'type': 'text', 'label': 'Nome do Paciente'},
            'birthday': {'type': 'date', 'label': 'Data de Nascimento'}
        }
        
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, 'M')
        
        # Should return empty dict when no gender fields found
        self.assertEqual(initial_values, {})

    def test_process_gender_auto_fill_edge_cases(self):
        """Test gender auto-fill processing edge cases."""
        field_config = {
            'masculino': {'type': 'boolean', 'label': 'Masculino'},
            'sexo': {'type': 'text', 'label': 'Sexo'}
        }
        
        # Test with None gender
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, None)
        self.assertEqual(initial_values, {})
        
        # Test with empty gender
        initial_values = DataFieldMapper.process_gender_auto_fill(field_config, '')
        self.assertEqual(initial_values, {})
        
        # Test with None field config
        initial_values = DataFieldMapper.process_gender_auto_fill(None, 'M')
        self.assertEqual(initial_values, {})