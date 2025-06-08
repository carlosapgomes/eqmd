"""
Tests for object-level permission template tags.
"""

from django.test import TestCase
from django.template import Context, Template
from django.contrib.auth import get_user_model
from unittest.mock import Mock, patch

from apps.core.templatetags.permission_tags import (
    can_user_change_patient_personal_data,
    can_user_delete_event,
    can_user_see_patient_in_search,
    can_change_patient_data,
)

User = get_user_model()


class TestObjectLevelPermissionTemplateTags(TestCase):
    """Test object-level permission template tags."""
    
    def setUp(self):
        self.user = Mock()
        self.user.is_authenticated = True
        self.patient = Mock()
        self.event = Mock()
    
    @patch('apps.core.templatetags.permission_tags.can_change_patient_personal_data')
    def test_can_user_change_patient_personal_data_tag(self, mock_can_change):
        """Test can_user_change_patient_personal_data template tag."""
        mock_can_change.return_value = True
        
        result = can_user_change_patient_personal_data(self.user, self.patient)
        
        self.assertTrue(result)
        mock_can_change.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.templatetags.permission_tags.can_delete_event')
    def test_can_user_delete_event_tag(self, mock_can_delete):
        """Test can_user_delete_event template tag."""
        mock_can_delete.return_value = True
        
        result = can_user_delete_event(self.user, self.event)
        
        self.assertTrue(result)
        mock_can_delete.assert_called_once_with(self.user, self.event)
    
    @patch('apps.core.templatetags.permission_tags.can_see_patient_in_search')
    def test_can_user_see_patient_in_search_tag(self, mock_can_see):
        """Test can_user_see_patient_in_search template tag."""
        mock_can_see.return_value = True
        
        result = can_user_see_patient_in_search(self.user, self.patient)
        
        self.assertTrue(result)
        mock_can_see.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.templatetags.permission_tags.is_doctor')
    def test_can_change_patient_data_filter(self, mock_is_doctor):
        """Test can_change_patient_data filter."""
        mock_is_doctor.return_value = True
        
        result = can_change_patient_data(self.user)
        
        self.assertTrue(result)
        mock_is_doctor.assert_called_once_with(self.user)
    
    def test_can_change_patient_data_filter_unauthenticated(self):
        """Test can_change_patient_data filter with unauthenticated user."""
        self.user.is_authenticated = False
        
        with patch('apps.core.templatetags.permission_tags.is_doctor') as mock_is_doctor:
            mock_is_doctor.return_value = False
            result = can_change_patient_data(self.user)
            self.assertFalse(result)


class TestObjectLevelPermissionTemplateTagsInTemplate(TestCase):
    """Test object-level permission template tags in actual templates."""
    
    def setUp(self):
        self.user = Mock()
        self.user.is_authenticated = True
        self.patient = Mock()
        self.event = Mock()
    
    @patch('apps.core.templatetags.permission_tags.can_change_patient_personal_data')
    def test_can_user_change_patient_personal_data_in_template(self, mock_can_change):
        """Test can_user_change_patient_personal_data tag in template."""
        mock_can_change.return_value = True
        
        template = Template(
            "{% load permission_tags %}"
            "{% can_user_change_patient_personal_data user patient as can_change %}"
            "{% if can_change %}YES{% else %}NO{% endif %}"
        )
        
        context = Context({'user': self.user, 'patient': self.patient})
        result = template.render(context)
        
        self.assertEqual(result, 'YES')
        mock_can_change.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.templatetags.permission_tags.can_delete_event')
    def test_can_user_delete_event_in_template(self, mock_can_delete):
        """Test can_user_delete_event tag in template."""
        mock_can_delete.return_value = False
        
        template = Template(
            "{% load permission_tags %}"
            "{% can_user_delete_event user event as can_delete %}"
            "{% if can_delete %}YES{% else %}NO{% endif %}"
        )
        
        context = Context({'user': self.user, 'event': self.event})
        result = template.render(context)
        
        self.assertEqual(result, 'NO')
        mock_can_delete.assert_called_once_with(self.user, self.event)
    
    @patch('apps.core.templatetags.permission_tags.can_see_patient_in_search')
    def test_can_user_see_patient_in_search_in_template(self, mock_can_see):
        """Test can_user_see_patient_in_search tag in template."""
        mock_can_see.return_value = True
        
        template = Template(
            "{% load permission_tags %}"
            "{% can_user_see_patient_in_search user patient as can_see %}"
            "{% if can_see %}VISIBLE{% else %}HIDDEN{% endif %}"
        )
        
        context = Context({'user': self.user, 'patient': self.patient})
        result = template.render(context)
        
        self.assertEqual(result, 'VISIBLE')
        mock_can_see.assert_called_once_with(self.user, self.patient)
    
    @patch('apps.core.templatetags.permission_tags.is_doctor')
    def test_can_change_patient_data_filter_in_template(self, mock_is_doctor):
        """Test can_change_patient_data filter in template."""
        mock_is_doctor.return_value = True
        
        template = Template(
            "{% load permission_tags %}"
            "{% if user|can_change_patient_data %}DOCTOR{% else %}NOT_DOCTOR{% endif %}"
        )
        
        context = Context({'user': self.user})
        result = template.render(context)
        
        self.assertEqual(result, 'DOCTOR')
        mock_is_doctor.assert_called_once_with(self.user)
    
    def test_multiple_tags_in_template(self):
        """Test multiple object-level permission tags in one template."""
        with patch('apps.core.templatetags.permission_tags.can_change_patient_personal_data') as mock_change_data, \
             patch('apps.core.templatetags.permission_tags.can_delete_event') as mock_delete_event, \
             patch('apps.core.templatetags.permission_tags.is_doctor') as mock_is_doctor:
            
            mock_change_data.return_value = True
            mock_delete_event.return_value = False
            mock_is_doctor.return_value = True
            
            template = Template(
                "{% load permission_tags %}"
                "{% can_user_change_patient_personal_data user patient as can_change_data %}"
                "{% can_user_delete_event user event as can_delete %}"
                "{% if can_change_data %}DATA:YES{% else %}DATA:NO{% endif %}|"
                "{% if can_delete %}DELETE:YES{% else %}DELETE:NO{% endif %}|"
                "{% if user|can_change_patient_data %}DOCTOR:YES{% else %}DOCTOR:NO{% endif %}"
            )
            
            context = Context({
                'user': self.user, 
                'patient': self.patient, 
                'event': self.event
            })
            result = template.render(context)
            
            self.assertEqual(result, 'DATA:YES|DELETE:NO|DOCTOR:YES')
            mock_change_data.assert_called_once_with(self.user, self.patient)
            mock_delete_event.assert_called_once_with(self.user, self.event)
            mock_is_doctor.assert_called_once_with(self.user)
