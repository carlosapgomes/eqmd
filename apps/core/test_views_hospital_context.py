"""
Test views for hospital context middleware functionality.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from apps.core.permissions import hospital_context_required
from apps.hospitals.models import Hospital


@login_required
def hospital_context_test_view(request):
    """Test view to demonstrate hospital context functionality."""
    context = {
        'user': request.user,
        'has_hospital_context': getattr(request.user, 'has_hospital_context', False),
        'current_hospital': getattr(request.user, 'current_hospital', None),
        'available_hospitals': Hospital.objects.all(),
    }
    
    return render(request, 'core/test_hospital_context.html', context)


@hospital_context_required
def hospital_context_required_view(request):
    """Test view that requires hospital context."""
    context = {
        'message': 'You have successfully accessed a hospital context required view!',
        'current_hospital': request.user.current_hospital,
        'hospital_name': request.user.current_hospital.name,
    }
    
    return render(request, 'core/test_hospital_context_success.html', context)


@login_required
def hospital_context_api_view(request):
    """API view to get current hospital context information."""
    data = {
        'is_authenticated': request.user.is_authenticated,
        'has_hospital_context': getattr(request.user, 'has_hospital_context', False),
        'current_hospital': None,
    }
    
    if hasattr(request.user, 'current_hospital') and request.user.current_hospital:
        data['current_hospital'] = {
            'id': str(request.user.current_hospital.pk),
            'name': request.user.current_hospital.name,
            'short_name': request.user.current_hospital.short_name,
            'city': request.user.current_hospital.city,
        }
    
    return JsonResponse(data)