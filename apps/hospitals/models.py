import uuid
from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings


class Hospital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, related_name='hospitals_created', null=True, blank=True)
    updated_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, related_name='hospitals_updated', null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('hospitals:detail', kwargs={'pk': self.pk})


class Ward(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    hospital = models.ForeignKey('Hospital', on_delete=models.CASCADE, related_name='wards')
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_wards')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_wards')

    @property
    def patient_count(self):
        # This will be implemented when Patient model is available
        # For now, return a placeholder value
        return 0

    @property
    def occupancy_rate(self):
        if self.capacity == 0:
            return 0
        return round((self.patient_count / self.capacity) * 100, 1)

    def __str__(self):
        return f"{self.name} ({self.hospital.name})"
