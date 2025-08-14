from django.core.management.base import BaseCommand
from apps.compliance.models import DataProcessingPurpose
import json

class Command(BaseCommand):
    help = 'Sets up LGPD legal basis documentation for EquipeMed'
    
    def handle(self, *args, **options):
        self.stdout.write("Setting up LGPD legal basis documentation...")
        
        # Patient data processing purposes
        patient_purposes = [
            {
                'data_category': 'patient_identification',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Identificação de pacientes para prestação de cuidados médicos conforme protocolo hospitalar',
                'data_fields_included': json.dumps([
                    'nome', 'data_nascimento', 'cpf', 'cartao_sus', 'endereco', 'telefone'
                ]),
                'processing_activities': 'Coleta, armazenamento, consulta, atualização para identificação e contato',
                'data_recipients': 'Equipe médica autorizada, enfermagem, fisioterapeutas, residentes',
                'retention_period_days': 7300,  # 20 years
                'retention_criteria': '20 anos após última consulta conforme Resolução CFM 1.821/2007',
                'security_measures': 'Controle de acesso por função, auditoria completa, criptografia, UUIDs'
            },
            {
                'data_category': 'patient_medical_history',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Registro e acompanhamento do histórico médico para continuidade do tratamento',
                'data_fields_included': json.dumps([
                    'historico_medico', 'diagnosticos', 'medicamentos', 'alergias', 'procedimentos'
                ]),
                'processing_activities': 'Coleta, armazenamento, consulta, atualização, análise clínica',
                'data_recipients': 'Médicos responsáveis, equipe multidisciplinar autorizada',
                'retention_period_days': 7300,
                'retention_criteria': '20 anos após última consulta para preservação histórico médico',
                'security_measures': 'Acesso restrito a profissionais autorizados, logs de auditoria, janela de edição 24h'
            },
            {
                'data_category': 'patient_current_treatment',
                'purpose': 'medical_care',
                'legal_basis': 'art11_ii_a',
                'description': 'Gerenciamento do tratamento atual e evolução clínica do paciente',
                'data_fields_included': json.dumps([
                    'evolucoes_diarias', 'prescricoes', 'exames', 'sinais_vitais', 'procedimentos'
                ]),
                'processing_activities': 'Registro em tempo real, consulta, atualização, compartilhamento entre equipe',
                'data_recipients': 'Equipe médica, enfermagem, especialistas consultados',
                'retention_period_days': 7300,
                'retention_criteria': '20 anos para acompanhamento longitudinal da saúde',
                'security_measures': 'Controle de acesso por setor, monitoramento de atividade suspeita'
            }
        ]
        
        # Staff data processing purposes
        staff_purposes = [
            {
                'data_category': 'staff_identification',
                'purpose': 'legal_obligation',
                'legal_basis': 'art7_ii',
                'description': 'Identificação de profissionais conforme exigências do CFM e CRM',
                'data_fields_included': json.dumps([
                    'nome', 'email', 'crm', 'especialidade', 'telefone'
                ]),
                'processing_activities': 'Cadastro, validação, consulta para identificação profissional',
                'data_recipients': 'Administração hospitalar, outros profissionais da equipe',
                'retention_period_days': 1825,  # 5 years
                'retention_criteria': '5 anos após fim do vínculo profissional para auditoria',
                'security_measures': 'Autenticação forte, controle de sessão, logs de acesso'
            },
            {
                'data_category': 'system_audit',
                'purpose': 'legitimate_interest',
                'legal_basis': 'art7_vi',
                'description': 'Auditoria de segurança e monitoramento de acesso para proteção de dados',
                'data_fields_included': json.dumps([
                    'logs_acesso', 'ip_address', 'timestamp', 'acao_realizada'
                ]),
                'processing_activities': 'Coleta automática, análise, armazenamento para auditoria',
                'data_recipients': 'Administradores de sistema, responsável pela segurança',
                'retention_period_days': 1095,  # 3 years
                'retention_criteria': '3 anos para investigação de incidentes e auditoria de segurança',
                'security_measures': 'Logs protegidos, acesso restrito, detecção de anomalias'
            }
        ]
        
        # Create all purposes
        all_purposes = patient_purposes + staff_purposes
        created_count = 0
        
        for purpose_data in all_purposes:
            obj, created = DataProcessingPurpose.objects.get_or_create(
                data_category=purpose_data['data_category'],
                purpose=purpose_data['purpose'],
                defaults=purpose_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {obj}")
            else:
                self.stdout.write(f"- Exists: {obj}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} legal basis records')
        )