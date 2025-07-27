from .models import Patient, Ward

def patient_stats(request):
    """
    Context processor that provides patient statistics for templates.
    """
    if not request.user.is_authenticated:
        return {}

    # Only calculate stats if user has permission to view patients
    if not request.user.has_perm('patients.view_patient'):
        return {}

    try:
        total_patients = Patient.objects.count()
        inpatient_count = Patient.objects.filter(status=Patient.Status.INPATIENT).count()
        outpatient_count = Patient.objects.filter(status=Patient.Status.OUTPATIENT).count()
        return {
            'total_patients': total_patients,
            'inpatient_count': inpatient_count,
            'outpatient_count': outpatient_count,
        }
    except:
        # Return empty dict if database isn't set up yet
        return {}

def recent_patients(request):
    """
    Context processor that provides recent patients for templates.
    """
    if not request.user.is_authenticated:
        return {}

    # Only get recent patients if user has permission
    if not request.user.has_perm('patients.view_patient'):
        return {}

    try:
        recent_patients = Patient.objects.all().order_by('-created_at')[:5]
        return {
            'recent_patients': recent_patients,
        }
    except:
        # Return empty dict if database isn't set up yet
        return {}

def ward_stats(request):
    """Add ward statistics to template context"""
    if not request.user.is_authenticated:
        return {}
    
    try:
        wards = Ward.objects.filter(is_active=True)
        ward_stats = []
        
        for ward in wards:
            ward_stats.append({
                "ward": ward,
                "patient_count": ward.get_current_patients_count(),
                "beds_in_use": len(ward.get_available_beds_list()),
            })
        
        return {
            "ward_statistics": ward_stats,
            "total_active_wards": wards.count(),
        }
    except:
        # Return empty dict if database isn't set up yet
        return {}