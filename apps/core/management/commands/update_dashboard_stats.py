from django.core.management.base import BaseCommand
from django.db.models import Count, Max, Q
from django.utils import timezone
from apps.core.models import DashboardCache
from apps.patients.models import Patient
import json


class Command(BaseCommand):
    help = 'Update dashboard statistics cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recent cache exists',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"[{start_time}] Starting dashboard stats update...")

        try:
            # Get patient counts (single query)
            self.stdout.write("Fetching patient counts...")
            counts = Patient.objects.aggregate(
                total=Count('id'),
                inpatients=Count('id', filter=Q(status=Patient.Status.INPATIENT)),
                outpatients=Count('id', filter=Q(status=Patient.Status.OUTPATIENT))
            )
            
            counts_data = {
                'total_patients': counts['total'],
                'inpatients': counts['inpatients'],
                'outpatients': counts['outpatients'],
                'updated_at': start_time.isoformat()
            }

            # Update patient counts cache
            DashboardCache.objects.update_or_create(
                key='patient_counts',
                defaults={'data': counts_data}
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Patient counts updated: {counts['total']} total "
                    f"({counts['inpatients']} inpatients, {counts['outpatients']} outpatients)"
                )
            )

            # Get recent patients (single query with subquery)
            self.stdout.write("Fetching recent patients...")
            recent_patients = Patient.objects.annotate(
                latest_event_datetime=Max('event__event_datetime')
            ).filter(
                latest_event_datetime__isnull=False
            ).order_by('-latest_event_datetime')[:30]

            # Serialize recent patients data
            patients_data = []
            for patient in recent_patients:
                patients_data.append({
                    'id': str(patient.id),
                    'name': patient.name,
                    'status': patient.status,
                    'latest_event_datetime': patient.latest_event_datetime.isoformat() if patient.latest_event_datetime else None
                })

            recent_data = {
                'patients': patients_data,
                'total_count': len(patients_data),
                'updated_at': start_time.isoformat()
            }

            # Update recent patients cache
            DashboardCache.objects.update_or_create(
                key='recent_patients',
                defaults={'data': recent_data}
            )
            self.stdout.write(
                self.style.SUCCESS(f"✓ Recent patients updated: {len(patients_data)} patients")
            )

            # Summary
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dashboard stats cache updated successfully in {duration:.2f}s"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating dashboard stats: {str(e)}")
            )
            # Don't raise the exception to prevent cron job failures
            return

        self.stdout.write(f"[{timezone.now()}] Dashboard stats update completed.")