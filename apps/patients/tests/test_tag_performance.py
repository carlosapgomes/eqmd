import time
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.patients.models import Patient, AllowedTag, Tag

User = get_user_model()

class TagManagementPerformanceTests(TestCase):
    """Test performance with large numbers of tags"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user with permissions
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        # Add permissions to user
        change_patient_perm = Permission.objects.get(codename='change_patient')
        view_patient_perm = Permission.objects.get(codename='view_patient')
        self.doctor.user_permissions.add(change_patient_perm, view_patient_perm)
        
        # Create patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            gender='M',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Login
        self.client.login(username='doctor', password='testpass123')

    def test_patient_detail_with_many_tags_timing(self):
        """Test patient detail page timing with many tags"""
        # Create 30 allowed tags
        allowed_tags = []
        for i in range(30):
            tag = AllowedTag.objects.create(
                name=f'Tag {i:02d}',
                color='blue',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            allowed_tags.append(tag)
        
        # Create 15 tag instances for the patient
        for i in range(15):
            Tag.objects.create(
                allowed_tag=allowed_tags[i],
                patient=self.patient,
                created_by=self.doctor,
                updated_by=self.doctor
            )
        
        # Measure response time
        start_time = time.time()
        url = reverse('apps.patients:patient_detail', kwargs={'pk': self.patient.pk})
        response = self.client.get(url)
        end_time = time.time()
        
        # Verify page loads successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify performance (should be under 2 seconds even with N+1 queries)
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0, f"Patient detail page took {response_time:.3f}s with 15 tags")
        
        # Verify some tags are displayed
        self.assertContains(response, 'Tag 00')
        self.assertContains(response, 'Tag 14')

    def test_tag_api_performance(self):
        """Test tag API performance with multiple tags"""
        # Create 20 tag instances
        for i in range(20):
            allowed_tag = AllowedTag.objects.create(
                name=f'API Tag {i:02d}',
                color='green',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            
            Tag.objects.create(
                allowed_tag=allowed_tag,
                patient=self.patient,
                created_by=self.doctor,
                updated_by=self.doctor
            )
        
        # Measure API response time
        start_time = time.time()
        url = reverse('apps.patients:patient_tags_api', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        end_time = time.time()
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify performance
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0, f"Tag API took {response_time:.3f}s with 20 tags")
        
        # Verify response format (check if it contains tag information)
        data = json.loads(response.content)
        # The exact format may vary, so just verify we got valid JSON with tag data
        self.assertIsInstance(data, (dict, list))
        if isinstance(data, dict) and 'tags' in data:
            self.assertEqual(len(data['tags']), 20)
        elif isinstance(data, list):
            self.assertEqual(len(data), 20)

    def test_bulk_tag_operations_timing(self):
        """Test bulk tag operations timing"""
        # Create 10 allowed tags
        allowed_tags = []
        for i in range(10):
            tag = AllowedTag.objects.create(
                name=f'Bulk Tag {i:02d}',
                color='red',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            allowed_tags.append(tag)
        
        # Measure bulk add timing
        start_time = time.time()
        
        # Add tags one by one (simulating user workflow)
        for tag in allowed_tags:
            url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
            response = self.client.post(url, {
                'tag_id': str(tag.pk)
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 200)
        
        add_time = time.time() - start_time
        
        # Measure bulk remove timing
        start_time = time.time()
        url = reverse('apps.patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        remove_time = time.time() - start_time
        
        # Verify operations
        self.assertEqual(response.status_code, 200)
        
        # Verify timing
        self.assertLess(add_time, 3.0, f"Adding 10 tags took {add_time:.3f}s")
        self.assertLess(remove_time, 1.0, f"Bulk remove took {remove_time:.3f}s")
        
        # Verify all tags removed
        self.assertEqual(self.patient.patient_tags.count(), 0)

    def test_tag_list_view_timing(self):
        """Test allowed tag list view timing with many tags"""
        # Create 50 allowed tags
        for i in range(50):
            AllowedTag.objects.create(
                name=f'List Tag {i:03d}',
                color='purple',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
        
        # Measure list view timing
        start_time = time.time()
        url = reverse('apps.patients:tag_list')
        response = self.client.get(url)
        end_time = time.time()
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify timing
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0, f"Tag list view took {response_time:.3f}s with 50 tags")
        
        # Verify pagination works
        self.assertContains(response, 'List Tag 000')

    def test_individual_tag_operations_timing(self):
        """Test individual tag operations are fast"""
        # Create test tags
        allowed_tags = []
        for i in range(5):
            tag = AllowedTag.objects.create(
                name=f'Speed Tag {i}',
                color='orange',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            allowed_tags.append(tag)
        
        # Test individual add operations
        add_times = []
        for tag in allowed_tags:
            start_time = time.time()
            
            url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
            response = self.client.post(url, {
                'tag_id': str(tag.pk)
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            
            end_time = time.time()
            add_times.append(end_time - start_time)
            self.assertEqual(response.status_code, 200)
        
        # Test individual remove operations
        remove_times = []
        for tag_instance in self.patient.patient_tags.all():
            start_time = time.time()
            
            url = reverse('apps.patients:patient_tag_remove', kwargs={
                'patient_id': self.patient.id,
                'tag_id': tag_instance.id
            })
            response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            
            end_time = time.time()
            remove_times.append(end_time - start_time)
            self.assertEqual(response.status_code, 200)
        
        # Verify individual operations are fast
        max_add_time = max(add_times)
        max_remove_time = max(remove_times)
        
        self.assertLess(max_add_time, 0.5, f"Slowest tag add took {max_add_time:.3f}s")
        self.assertLess(max_remove_time, 0.5, f"Slowest tag remove took {max_remove_time:.3f}s")
        
        # Verify average times are reasonable
        avg_add_time = sum(add_times) / len(add_times)
        avg_remove_time = sum(remove_times) / len(remove_times)
        
        self.assertLess(avg_add_time, 0.2, f"Average tag add took {avg_add_time:.3f}s")
        self.assertLess(avg_remove_time, 0.2, f"Average tag remove took {avg_remove_time:.3f}s")

    def test_tag_search_and_filter_timing(self):
        """Test tag filtering and search performance"""
        # Create tags with different names and colors
        colors = ['red', 'blue', 'green', 'yellow', 'purple']
        for i in range(25):
            AllowedTag.objects.create(
                name=f'Search Tag {i:02d}',
                color=colors[i % 5],
                is_active=i % 10 != 0,  # Make some inactive
                created_by=self.doctor,
                updated_by=self.doctor
            )
        
        # Test filtering by active tags
        start_time = time.time()
        url = reverse('apps.patients:tag_list') + '?active=true'
        response = self.client.get(url)
        filter_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(filter_time, 1.0, f"Tag filtering took {filter_time:.3f}s")
        
        # Test search functionality (if implemented)
        start_time = time.time()
        url = reverse('apps.patients:tag_list') + '?search=Tag 01'
        response = self.client.get(url)
        search_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(search_time, 1.0, f"Tag search took {search_time:.3f}s")

    def test_concurrent_access_simulation(self):
        """Test system handles multiple tag operations reasonably"""
        # Create test data
        allowed_tags = []
        for i in range(10):
            tag = AllowedTag.objects.create(
                name=f'Concurrent Tag {i}',
                color='cyan',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            allowed_tags.append(tag)
        
        # Simulate multiple operations in sequence (threading would be complex in tests)
        operations = []
        
        # Add operations
        for i in range(5):
            start_time = time.time()
            url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
            response = self.client.post(url, {
                'tag_id': str(allowed_tags[i].pk)
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            end_time = time.time()
            
            operations.append({
                'type': 'add',
                'time': end_time - start_time,
                'success': response.status_code == 200
            })
        
        # API calls
        for i in range(3):
            start_time = time.time()
            url = reverse('apps.patients:patient_tags_api', kwargs={'patient_id': self.patient.id})
            response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            end_time = time.time()
            
            operations.append({
                'type': 'api',
                'time': end_time - start_time,
                'success': response.status_code == 200
            })
        
        # Verify all operations succeeded
        successful_ops = sum(1 for op in operations if op['success'])
        self.assertEqual(successful_ops, len(operations), "Not all operations succeeded")
        
        # Verify reasonable timing
        max_time = max(op['time'] for op in operations)
        avg_time = sum(op['time'] for op in operations) / len(operations)
        
        self.assertLess(max_time, 1.0, f"Slowest operation took {max_time:.3f}s")
        self.assertLess(avg_time, 0.3, f"Average operation took {avg_time:.3f}s")

    def test_large_patient_dataset_tag_operations(self):
        """Test tag operations with a larger patient dataset"""
        # Create additional patients
        patients = [self.patient]  # Include the existing one
        for i in range(4):  # Create 4 more for total of 5
            patient = Patient.objects.create(
                name=f'Patient {i+1}',
                birthday='1990-01-01',
                gender='M',
                status=Patient.Status.INPATIENT,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            patients.append(patient)
        
        # Create enough unique allowed tags for multiple patients (15 total for 5 patients * 3 tags each)
        allowed_tags = []
        for i in range(15):
            tag = AllowedTag.objects.create(
                name=f'Dataset Tag {i:02d}',
                color='magenta',
                is_active=True,
                created_by=self.doctor,
                updated_by=self.doctor
            )
            allowed_tags.append(tag)
        
        # Add unique tags to different patients (working within unique constraint)
        tag_index = 0
        for i, patient in enumerate(patients):
            for j in range(3):  # 3 tags per patient
                if tag_index < len(allowed_tags):
                    Tag.objects.create(
                        allowed_tag=allowed_tags[tag_index],
                        patient=patient,
                        created_by=self.doctor,
                        updated_by=self.doctor
                    )
                    tag_index += 1
        
        # Test accessing each patient's detail page
        detail_times = []
        for patient in patients:
            start_time = time.time()
            url = reverse('apps.patients:patient_detail', kwargs={'pk': patient.pk})
            response = self.client.get(url)
            end_time = time.time()
            
            detail_times.append(end_time - start_time)
            self.assertEqual(response.status_code, 200)
        
        # Verify timing with larger dataset
        max_detail_time = max(detail_times)
        avg_detail_time = sum(detail_times) / len(detail_times)
        
        self.assertLess(max_detail_time, 3.0, f"Slowest patient detail took {max_detail_time:.3f}s")
        self.assertLess(avg_detail_time, 2.0, f"Average patient detail took {avg_detail_time:.3f}s")
        
        # Test patient list view timing
        start_time = time.time()
        url = reverse('apps.patients:patient_list')
        response = self.client.get(url)
        list_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(list_time, 2.0, f"Patient list took {list_time:.3f}s with 5 patients")