from django.test import TestCase
from django import forms
from unittest.mock import patch, MagicMock
from apps.pdf_forms.services.form_generator import DynamicFormGenerator
from apps.pdf_forms.services.section_utils import SectionUtils
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, UserFactory


class SectionConfigurationTests(TestCase):
    """Test section-based form configuration."""

    def setUp(self):
        self.generator = DynamicFormGenerator()
        self.user = UserFactory()

    def test_sectioned_form_generation(self):
        """Test form generation with sections."""
        sectioned_config = {
            'sections': {
                'patient_info': {
                    'label': 'Informações do Paciente',
                    'description': 'Dados básicos do paciente',
                    'order': 1,
                    'collapsed': False,
                    'icon': 'bi-person'
                },
                'procedure': {
                    'label': 'Detalhes do Procedimento',
                    'description': 'Informações sobre o procedimento',
                    'order': 2,
                    'collapsed': True,
                    'icon': 'bi-clipboard-pulse'
                }
            },
            'fields': {
                'patient_name': {
                    'type': 'text',
                    'label': 'Nome do Paciente',
                    'section': 'patient_info',
                    'field_order': 1,
                    'x': 2.0, 'y': 3.0, 'width': 6.0, 'height': 0.7,
                    'required': True
                },
                'patient_age': {
                    'type': 'number',
                    'label': 'Idade',
                    'section': 'patient_info',
                    'field_order': 2,
                    'x': 2.0, 'y': 4.0, 'width': 2.0, 'height': 0.7,
                    'required': True
                },
                'procedure_name': {
                    'type': 'text',
                    'label': 'Nome do Procedimento',
                    'section': 'procedure',
                    'field_order': 1,
                    'x': 2.0, 'y': 8.0, 'width': 8.0, 'height': 0.7,
                    'required': True
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=sectioned_config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()

        # Test that all fields are created
        self.assertIn('patient_name', form_instance.fields)
        self.assertIn('patient_age', form_instance.fields)
        self.assertIn('procedure_name', form_instance.fields)

        # Test that form has section metadata
        self.assertTrue(hasattr(form_class, '_has_sections'))
        self.assertTrue(form_class._has_sections)
        self.assertTrue(hasattr(form_class, '_sections_metadata'))

        # Test section structure
        sections_metadata = form_class._sections_metadata
        self.assertIn('sections', sections_metadata)
        self.assertEqual(len(sections_metadata['sections']), 2)

        # Test patient_info section
        patient_section = sections_metadata['sections']['patient_info']
        self.assertEqual(patient_section['info']['label'], 'Informações do Paciente')
        self.assertEqual(patient_section['info']['order'], 1)
        self.assertFalse(patient_section['info']['collapsed'])
        self.assertEqual(len(patient_section['fields']), 2)
        self.assertIn('patient_name', patient_section['fields'])
        self.assertIn('patient_age', patient_section['fields'])

        # Test procedure section
        procedure_section = sections_metadata['sections']['procedure']
        self.assertEqual(procedure_section['info']['label'], 'Detalhes do Procedimento')
        self.assertEqual(procedure_section['info']['order'], 2)
        self.assertTrue(procedure_section['info']['collapsed'])
        self.assertEqual(len(procedure_section['fields']), 1)
        self.assertIn('procedure_name', procedure_section['fields'])

    def test_unsectioned_form_backward_compatibility(self):
        """Test that forms without sections still work."""
        legacy_config = {
            'patient_name': {
                'type': 'text',
                'label': 'Nome do Paciente',
                'x': 2.0, 'y': 3.0, 'width': 6.0, 'height': 0.7,
                'required': True
            },
            'patient_age': {
                'type': 'number',
                'label': 'Idade',
                'x': 2.0, 'y': 4.0, 'width': 2.0, 'height': 0.7,
                'required': True
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=legacy_config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()

        # Test that fields are created normally
        self.assertIn('patient_name', form_instance.fields)
        self.assertIn('patient_age', form_instance.fields)

        # Test that form has no sections
        self.assertTrue(hasattr(form_class, '_has_sections'))
        self.assertFalse(form_class._has_sections)

        # Test unsectioned fields
        self.assertTrue(hasattr(form_class, '_unsectioned_fields'))
        unsectioned_fields = form_class._unsectioned_fields
        self.assertEqual(len(unsectioned_fields), 2)
        self.assertIn('patient_name', unsectioned_fields)
        self.assertIn('patient_age', unsectioned_fields)

    def test_section_validation(self):
        """Test section configuration validation."""
        # Test invalid section reference - should raise ValidationError
        invalid_config = {
            'sections': {
                'patient_info': {
                    'label': 'Informações do Paciente',
                    'order': 1,
                    'collapsed': False
                }
            },
            'fields': {
                'patient_name': {
                    'type': 'text',
                    'label': 'Nome do Paciente',
                    'section': 'nonexistent_section',  # Invalid section reference
                    'field_order': 1,
                    'x': 2.0, 'y': 3.0, 'width': 6.0, 'height': 0.7,
                    'required': True
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=invalid_config,
            created_by=self.user
        )

        # Should raise ValidationError due to invalid section reference
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as context:
            self.generator.generate_form_class(template)
        
        self.assertIn('nonexistent_section', str(context.exception))

    def test_field_section_assignment(self):
        """Test field assignment to sections."""
        config = {
            'sections': {
                'section_a': {
                    'label': 'Seção A',
                    'order': 1,
                    'collapsed': False
                },
                'section_b': {
                    'label': 'Seção B',
                    'order': 2,
                    'collapsed': True
                }
            },
            'fields': {
                'field_1': {
                    'type': 'text',
                    'label': 'Campo 1',
                    'section': 'section_a',
                    'field_order': 1,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                },
                'field_2': {
                    'type': 'text',
                    'label': 'Campo 2',
                    'section': 'section_a',
                    'field_order': 2,
                    'x': 1.0, 'y': 2.0, 'width': 4.0, 'height': 0.7
                },
                'field_3': {
                    'type': 'text',
                    'label': 'Campo 3',
                    'section': 'section_b',
                    'field_order': 1,
                    'x': 1.0, 'y': 3.0, 'width': 4.0, 'height': 0.7
                },
                'field_4': {
                    'type': 'text',
                    'label': 'Campo 4',
                    # No section assigned - should go to unsectioned
                    'x': 1.0, 'y': 4.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        
        # Test section assignments
        sections_metadata = form_class._sections_metadata
        
        # Section A should have 2 fields
        section_a = sections_metadata['sections']['section_a']
        self.assertEqual(len(section_a['fields']), 2)
        self.assertIn('field_1', section_a['fields'])
        self.assertIn('field_2', section_a['fields'])
        
        # Section B should have 1 field
        section_b = sections_metadata['sections']['section_b']
        self.assertEqual(len(section_b['fields']), 1)
        self.assertIn('field_3', section_b['fields'])
        
        # Field 4 should be in unsectioned
        self.assertIn('field_4', form_class._unsectioned_fields)

    def test_section_ordering(self):
        """Test section and field ordering."""
        config = {
            'sections': {
                'third_section': {
                    'label': 'Terceira Seção',
                    'order': 3,
                    'collapsed': False
                },
                'first_section': {
                    'label': 'Primeira Seção',
                    'order': 1,
                    'collapsed': False
                },
                'second_section': {
                    'label': 'Segunda Seção',
                    'order': 2,
                    'collapsed': False
                }
            },
            'fields': {
                'field_b': {
                    'type': 'text',
                    'label': 'Campo B',
                    'section': 'first_section',
                    'field_order': 2,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                },
                'field_a': {
                    'type': 'text',
                    'label': 'Campo A',
                    'section': 'first_section',
                    'field_order': 1,
                    'x': 1.0, 'y': 2.0, 'width': 4.0, 'height': 0.7
                },
                'field_c': {
                    'type': 'text',
                    'label': 'Campo C',
                    'section': 'first_section',
                    'field_order': 3,
                    'x': 1.0, 'y': 3.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        sections_metadata = form_class._sections_metadata
        
        # Test section ordering
        section_keys = list(sections_metadata['sections'].keys())
        self.assertEqual(section_keys[0], 'first_section')
        self.assertEqual(section_keys[1], 'second_section')
        self.assertEqual(section_keys[2], 'third_section')
        
        # Test field ordering within section
        first_section_fields = sections_metadata['sections']['first_section']['fields']
        self.assertEqual(first_section_fields, ['field_a', 'field_b', 'field_c'])

    def test_mixed_sectioned_and_unsectioned_fields(self):
        """Test forms with both sectioned and unsectioned fields."""
        config = {
            'sections': {
                'main_section': {
                    'label': 'Seção Principal',
                    'order': 1,
                    'collapsed': False
                }
            },
            'fields': {
                'sectioned_field': {
                    'type': 'text',
                    'label': 'Campo da Seção',
                    'section': 'main_section',
                    'field_order': 1,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                },
                'unsectioned_field_1': {
                    'type': 'text',
                    'label': 'Campo Sem Seção 1',
                    'x': 1.0, 'y': 2.0, 'width': 4.0, 'height': 0.7
                },
                'unsectioned_field_2': {
                    'type': 'text',
                    'label': 'Campo Sem Seção 2',
                    'x': 1.0, 'y': 3.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        
        # Should have sections
        self.assertTrue(form_class._has_sections)
        
        # Test sectioned field
        sections_metadata = form_class._sections_metadata
        main_section = sections_metadata['sections']['main_section']
        self.assertEqual(len(main_section['fields']), 1)
        self.assertIn('sectioned_field', main_section['fields'])
        
        # Test unsectioned fields
        unsectioned_fields = form_class._unsectioned_fields
        self.assertEqual(len(unsectioned_fields), 2)
        self.assertIn('unsectioned_field_1', unsectioned_fields)
        self.assertIn('unsectioned_field_2', unsectioned_fields)

    def test_empty_sections_handling(self):
        """Test handling of sections with no fields."""
        config = {
            'sections': {
                'empty_section': {
                    'label': 'Seção Vazia',
                    'order': 1,
                    'collapsed': False
                },
                'populated_section': {
                    'label': 'Seção com Campos',
                    'order': 2,
                    'collapsed': False
                }
            },
            'fields': {
                'field_1': {
                    'type': 'text',
                    'label': 'Campo 1',
                    'section': 'populated_section',
                    'field_order': 1,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        sections_metadata = form_class._sections_metadata
        
        # Empty section should still be present but with no fields
        self.assertIn('empty_section', sections_metadata['sections'])
        empty_section = sections_metadata['sections']['empty_section']
        self.assertEqual(len(empty_section['fields']), 0)
        
        # Populated section should have the field
        populated_section = sections_metadata['sections']['populated_section']
        self.assertEqual(len(populated_section['fields']), 1)
        self.assertIn('field_1', populated_section['fields'])

    def test_section_metadata_preservation(self):
        """Test that section metadata is properly preserved."""
        config = {
            'sections': {
                'detailed_section': {
                    'label': 'Seção Detalhada',
                    'description': 'Esta é uma descrição detalhada da seção',
                    'order': 1,
                    'collapsed': True,
                    'icon': 'bi-clipboard-data',
                    'custom_attr': 'custom_value'  # Custom attributes should be preserved
                }
            },
            'fields': {
                'test_field': {
                    'type': 'text',
                    'label': 'Campo de Teste',
                    'section': 'detailed_section',
                    'field_order': 1,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        sections_metadata = form_class._sections_metadata
        section_info = sections_metadata['sections']['detailed_section']['info']
        
        # Test all metadata is preserved
        self.assertEqual(section_info['label'], 'Seção Detalhada')
        self.assertEqual(section_info['description'], 'Esta é uma descrição detalhada da seção')
        self.assertEqual(section_info['order'], 1)
        self.assertTrue(section_info['collapsed'])
        self.assertEqual(section_info['icon'], 'bi-clipboard-data')
        self.assertEqual(section_info['custom_attr'], 'custom_value')


class SectionUtilsTests(TestCase):
    """Test section utility functions."""

    def test_get_default_section_config(self):
        """Test default section configuration."""
        default_config = SectionUtils.get_default_section_config()
        
        self.assertIsInstance(default_config, dict)
        self.assertIn('label', default_config)
        self.assertIn('order', default_config)
        self.assertIn('collapsed', default_config)

    def test_migrate_unsectioned_form(self):
        """Test migration of old format to new sectioned format."""
        old_config = {
            'patient_name': {
                'type': 'text',
                'label': 'Nome do Paciente',
                'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
            },
            'patient_age': {
                'type': 'number',
                'label': 'Idade',
                'x': 1.0, 'y': 2.0, 'width': 2.0, 'height': 0.7
            }
        }

        new_config = SectionUtils.migrate_unsectioned_form(old_config)
        
        # Should create sections structure
        self.assertIn('sections', new_config)
        self.assertIn('fields', new_config)
        
        # Fields should be preserved
        self.assertIn('patient_name', new_config['fields'])
        self.assertIn('patient_age', new_config['fields'])
        
        # Original field properties should be maintained
        self.assertEqual(new_config['fields']['patient_name']['type'], 'text')
        self.assertEqual(new_config['fields']['patient_name']['x'], 1.0)

    def test_validate_section_assignment(self):
        """Test validation of field section assignments."""
        sections = {
            'section_1': {'label': 'Seção 1'},
            'section_2': {'label': 'Seção 2'}
        }
        
        # Valid assignment
        valid_fields = {
            'field_1': {'section': 'section_1'},
            'field_2': {'section': 'section_2'},
            'field_3': {}  # No section assigned - should be valid
        }
        
        is_valid, errors = SectionUtils.validate_section_assignment(sections, valid_fields)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid assignment
        invalid_fields = {
            'field_1': {'section': 'nonexistent_section'}
        }
        
        is_valid, errors = SectionUtils.validate_section_assignment(sections, invalid_fields)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_get_section_icons(self):
        """Test available section icons."""
        icons = SectionUtils.get_section_icons()
        
        self.assertIsInstance(icons, list)
        self.assertGreater(len(icons), 0)
        
        # Should include common medical icons
        icon_values = [icon['value'] for icon in icons]
        expected_icons = ['bi-person', 'bi-clipboard-pulse', 'bi-journal-medical']
        for icon in expected_icons:
            self.assertIn(icon, icon_values)
        
        # Should include "No Icon" option
        no_icon_option = next((icon for icon in icons if icon['value'] == ''), None)
        self.assertIsNotNone(no_icon_option)
        self.assertEqual(no_icon_option['label'], 'No Icon')


class SectionFormIntegrationTests(TestCase):
    """Integration tests for sectioned forms."""

    def setUp(self):
        self.generator = DynamicFormGenerator()
        self.user = UserFactory()

    def test_sectioned_form_validation(self):
        """Test form validation with sectioned fields."""
        config = {
            'sections': {
                'required_section': {
                    'label': 'Campos Obrigatórios',
                    'order': 1,
                    'collapsed': False
                },
                'optional_section': {
                    'label': 'Campos Opcionais',
                    'order': 2,
                    'collapsed': True
                }
            },
            'fields': {
                'required_field': {
                    'type': 'text',
                    'label': 'Campo Obrigatório',
                    'section': 'required_section',
                    'field_order': 1,
                    'required': True,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                },
                'optional_field': {
                    'type': 'text',
                    'label': 'Campo Opcional',
                    'section': 'optional_section',
                    'field_order': 1,
                    'required': False,
                    'x': 1.0, 'y': 2.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        
        # Test validation with missing required field
        form_instance = form_class({'optional_field': 'value'})
        self.assertFalse(form_instance.is_valid())
        self.assertIn('required_field', form_instance.errors)
        
        # Test validation with all required fields
        form_instance = form_class({
            'required_field': 'required_value',
            'optional_field': 'optional_value'
        })
        self.assertTrue(form_instance.is_valid())

    def test_sectioned_form_rendering_context(self):
        """Test that sectioned forms provide proper context for templates."""
        config = {
            'sections': {
                'test_section': {
                    'label': 'Seção de Teste',
                    'description': 'Descrição da seção',
                    'order': 1,
                    'collapsed': False,
                    'icon': 'bi-test'
                }
            },
            'fields': {
                'test_field': {
                    'type': 'text',
                    'label': 'Campo de Teste',
                    'section': 'test_section',
                    'field_order': 1,
                    'x': 1.0, 'y': 1.0, 'width': 4.0, 'height': 0.7
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()
        
        # Test that template can access section metadata
        self.assertTrue(hasattr(form_class, '_has_sections'))
        self.assertTrue(hasattr(form_class, '_sections_metadata'))
        
        sections_metadata = form_class._sections_metadata
        self.assertIn('sections', sections_metadata)
        
        # Test section structure for template rendering
        test_section = sections_metadata['sections']['test_section']
        self.assertIn('info', test_section)
        self.assertIn('fields', test_section)
        
        # Template should be able to iterate over sections and fields
        for section_key, section_data in sections_metadata['sections'].items():
            self.assertIn('info', section_data)
            self.assertIn('fields', section_data)
            self.assertIsInstance(section_data['fields'], list)

    def test_complex_sectioned_form_workflow(self):
        """Test complete workflow with complex sectioned form."""
        config = {
            'sections': {
                'patient_data': {
                    'label': 'Dados do Paciente',
                    'description': 'Informações básicas do paciente',
                    'order': 1,
                    'collapsed': False,
                    'icon': 'bi-person'
                },
                'medical_history': {
                    'label': 'Histórico Médico',
                    'description': 'Antecedentes médicos relevantes',
                    'order': 2,
                    'collapsed': True,
                    'icon': 'bi-journal-medical'
                },
                'current_treatment': {
                    'label': 'Tratamento Atual',
                    'description': 'Informações sobre o tratamento atual',
                    'order': 3,
                    'collapsed': True,
                    'icon': 'bi-clipboard-pulse'
                }
            },
            'fields': {
                'patient_name': {
                    'type': 'text',
                    'label': 'Nome Completo',
                    'section': 'patient_data',
                    'field_order': 1,
                    'required': True,
                    'x': 1.0, 'y': 1.0, 'width': 8.0, 'height': 0.7
                },
                'patient_birth_date': {
                    'type': 'date',
                    'label': 'Data de Nascimento',
                    'section': 'patient_data',
                    'field_order': 2,
                    'required': True,
                    'x': 1.0, 'y': 2.0, 'width': 4.0, 'height': 0.7
                },
                'allergies': {
                    'type': 'multiple_choice',
                    'label': 'Alergias',
                    'section': 'medical_history',
                    'field_order': 1,
                    'choices': ['Penicilina', 'Látex', 'Nozes', 'Frutos do Mar'],
                    'required': False,
                    'x': 1.0, 'y': 3.0, 'width': 6.0, 'height': 1.0
                },
                'medications': {
                    'type': 'textarea',
                    'label': 'Medicamentos Atuais',
                    'section': 'current_treatment',
                    'field_order': 1,
                    'required': False,
                    'x': 1.0, 'y': 4.0, 'width': 8.0, 'height': 2.0
                },
                'notes': {
                    'type': 'textarea',
                    'label': 'Observações Gerais',
                    # No section - should go to unsectioned
                    'required': False,
                    'x': 1.0, 'y': 6.0, 'width': 8.0, 'height': 2.0
                }
            }
        }

        template = PDFFormTemplateFactory(
            form_fields=config,
            created_by=self.user
        )

        # Generate form class
        form_class = self.generator.generate_form_class(template)
        
        # Test form structure
        self.assertTrue(form_class._has_sections)
        sections_metadata = form_class._sections_metadata
        
        # Test all sections are present and ordered correctly
        section_keys = list(sections_metadata['sections'].keys())
        self.assertEqual(section_keys, ['patient_data', 'medical_history', 'current_treatment'])
        
        # Test field distribution
        patient_data_fields = sections_metadata['sections']['patient_data']['fields']
        self.assertEqual(patient_data_fields, ['patient_name', 'patient_birth_date'])
        
        medical_history_fields = sections_metadata['sections']['medical_history']['fields']
        self.assertEqual(medical_history_fields, ['allergies'])
        
        current_treatment_fields = sections_metadata['sections']['current_treatment']['fields']
        self.assertEqual(current_treatment_fields, ['medications'])
        
        # Test unsectioned field
        self.assertIn('notes', form_class._unsectioned_fields)
        
        # Test form validation with complex data
        form_data = {
            'patient_name': 'João Silva',
            'patient_birth_date': '1985-03-15',
            'allergies': ['Penicilina', 'Látex'],
            'medications': 'Paracetamol 500mg - 2x ao dia',
            'notes': 'Paciente colaborativo'
        }
        
        form_instance = form_class(form_data)
        self.assertTrue(form_instance.is_valid())
        
        # Test cleaned data structure
        cleaned_data = form_instance.cleaned_data
        self.assertEqual(cleaned_data['patient_name'], 'João Silva')
        self.assertEqual(len(cleaned_data['allergies']), 2)
        self.assertIn('Penicilina', cleaned_data['allergies'])