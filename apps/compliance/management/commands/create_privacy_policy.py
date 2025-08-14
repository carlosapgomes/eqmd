from django.core.management.base import BaseCommand
from apps.compliance.models import PrivacyPolicy, LGPDComplianceSettings
from datetime import date, datetime
import os

class Command(BaseCommand):
    help = 'Creates initial privacy policy from template'
    
    def add_arguments(self, parser):
        parser.add_argument('--template', type=str, help='Template file path')
        parser.add_argument('--policy-version', type=str, default='1.0', help='Policy version')
        parser.add_argument('--preview', action='store_true', help='Preview without saving')
    
    def handle(self, *args, **options):
        # Get LGPD settings
        try:
            lgpd_settings = LGPDComplianceSettings.objects.first()
            if not lgpd_settings:
                self.stdout.write(self.style.ERROR('LGPD settings not configured. Run setup_lgpd_settings first.'))
                return
        except:
            self.stdout.write(self.style.ERROR('LGPD settings not found.'))
            return
        
        # Load template
        template_path = options.get('template') or 'prompts/compliance/templates/privacy_policy_template.md'
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Template file not found: {template_path}'))
            return
        
        # Template variables
        variables = {
            'hospital_name': lgpd_settings.controller_name,
            'cnpj': lgpd_settings.controller_cnpj,
            'address': lgpd_settings.controller_address,
            'phone': '[TELEFONE_HOSPITAL]',  # Not in settings yet
            'email': '[EMAIL_HOSPITAL]',     # Not in settings yet
            'dpo_name': lgpd_settings.dpo_name,
            'dpo_email': lgpd_settings.dpo_email,
            'dpo_phone': lgpd_settings.dpo_phone,
            'version': options['policy_version'],
            'effective_date': date.today().strftime('%d/%m/%Y'),
            'last_updated': date.today().strftime('%d/%m/%Y'),
            'legal_reviewer': '[REVISOR_JURIDICO]',
            'legal_review_date': '[DATA_REVISAO]',
            'next_review_date': '[PROXIMA_REVISAO]',
            'hospital_address': lgpd_settings.controller_address,
        }
        
        # Replace template variables
        content = template_content
        for key, value in variables.items():
            content = content.replace(f'{{{{ {key} }}}}', str(value))
        
        if options['preview']:
            self.stdout.write("Privacy Policy Preview:")
            self.stdout.write("-" * 50)
            self.stdout.write(content[:1000] + "..." if len(content) > 1000 else content)
            return
        
        # Create privacy policy
        policy = PrivacyPolicy.objects.create(
            version=options['policy_version'],
            policy_type='main',
            title=f'Política de Privacidade - {lgpd_settings.controller_name}',
            summary='Política principal de privacidade conforme LGPD',
            content_markdown=content,
            effective_date=datetime.now(),
            is_active=True,
            legal_review_completed=False
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Privacy policy created successfully: {policy}')
        )
        self.stdout.write(
            self.style.WARNING('Remember to:')
        )
        self.stdout.write('1. Review and complete placeholder values')
        self.stdout.write('2. Have legal team review the policy')
        self.stdout.write('3. Mark legal_review_completed = True')
        self.stdout.write('4. Configure hospital contact information')