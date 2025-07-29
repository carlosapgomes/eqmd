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
        Patient.Status.DECEASED: 'bg-dark',           # 6 - Óbito
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


@register.filter
def can_change_status(user, patient):
    """Check if user can change patient status"""
    from apps.core.permissions.utils import can_change_patient_status
    return can_change_patient_status(user, patient, None)


@register.simple_tag
def available_status_actions(user, patient):
    """Get list of available status change actions for user/patient"""
    from apps.core.permissions.utils import can_change_patient_status
    
    actions = []
    current_status = patient.status
    
    # Define possible transitions with their display information
    possible_transitions = [
        (Patient.Status.INPATIENT, 'Internar', 'hospital', 'btn-success'),
        (Patient.Status.EMERGENCY, 'Emergência', 'exclamation-triangle', 'btn-danger'),
        (Patient.Status.DISCHARGED, 'Dar Alta', 'door-open', 'btn-info'),
        (Patient.Status.TRANSFERRED, 'Transferir', 'arrow-left-right', 'btn-primary'),
        (Patient.Status.OUTPATIENT, 'Ambulatorial', 'person-check', 'btn-secondary'),
        (Patient.Status.DECEASED, 'Declarar Óbito', 'heart-pulse', 'btn-dark'),
    ]
    
    # Check each possible status change
    for status_value, action_label, icon, btn_class in possible_transitions:
        if status_value != current_status:
            if can_change_patient_status(user, patient, status_value):
                actions.append({
                    'status': status_value,
                    'label': action_label,
                    'icon': icon,
                    'btn_class': btn_class,
                    'action_name': _get_action_name(current_status, status_value)
                })
    
    return actions


def _get_action_name(current_status, target_status):
    """Generate action name for status transition"""
    action_names = {
        Patient.Status.INPATIENT: 'admit_patient',
        Patient.Status.EMERGENCY: 'emergency_admission',
        Patient.Status.DISCHARGED: 'discharge_patient',
        Patient.Status.TRANSFERRED: 'transfer_patient',
        Patient.Status.OUTPATIENT: 'set_outpatient',
        Patient.Status.DECEASED: 'declare_death',
    }
    return action_names.get(target_status, 'change_status')


@register.filter
def patient_gender_badge(gender):
    """
    Returns a Bootstrap badge with appropriate color for patient gender.

    Usage: {{ patient.gender|patient_gender_badge }}
    """
    gender_classes = {
        Patient.GenderChoices.MALE: 'bg-primary',        # M - Masculino
        Patient.GenderChoices.FEMALE: 'bg-danger',       # F - Feminino  
        Patient.GenderChoices.OTHER: 'bg-success',       # O - Outro
        Patient.GenderChoices.NOT_INFORMED: 'bg-secondary', # N - Não Informado
    }

    gender_labels = dict(Patient.GenderChoices.choices)
    gender_class = gender_classes.get(gender, 'bg-secondary')
    gender_label = gender_labels.get(gender, 'Não Informado')

    return mark_safe(f'<span class="badge {gender_class}">{gender_label}</span>')


@register.filter
def patient_gender_icon(gender):
    """
    Returns a Bootstrap icon for patient gender.

    Usage: {{ patient.gender|patient_gender_icon }}
    """
    gender_icons = {
        Patient.GenderChoices.MALE: 'person-standing',
        Patient.GenderChoices.FEMALE: 'person-standing-dress',
        Patient.GenderChoices.OTHER: 'person',
        Patient.GenderChoices.NOT_INFORMED: 'question-circle',
    }

    icon_class = gender_icons.get(gender, 'question-circle')
    return mark_safe(f'<i class="bi bi-{icon_class}"></i>')


@register.filter
def patient_gender_display(gender):
    """
    Returns the display name for patient gender.

    Usage: {{ patient.gender|patient_gender_display }}
    """
    gender_labels = dict(Patient.GenderChoices.choices)
    return gender_labels.get(gender, 'Não Informado')