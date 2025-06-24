"""
Template tests for VideoClip functionality (Slice 4)
Tests that all video-related templates render correctly
"""

import os
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from apps.mediafiles.models import VideoClip, MediaFile
from apps.mediafiles.templatetags.mediafiles_tags import (
    video_player, video_thumbnail, video_duration, video_modal_trigger
)

User = get_user_model()


class VideoClipTemplateTests(TestCase):
    """Test VideoClip template rendering"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='123 Test St',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create test video file
        test_video_path = os.path.join(
            os.path.dirname(__file__), 
            'test_media', 
            'test_video.mp4'
        )
        
        with open(test_video_path, 'rb') as f:
            video_content = f.read()
        
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            video_content,
            content_type="video/mp4"
        )
        
        # Create MediaFile using the proper method
        self.media_file = MediaFile.objects.create_from_upload(video_file)
        
        # Create VideoClip
        self.videoclip = VideoClip.objects.create(
            patient=self.patient,
            media_file=self.media_file,
            description='Test video clip',
            caption='Test caption',
            event_datetime=timezone.now(),
            created_by=self.user
        )
        
        self.client = Client()
        self.client.force_login(self.user)

    def test_videoclip_form_template_renders(self):
        """Test that videoclip_form.html renders without errors"""
        url = reverse('mediafiles:videoclip_create', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo Vídeo')
        self.assertContains(response, 'video-upload-area')
        self.assertContains(response, 'videoclip.css')
        self.assertContains(response, 'videoclip.js')

    def test_videoclip_detail_template_renders(self):
        """Test that videoclip_detail.html renders without errors"""
        url = reverse('mediafiles:videoclip_detail', kwargs={'pk': self.videoclip.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test video clip')
        self.assertContains(response, 'video-player')
        self.assertContains(response, 'fullscreenModal')
        self.assertContains(response, 'videoclip.css')

    def test_videoclip_update_template_renders(self):
        """Test that videoclip_form.html renders for update"""
        url = reverse('mediafiles:videoclip_update', kwargs={'pk': self.videoclip.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Vídeo')
        self.assertContains(response, 'Vídeo Atual')
        self.assertContains(response, 'test_video.mp4')

    def test_videoclip_delete_template_renders(self):
        """Test that videoclip_confirm_delete.html renders without errors"""
        url = reverse('mediafiles:videoclip_delete', kwargs={'pk': self.videoclip.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Exclusão')
        self.assertContains(response, 'Test video clip')
        self.assertContains(response, 'confirmDelete')

    def test_event_card_videoclip_template_renders(self):
        """Test that event_card_videoclip.html renders without errors"""
        # This template is included in timeline views
        template_string = '''
        {% load mediafiles_tags %}
        {% include "events/partials/event_card_videoclip.html" with event=videoclip event_data=event_data %}
        '''
        
        template = Template(template_string)
        context = Context({
            'videoclip': self.videoclip,
            'event_data': {
                'event': self.videoclip,
                'can_edit': True,
                'can_delete': True,
                'excerpt': 'Test excerpt'
            }
        })
        
        rendered = template.render(context)
        
        # Check for key elements
        self.assertIn('video-thumbnail', rendered)
        self.assertIn('video-duration-badge', rendered)
        self.assertIn('videoModal', rendered)

    def test_video_player_partial_renders(self):
        """Test that video_player.html partial renders without errors"""
        template_string = '''
        {% include "mediafiles/partials/video_player.html" with videoclip=videoclip controls=True %}
        '''
        
        template = Template(template_string)
        context = Context({'videoclip': self.videoclip})
        
        rendered = template.render(context)
        
        # Check for key elements
        self.assertIn('video-player-component', rendered)
        self.assertIn('controls', rendered)
        self.assertIn('video/mp4', rendered)

    def test_video_modal_partial_renders(self):
        """Test that video_modal.html partial renders without errors"""
        template_string = '''
        {% include "mediafiles/partials/video_modal.html" %}
        '''
        
        template = Template(template_string)
        context = Context({})
        
        rendered = template.render(context)
        
        # Check for key elements
        self.assertIn('videoModal', rendered)
        self.assertIn('video-modal-player', rendered)
        self.assertIn('videoPlayPause', rendered)


class VideoClipTemplateTagTests(TestCase):
    """Test VideoClip template tags"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='123 Test St',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create test video file
        test_video_path = os.path.join(
            os.path.dirname(__file__), 
            'test_media', 
            'test_video.mp4'
        )
        
        with open(test_video_path, 'rb') as f:
            video_content = f.read()
        
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            video_content,
            content_type="video/mp4"
        )
        
        # Create MediaFile using the proper method
        self.media_file = MediaFile.objects.create_from_upload(video_file)
        
        # Create VideoClip
        self.videoclip = VideoClip.objects.create(
            patient=self.patient,
            media_file=self.media_file,
            description='Test video clip',
            caption='Test caption',
            event_datetime=timezone.now(),
            created_by=self.user
        )

    def test_video_player_tag(self):
        """Test video_player template tag"""
        result = video_player(self.videoclip, controls=True, autoplay=False)
        
        self.assertIn('video-player', result)
        self.assertIn('controls', result)
        self.assertIn('videoclip_stream', result)
        self.assertIn('video/mp4', result)

    def test_video_thumbnail_tag(self):
        """Test video_thumbnail template tag"""
        result = video_thumbnail(self.videoclip, size='medium')
        
        self.assertIn('video-thumbnail', result)
        self.assertIn('video-duration-badge', result)
        self.assertIn('video-play-overlay', result)

    def test_video_duration_tag(self):
        """Test video_duration template tag"""
        result = video_duration(self.videoclip)
        
        self.assertEqual(result, '0:30')  # 30 seconds formatted

    def test_video_modal_trigger_tag(self):
        """Test video_modal_trigger template tag"""
        result = video_modal_trigger(self.videoclip, trigger_text='Play Video')
        
        self.assertIn('videoModal', result)
        self.assertIn('Play Video', result)
        self.assertIn('data-video-id', result)
        self.assertIn('data-video-url', result)

    def test_template_tags_with_none_videoclip(self):
        """Test template tags handle None videoclip gracefully"""
        self.assertEqual(video_player(None), "")
        self.assertEqual(video_thumbnail(None), "")
        self.assertEqual(video_duration(None), "")
        self.assertEqual(video_modal_trigger(None), "")


class VideoClipCSSJSTests(TestCase):
    """Test that CSS and JS files are properly loaded"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='123 Test St',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client = Client()
        self.client.force_login(self.user)

    def test_videoclip_css_loaded_in_form(self):
        """Test that videoclip.css is loaded in form template"""
        url = reverse('mediafiles:videoclip_create', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        
        self.assertContains(response, 'videoclip.css')

    def test_videoclip_js_loaded_in_form(self):
        """Test that videoclip.js is loaded in form template"""
        url = reverse('mediafiles:videoclip_create', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        
        self.assertContains(response, 'videoclip.js')
        self.assertContains(response, 'VideoClip.init()')

    def test_static_files_exist(self):
        """Test that static files exist"""
        from django.contrib.staticfiles.finders import find
        
        # Check CSS file exists
        css_path = find('mediafiles/css/videoclip.css')
        self.assertIsNotNone(css_path, "videoclip.css not found in static files")
        
        # Check JS file exists
        js_path = find('mediafiles/js/videoclip.js')
        self.assertIsNotNone(js_path, "videoclip.js not found in static files")
