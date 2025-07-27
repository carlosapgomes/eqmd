from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.patients.models import Ward

User = get_user_model()

class Command(BaseCommand):
    help = "Create sample wards for development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-existing",
            action="store_true",
            help="Delete existing wards before creating new ones",
        )

    def handle(self, *args, **options):
        if options["delete_existing"]:
            Ward.objects.all().delete()
            self.stdout.write("Deleted existing wards")

        # Get superuser for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No users found. Create a user first.")
            )
            return

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

        created_count = 0
        for ward_data in wards_data:
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
                self.stdout.write(f"Created ward: {ward}")
            else:
                self.stdout.write(f"Ward already exists: {ward}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} wards")
        )