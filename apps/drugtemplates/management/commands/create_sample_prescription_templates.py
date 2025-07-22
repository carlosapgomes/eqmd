from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.drugtemplates.models import PrescriptionTemplate, PrescriptionTemplateItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample prescription templates for common medical conditions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of user to create sample templates (defaults to first superuser)',
        )
        parser.add_argument(
            '--make-public',
            action='store_true',
            help='Make all created templates public (default: private)',
        )

    def handle(self, *args, **options):
        # Get user
        if options['user_email']:
            try:
                user = User.objects.get(email=options['user_email'])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email {options["user_email"]} not found')
                )
                return
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Please create a superuser first.')
                )
                return

        is_public = options.get('make_public', False)

        # Sample prescription template data
        sample_templates = [
            {
                'name': 'Hipertensão Arterial - Inicial',
                'items': [
                    {
                        'drug_name': 'Losartana',
                        'presentation': '50mg comprimido revestido',
                        'quantity': '30 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido pela manhã, em jejum',
                        'order': 1
                    },
                    {
                        'drug_name': 'Hidroclorotiazida',
                        'presentation': '25mg comprimido',
                        'quantity': '30 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido pela manhã junto com a Losartana',
                        'order': 2
                    },
                ]
            },
            {
                'name': 'Diabetes Mellitus Tipo 2 - Inicial',
                'items': [
                    {
                        'drug_name': 'Metformina',
                        'presentation': '850mg comprimido revestido',
                        'quantity': '60 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido 2 vezes ao dia, após o almoço e jantar',
                        'order': 1
                    },
                    {
                        'drug_name': 'Glibenclamida',
                        'presentation': '5mg comprimido',
                        'quantity': '30 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido pela manhã, 30 minutos antes do café da manhã',
                        'order': 2
                    },
                ]
            },
            {
                'name': 'Dor e Febre - Adulto',
                'items': [
                    {
                        'drug_name': 'Dipirona',
                        'presentation': '500mg comprimido',
                        'quantity': '20 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido até 4 vezes ao dia, em caso de dor ou febre',
                        'order': 1
                    },
                    {
                        'drug_name': 'Paracetamol',
                        'presentation': '750mg comprimido',
                        'quantity': '20 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido até 3 vezes ao dia (alternativa à dipirona)',
                        'order': 2
                    },
                ]
            },
            {
                'name': 'Gastrite - Tratamento',
                'items': [
                    {
                        'drug_name': 'Omeprazol',
                        'presentation': '20mg cápsula',
                        'quantity': '30 cápsulas',
                        'usage_instructions': 'Tomar 1 cápsula pela manhã, 30 minutos antes do café da manhã',
                        'order': 1
                    },
                    {
                        'drug_name': 'Domperidona',
                        'presentation': '10mg comprimido',
                        'quantity': '30 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido 3 vezes ao dia, 30 minutos antes das refeições',
                        'order': 2
                    },
                ]
            },
            {
                'name': 'Infecção Respiratória - Adulto',
                'items': [
                    {
                        'drug_name': 'Azitromicina',
                        'presentation': '500mg comprimido revestido',
                        'quantity': '5 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido ao dia por 5 dias, preferencialmente no mesmo horário',
                        'order': 1
                    },
                    {
                        'drug_name': 'Loratadina',
                        'presentation': '10mg comprimido',
                        'quantity': '10 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido ao dia para alívio dos sintomas alérgicos',
                        'order': 2
                    },
                    {
                        'drug_name': 'Dipirona',
                        'presentation': '500mg comprimido',
                        'quantity': '20 comprimidos',
                        'usage_instructions': 'Tomar 1 comprimido até 4 vezes ao dia em caso de febre ou dor',
                        'order': 3
                    },
                ]
            },
        ]

        created_count = 0
        for template_data in sample_templates:
            # Check if template already exists
            existing = PrescriptionTemplate.objects.filter(
                name=template_data['name'],
                creator=user
            ).first()
            
            if not existing:
                # Create template
                template = PrescriptionTemplate.objects.create(
                    name=template_data['name'],
                    creator=user,
                    is_public=is_public
                )
                
                # Create template items
                for item_data in template_data['items']:
                    PrescriptionTemplateItem.objects.create(
                        template=template,
                        drug_name=item_data['drug_name'],
                        presentation=item_data['presentation'],
                        quantity=item_data['quantity'],
                        usage_instructions=item_data['usage_instructions'],
                        order=item_data['order']
                    )
                
                created_count += 1
                item_count = len(template_data['items'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created: "{template_data["name"]}" with {item_count} items'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Already exists: "{template_data["name"]}"')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nPrescription template creation completed. Created {created_count} new templates.')
        )
        
        if is_public:
            self.stdout.write(
                self.style.SUCCESS('All templates created as public (visible to all users).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All templates created as private (visible only to creator).')
            )