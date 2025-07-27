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
    
    def handle(self, *args, **options):
        if options['patient_id']:
            try:
                patients = [Patient.objects.get(pk=options['patient_id'])]
            except Patient.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Patient {options["patient_id"]} not found')
                )
                return
        else:
            patients = Patient.objects.all()
        
        updated_count = 0
        
        for patient in patients:
            patient.refresh_denormalized_fields()
            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Refreshed denormalized fields for {updated_count} patients')
        )