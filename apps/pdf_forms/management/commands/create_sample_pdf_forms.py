from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.pdf_forms.models import PDFFormTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample PDF form templates for testing'

    def handle(self, *args, **options):
        # Get or create superuser
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No superuser found. Create one first.')
            )
            return

        # Sample form configurations
        sample_forms = [
            {
                'name': 'Solicitação de Transfusão',
                'description': 'Formulário para solicitação de transfusão sanguínea',
                'form_fields': {
                    'patient_name': {
                        'type': 'text',
                        'required': True,
                        'label': 'Nome do Paciente',
                        'max_length': 200,
                        'x': 4.5,
                        'y': 8.5,
                        'width': 12.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'patient_id': {
                        'type': 'text',
                        'required': True,
                        'label': 'Registro do Paciente',
                        'max_length': 20,
                        'x': 17.0,
                        'y': 8.5,
                        'width': 4.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'blood_type': {
                        'type': 'choice',
                        'required': True,
                        'label': 'Tipo Sanguíneo',
                        'choices': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
                        'x': 4.5,
                        'y': 10.0,
                        'width': 3.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'rh_factor': {
                        'type': 'choice',
                        'required': True,
                        'label': 'Fator RH',
                        'choices': ['Positivo', 'Negativo'],
                        'x': 8.0,
                        'y': 10.0,
                        'width': 3.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'units_requested': {
                        'type': 'number',
                        'required': True,
                        'label': 'Unidades Solicitadas',
                        'x': 12.0,
                        'y': 10.0,
                        'width': 3.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'urgency': {
                        'type': 'choice',
                        'required': True,
                        'label': 'Urgência',
                        'choices': ['Rotina', 'Urgente', 'Emergência'],
                        'x': 15.5,
                        'y': 10.0,
                        'width': 4.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'clinical_indication': {
                        'type': 'textarea',
                        'required': True,
                        'label': 'Indicação Clínica',
                        'x': 4.5,
                        'y': 12.0,
                        'width': 15.0,
                        'height': 3.0,
                        'font_size': 11
                    },
                    'requesting_physician': {
                        'type': 'text',
                        'required': True,
                        'label': 'Médico Solicitante',
                        'max_length': 100,
                        'x': 4.5,
                        'y': 15.5,
                        'width': 12.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'request_date': {
                        'type': 'date',
                        'required': True,
                        'label': 'Data da Solicitação',
                        'x': 17.0,
                        'y': 15.5,
                        'width': 4.0,
                        'height': 0.7,
                        'font_size': 12
                    }
                }
            },
            {
                'name': 'Transferência para UTI',
                'description': 'Formulário para solicitação de transferência para UTI',
                'form_fields': {
                    'patient_name': {
                        'type': 'text',
                        'required': True,
                        'label': 'Nome do Paciente',
                        'max_length': 200,
                        'x': 4.5,
                        'y': 8.0,
                        'width': 12.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'current_location': {
                        'type': 'text',
                        'required': True,
                        'label': 'Localização Atual',
                        'max_length': 50,
                        'x': 17.0,
                        'y': 8.0,
                        'width': 5.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'requested_icu': {
                        'type': 'choice',
                        'required': True,
                        'label': 'UTI Solicitada',
                        'choices': ['UTI Geral', 'UTI Cardiológica', 'UTI Neurológica', 'UTI Pediátrica', 'UTI COVID'],
                        'x': 4.5,
                        'y': 9.5,
                        'width': 6.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'clinical_condition': {
                        'type': 'textarea',
                        'required': True,
                        'label': 'Condição Clínica',
                        'x': 4.5,
                        'y': 11.0,
                        'width': 15.0,
                        'height': 4.0,
                        'font_size': 11
                    },
                    'vital_signs': {
                        'type': 'textarea',
                        'required': True,
                        'label': 'Sinais Vitais',
                        'x': 4.5,
                        'y': 15.5,
                        'width': 15.0,
                        'height': 2.0,
                        'font_size': 11
                    },
                    'life_support': {
                        'type': 'boolean',
                        'required': False,
                        'label': 'Necessita Suporte de Vida',
                        'x': 4.5,
                        'y': 18.0,
                        'width': 1.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'requesting_physician': {
                        'type': 'text',
                        'required': True,
                        'label': 'Médico Solicitante',
                        'max_length': 100,
                        'x': 6.0,
                        'y': 19.5,
                        'width': 10.0,
                        'height': 0.7,
                        'font_size': 12
                    },
                    'contact_phone': {
                        'type': 'text',
                        'required': True,
                        'label': 'Telefone de Contato',
                        'max_length': 20,
                        'x': 16.5,
                        'y': 19.5,
                        'width': 4.0,
                        'height': 0.7,
                        'font_size': 12
                    }
                }
            }
        ]

        created_count = 0
        for form_data in sample_forms:
            template, created = PDFFormTemplate.objects.get_or_create(
                name=form_data['name'],
                defaults={
                    'description': form_data['description'],
                    'form_fields': form_data['form_fields'],
                    'created_by': admin_user,
                    'hospital_specific': True,
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new PDF form templates')
        )