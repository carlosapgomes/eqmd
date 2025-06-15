from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.sample_content.models import SampleContent
from apps.events.models import Event

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample content for different event types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--superuser-email',
            type=str,
            help='Email of superuser to create sample content (defaults to first superuser)',
        )

    def handle(self, *args, **options):
        # Get superuser
        if options['superuser_email']:
            try:
                superuser = User.objects.get(email=options['superuser_email'], is_superuser=True)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Superuser with email {options["superuser_email"]} not found')
                )
                return
        else:
            superuser = User.objects.filter(is_superuser=True).first()
            if not superuser:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Please create a superuser first.')
                )
                return

        # Sample content data
        sample_contents = [
            {
                'title': 'Template de Evolução Diária',
                'content': '''Paciente apresenta-se em estado geral [bom/regular/grave].
                
Sinais vitais:
- PA: ___/___ mmHg
- FC: ___ bpm
- FR: ___ rpm
- Temp: ___°C
- SatO2: ___%

Exame físico:
- [Descrever achados relevantes]

Condutas:
- [Listar medicações e procedimentos]

Evolução:
- [Descrever evolução desde última avaliação]

Plano:
- [Próximos passos e condutas]''',
                'event_type': Event.DAILY_NOTE_EVENT,
            },
            {
                'title': 'Template de Anamnese e Exame Físico',
                'content': '''IDENTIFICAÇÃO:
Nome: _______________
Idade: ___ anos
Sexo: _______________

QUEIXA PRINCIPAL:
[Descrever motivo da consulta]

HISTÓRIA DA DOENÇA ATUAL:
[Cronologia dos sintomas]

ANTECEDENTES:
- Pessoais: _______________
- Familiares: _____________
- Medicamentos em uso: ____

EXAME FÍSICO:
- Estado geral: ___________
- Sinais vitais: __________
- Aparelho cardiovascular: _
- Aparelho respiratório: ___
- Abdome: ________________
- Extremidades: ___________

HIPÓTESES DIAGNÓSTICAS:
1. ______________________
2. ______________________

CONDUTA:
[Exames solicitados, medicações, orientações]''',
                'event_type': Event.HISTORY_AND_PHYSICAL_EVENT,
            },
            {
                'title': 'Nota de Observação Simples',
                'content': '''Data: ___/___/___
Hora: ___:___

Observação:
[Descrever fato relevante ou mudança no quadro clínico]

Conduta tomada:
[Se houver alguma intervenção realizada]

Profissional: _______________
Categoria: _________________''',
                'event_type': Event.SIMPLE_NOTE_EVENT,
            },
            {
                'title': 'Relatório de Alta Hospitalar',
                'content': '''RELATÓRIO DE ALTA HOSPITALAR

Paciente: _______________
Data de internação: ___/___/___
Data de alta: ___/___/___

DIAGNÓSTICO PRINCIPAL:
[CID-10: ___]

DIAGNÓSTICOS SECUNDÁRIOS:
[Listar se aplicável]

RESUMO DA INTERNAÇÃO:
[Evolução durante internação, procedimentos realizados]

MEDICAÇÕES NA ALTA:
1. ______________________
2. ______________________

ORIENTAÇÕES:
- Retorno em ___ dias
- Sinais de alerta: _______
- Cuidados especiais: ____

Médico responsável: ______________
CRM: ___________''',
                'event_type': Event.DISCHARGE_REPORT_EVENT,
            },
            {
                'title': 'Requisição de Exames',
                'content': '''REQUISIÇÃO DE EXAMES

Paciente: _______________
Data: ___/___/___

EXAMES SOLICITADOS:

Laboratoriais:
□ Hemograma completo
□ Bioquímica (glicose, ureia, creatinina)
□ Eletrólitos (Na, K, Cl)
□ Função hepática (TGO, TGP, bilirrubinas)
□ Coagulograma (TP, TTPA, INR)
□ Outros: _______________

Imagens:
□ Raio-X de tórax
□ Ultrassom abdominal
□ Tomografia computadorizada
□ Ressonância magnética
□ Outros: _______________

JUSTIFICATIVA:
[Indicação clínica para os exames]

Médico solicitante: ______________
CRM: ___________''',
                'event_type': Event.EXAMS_REQUEST_EVENT,
            },
        ]

        created_count = 0
        for sample_data in sample_contents:
            # Check if sample content already exists
            existing = SampleContent.objects.filter(
                title=sample_data['title'],
                event_type=sample_data['event_type']
            ).first()
            
            if not existing:
                SampleContent.objects.create(
                    title=sample_data['title'],
                    content=sample_data['content'],
                    event_type=sample_data['event_type'],
                    created_by=superuser,
                    updated_by=superuser
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {sample_data["title"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Already exists: {sample_data["title"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSample content creation completed. Created {created_count} new items.')
        )