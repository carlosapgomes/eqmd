from django import template
from django.utils.html import format_html
from apps.hospitals.models import Ward

register = template.Library()

@register.simple_tag
def capacity_bar(ward):
    """Renders a progress bar showing ward capacity usage"""
    if not isinstance(ward, Ward):
        return ''

    occupancy = ward.occupancy_rate
    bar_class = 'bg-success'
    if occupancy > 90:
        bar_class = 'bg-danger'
    elif occupancy > 70:
        bar_class = 'bg-warning'

    return format_html(
        '<div class="progress" style="height: 20px;">'
        '<div class="progress-bar {}" role="progressbar" style="width: {}%;" '
        'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">{}/{} beds ({}%)</div>'
        '</div>',
        bar_class, occupancy, occupancy, ward.patient_count, ward.capacity, occupancy
    )