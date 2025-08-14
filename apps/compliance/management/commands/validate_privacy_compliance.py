from django.core.management.base import BaseCommand
from apps.compliance.models import PrivacyPolicy, DataProcessingNotice, LGPDComplianceSettings

class Command(BaseCommand):
    help = 'Validates privacy transparency compliance'
    
    def handle(self, *args, **options):
        self.stdout.write("Validating privacy transparency compliance...")
        
        # Check LGPD settings
        lgpd_settings = LGPDComplianceSettings.objects.first()
        if not lgpd_settings:
            self.stdout.write(self.style.ERROR("❌ LGPD settings not configured"))
            return
        
        # Check active privacy policy
        active_policy = PrivacyPolicy.objects.filter(is_active=True, policy_type='main').first()
        if not active_policy:
            self.stdout.write(self.style.ERROR("❌ No active privacy policy"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Active privacy policy: v{active_policy.version}"))
        
        # Check legal review
        if active_policy and not active_policy.legal_review_completed:
            self.stdout.write(self.style.WARNING("⚠️  Privacy policy needs legal review"))
        
        # Check processing notices
        required_contexts = ['patient_registration', 'photo_video_capture', 'emergency_treatment']
        missing_notices = []
        
        for context in required_contexts:
            if not DataProcessingNotice.objects.filter(context=context, is_active=True).exists():
                missing_notices.append(context)
        
        if missing_notices:
            self.stdout.write(self.style.ERROR(f"❌ Missing processing notices: {', '.join(missing_notices)}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All required processing notices present"))
        
        # Check DPO information
        if not lgpd_settings.dpo_email or '[' in lgpd_settings.dpo_email:
            self.stdout.write(self.style.ERROR("❌ DPO contact information incomplete"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ DPO contact information configured"))
        
        # Statistics
        total_policies = PrivacyPolicy.objects.count()
        total_notices = DataProcessingNotice.objects.filter(is_active=True).count()
        
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"- Privacy policies: {total_policies}")
        self.stdout.write(f"- Active processing notices: {total_notices}")
        self.stdout.write(f"- DPO configured: {'Yes' if lgpd_settings.dpo_email else 'No'}")