from django.core.management.base import BaseCommand
from apps.compliance.models import LGPDComplianceSettings
from datetime import date

class Command(BaseCommand):
    help = 'Sets up initial LGPD compliance settings'
    
    def add_arguments(self, parser):
        parser.add_argument('--dpo-name', type=str, help='DPO name')
        parser.add_argument('--dpo-email', type=str, help='DPO email')
        parser.add_argument('--hospital-name', type=str, help='Hospital name')
        parser.add_argument('--cnpj', type=str, help='Hospital CNPJ')
    
    def handle(self, *args, **options):
        if LGPDComplianceSettings.objects.exists():
            self.stdout.write(self.style.WARNING('LGPD settings already exist'))
            return
        
        # Use provided values or defaults
        dpo_name = options.get('dpo_name') or '[NOME_DO_DPO]'
        dpo_email = options.get('dpo_email') or 'lgpd@hospital.com.br'
        hospital_name = options.get('hospital_name') or '[NOME_DO_HOSPITAL]'
        cnpj = options.get('cnpj') or '[CNPJ_DO_HOSPITAL]'
        
        settings = LGPDComplianceSettings.objects.create(
            dpo_name=dpo_name,
            dpo_email=dpo_email,
            dpo_phone='[TELEFONE_DPO]',
            controller_name=hospital_name,
            controller_address='[ENDEREÇO_DO_HOSPITAL]',
            controller_cnpj=cnpj,
            anpd_notification_threshold=100,
            breach_notification_email=dpo_email,
            default_retention_days=7300,  # 20 years
            deletion_warning_days=180,    # 6 months
            privacy_policy_version="1.0"
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'LGPD settings created successfully: {settings}')
        )
        self.stdout.write(
            self.style.WARNING('Remember to update placeholder values in Django admin')
        )