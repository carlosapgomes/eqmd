from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test.utils import override_settings
from django.db import transaction
from django.test import Client
from datetime import timedelta
import time

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PerformanceTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_bulk_patient_creation_performance(self):
        """Test performance of creating many patients with record tracking"""
        start_time = time.time()
        
        patients = []
        with transaction.atomic():
            for i in range(100):
                patient = Patient.objects.create(
                    name=f'Patient {i:03d}',
                    birthday=timezone.now().date() - timedelta(days=365*30),
                    created_by=self.user,
                    updated_by=self.user
                )
                
                # Add record number
                PatientRecordNumber.objects.create(
                    patient=patient,
                    record_number=f'REC{i:03d}',
                    created_by=self.user,
                    updated_by=self.user
                )
                
                patients.append(patient)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        self.assertLess(creation_time, 10.0, f"Creation took {creation_time:.2f}s")
        
        # Verify denormalized fields are correct
        for patient in patients:
            patient.refresh_from_db()
            self.assertIsNotNone(patient.current_record_number)
    
    def test_patient_list_query_performance(self):
        """Test performance of patient list queries with record tracking"""
        # Create test data
        patients = []
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Patient {i:03d}',
                birthday=timezone.now().date() - timedelta(days=365*30),
                created_by=self.user,
                updated_by=self.user
            )
            
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=f'REC{i:03d}',
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add some admissions
            if i % 3 == 0:
                PatientAdmission.objects.create(
                    patient=patient,
                    admission_datetime=timezone.now() - timedelta(days=i),
                    admission_type=PatientAdmission.AdmissionType.EMERGENCY,
                    created_by=self.user,
                    updated_by=self.user
                )
            
            patients.append(patient)
        
        # Test patient list query performance
        start_time = time.time()
        
        # Simulate patient list view query
        with self.assertNumQueries(1):  # Should be one efficient query
            patient_list = list(Patient.objects.all()[:20])
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should be fast due to denormalized fields
        self.assertLess(query_time, 1.0, f"Query took {query_time:.2f}s")
        self.assertEqual(len(patient_list), 20)
    
    def test_patient_search_performance(self):
        """Test performance of patient search with record numbers"""
        # Create test data
        for i in range(100):
            patient = Patient.objects.create(
                name=f'Patient {i:03d}',
                birthday=timezone.now().date() - timedelta(days=365*30),
                created_by=self.user,
                updated_by=self.user
            )
            
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=f'REC{i:03d}',
                created_by=self.user,
                updated_by=self.user
            )
        
        # Test search performance
        start_time = time.time()
        
        # Search by record number
        search_results = Patient.objects.filter(
            current_record_number__icontains='REC005'
        )
        result_list = list(search_results)
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Should be fast due to denormalized field
        self.assertLess(search_time, 1.0, f"Search took {search_time:.2f}s")
        self.assertEqual(len(result_list), 1)
    
    def test_admission_cycle_performance(self):
        """Test performance of admission/discharge cycles"""
        patient = Patient.objects.create(
            name='Performance Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        
        start_time = time.time()
        
        # Perform multiple admission/discharge cycles
        for i in range(10):
            admission_time = timezone.now() - timedelta(days=i*10)
            discharge_time = admission_time + timedelta(days=5)
            
            # Admit
            admission = patient.admit_patient(
                admission_datetime=admission_time,
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                user=self.user
            )
            
            # Discharge
            patient.discharge_patient(
                discharge_datetime=discharge_time,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                user=self.user
            )
        
        end_time = time.time()
        cycle_time = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(cycle_time, 5.0, f"Admission cycles took {cycle_time:.2f}s")
        
        # Verify final state
        patient.refresh_from_db()
        self.assertEqual(patient.total_admissions_count, 10)
        self.assertEqual(patient.total_inpatient_days, 50)  # 10 admissions * 5 days each
        self.assertFalse(patient.is_currently_admitted())

class DatabaseQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        
        # Create test patient with history
        self.patient = Patient.objects.create(
            name='Query Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add record number history
        for i in range(3):
            is_current = (i == 2)  # Last one is current
            PatientRecordNumber.objects.create(
                patient=self.patient,
                record_number=f'REC{i:03d}',
                is_current=is_current,
                created_by=self.user,
                updated_by=self.user
            )
        
        # Add admission history
        for i in range(2):
            admission_time = timezone.now() - timedelta(days=(i+1)*10)
            discharge_time = admission_time + timedelta(days=5)
            
            PatientAdmission.objects.create(
                patient=self.patient,
                admission_datetime=admission_time,
                discharge_datetime=discharge_time,
                admission_type=PatientAdmission.AdmissionType.EMERGENCY,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                created_by=self.user,
                updated_by=self.user
            )
    
    def test_patient_detail_query_efficiency(self):
        """Test that patient detail queries are efficient"""
        # Should be able to get all patient info with minimal queries
        with self.assertNumQueries(4):  # Patient + record numbers + admissions + events
            patient = Patient.objects.get(pk=self.patient.pk)
            record_numbers = list(patient.record_numbers.all())
            admissions = list(patient.admissions.all())
            current_record = patient.record_numbers.filter(is_current=True).first()
        
        self.assertEqual(len(record_numbers), 3)
        self.assertEqual(len(admissions), 2)
        self.assertIsNotNone(current_record)
    
    def test_bulk_patient_queries(self):
        """Test bulk operations are efficient"""
        # Create more test patients
        patients = []
        for i in range(10):
            patient = Patient.objects.create(
                name=f'Bulk Patient {i}',
                birthday=timezone.now().date() - timedelta(days=365*25),
                created_by=self.user,
                updated_by=self.user
            )
            patients.append(patient)
        
        # Bulk update denormalized fields should be efficient
        start_time = time.time()
        
        for patient in patients:
            patient.refresh_denormalized_fields()
        
        end_time = time.time()
        update_time = end_time - start_time
        
        self.assertLess(update_time, 2.0, f"Bulk update took {update_time:.2f}s")
    
    def test_complex_query_performance(self):
        """Test performance of complex queries"""
        # Create test data
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Complex Patient {i:03d}',
                birthday=timezone.now().date() - timedelta(days=365*20 + i*30),
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add record numbers
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=f'REC{i:03d}',
                is_current=True,
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add admissions with different patterns
            if i % 2 == 0:
                admission = PatientAdmission.objects.create(
                    patient=patient,
                    admission_datetime=timezone.now() - timedelta(days=i),
                    admission_type=PatientAdmission.AdmissionType.EMERGENCY,
                    initial_bed=f'A{i:03d}',
                    created_by=self.user,
                    updated_by=self.user
                )
                
                if i % 4 == 0:
                    admission.discharge_datetime = timezone.now() - timedelta(days=i//2)
                    admission.discharge_type = PatientAdmission.DischargeType.MEDICAL
                    admission.save()
        
        # Test complex query performance
        start_time = time.time()
        
        # Query patients with active admissions
        active_patients = Patient.objects.filter(
            status=Patient.Status.INPATIENT
        ).select_related().prefetch_related('record_numbers', 'admissions')
        
        patient_list = list(active_patients)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        self.assertLess(query_time, 2.0, f"Complex query took {query_time:.2f}s")
    
    def test_patient_list_with_aggregates(self):
        """Test patient list with aggregate data"""
        # Create test data
        for i in range(20):
            patient = Patient.objects.create(
                name=f'Aggregate Patient {i}',
                birthday=timezone.now().date() - timedelta(days=365*30),
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add record number
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=f'REC{i:03d}',
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add multiple admissions
            for j in range(3):
                admission_time = timezone.now() - timedelta(days=i*10 + j*5)
                discharge_time = admission_time + timedelta(days=j+1)
                
                PatientAdmission.objects.create(
                    patient=patient,
                    admission_datetime=admission_time,
                    discharge_datetime=discharge_time,
                    admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                    discharge_type=PatientAdmission.DischargeType.MEDICAL,
                    created_by=self.user,
                    updated_by=self.user
                )
        
        # Test aggregate query performance
        start_time = time.time()
        
        # Get patients with admission counts
        from django.db.models import Count, Sum
        patients = Patient.objects.annotate(
            admission_count=Count('admissions'),
            total_days=Sum('admissions__stay_duration_days')
        ).order_by('-admission_count')[:10]
        
        result_list = list(patients)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        self.assertLess(query_time, 1.5, f"Aggregate query took {query_time:.2f}s")
        self.assertGreaterEqual(len(result_list), 1)
    
    def test_memory_usage_with_large_dataset(self):
        """Test memory usage with large dataset"""
        # Create large dataset
        patients = []
        for i in range(100):
            patient = Patient.objects.create(
                name=f'Large Dataset Patient {i}',
                birthday=timezone.now().date() - timedelta(days=365*30),
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add record number
            PatientRecordNumber.objects.create(
                patient=patient,
                record_number=f'REC{i:03d}',
                created_by=self.user,
                updated_by=self.user
            )
            
            # Add admissions
            for j in range(5):
                admission_time = timezone.now() - timedelta(days=i*10 + j)
                discharge_time = admission_time + timedelta(days=2)
                
                PatientAdmission.objects.create(
                    patient=patient,
                    admission_datetime=admission_time,
                    discharge_datetime=discharge_time,
                    admission_type=PatientAdmission.AdmissionType.EMERGENCY,
                    discharge_type=PatientAdmission.DischargeType.MEDICAL,
                    created_by=self.user,
                    updated_by=self.user
                )
            
            patients.append(patient)
        
        # Test memory efficient query
        start_time = time.time()
        
        # Use iterator for memory efficiency
        patient_count = 0
        for patient in Patient.objects.iterator():
            # Access related data efficiently
            patient.refresh_from_db()
            patient_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        self.assertLess(processing_time, 5.0, f"Large dataset processing took {processing_time:.2f}s")
        self.assertEqual(patient_count, 100)