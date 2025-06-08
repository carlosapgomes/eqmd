from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.patients.models import AllowedTag

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample allowed tags for testing'

    def handle(self, *args, **options):
        # Get or create a superuser for creating tags
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created admin user: admin/admin123')
            )

        # Sample tags with different colors
        sample_tags = [
            {
                'name': 'High Priority',
                'description': 'Patient requires immediate attention',
                'color': '#dc3545',  # Red
            },
            {
                'name': 'Follow Up',
                'description': 'Patient needs follow-up appointment',
                'color': '#ffc107',  # Yellow
            },
            {
                'name': 'VIP',
                'description': 'VIP patient - special treatment',
                'color': '#6f42c1',  # Purple
            },
            {
                'name': 'Diabetic',
                'description': 'Patient has diabetes',
                'color': '#fd7e14',  # Orange
            },
            {
                'name': 'Cardiac',
                'description': 'Patient has cardiac condition',
                'color': '#e74c3c',  # Dark red
            },
            {
                'name': 'Elderly',
                'description': 'Elderly patient requiring special care',
                'color': '#6c757d',  # Gray
            },
            {
                'name': 'Pediatric',
                'description': 'Pediatric patient',
                'color': '#20c997',  # Teal
            },
        ]

        created_count = 0
        for tag_data in sample_tags:
            tag, created = AllowedTag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'description': tag_data['description'],
                    'color': tag_data['color'],
                    'created_by': user,
                    'updated_by': user,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tag: {tag.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tag already exists: {tag.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new tags')
        )