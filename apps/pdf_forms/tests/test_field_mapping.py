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