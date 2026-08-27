from django.core.management.base import BaseCommand
from django.db import transaction

from apps.patients.models import Patient


class Command(BaseCommand):
    help = 'Refresh denormalized fields for all patients (development utility)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient-id',
            type=str,
            help='Refresh specific patient by UUID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Execute the refresh inside a rolled-back transaction; '
                 'no changes are saved',
        )

    def handle(self, *args, **options):
        if options['patient_id']:
            try:
                patients = [Patient.objects.get(pk=options['patient_id'])]
            except Patient.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Patient {options["patient_id"]} not found')
                )
                return
            selected_count = 1
        else:
            patients = Patient.objects.all()
            selected_count = patients.count()

        if options['verbosity'] >= 2:
            self.stdout.write(
                f'Selected {selected_count} patients '
                f'for denormalized-field refresh'
            )

        if options['dry_run']:
            with transaction.atomic():
                for patient in patients:
                    patient.refresh_denormalized_fields()
                transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: would refresh {selected_count} patients; '
                    f'no changes were saved'
                )
            )
            return

        updated_count = 0

        for patient in patients:
            patient.refresh_denormalized_fields()
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Refreshed denormalized fields for {updated_count} patients')
        )
