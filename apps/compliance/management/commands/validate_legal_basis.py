from django.core.management.base import BaseCommand
from apps.compliance.models import DataProcessingPurpose
from apps.patients.models import Patient
from apps.accounts.models import EqmdCustomUser

class Command(BaseCommand):
    help = 'Validates LGPD legal basis coverage'
    
    def handle(self, *args, **options):
        self.stdout.write("Validating LGPD legal basis coverage...")
        
        # Check if basic purposes are defined
        required_categories = [
            'patient_identification',
            'patient_medical_history', 
            'staff_identification',
            'system_audit'
        ]
        
        missing_categories = []
        for category in required_categories:
            if not DataProcessingPurpose.objects.filter(data_category=category, is_active=True).exists():
                missing_categories.append(category)
        
        if missing_categories:
            self.stdout.write(
                self.style.ERROR(f"Missing legal basis for: {', '.join(missing_categories)}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All required data categories have legal basis documented")
            )
        
        # Show statistics
        total_purposes = DataProcessingPurpose.objects.filter(is_active=True).count()
        patient_count = Patient.objects.count()
        staff_count = EqmdCustomUser.objects.count()
        
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"- Legal basis records: {total_purposes}")
        self.stdout.write(f"- Patients in system: {patient_count}")
        self.stdout.write(f"- Staff members: {staff_count}")
        
        # Compliance status
        compliance_percentage = (len(required_categories) - len(missing_categories)) / len(required_categories) * 100
        self.stdout.write(f"- Legal basis compliance: {compliance_percentage:.0f}%")