from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from .models import Hospital

User = get_user_model()


class HospitalModelTest(TestCase):
    def test_hospital_creation(self):
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR"
        )
        self.assertEqual(hospital.name, "Hospital São Rafael")
        self.assertEqual(hospital.short_name, "HSR")
        self.assertIsNotNone(hospital.id)

    def test_hospital_str_representation(self):
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR"
        )
        self.assertEqual(str(hospital), "Hospital São Rafael")

    def test_hospital_location_fields(self):
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR",
            address="Rua Saldanha Marinho, 2000",
            city="Salvador",
            state="BA",
            zip_code="40070-110"
        )
        self.assertEqual(hospital.address, "Rua Saldanha Marinho, 2000")
        self.assertEqual(hospital.city, "Salvador")
        self.assertEqual(hospital.state, "BA")
        self.assertEqual(hospital.zip_code, "40070-110")

    def test_hospital_location_fields_optional(self):
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR"
        )
        self.assertEqual(hospital.address, "")
        self.assertEqual(hospital.city, "")
        self.assertEqual(hospital.state, "")
        self.assertEqual(hospital.zip_code, "")

    def test_get_absolute_url(self):
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR"
        )
        expected_url = f"/hospitals/{hospital.pk}/"
        self.assertEqual(hospital.get_absolute_url(), expected_url)

    def test_tracking_fields(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR",
            phone="(71) 3281-6000",
            created_by=user,
            updated_by=user
        )
        
        self.assertEqual(hospital.phone, "(71) 3281-6000")
        self.assertIsNotNone(hospital.created_at)
        self.assertIsNotNone(hospital.updated_at)
        self.assertEqual(hospital.created_by, user)
        self.assertEqual(hospital.updated_by, user)
        
    def test_automatic_timestamp_updates(self):
        user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123"
        )
        hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR",
            created_by=user,
            updated_by=user
        )
        
        original_created_at = hospital.created_at
        original_updated_at = hospital.updated_at
        
        # Update the hospital
        hospital.name = "Hospital São Rafael Updated"
        hospital.save()
        
        # Refresh from database
        hospital.refresh_from_db()
        
        # created_at should remain the same, updated_at should change
        self.assertEqual(hospital.created_at, original_created_at)
        self.assertGreater(hospital.updated_at, original_updated_at)


class HospitalListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
    def test_list_view_url_resolution(self):
        url = reverse('apps.hospitals:list')
        self.assertEqual(url, '/hospitals/')
        
    def test_list_view_status_code(self):
        response = self.client.get('/hospitals/')
        self.assertEqual(response.status_code, 200)
        
    def test_list_view_uses_correct_template(self):
        response = self.client.get('/hospitals/')
        self.assertTemplateUsed(response, 'hospitals/hospital_list.html')
        
    def test_list_view_with_no_hospitals(self):
        response = self.client.get('/hospitals/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nenhum hospital encontrado')
        self.assertEqual(len(response.context['hospitals']), 0)
        
    def test_list_view_with_hospitals(self):
        Hospital.objects.create(name="Hospital A", short_name="HA")
        Hospital.objects.create(name="Hospital B", short_name="HB")
        
        response = self.client.get('/hospitals/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital A')
        self.assertContains(response, 'Hospital B')
        self.assertEqual(len(response.context['hospitals']), 2)
        
    def test_list_view_ordering(self):
        hospital_b = Hospital.objects.create(name="Hospital B", short_name="HB")
        hospital_a = Hospital.objects.create(name="Hospital A", short_name="HA")
        
        response = self.client.get('/hospitals/')
        hospitals = response.context['hospitals']
        
        # Should be ordered by name (Hospital A should come first)
        self.assertEqual(hospitals[0], hospital_a)
        self.assertEqual(hospitals[1], hospital_b)


class HospitalDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.hospital = Hospital.objects.create(
            name="Hospital São Rafael",
            short_name="HSR",
            address="Rua Saldanha Marinho, 2000",
            city="Salvador",
            state="BA",
            zip_code="40070-110",
            phone="(71) 3281-6000"
        )
        
    def test_detail_view_url_resolution(self):
        url = reverse('apps.hospitals:detail', kwargs={'pk': self.hospital.pk})
        expected_url = f'/hospitals/{self.hospital.pk}/'
        self.assertEqual(url, expected_url)
        
    def test_detail_view_status_code(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        self.assertEqual(response.status_code, 200)
        
    def test_detail_view_uses_correct_template(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        self.assertTemplateUsed(response, 'hospitals/hospital_detail.html')
        
    def test_detail_view_context_data(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        self.assertEqual(response.context['hospital'], self.hospital)
        
    def test_detail_view_displays_hospital_information(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        self.assertContains(response, self.hospital.name)
        self.assertContains(response, self.hospital.short_name)
        self.assertContains(response, self.hospital.address)
        self.assertContains(response, self.hospital.city)
        self.assertContains(response, self.hospital.state)
        self.assertContains(response, self.hospital.phone)
        
    def test_detail_view_with_minimal_data(self):
        minimal_hospital = Hospital.objects.create(
            name="Minimal Hospital",
            short_name="MH"
        )
        response = self.client.get(f'/hospitals/{minimal_hospital.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, minimal_hospital.name)
        self.assertContains(response, minimal_hospital.short_name)
        
    def test_detail_view_404_for_nonexistent_hospital(self):
        import uuid
        nonexistent_id = uuid.uuid4()
        response = self.client.get(f'/hospitals/{nonexistent_id}/')
        self.assertEqual(response.status_code, 404)


class HospitalCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
    def test_create_view_requires_login(self):
        response = self.client.get('/hospitals/create/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_create_view_url_resolution(self):
        url = reverse('apps.hospitals:create')
        self.assertEqual(url, '/hospitals/create/')
        
    def test_create_view_uses_correct_template(self):
        self.client.force_login(self.user)
        response = self.client.get('/hospitals/create/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hospitals/hospital_form.html')
        
    def test_create_view_context_data(self):
        self.client.force_login(self.user)
        response = self.client.get('/hospitals/create/')
        self.assertEqual(response.context['form_title'], 'Criar Novo Hospital')
        self.assertEqual(response.context['submit_text'], 'Criar Hospital')
        
    def test_create_hospital_with_valid_data(self):
        self.client.force_login(self.user)
        data = {
            'name': 'Hospital Test',
            'short_name': 'HT',
            'address': 'Test Address',
            'city': 'Salvador',
            'state': 'BA',
            'zip_code': '40000-000',
            'phone': '(71) 3333-4444'
        }
        response = self.client.post('/hospitals/create/', data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        hospital = Hospital.objects.get(name='Hospital Test')
        self.assertEqual(hospital.short_name, 'HT')
        self.assertEqual(hospital.created_by, self.user)
        self.assertEqual(hospital.updated_by, self.user)
        
    def test_create_hospital_with_minimal_data(self):
        self.client.force_login(self.user)
        data = {
            'name': 'Minimal Hospital',
            'short_name': 'MH'
        }
        response = self.client.post('/hospitals/create/', data)
        self.assertEqual(response.status_code, 302)
        
        hospital = Hospital.objects.get(name='Minimal Hospital')
        self.assertEqual(hospital.short_name, 'MH')
        
    def test_create_hospital_form_validation(self):
        self.client.force_login(self.user)
        # Missing required fields
        data = {'name': '', 'short_name': ''}
        response = self.client.post('/hospitals/create/', data)
        self.assertEqual(response.status_code, 200)  # Stay on form page
        self.assertContains(response, 'Este campo é obrigatório')


class HospitalUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.hospital = Hospital.objects.create(
            name="Original Hospital",
            short_name="OH",
            created_by=self.user,
            updated_by=self.user
        )
        
    def test_update_view_requires_login(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/edit/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_update_view_url_resolution(self):
        url = reverse('apps.hospitals:update', kwargs={'pk': self.hospital.pk})
        expected_url = f'/hospitals/{self.hospital.pk}/edit/'
        self.assertEqual(url, expected_url)
        
    def test_update_view_uses_correct_template(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/hospitals/{self.hospital.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hospitals/hospital_form.html')
        
    def test_update_view_context_data(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/hospitals/{self.hospital.pk}/edit/')
        self.assertEqual(response.context['form_title'], f'Editar Hospital: {self.hospital.name}')
        self.assertEqual(response.context['submit_text'], 'Salvar Alterações')
        
    def test_update_hospital_with_valid_data(self):
        self.client.force_login(self.user)
        data = {
            'name': 'Updated Hospital',
            'short_name': 'UH',
            'address': 'Updated Address',
            'city': 'Salvador',
            'state': 'BA',
            'zip_code': '40001-000',
            'phone': '(71) 3333-5555'
        }
        response = self.client.post(f'/hospitals/{self.hospital.pk}/edit/', data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.name, 'Updated Hospital')
        self.assertEqual(self.hospital.short_name, 'UH')
        self.assertEqual(self.hospital.updated_by, self.user)
        
    def test_update_hospital_404_for_nonexistent(self):
        self.client.force_login(self.user)
        import uuid
        nonexistent_id = uuid.uuid4()
        response = self.client.get(f'/hospitals/{nonexistent_id}/edit/')
        self.assertEqual(response.status_code, 404)


class HospitalDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.hospital = Hospital.objects.create(
            name="Hospital to Delete",
            short_name="HTD",
            created_by=self.user,
            updated_by=self.user
        )
        
    def test_delete_view_requires_login(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/delete/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_delete_view_url_resolution(self):
        url = reverse('apps.hospitals:delete', kwargs={'pk': self.hospital.pk})
        expected_url = f'/hospitals/{self.hospital.pk}/delete/'
        self.assertEqual(url, expected_url)
        
    def test_delete_view_uses_correct_template(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/hospitals/{self.hospital.pk}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hospitals/hospital_confirm_delete.html')
        
    def test_delete_view_displays_hospital_information(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/hospitals/{self.hospital.pk}/delete/')
        self.assertContains(response, self.hospital.name)
        self.assertContains(response, self.hospital.short_name)
        self.assertContains(response, 'Confirmar Exclusão')
        
    def test_delete_hospital_confirmation_and_deletion(self):
        self.client.force_login(self.user)
        hospital_id = self.hospital.pk
        
        # POST to delete
        response = self.client.post(f'/hospitals/{hospital_id}/delete/')
        self.assertEqual(response.status_code, 302)  # Redirect after deletion
        
        # Hospital should be deleted
        with self.assertRaises(Hospital.DoesNotExist):
            Hospital.objects.get(pk=hospital_id)
            
    def test_delete_view_redirects_to_list(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/hospitals/{self.hospital.pk}/delete/')
        self.assertRedirects(response, reverse('apps.hospitals:list'))
        
    def test_delete_view_404_for_nonexistent_hospital(self):
        self.client.force_login(self.user)
        import uuid
        nonexistent_id = uuid.uuid4()
        response = self.client.get(f'/hospitals/{nonexistent_id}/delete/')
        self.assertEqual(response.status_code, 404)


class HospitalSearchAndFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create test hospitals
        self.hospital_sp = Hospital.objects.create(
            name="Hospital São Paulo",
            short_name="HSP",
            city="São Paulo",
            state="SP"
        )
        self.hospital_ba = Hospital.objects.create(
            name="Hospital Bahia",
            short_name="HBA",
            city="Salvador",
            state="BA"
        )
        self.hospital_rj = Hospital.objects.create(
            name="Hospital Rio de Janeiro",
            short_name="HRJ",
            city="Rio de Janeiro",
            state="RJ"
        )
        self.hospital_ba2 = Hospital.objects.create(
            name="Hospital Salvador",
            short_name="HS",
            city="Salvador",
            state="BA"
        )
        
    def test_search_by_name(self):
        response = self.client.get('/hospitals/?q=São Paulo')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 1)
        self.assertEqual(hospitals[0], self.hospital_sp)
        
    def test_search_by_short_name(self):
        response = self.client.get('/hospitals/?q=HSP')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 1)
        self.assertEqual(hospitals[0], self.hospital_sp)
        
    def test_search_by_city(self):
        response = self.client.get('/hospitals/?q=Salvador')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 2)  # hospital_ba and hospital_ba2 have Salvador as city
        
    def test_search_by_state(self):
        response = self.client.get('/hospitals/?q=BA')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 2)  # hospital_ba and hospital_ba2
        
    def test_filter_by_state(self):
        response = self.client.get('/hospitals/?state=BA')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 2)
        state_codes = [h.state for h in hospitals]
        self.assertTrue(all(state == 'BA' for state in state_codes))
        
    def test_filter_by_city(self):
        response = self.client.get('/hospitals/?city=Salvador')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 2)  # hospital_ba and hospital_ba2
        cities = [h.city for h in hospitals]
        self.assertTrue(all(city == 'Salvador' for city in cities))
        
    def test_combined_search_and_filter(self):
        response = self.client.get('/hospitals/?q=Hospital&state=BA')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 2)  # Both BA hospitals contain "Hospital"
        
    def test_search_context_data(self):
        response = self.client.get('/hospitals/?q=test&state=SP&city=São Paulo')
        self.assertEqual(response.context['search_query'], 'test')
        self.assertEqual(response.context['state_filter'], 'SP')
        self.assertEqual(response.context['city_filter'], 'São Paulo')
        
    def test_available_states_in_context(self):
        response = self.client.get('/hospitals/')
        available_states = list(response.context['available_states'])
        expected_states = ['BA', 'RJ', 'SP']
        self.assertEqual(sorted(available_states), expected_states)
        
    def test_available_cities_in_context(self):
        response = self.client.get('/hospitals/')
        available_cities = list(response.context['available_cities'])
        expected_cities = ['Rio de Janeiro', 'Salvador', 'São Paulo']
        self.assertEqual(sorted(available_cities), expected_cities)
        
    def test_empty_search_returns_all(self):
        response = self.client.get('/hospitals/?q=')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 4)  # All hospitals
        
    def test_no_results_search(self):
        response = self.client.get('/hospitals/?q=NonexistentHospital')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 0)
        
    def test_case_insensitive_search(self):
        response = self.client.get('/hospitals/?q=hospital são paulo')
        self.assertEqual(response.status_code, 200)
        hospitals = response.context['hospitals']
        self.assertEqual(len(hospitals), 1)
        self.assertEqual(hospitals[0], self.hospital_sp)


class HospitalRelatedDataTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.hospital = Hospital.objects.create(
            name="Test Hospital",
            short_name="TH",
            city="Test City",
            state="TC"
        )
        
    def test_detail_view_has_related_data_context(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        self.assertEqual(response.status_code, 200)
        
        # Check that related data context variables are present
        self.assertIn('related_wards', response.context)
        self.assertIn('related_users', response.context)
        self.assertIn('statistics', response.context)
        
    def test_related_wards_placeholder(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        related_wards = response.context['related_wards']
        self.assertEqual(related_wards, [])  # Should be empty placeholder
        
    def test_related_users_placeholder(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        related_users = response.context['related_users']
        self.assertEqual(related_users, [])  # Should be empty placeholder
        
    def test_statistics_placeholder(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        statistics = response.context['statistics']
        
        expected_statistics = {
            'total_wards': 0,
            'active_users': 0,
            'current_patients': 0,
            'occupancy_rate': 0,
        }
        self.assertEqual(statistics, expected_statistics)
        
    def test_template_renders_related_sections(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        content = response.content.decode()
        
        # Check that related sections are present in template
        self.assertIn('Enfermarias', content)
        self.assertIn('Equipe Médica', content)
        self.assertIn('Estatísticas e Relatórios', content)
        self.assertIn('Em breve', content)  # Development badges
        
    def test_template_shows_placeholder_messages(self):
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        content = response.content.decode()
        
        # Check for placeholder messages
        self.assertIn('Módulo em Desenvolvimento', content)
        self.assertIn('módulo de enfermarias for implementado', content)
        self.assertIn('módulo de equipe médica for implementado', content)
        
    def test_future_ready_context_structure(self):
        # Test that the context structure is ready for future development
        response = self.client.get(f'/hospitals/{self.hospital.pk}/')
        
        # Verify context has the expected structure for future enhancement
        self.assertTrue(isinstance(response.context['related_wards'], list))
        self.assertTrue(isinstance(response.context['related_users'], list))
        self.assertTrue(isinstance(response.context['statistics'], dict))
        
        # Verify statistics has the expected keys
        statistics_keys = response.context['statistics'].keys()
        expected_keys = {'total_wards', 'active_users', 'current_patients', 'occupancy_rate'}
        self.assertEqual(set(statistics_keys), expected_keys)
