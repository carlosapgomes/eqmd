from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'public_id', 'display_name', 'bio', 
            'is_active', 'is_staff', 'email', 
            'first_name', 'last_name', 'full_name',
            'profession'
        ]
        read_only_fields = [
            'public_id', 'is_active', 'is_staff', 'email', 
            'first_name', 'last_name', 'full_name',
            'profession'
        ]