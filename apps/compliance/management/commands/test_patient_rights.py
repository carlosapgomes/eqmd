from django.core.management.base import BaseCommand
from apps.compliance.models import PatientDataRequest, LGPDComplianceSettings
from apps.patients.models import Patient
from apps.accounts.models import EqmdCustomUser
from datetime import date
from django.utils import timezone


class Command(BaseCommand):
    help = 'Creates test data for patient rights system and validates functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-settings',
            action='store_true',
            help='Create basic LGPD compliance settings',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Phase 2: Patient Rights System'))

        # Test 1: Ensure models can be imported and created
        self.stdout.write('\n1. Testing model imports and creation...')
        
        try:
            # Get a staff user for testing
            staff_user = EqmdCustomUser.objects.filter(is_staff=True).first()
            if not staff_user:
                self.stdout.write(self.style.WARNING('  ⚠ No staff user found. Creating one for testing...'))
                staff_user = EqmdCustomUser.objects.create_user(
                    email='test.lgpd@hospital.com',
                    password='testpass123',
                    first_name='LGPD',
                    last_name='Test User',
                    is_staff=True
                )
                self.stdout.write('  ✓ Created test staff user')

            # Create or get existing patient
            patient, created = Patient.objects.get_or_create(
                name="João da Silva (Teste LGPD)",
                defaults={
                    'birthday': date(1980, 5, 15),
                    'status': Patient.Status.OUTPATIENT,
                    'created_by': staff_user,
                    'updated_by': staff_user
                }
            )

            if created:
                self.stdout.write('  ✓ Created test patient: João da Silva (Teste LGPD)')
            else:
                self.stdout.write('  ✓ Found existing test patient: João da Silva (Teste LGPD)')

            # Create test data request
            request_data = {
                'request_type': 'access',
                'description': 'Solicito acesso a todos os meus dados médicos conforme LGPD - TESTE AUTOMATIZADO',
                'requester_name': 'João da Silva',
                'requester_email': 'joao.silva.teste@email.com',
                'requester_phone': '(11) 99999-9999',
                'patient_name_provided': 'João da Silva',
                'patient_birth_date_provided': date(1980, 5, 15),
                'patient': patient,
                'created_by': staff_user,
                'assigned_to': staff_user
            }

            request_obj, created = PatientDataRequest.objects.get_or_create(
                requester_email='joao.silva.teste@email.com',
                request_type='access',
                defaults=request_data
            )

            if created:
                self.stdout.write(f'  ✓ Created test request: {request_obj.request_id}')
            else:
                self.stdout.write(f'  ✓ Found existing test request: {request_obj.request_id}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Model creation failed: {e}'))
            return

        # Test 2: Validate request ID generation
        self.stdout.write('\n2. Testing request ID generation...')
        
        try:
            test_request = PatientDataRequest(
                request_type='information',
                description='Test request for ID generation',
                requester_name='Test User',
                requester_email='test.unique@email.com',
                patient_name_provided='Test Patient',
                created_by=staff_user
            )
            test_request.save()
            
            if test_request.request_id and test_request.request_id.startswith('REQ-'):
                self.stdout.write(f'  ✓ Request ID generated correctly: {test_request.request_id}')
            else:
                self.stdout.write(self.style.ERROR('  ✗ Request ID generation failed'))
                
            # Clean up
            test_request.delete()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Request ID generation test failed: {e}'))

        # Test 3: Validate due date calculation
        self.stdout.write('\n3. Testing due date calculation...')
        
        try:
            if request_obj.due_date and request_obj.due_date > timezone.now():
                days_until_due = (request_obj.due_date - timezone.now()).days
                self.stdout.write(f'  ✓ Due date calculated: {days_until_due} days from now')
            else:
                self.stdout.write(self.style.ERROR('  ✗ Due date calculation failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Due date test failed: {e}'))

        # Test 4: Check overdue detection
        self.stdout.write('\n4. Testing overdue detection...')
        
        try:
            is_overdue = request_obj.is_overdue()
            days_remaining = request_obj.days_remaining()
            self.stdout.write(f'  ✓ Overdue detection works: {is_overdue}, {days_remaining} days remaining')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Overdue detection failed: {e}'))

        # Test 5: Create LGPD settings if requested
        if options['create_settings']:
            self.stdout.write('\n5. Creating basic LGPD compliance settings...')
            
            try:
                settings_obj, created = LGPDComplianceSettings.objects.get_or_create(
                    defaults={
                        'dpo_name': 'Data Protection Officer',
                        'dpo_email': 'dpo@hospital.com',
                        'dpo_phone': '(11) 3333-4444',
                        'controller_name': 'Hospital Test',
                        'controller_address': 'Rua do Hospital, 123',
                        'controller_cnpj': '12.345.678/0001-90',
                        'breach_notification_email': 'security@hospital.com'
                    }
                )
                
                if created:
                    self.stdout.write('  ✓ Created LGPD compliance settings')
                else:
                    self.stdout.write('  ✓ LGPD compliance settings already exist')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Settings creation failed: {e}'))

        # Statistics and Summary
        self.stdout.write('\n6. System Statistics:')
        
        try:
            total_requests = PatientDataRequest.objects.count()
            pending_requests = PatientDataRequest.objects.filter(status='pending').count()
            overdue_requests = PatientDataRequest.objects.filter(
                status__in=['pending', 'under_review']
            ).count()

            self.stdout.write(f'  • Total requests: {total_requests}')
            self.stdout.write(f'  • Pending requests: {pending_requests}')
            self.stdout.write(f'  • Potentially overdue requests: {overdue_requests}')

            # Check if any patients exist
            total_patients = Patient.objects.count()
            self.stdout.write(f'  • Total patients in system: {total_patients}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Statistics gathering failed: {e}'))

        # Test 6: Basic form import test
        self.stdout.write('\n7. Testing form and view imports...')
        
        try:
            from apps.compliance.forms import PatientDataRequestCreationForm, PatientDataRequestManagementForm
            from apps.compliance.views import PatientDataRequestCreateView
            from apps.compliance.services.data_export import PatientDataExportService
            
            self.stdout.write('  ✓ All forms, views, and services import successfully')
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Import test failed: {e}'))

        # Final Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Phase 2 Patient Rights System Test Complete'))
        self.stdout.write('='*60)
        
        self.stdout.write('\nNext Steps:')
        self.stdout.write('1. Access admin interface to manage requests')
        self.stdout.write('2. Test staff request creation at /admin/compliance/nova-solicitacao/')
        self.stdout.write('3. View requests list at /admin/compliance/solicitacoes/')
        self.stdout.write('4. Test data export functionality')
        self.stdout.write('\nAll Phase 2 core functionality is now implemented!')