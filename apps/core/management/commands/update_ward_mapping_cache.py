from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone
from apps.core.models import WardMappingCache
from apps.patients.models import Ward, Patient, AllowedTag
from datetime import timedelta
import json


class Command(BaseCommand):
    help = 'Update ward mapping cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recent cache exists',
        )

    def calculate_admission_duration(self, patient):
        """Calculate admission duration for display"""
        if not patient.last_admission_date:
            return None
        
        days = (timezone.now().date() - patient.last_admission_date).days
        if days == 0:
            return "Hoje"
        elif days == 1:
            return "1 dia"
        else:
            return f"{days} dias"

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"[{start_time}] Starting ward mapping cache update...")

        try:
            # Get all wards with their patients
            self.stdout.write("Fetching ward data...")
            wards = Ward.objects.prefetch_related(
                'patients',
                'patients__patient_tags__allowed_tag'
            ).annotate(
                patient_count=Count('patients', filter=Q(patients__status=Patient.Status.INPATIENT))
            ).order_by('name')

            ward_data_list = []
            total_patients = 0
            total_wards = wards.count()

            for ward in wards:
                # Get only inpatients
                inpatients = ward.patients.filter(status=Patient.Status.INPATIENT)
                patient_count = inpatients.count()
                total_patients += patient_count

                # Calculate utilization (assuming a basic estimate)
                capacity_estimate = None
                utilization_percentage = None
                
                patients_data = []
                for patient in inpatients:
                    # Get patient tags
                    tags_data = []
                    for patient_tag in patient.patient_tags.all():
                        tags_data.append({
                            'allowed_tag': {
                                'id': patient_tag.allowed_tag.id,
                                'name': patient_tag.allowed_tag.name,
                                'color': patient_tag.allowed_tag.color
                            }
                        })

                    patients_data.append({
                        'patient': {
                            'pk': str(patient.pk),
                            'name': patient.name
                        },
                        'bed': patient.bed or 'Sem leito',
                        'admission_duration': self.calculate_admission_duration(patient),
                        'tags': tags_data
                    })

                ward_info = {
                    'ward': {
                        'id': str(ward.id),
                        'name': ward.name,
                        'abbreviation': ward.abbreviation,
                        'floor': getattr(ward, 'floor', None)
                    },
                    'patient_count': patient_count,
                    'capacity_estimate': capacity_estimate,
                    'utilization_percentage': utilization_percentage,
                    'patients': patients_data
                }
                ward_data_list.append(ward_info)

            # Create main ward mapping data
            ward_mapping_data = {
                'ward_data': ward_data_list,
                'total_patients': total_patients,
                'total_wards': total_wards,
                'updated_at': start_time.isoformat()
            }

            # Update ward mapping cache
            WardMappingCache.objects.update_or_create(
                cache_key='ward_mapping_full',
                defaults={'ward_data': ward_mapping_data}
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Ward mapping updated: {total_wards} wards, {total_patients} inpatients"
                )
            )

            # Create filter data cache
            self.stdout.write("Preparing filter data...")
            
            # All wards for dropdown
            all_wards_data = []
            for ward in Ward.objects.all().order_by('name'):
                all_wards_data.append({
                    'id': str(ward.id),
                    'name': ward.name,
                    'abbreviation': ward.abbreviation
                })

            # Available tags for dropdown
            available_tags_data = []
            for tag in AllowedTag.objects.all().order_by('name'):
                available_tags_data.append({
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color
                })

            filter_data = {
                'all_wards': all_wards_data,
                'available_tags': available_tags_data,
                'updated_at': start_time.isoformat()
            }

            # Update filter cache
            WardMappingCache.objects.update_or_create(
                cache_key='ward_filters',
                defaults={'ward_data': filter_data}
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Filter data updated: {len(all_wards_data)} wards, {len(available_tags_data)} tags"
                )
            )

            # Summary
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ward mapping cache updated successfully in {duration:.2f}s"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating ward mapping cache: {str(e)}")
            )
            # Don't raise the exception to prevent cron job failures
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return

        self.stdout.write(f"[{timezone.now()}] Ward mapping cache update completed.")