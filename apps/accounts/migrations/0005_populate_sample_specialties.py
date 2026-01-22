# Generated manually for sample data

from django.db import migrations
import uuid


def create_sample_specialties(apps, schema_editor):
    """Create sample medical specialties."""
    MedicalSpecialty = apps.get_model('accounts', 'MedicalSpecialty')

    specialties = [
        ('Cirurgia Geral', 'CIRGER', 'General surgery'),
        ('Cirurgia Vascular', 'CIRVASC', 'Vascular surgery'),
        ('Cirurgia Cardíaca', 'CIRCARD', 'Cardiac surgery'),
        ('Cirurgia Torácica', 'CIRTORAC', 'Thoracic surgery'),
        ('Cardiologia', 'CARDIO', 'Medical cardiology'),
        ('Pediatria', 'PED', 'Pediatrics'),
        ('Ortopedia', 'ORTO', 'Orthopedics'),
        ('Ginecologia e Obstetrícia', 'GO', 'Gynecology and obstetrics'),
        ('Clínica Médica', 'CLIN', 'Internal medicine'),
        ('Emergência', 'EMERG', 'Emergency medicine'),
        ('UTI Adulto', 'UTI', 'Intensive care - Adult'),
        ('UTI Pediátrica', 'UTIPED', 'Intensive care - Pediatric'),
        ('Otorrinolaringologia', 'ORL', 'ENT (Otolaryngology)'),
        ('Oftalmologia', 'OFTALMO', 'Ophthalmology'),
        ('Dermatologia', 'DERM', 'Dermatology'),
        ('Neurologia', 'NEURO', 'Neurology'),
        ('Psiquiatria', 'PSIQ', 'Psychiatry'),
        ('Infectologia', 'INFECTO', 'Infectious diseases'),
        ('Endocrinologia', 'ENDO', 'Endocrinology'),
        ('Nefrologia', 'NEFRO', 'Nephrology'),
        ('Gastroenterologia', 'GASTRO', 'Gastroenterology'),
        ('Pneumologia', 'PNEUMO', 'Pulmonology'),
        ('Reumatologia', 'REUMA', 'Rheumatology'),
        ('Urologia', 'URO', 'Urology'),
        ('Anestesiologia', 'ANEST', 'Anesthesiology'),
        ('Radiologia', 'RADIO', 'Radiology'),
        ('Oncologia Clínica', 'ONCO', 'Clinical oncology'),
        ('Cirurgia Plástica', 'CIRPLAST', 'Plastic surgery'),
        ('Cirurgia Pediátrica', 'CIRPED', 'Pediatric surgery'),
        ('Neurocirurgia', 'NEUROCIR', 'Neurosurgery'),
    ]

    for name, abbr, desc in specialties:
        MedicalSpecialty.objects.create(
            name=name,
            abbreviation=abbr,
            description=desc,
            is_active=True
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_medical_specialty_models'),
    ]

    operations = [
        migrations.RunPython(create_sample_specialties),
    ]
