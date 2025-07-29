from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from faker import Faker

from apps.patients.models import Patient, AllowedTag, Tag, PatientRecordNumber, PatientAdmission, Ward
from apps.dailynotes.models import DailyNote
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem

User = get_user_model()
fake = Faker('pt_BR')


class Command(BaseCommand):
    help = 'Populate database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing sample data before creating new data',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']

        if options['clear_existing']:
            self.clear_existing_data()

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be created'))

        self.create_users()
        self.create_sample_wards()
        self.create_tags()
        self.create_patients()
        self.create_daily_notes()
        self.create_drug_templates()
        self.create_prescription_templates()
        self.create_outpatient_prescriptions()

        self.display_completion_message()

    def clear_existing_data(self):
        if self.dry_run:
            self.stdout.write('Would clear existing sample data')
            return

        self.stdout.write('Clearing existing sample data...')
        # Clear in proper order to respect foreign key constraints

        # First clear all events (including outpatient prescriptions and daily notes)
        from apps.events.models import Event
        Event.objects.filter(created_by__username__startswith='sample_').delete()

        # Clear prescription templates and their items
        PrescriptionTemplate.objects.filter(creator__username__startswith='sample_').delete()
        # Clear drug templates
        DrugTemplate.objects.filter(creator__username__startswith='sample_').delete()

        # Clear tags (both Tag and AllowedTag instances)
        Tag.objects.filter(created_by__username__startswith='sample_').delete()
        AllowedTag.objects.filter(created_by__username__startswith='sample_').delete()

        # Clear patient admissions and record numbers before patients
        PatientAdmission.objects.filter(created_by__username__startswith='sample_').delete()
        PatientRecordNumber.objects.filter(created_by__username__startswith='sample_').delete()

        # Clear patients (now safe since events, tags, admissions and record numbers are deleted)
        Patient.objects.filter(created_by__username__startswith='sample_').delete()

        # Clear wards
        Ward.objects.filter(created_by__username__startswith='sample_').delete()

        # Clear users last (now safe since all dependent objects are deleted)
        User.objects.filter(username__startswith='sample_').delete()


    def create_users(self):
        self.stdout.write('Creating users...')
        
        
        users_data = [
            # Doctors
            {'username': 'sample_dr_silva', 'email': 'dr.silva@example.com', 'first_name': 'João', 'last_name': 'Silva', 'profession': 0},
            {'username': 'sample_dr_santos', 'email': 'dr.santos@example.com', 'first_name': 'Maria', 'last_name': 'Santos', 'profession': 0},
            {'username': 'sample_dr_oliveira', 'email': 'dr.oliveira@example.com', 'first_name': 'Carlos', 'last_name': 'Oliveira', 'profession': 0},
            {'username': 'sample_dr_costa', 'email': 'dr.costa@example.com', 'first_name': 'Ana', 'last_name': 'Costa', 'profession': 0},
            {'username': 'sample_dr_ferreira', 'email': 'dr.ferreira@example.com', 'first_name': 'Pedro', 'last_name': 'Ferreira', 'profession': 0},
            
            # Nurses
            {'username': 'sample_enf_maria', 'email': 'enf.maria@example.com', 'first_name': 'Maria', 'last_name': 'Souza', 'profession': 2},
            {'username': 'sample_enf_jose', 'email': 'enf.jose@example.com', 'first_name': 'José', 'last_name': 'Lima', 'profession': 2},
            
            # Residents
            {'username': 'sample_res_ana', 'email': 'res.ana@example.com', 'first_name': 'Ana', 'last_name': 'Rodrigues', 'profession': 1},
            {'username': 'sample_res_carlos', 'email': 'res.carlos@example.com', 'first_name': 'Carlos', 'last_name': 'Mendes', 'profession': 1},
            
            # Students
            {'username': 'sample_est_paula', 'email': 'est.paula@example.com', 'first_name': 'Paula', 'last_name': 'Alves', 'profession': 4},
            {'username': 'sample_est_pedro', 'email': 'est.pedro@example.com', 'first_name': 'Pedro', 'last_name': 'Barbosa', 'profession': 4},
        ]

        self.users = []
        password = 'samplepass123'
        
        for user_data in users_data:
            if self.dry_run:
                self.stdout.write(f'Would create user: {user_data["username"]} ({user_data["email"]})')
                continue
                
            profession = user_data.pop('profession')
            user = User.objects.create_user(
                password=password,
                profession_type=profession,
                professional_registration_number=f'REG{random.randint(10000, 99999)}',
                **user_data
            )
            
            
            self.users.append(user)
            profession_name = user.get_profession_type_display()
            self.stdout.write(f'  Created {profession_name}: {user.email}')

    def create_sample_wards(self):
        self.stdout.write('Creating sample wards...')
        
        admin_user = self.users[0] if self.users and not self.dry_run else None
        
        wards_data = [
            {
                "name": "Unidade de Terapia Intensiva",
                "abbreviation": "UTI",
                "description": "Unidade de cuidados intensivos para pacientes críticos",
                "floor": "3º Andar",
                "capacity_estimate": 12,
            },
            {
                "name": "Pronto Socorro",
                "abbreviation": "PS",
                "description": "Atendimento de emergência e urgência",
                "floor": "Térreo",
                "capacity_estimate": 8,
            },
            {
                "name": "Clínica Médica",
                "abbreviation": "CM",
                "description": "Internação clínica geral",
                "floor": "2º Andar",
                "capacity_estimate": 20,
            },
            {
                "name": "Clínica Cirúrgica",
                "abbreviation": "CC",
                "description": "Internação de pacientes cirúrgicos",
                "floor": "2º Andar",
                "capacity_estimate": 15,
            },
            {
                "name": "Pediatria",
                "abbreviation": "PED",
                "description": "Atendimento pediátrico",
                "floor": "1º Andar",
                "capacity_estimate": 10,
            },
            {
                "name": "Maternidade",
                "abbreviation": "MAT",
                "description": "Atendimento obstétrico e neonatal",
                "floor": "1º Andar",
                "capacity_estimate": 12,
            },
        ]

        self.wards = []
        created_count = 0
        
        for ward_data in wards_data:
            if self.dry_run:
                self.stdout.write(f'Would create ward: {ward_data["name"]}')
                continue
                
            ward, created = Ward.objects.get_or_create(
                abbreviation=ward_data["abbreviation"],
                defaults={
                    **ward_data,
                    "created_by": admin_user,
                    "updated_by": admin_user,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created ward: {ward}')
            else:
                self.stdout.write(f'  Ward already exists: {ward}')
            
            self.wards.append(ward)

        if not self.dry_run:
            self.stdout.write(f'Created {created_count} sample wards')

    def create_tags(self):
        self.stdout.write('Creating sample tags...')
        
        tags_data = [
            {'name': 'Diabetes', 'description': 'Paciente diabético', 'color': '#dc3545'},
            {'name': 'Hipertensão', 'description': 'Paciente hipertenso', 'color': '#fd7e14'},
            {'name': 'Cardiopata', 'description': 'Paciente com problemas cardíacos', 'color': '#6610f2'},
            {'name': 'Idoso', 'description': 'Paciente idoso', 'color': '#6f42c1'},
            {'name': 'Crítico', 'description': 'Paciente em estado crítico', 'color': '#e83e8c'},
            {'name': 'Alérgico', 'description': 'Paciente com alergias conhecidas', 'color': '#20c997'},
        ]

        self.allowed_tags = []
        admin_user = self.users[0] if self.users and not self.dry_run else None
        
        for tag_data in tags_data:
            if self.dry_run:
                self.stdout.write(f'Would create tag: {tag_data["name"]}')
                continue
                
            allowed_tag = AllowedTag.objects.create(
                created_by=admin_user,
                updated_by=admin_user,
                **tag_data
            )
            self.allowed_tags.append(allowed_tag)
            self.stdout.write(f'  Created tag: {allowed_tag.name}')

    def create_patients(self):
        self.stdout.write('Creating patients...')
        
        self.patients = []
        
        # Create 20 patients with mixed statuses
        for i in range(20):
            is_inpatient = i < 10  # First 10 are inpatients
            patient = self.create_patient(is_inpatient)
            if patient:
                self.patients.append(patient)
        
        self.stdout.write(f'Created {len(self.patients)} patients total')

    def create_patient(self, is_inpatient):
        if self.dry_run:
            status = 'inpatient' if is_inpatient else 'outpatient'
            self.stdout.write(f'Would create {status} patient')
            return None
            
        creator = random.choice(self.users)
        
        # Generate realistic patient data with realistic gender distribution
        # Realistic hospital demographics: ~48% male, ~48% female, ~2% other, ~2% not informed
        gender_weights = [
            (Patient.GenderChoices.MALE, 48),
            (Patient.GenderChoices.FEMALE, 48),
            (Patient.GenderChoices.OTHER, 2),
            (Patient.GenderChoices.NOT_INFORMED, 2)
        ]
        
        # Use weighted random selection for more realistic distribution
        choices, weights = zip(*gender_weights)
        gender = random.choices(choices, weights=weights)[0]
        if gender == Patient.GenderChoices.MALE:
            first_name = fake.first_name_male()
        elif gender == Patient.GenderChoices.FEMALE:
            first_name = fake.first_name_female()
        else:
            # For OTHER and NOT_INFORMED, use a random name
            first_name = fake.first_name()
        
        last_name = fake.last_name()
        name = f'{first_name} {last_name}'
        
        # Generate record number
        record_number = f'PRN{random.randint(100000, 999999)}'
        
        # Create patient first
        patient = Patient.objects.create(
            name=name,
            birthday=fake.date_of_birth(minimum_age=18, maximum_age=90),
            gender=gender,
            healthcard_number=f'SUS{random.randint(100000000, 999999999)}',
            id_number=fake.rg(),
            fiscal_number=fake.cpf(),
            phone=fake.phone_number(),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            zip_code=fake.postcode(),
            status=Patient.Status.OUTPATIENT,  # Start as outpatient, will be updated if needed
            current_record_number=record_number,
            created_by=creator,
            updated_by=creator,
        )
        
        # Create patient record number entry
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number=record_number,
            is_current=True,
            change_reason='Registro inicial do paciente',
            effective_date=timezone.now(),
            created_by=creator,
            updated_by=creator,
        )
        
        # Handle admission if patient should be inpatient
        if is_inpatient:
            admission_datetime = fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.get_current_timezone())
            admission_type = random.choice([PatientAdmission.AdmissionType.EMERGENCY, PatientAdmission.AdmissionType.SCHEDULED])
            bed = f'Leito {random.randint(1, 50)}'
            
            # Create admission record
            admission = PatientAdmission.objects.create(
                patient=patient,
                admission_datetime=admission_datetime,
                admission_type=admission_type,
                initial_bed=bed,
                admission_diagnosis=self.get_random_admission_diagnosis(),
                is_active=True,
                created_by=creator,
                updated_by=creator,
            )
            
            # Update patient status and fields
            patient.status = Patient.Status.INPATIENT
            patient.current_admission_id = admission.id
            patient.bed = bed
            patient.last_admission_date = admission_datetime.date()
            patient.total_admissions_count = 1
            patient.save(update_fields=[
                'status', 'current_admission_id', 'bed', 'last_admission_date', 
                'total_admissions_count', 'updated_at'
            ])
        
        # Assign random tags
        if self.allowed_tags:
            num_tags = random.randint(0, 3)
            selected_allowed_tags = random.sample(self.allowed_tags, min(num_tags, len(self.allowed_tags)))
            
            for allowed_tag in selected_allowed_tags:
                tag, created = Tag.objects.get_or_create(
                    allowed_tag=allowed_tag,
                    defaults={
                        'notes': f'Tag aplicada ao paciente {patient.name}',
                        'created_by': creator,
                        'updated_by': creator,
                    }
                )
                patient.tags.add(tag)
        
        return patient
    
    def get_random_admission_diagnosis(self):
        """Generate random admission diagnoses."""
        diagnoses = [
            "Pneumonia adquirida na comunidade",
            "Insuficiência cardíaca congestiva",
            "Diabetes mellitus descompensada",
            "Hipertensão arterial sistêmica",
            "Infecção do trato urinário",
            "Gastroenterite aguda",
            "Bronquite aguda",
            "Crise hipertensiva",
            "Síndrome coronariana aguda",
            "Acidente vascular cerebral",
            "Fratura de fêmur",
            "Apendicite aguda",
            "Colecistite aguda",
            "Pancreatite aguda",
            "Insuficiência renal aguda"
        ]
        return random.choice(diagnoses)

    def create_daily_notes(self):
        self.stdout.write('Creating daily notes...')
        
        if self.dry_run:
            self.stdout.write('Would create 5 daily notes per patient (200 total)')
            return
            
        medical_notes_templates = [
            "Paciente em bom estado geral, consciente, orientado no tempo e espaço. Sinais vitais estáveis. Mantém-se afebril. Aceita dieta por via oral sem intercorrências.",
            "Evolução favorável do quadro clínico. Paciente relata melhora da dor. Exame físico sem particularidades. Mantido esquema terapêutico atual.",
            "Paciente estável, com boa aceitação da medicação prescrita. Ausculta pulmonar com murmúrio vesicular presente bilateralmente. Abdome flácido, indolor.",
            "Encontra-se em regular estado geral, cooperativo ao exame. Sinais vitais dentro dos parâmetros normais. Diurese presente e espontânea.",
            "Paciente consciente, responsivo, mantém padrão respiratório adequado. Ferida operatória com bom aspecto, sem sinais flogísticos.",
            "Evolução satisfatória. Paciente deambula sem auxílio, alimenta-se bem. Exame cardiovascular sem alterações significativas.",
            "Mantém quadro estável. Glicemia capilar controlada. Paciente orientado quanto aos cuidados domiciliares e retorno ambulatorial.",
            "Estado geral preservado. Paciente refere diminuição dos sintomas iniciais. Exame neurológico dentro da normalidade.",
        ]
        
        total_notes = 0
        
        for patient in self.patients:
            # Create 5 daily notes per patient with different dates
            for i in range(5):
                creator = random.choice(self.users)
                
                # Create notes from 15 days ago to today
                days_ago = random.randint(0, 15)
                note_datetime = timezone.now() - timedelta(days=days_ago, 
                                                         hours=random.randint(8, 18), 
                                                         minutes=random.randint(0, 59))
                
                content = random.choice(medical_notes_templates)
                
                # Add some variation to the content
                additional_info = [
                    f" Temperatura: {random.uniform(36.0, 37.5):.1f}°C.",
                    f" Pressão arterial: {random.randint(110, 140)}/{random.randint(70, 90)} mmHg.",
                    f" Frequência cardíaca: {random.randint(60, 100)} bpm.",
                    " Solicita reavaliação médica em 24h.",
                    " Familiar presente e orientado sobre o quadro clínico.",
                ]
                
                if random.random() < 0.3:  # 30% chance of additional info
                    content += random.choice(additional_info)
                
                daily_note = DailyNote.objects.create(
                    event_datetime=note_datetime,
                    description=f"Evolução diária - {patient.name}",
                    patient=patient,
                    content=content,
                    created_by=creator,
                    updated_by=creator,
                )
                
                total_notes += 1
        
        self.stdout.write(f'Created {total_notes} daily notes')

    def create_drug_templates(self):
        self.stdout.write('Creating drug templates...')

        # Realistic drug template data for Brazilian medical context
        drug_templates_data = [
            {
                'name': 'Dipirona Sódica',
                'presentation': '500mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral a cada 6 horas, se necessário para dor ou febre. Não exceder 4 comprimidos por dia.',
                'is_public': True
            },
            {
                'name': 'Paracetamol',
                'presentation': '750mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral a cada 8 horas. Máximo 3 comprimidos por dia.',
                'is_public': True
            },
            {
                'name': 'Omeprazol',
                'presentation': '20mg cápsula',
                'usage_instructions': 'Tomar 1 cápsula por via oral em jejum, 30 minutos antes do café da manhã.',
                'is_public': True
            },
            {
                'name': 'Losartana Potássica',
                'presentation': '50mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                'is_public': True
            },
            {
                'name': 'Metformina',
                'presentation': '850mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral 2 vezes ao dia, durante as refeições (café da manhã e jantar).',
                'is_public': True
            },
            {
                'name': 'Sinvastatina',
                'presentation': '20mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente à noite.',
                'is_public': True
            },
            {
                'name': 'Captopril',
                'presentation': '25mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral 2 vezes ao dia, em jejum (1 hora antes das refeições).',
                'is_public': True
            },
            {
                'name': 'Hidroclorotiazida',
                'presentation': '25mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                'is_public': True
            },
            {
                'name': 'Ácido Acetilsalicílico',
                'presentation': '100mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, após o café da manhã.',
                'is_public': True
            },
            {
                'name': 'Atenolol',
                'presentation': '50mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                'is_public': True
            },
            {
                'name': 'Amoxicilina',
                'presentation': '500mg cápsula',
                'usage_instructions': 'Tomar 1 cápsula por via oral a cada 8 horas por 7 dias. Tomar com água, pode ser com alimentos.',
                'is_public': False
            },
            {
                'name': 'Azitromicina',
                'presentation': '500mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia por 3 dias, em jejum (1 hora antes ou 2 horas após as refeições).',
                'is_public': False
            },
            {
                'name': 'Prednisona',
                'presentation': '20mg comprimido',
                'usage_instructions': 'Tomar conforme orientação médica. Geralmente 1 comprimido pela manhã, após o café da manhã.',
                'is_public': False
            },
            {
                'name': 'Diclofenaco Sódico',
                'presentation': '50mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral a cada 8 horas, após as refeições. Usar pelo menor tempo possível.',
                'is_public': False
            },
            {
                'name': 'Furosemida',
                'presentation': '40mg comprimido',
                'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                'is_public': False
            }
        ]

        self.drug_templates = []

        for template_data in drug_templates_data:
            if self.dry_run:
                self.stdout.write(f'Would create drug template: {template_data["name"]}')
                continue

            creator = random.choice(self.users)

            drug_template = DrugTemplate.objects.create(
                name=template_data['name'],
                presentation=template_data['presentation'],
                usage_instructions=template_data['usage_instructions'],
                creator=creator,
                is_public=template_data['is_public']
            )

            self.drug_templates.append(drug_template)
            visibility = 'público' if drug_template.is_public else 'privado'
            self.stdout.write(f'  Created drug template: {drug_template.name} ({visibility})')

        if not self.dry_run:
            self.stdout.write(f'Created {len(self.drug_templates)} drug templates')

    def create_prescription_templates(self):
        self.stdout.write('Creating prescription templates...')

        # Common prescription template scenarios
        prescription_templates_data = [
            {
                'name': 'Hipertensão Arterial - Tratamento Inicial',
                'is_public': True,
                'items': [
                    {
                        'drug_name': 'Losartana Potássica',
                        'presentation': '50mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                        'quantity': '30 comprimidos',
                        'order': 1
                    },
                    {
                        'drug_name': 'Hidroclorotiazida',
                        'presentation': '25mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente pela manhã.',
                        'quantity': '30 comprimidos',
                        'order': 2
                    }
                ]
            },
            {
                'name': 'Diabetes Mellitus Tipo 2 - Monoterapia',
                'is_public': True,
                'items': [
                    {
                        'drug_name': 'Metformina',
                        'presentation': '850mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral 2 vezes ao dia, durante as refeições (café da manhã e jantar).',
                        'quantity': '60 comprimidos',
                        'order': 1
                    }
                ]
            },
            {
                'name': 'Dislipidemia - Tratamento com Estatina',
                'is_public': True,
                'items': [
                    {
                        'drug_name': 'Sinvastatina',
                        'presentation': '20mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia, preferencialmente à noite.',
                        'quantity': '30 comprimidos',
                        'order': 1
                    }
                ]
            },
            {
                'name': 'Proteção Gástrica + Analgesia',
                'is_public': True,
                'items': [
                    {
                        'drug_name': 'Omeprazol',
                        'presentation': '20mg cápsula',
                        'usage_instructions': 'Tomar 1 cápsula por via oral em jejum, 30 minutos antes do café da manhã.',
                        'quantity': '30 cápsulas',
                        'order': 1
                    },
                    {
                        'drug_name': 'Dipirona Sódica',
                        'presentation': '500mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral a cada 6 horas, se necessário para dor. Não exceder 4 comprimidos por dia.',
                        'quantity': '20 comprimidos',
                        'order': 2
                    }
                ]
            },
            {
                'name': 'Infecção Respiratória - Antibiótico',
                'is_public': False,
                'items': [
                    {
                        'drug_name': 'Azitromicina',
                        'presentation': '500mg comprimido',
                        'usage_instructions': 'Tomar 1 comprimido por via oral uma vez ao dia por 3 dias, em jejum (1 hora antes ou 2 horas após as refeições).',
                        'quantity': '3 comprimidos',
                        'order': 1
                    }
                ]
            }
        ]

        self.prescription_templates = []

        for template_data in prescription_templates_data:
            if self.dry_run:
                self.stdout.write(f'Would create prescription template: {template_data["name"]}')
                continue

            creator = random.choice(self.users)
            items_data = template_data.pop('items')

            prescription_template = PrescriptionTemplate.objects.create(
                name=template_data['name'],
                creator=creator,
                is_public=template_data['is_public']
            )

            # Create template items
            for item_data in items_data:
                PrescriptionTemplateItem.objects.create(
                    template=prescription_template,
                    **item_data
                )

            self.prescription_templates.append(prescription_template)
            visibility = 'público' if prescription_template.is_public else 'privado'
            self.stdout.write(f'  Created prescription template: {prescription_template.name} ({visibility}) with {len(items_data)} items')

        if not self.dry_run:
            self.stdout.write(f'Created {len(self.prescription_templates)} prescription templates')

    def create_outpatient_prescriptions(self):
        self.stdout.write('Creating outpatient prescriptions...')

        if self.dry_run:
            self.stdout.write('Would create 2-3 outpatient prescriptions per patient')
            return

        self.outpatient_prescriptions = []

        # Create prescriptions for outpatients and some inpatients
        eligible_patients = [p for p in self.patients if p.status in [Patient.Status.OUTPATIENT, Patient.Status.INPATIENT]]

        for patient in eligible_patients:
            # Create 2-3 prescriptions per patient with different dates
            num_prescriptions = random.randint(2, 3)

            for i in range(num_prescriptions):
                # Create prescriptions from 60 days ago to today
                days_ago = random.randint(0, 60)
                prescription_date = timezone.now().date() - timedelta(days=days_ago)
                event_datetime = timezone.now() - timedelta(days=days_ago,
                                                          hours=random.randint(8, 18),
                                                          minutes=random.randint(0, 59))

                # Select a prescribing doctor (only doctors can prescribe)
                doctors = [u for u in self.users if u.profession_type == 0]  # MEDICAL_DOCTOR
                if not doctors:
                    continue

                prescriber = random.choice(doctors)

                # Create prescription
                prescription = OutpatientPrescription.objects.create(
                    event_datetime=event_datetime,
                    description=f'Receita médica - {patient.name}',
                    patient=patient,
                    created_by=prescriber,
                    updated_by=prescriber,
                    instructions=self.get_random_prescription_instructions(),
                    status=random.choice(['draft', 'finalized']),
                    prescription_date=prescription_date
                )

                # Add prescription items - either from templates or individual drugs
                if random.random() < 0.4 and hasattr(self, 'prescription_templates') and self.prescription_templates:
                    # 40% chance to use a prescription template
                    template = random.choice(self.prescription_templates)
                    prescription.copy_from_prescription_template(template)
                else:
                    # Create individual prescription items from drug templates
                    num_items = random.randint(1, 4)
                    available_drugs = list(self.drug_templates) if hasattr(self, 'drug_templates') else []

                    if available_drugs:
                        selected_drugs = random.sample(available_drugs, min(num_items, len(available_drugs)))

                        for order, drug_template in enumerate(selected_drugs, 1):
                            # Create prescription item
                            prescription_item = PrescriptionItem.objects.create(
                                prescription=prescription,
                                drug_name=drug_template.name,
                                presentation=drug_template.presentation,
                                usage_instructions=drug_template.usage_instructions,
                                quantity=self.get_random_quantity(),
                                order=order,
                                source_template=drug_template
                            )

                self.outpatient_prescriptions.append(prescription)

        self.stdout.write(f'Created {len(self.outpatient_prescriptions)} outpatient prescriptions')

    def get_random_prescription_instructions(self):
        """Generate random prescription instructions."""
        instructions = [
            "Retornar em 30 dias para reavaliação. Manter dieta hipossódica e atividade física regular.",
            "Controle da pressão arterial em casa. Retorno em 15 dias com exames laboratoriais.",
            "Tomar medicações conforme prescrição. Evitar automedicação. Retorno em 1 mês.",
            "Manter jejum de 12 horas antes dos exames de controle. Agendar retorno em 3 meses.",
            "Seguir orientações nutricionais. Controle glicêmico domiciliar. Retorno em 2 meses.",
            "Medicação de uso contínuo. Não interromper sem orientação médica. Retorno em 6 meses.",
            "Evitar exposição solar excessiva durante o tratamento. Retorno se houver efeitos adversos.",
            "Tomar medicação sempre no mesmo horário. Retorno em 45 dias para ajuste de dose."
        ]
        return random.choice(instructions)

    def get_random_quantity(self):
        """Generate random medication quantities."""
        quantities = [
            "30 comprimidos", "60 comprimidos", "90 comprimidos",
            "20 cápsulas", "30 cápsulas", "60 cápsulas",
            "1 frasco", "2 frascos", "100ml",
            "15 comprimidos", "21 comprimidos", "28 comprimidos"
        ]
        return random.choice(quantities)

    def display_completion_message(self):
        if self.dry_run:
            self.stdout.write(self.style.SUCCESS('\nDRY RUN COMPLETED - No data was actually created'))
            return
            
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SAMPLE DATA CREATION COMPLETED'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        self.stdout.write(self.style.WARNING(f'Created {len(self.users)} users with login credentials:'))
        self.stdout.write(self.style.ERROR('All users have password: samplepass123'))
        self.stdout.write('')
        
        # Group users by profession
        doctors = [u for u in self.users if u.profession_type == 0]
        nurses = [u for u in self.users if u.profession_type == 2]
        residents = [u for u in self.users if u.profession_type == 1]
        students = [u for u in self.users if u.profession_type == 4]
        
        if doctors:
            self.stdout.write('Doctors:')
            for user in doctors:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
        
        if nurses:
            self.stdout.write('Nurses:')
            for user in nurses:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
        
        if residents:
            self.stdout.write('Residents:')
            for user in residents:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
        
        if students:
            self.stdout.write('Students:')
            for user in students:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
        
        self.stdout.write('')
        self.stdout.write(f'Created {len(self.patients)} patients (single-hospital configuration)')
        self.stdout.write(f'Created {PatientRecordNumber.objects.filter(created_by__username__startswith="sample_").count()} patient record numbers')
        self.stdout.write(f'Created {PatientAdmission.objects.filter(created_by__username__startswith="sample_").count()} patient admissions')
        self.stdout.write(f'Hospital info configured via environment variables')
        self.stdout.write(f'Created {DailyNote.objects.count()} daily notes')
        self.stdout.write(f'Created {len(self.allowed_tags)} sample tags')
        if hasattr(self, 'wards'):
            self.stdout.write(f'Created {len(self.wards)} hospital wards')

        # Add statistics for new data types
        if hasattr(self, 'drug_templates'):
            self.stdout.write(f'Created {len(self.drug_templates)} drug templates')
        if hasattr(self, 'prescription_templates'):
            self.stdout.write(f'Created {len(self.prescription_templates)} prescription templates')
        if hasattr(self, 'outpatient_prescriptions'):
            self.stdout.write(f'Created {len(self.outpatient_prescriptions)} outpatient prescriptions')

        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.ERROR('Remember: All users password is "samplepass123"'))
        self.stdout.write(self.style.SUCCESS('='*60))