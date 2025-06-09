from django import template
from django.utils.safestring import mark_safe
from apps.patients.models import Patient

register = template.Library()

@register.filter
def patient_status_badge(status):
    """
    Returns a Bootstrap badge with appropriate color for patient status.

    Usage: {{ patient.status|patient_status_badge }}
    """
    status_classes = {
        Patient.Status.OUTPATIENT: 'bg-success',      # 1 - Ambulatorial
        Patient.Status.INPATIENT: 'bg-primary',       # 2 - Internado  
        Patient.Status.EMERGENCY: 'bg-danger',        # 3 - Emergência
        Patient.Status.DISCHARGED: 'bg-secondary',    # 4 - Alta
        Patient.Status.TRANSFERRED: 'bg-warning',     # 5 - Transferido
    }

    status_labels = dict(Patient.Status.choices)
    status_class = status_classes.get(status, 'bg-secondary')
    status_label = status_labels.get(status, 'Desconhecido')

    return mark_safe(f'<span class="badge {status_class}">{status_label}</span>')

@register.inclusion_tag('patients/tags/patient_tags.html')
def patient_tags(patient):
    """
    Renders the tags for a patient.

    Usage: {% patient_tags patient %}
    """
    return {'tags': patient.tags.all()}