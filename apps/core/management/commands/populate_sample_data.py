from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from faker import Faker

from apps.hospitals.models import Hospital, Ward
from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag, Tag
from apps.dailynotes.models import DailyNote

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

        self.create_hospitals()
        self.create_users()
        self.create_tags()
        self.create_patients()
        self.create_daily_notes()
        
        self.display_completion_message()

    def clear_existing_data(self):
        if self.dry_run:
            self.stdout.write('Would clear existing sample data')
            return
            
        self.stdout.write('Clearing existing sample data...')
        DailyNote.objects.filter(created_by__username__startswith='sample_').delete()
        Patient.objects.filter(created_by__username__startswith='sample_').delete()
        User.objects.filter(username__startswith='sample_').delete()
        Hospital.objects.filter(name__startswith='Hospital ').delete()
        AllowedTag.objects.filter(name__startswith='Tag ').delete()

    def create_hospitals(self):
        self.stdout.write('Creating hospitals and wards...')
        
        hospitals_data = [
            {
                'name': 'Hospital São João',
                'short_name': 'HSJ',
                'address': 'Rua das Flores, 123',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01234-567',
                'phone': '(11) 1234-5678',
                'wards': [
                    {'name': 'UTI', 'description': 'Unidade de Terapia Intensiva', 'capacity': 12},
                    {'name': 'Clínica Médica', 'description': 'Enfermaria de Clínica Médica', 'capacity': 30},
                    {'name': 'Cardiologia', 'description': 'Enfermaria de Cardiologia', 'capacity': 20},
                ]
            },
            {
                'name': 'Hospital Santa Maria',
                'short_name': 'HSM',
                'address': 'Avenida Central, 456',
                'city': 'Rio de Janeiro',
                'state': 'RJ',
                'zip_code': '20000-000',
                'phone': '(21) 9876-5432',
                'wards': [
                    {'name': 'Emergência', 'description': 'Pronto Socorro', 'capacity': 25},
                    {'name': 'Cirurgia', 'description': 'Enfermaria Cirúrgica', 'capacity': 18},
                    {'name': 'Pediatria', 'description': 'Enfermaria Pediátrica', 'capacity': 15},
                ]
            }
        ]

        self.hospitals = []
        for hospital_data in hospitals_data:
            if self.dry_run:
                self.stdout.write(f'Would create hospital: {hospital_data["name"]}')
                continue
                
            wards_data = hospital_data.pop('wards')
            hospital = Hospital.objects.create(**hospital_data)
            self.hospitals.append(hospital)
            
            for ward_data in wards_data:
                Ward.objects.create(hospital=hospital, **ward_data)
                
            self.stdout.write(f'  Created hospital: {hospital.name} with {len(wards_data)} wards')

    def create_users(self):
        self.stdout.write('Creating users...')
        
        # Get existing hospitals (including the one user already created)
        all_hospitals = list(Hospital.objects.all())
        
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
            
            # Assign user to random hospitals
            user_hospitals = random.sample(all_hospitals, random.randint(1, 2))
            user.hospitals.set(user_hospitals)
            user.last_hospital = user_hospitals[0]
            user.save()
            
            self.users.append(user)
            profession_name = user.get_profession_type_display()
            self.stdout.write(f'  Created {profession_name}: {user.email}')

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
        
        all_hospitals = list(Hospital.objects.all())
        self.patients = []
        
        # Create 10 patients per hospital (30 total)
        for hospital in all_hospitals:
            for i in range(10):
                patient = self.create_patient(hospital, i < 5)  # First 5 are inpatients
                if patient:
                    self.patients.append(patient)
        
        # Create 10 outpatients (no hospital)
        for i in range(10):
            patient = self.create_patient(None, False)
            if patient:
                self.patients.append(patient)
        
        self.stdout.write(f'Created {len(self.patients)} patients total')

    def create_patient(self, hospital, is_inpatient):
        if self.dry_run:
            status = 'inpatient' if is_inpatient else 'outpatient'
            hospital_name = hospital.name if hospital else 'No hospital'
            self.stdout.write(f'Would create {status} patient at {hospital_name}')
            return None
            
        creator = random.choice(self.users)
        
        # Generate realistic patient data
        gender = random.choice(['M', 'F'])
        if gender == 'M':
            first_name = fake.first_name_male()
        else:
            first_name = fake.first_name_female()
        
        last_name = fake.last_name()
        name = f'{first_name} {last_name}'
        
        # Determine status
        if hospital:
            if is_inpatient:
                status = random.choice([Patient.Status.INPATIENT, Patient.Status.EMERGENCY])
            else:
                status = Patient.Status.OUTPATIENT
        else:
            status = Patient.Status.OUTPATIENT
        
        patient = Patient.objects.create(
            name=name,
            birthday=fake.date_of_birth(minimum_age=18, maximum_age=90),
            healthcard_number=f'SUS{random.randint(100000000, 999999999)}',
            id_number=fake.rg(),
            fiscal_number=fake.cpf(),
            phone=fake.phone_number(),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            zip_code=fake.postcode(),
            status=status,
            current_hospital=hospital,
            bed=f'Leito {random.randint(1, 50)}' if is_inpatient else '',
            last_admission_date=fake.date_between(start_date='-30d', end_date='today') if hospital else None,
            created_by=creator,
            updated_by=creator,
        )
        
        # Create hospital record if patient belongs to a hospital
        if hospital:
            PatientHospitalRecord.objects.create(
                patient=patient,
                hospital=hospital,
                record_number=f'REG{random.randint(100000, 999999)}',
                first_admission_date=patient.last_admission_date,
                last_admission_date=patient.last_admission_date,
                created_by=creator,
                updated_by=creator,
            )
        
        # Assign random tags
        if self.allowed_tags:
            num_tags = random.randint(0, 3)
            selected_allowed_tags = random.sample(self.allowed_tags, min(num_tags, len(self.allowed_tags)))
            
            for allowed_tag in selected_allowed_tags:
                tag = Tag.objects.create(
                    allowed_tag=allowed_tag,
                    notes=f'Tag aplicada ao paciente {patient.name}',
                    created_by=creator,
                    updated_by=creator,
                )
                patient.tags.add(tag)
        
        return patient

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
        self.stdout.write(f'Created {len(Hospital.objects.all())} hospitals')
        self.stdout.write(f'Created {len(self.patients)} patients')
        self.stdout.write(f'Created {DailyNote.objects.count()} daily notes')
        self.stdout.write(f'Created {len(self.allowed_tags)} sample tags')
        
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.ERROR('Remember: All users password is "samplepass123"'))
        self.stdout.write(self.style.SUCCESS('='*60))