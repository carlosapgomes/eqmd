from django.core.management.base import BaseCommand
from apps.compliance.models import DataRetentionPolicy

class Command(BaseCommand):
    help = 'Sets up default data retention policies'
    
    def handle(self, *args, **options):
        self.stdout.write("Setting up default retention policies...")
        
        policies = [
            {
                'policy_id': 'PATIENT_MEDICAL_RECORDS',
                'name': 'Registros Médicos de Pacientes',
                'data_category': 'patient_medical_records',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'PATIENT_IDENTIFICATION',
                'name': 'Dados de Identificação de Pacientes',
                'data_category': 'patient_identification',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'STAFF_PROFESSIONAL_DATA',
                'name': 'Dados Profissionais da Equipe',
                'data_category': 'staff_professional_data',
                'retention_period_days': 1825,  # 5 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Legislação Trabalhista',
                'warning_period_days': 90,
                'grace_period_days': 30,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': False,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': False,
            },
            {
                'policy_id': 'AUDIT_LOGS',
                'name': 'Logs de Auditoria',
                'data_category': 'audit_logs',
                'retention_period_days': 1095,  # 3 years
                'retention_basis': 'business_necessity',
                'legal_reference': 'LGPD Art. 37 - Registro de Operações',
                'warning_period_days': 30,
                'grace_period_days': 7,
                'auto_delete_enabled': True,
                'anonymize_instead_delete': False,
                'require_manual_approval': False,
                'legal_hold_exempt': True,
                'emergency_access_required': False,
            },
            {
                'policy_id': 'CONSENT_RECORDS',
                'name': 'Registros de Consentimento',
                'data_category': 'consent_records',
                'retention_period_days': 7665,  # 21 years (1 year beyond medical records)
                'retention_basis': 'legal_obligation',
                'legal_reference': 'LGPD Art. 8 - Comprovação de Consentimento',
                'warning_period_days': 365,
                'grace_period_days': 180,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': False,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'MEDIA_FILES',
                'name': 'Arquivos de Mídia Médica',
                'data_category': 'media_files',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'medical_requirement',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            }
        ]
        
        created_count = 0
        for policy_data in policies:
            policy, created = DataRetentionPolicy.objects.get_or_create(
                policy_id=policy_data['policy_id'],
                defaults=policy_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {policy}")
            else:
                self.stdout.write(f"- Exists: {policy}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} retention policies')
        )
        
        # Show summary
        total_policies = DataRetentionPolicy.objects.filter(is_active=True).count()
        self.stdout.write(f"\nActive retention policies: {total_policies}")
        
        # Show policy overview
        self.stdout.write(f"\nPolicy Overview:")
        for policy in DataRetentionPolicy.objects.filter(is_active=True).order_by('data_category'):
            years = policy.retention_period_days / 365.25
            self.stdout.write(f"  {policy.data_category}: {years:.1f} years")