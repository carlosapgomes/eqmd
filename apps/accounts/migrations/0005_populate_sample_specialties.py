# Generated manually for sample data

from django.db import migrations
import uuid


def create_sample_specialties(apps, schema_editor):
    """Create sample medical specialties."""
    MedicalSpecialty = apps.get_model("accounts", "MedicalSpecialty")

    specialties = [
        ("Cirurgia Geral", "CG", "General surgery"),
        ("Cirurgia Vascular", "CVASC", "Vascular surgery"),
        ("Cirurgia Cardíaca", "CIRCARD", "Cardiac surgery"),
        ("Cirurgia Torácica", "TORACICA", "Thoracic surgery"),
        ("Cardiologia", "CARDIO", "Medical cardiology"),
        ("Pediatria", "PED", "Pediatrics"),
        ("Ortopedia", "ORTO", "Orthopedics"),
        ("Ginecologia e Obstetrícia", "GO", "Gynecology and obstetrics"),
        ("Clínica Médica", "CM", "Internal medicine"),
        ("Emergência", "EM", "Emergency medicine"),
        ("UTI Adulto", "UTI", "Intensive care - Adult"),
        ("UTI Pediátrica", "UTIPED", "Intensive care - Pediatric"),
        ("Otorrinolaringologia", "ORL", "ENT (Otolaryngology)"),
        ("Oftalmologia", "OFTALMO", "Ophthalmology"),
        ("Dermatologia", "DERMA", "Dermatology"),
        ("Neurologia", "NEURO", "Neurology"),
        ("Psiquiatria", "PQU", "Psychiatry"),
        ("Infectologia", "INFECTO", "Infectious diseases"),
        ("Endocrinologia", "ENDOCRINO", "Endocrinology"),
        ("Nefrologia", "NEFRO", "Nephrology"),
        ("Gastroenterologia", "GASTRO", "Gastroenterology"),
        ("Pneumologia", "PNEUMO", "Pulmonology"),
        ("Reumatologia", "REUMATO", "Rheumatology"),
        ("Urologia", "URO", "Urology"),
        ("Anestesiologia", "ANESTESIO", "Anesthesiology"),
        ("Radiologia", "RADIO", "Radiology"),
        ("Oncologia Clínica", "ONCO", "Clinical oncology"),
        ("Cirurgia Plástica", "PLASTICA", "Plastic surgery"),
        ("Cirurgia Pediátrica", "CIPE", "Pediatric surgery"),
        ("Neurocirurgia", "NEUROCIR", "Neurosurgery"),
    ]

    for name, abbr, desc in specialties:
        MedicalSpecialty.objects.create(
            name=name, abbreviation=abbr, description=desc, is_active=True
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_add_medical_specialty_models"),
    ]

    operations = [
        migrations.RunPython(create_sample_specialties),
    ]
