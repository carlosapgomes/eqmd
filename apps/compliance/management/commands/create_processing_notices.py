from django.core.management.base import BaseCommand
from apps.compliance.models import DataProcessingNotice

class Command(BaseCommand):
    help = 'Creates initial data processing notices'
    
    def handle(self, *args, **options):
        notices = [
            {
                'notice_id': 'PATIENT_REGISTRATION',
                'context': 'patient_registration',
                'title': 'Aviso de Processamento - Cadastro de Paciente',
                'purpose_description': 'Coletamos seus dados pessoais para identificação e prestação de cuidados médicos conforme protocolos hospitalares.',
                'data_categories': 'Nome, CPF, data de nascimento, endereço, telefone, dados de saúde',
                'legal_basis': 'Art. 11º, II, a da LGPD (procedimentos médicos)',
                'retention_period': '20 anos após última consulta (Resolução CFM 1.821/2007)',
                'recipients': 'Equipe médica autorizada, enfermagem, administração hospitalar',
                'rights_summary': 'Você tem direito a acessar, corrigir, excluir e portar seus dados conforme LGPD',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'modal'
            },
            {
                'notice_id': 'PHOTO_VIDEO_CAPTURE',
                'context': 'photo_video_capture',
                'title': 'Aviso - Captura de Imagens Médicas',
                'purpose_description': 'Capturamos fotos e vídeos para documentação médica, diagnóstico e acompanhamento do tratamento.',
                'data_categories': 'Imagens fotográficas e vídeos com conteúdo médico',
                'legal_basis': 'Art. 7º, I da LGPD (consentimento) + Art. 11º, II, a (procedimentos médicos)',
                'retention_period': '20 anos conforme prontuário médico',
                'recipients': 'Médicos responsáveis, especialistas consultados',
                'rights_summary': 'Você pode retirar o consentimento a qualquer momento, solicitar acesso ou exclusão das imagens',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'modal'
            },
            {
                'notice_id': 'EMERGENCY_TREATMENT',
                'context': 'emergency_treatment',
                'title': 'Processamento em Emergência',
                'purpose_description': 'Em situações de emergência, processamos seus dados para proteção da vida e prestação de cuidados urgentes.',
                'data_categories': 'Dados de identificação, histórico médico, dados de emergência',
                'legal_basis': 'Art. 11º, II, e da LGPD (proteção da vida)',
                'retention_period': '20 anos conforme legislação médica',
                'recipients': 'Equipe de emergência, médicos plantonistas',
                'rights_summary': 'Após estabilização, você poderá exercer todos os direitos previstos na LGPD',
                'contact_info': 'DPO: [EMAIL_DPO] | [TELEFONE_DPO]',
                'display_format': 'banner'
            }
        ]
        
        created_count = 0
        for notice_data in notices:
            notice, created = DataProcessingNotice.objects.get_or_create(
                notice_id=notice_data['notice_id'],
                defaults=notice_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {notice}")
            else:
                self.stdout.write(f"- Exists: {notice}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} processing notices')
        )