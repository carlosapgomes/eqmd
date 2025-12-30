# Phase 2 Prompt: Basic CRUD Operations

Implement CRUD views and templates for Django discharge reports app.

CONTEXT:

- Phase 1 completed: DischargeReport model exists extending Event
- Model has fields: admission_date, discharge_date, medical_specialty, admission_history, problems_and_diagnosis, exams_list, procedures_list, inpatient_medical_history, discharge_status, discharge_recommendations, is_draft
- Bootstrap 5.3 styling, Portuguese localization
- Project uses LoginRequiredMixin, UUID primary keys
- Separate create/update templates required (don't reuse create for edit)

GOAL: Create complete CRUD interface with forms, views, and templates.

TASKS:

1. UPDATE FORMS.PY:

```python
from django import forms
from .models import DischargeReport


class DischargeReportForm(forms.ModelForm):
    """Form for discharge report create/update"""

    class Meta:
        model = DischargeReport
        fields = [
            'patient', 'event_datetime', 'description',
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history',
            'discharge_status', 'discharge_recommendations'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'event_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'description': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Descrição do relatório'}
            ),
            'admission_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'discharge_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'medical_specialty': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Ex: Cardiologia'}
            ),
            'admission_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'problems_and_diagnosis': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'exams_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'procedures_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'inpatient_medical_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 6}
            ),
            'discharge_status': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'discharge_recommendations': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        admission_date = cleaned_data.get('admission_date')
        discharge_date = cleaned_data.get('discharge_date')

        if admission_date and discharge_date:
            if admission_date > discharge_date:
                raise forms.ValidationError(
                    "A data de admissão deve ser anterior à data de alta."
                )

        return cleaned_data
```

1. UPDATE VIEWS.PY:

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from .models import DischargeReport
from .forms import DischargeReportForm


class DischargeReportListView(LoginRequiredMixin, ListView):
    """List all discharge reports"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        return DischargeReport.objects.select_related('patient').order_by('-created_at')


class DischargeReportDetailView(LoginRequiredMixin, DetailView):
    """View discharge report details"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_detail.html'
    context_object_name = 'report'


class DischargeReportCreateView(LoginRequiredMixin, CreateView):
    """Create new discharge report"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_create.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.event_datetime = form.instance.event_datetime or timezone.now()

        # Handle draft vs final save
        if 'save_final' in self.request.POST:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta salvo definitivamente.')
        else:
            form.instance.is_draft = True
            messages.success(self.request, 'Relatório de alta salvo como rascunho.')

        return super().form_valid(form)


class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_update.html'

    def get_object(self):
        obj = super().get_object()
        # Check if editable (draft or within 24h window)
        if not obj.is_draft and not obj.can_be_edited:
            raise PermissionDenied("Relatório não pode mais ser editado.")
        return obj

    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        # Handle draft vs final save
        if 'save_final' in self.request.POST:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta finalizado.')
        else:
            messages.success(self.request, 'Relatório de alta atualizado.')

        return super().form_valid(form)


class DischargeReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete discharge report (drafts only)"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_confirm_delete.html'
    success_url = reverse_lazy('apps.dischargereports:dischargereport_list')

    def get_object(self):
        obj = super().get_object()
        if not obj.is_draft:
            raise PermissionDenied("Apenas rascunhos podem ser excluídos.")
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Rascunho do relatório de alta excluído.')
        return super().delete(request, *args, **kwargs)
```

1. UPDATE URLS.PY:

```python
from django.urls import path
from . import views

app_name = 'apps.dischargereports'

urlpatterns = [
    path('', views.DischargeReportListView.as_view(), name='dischargereport_list'),
    path('create/', views.DischargeReportCreateView.as_view(), name='dischargereport_create'),
    path('<uuid:pk>/', views.DischargeReportDetailView.as_view(), name='dischargereport_detail'),
    path('<uuid:pk>/update/', views.DischargeReportUpdateView.as_view(), name='dischargereport_update'),
    path('<uuid:pk>/delete/', views.DischargeReportDeleteView.as_view(), name='dischargereport_delete'),
]
```

1. CREATE TEMPLATES:

Create base directory structure:

```bash
mkdir -p apps/dischargereports/templates/dischargereports
```

apps/dischargereports/templates/dischargereports/dischargereport_create.html:

```html
{% extends 'base.html' %} {% load static %} {% load bootstrap5 %} {% block title
%}Novo Relatório de Alta{% endblock %} {% block content %}
<div class="container-fluid">
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <h3>Novo Relatório de Alta</h3>
          <a
            href="{% url 'apps.dischargereports:dischargereport_list' %}"
            class="btn btn-outline-secondary"
          >
            <i class="bi bi-arrow-left"></i> Voltar
          </a>
        </div>
        <div class="card-body">
          <form method="post">
            {% csrf_token %}

            <!-- Basic Info -->
            <div class="row mb-3">
              <div class="col-md-6">{% bootstrap_field form.patient %}</div>
              <div class="col-md-6">
                {% bootstrap_field form.event_datetime %}
              </div>
            </div>

            <div class="mb-3">{% bootstrap_field form.description %}</div>

            <!-- Date Fields -->
            <div class="row mb-3">
              <div class="col-md-6">
                {% bootstrap_field form.admission_date %}
              </div>
              <div class="col-md-6">
                {% bootstrap_field form.discharge_date %}
              </div>
            </div>

            <!-- Specialty -->
            <div class="mb-3">{% bootstrap_field form.medical_specialty %}</div>

            <!-- Content Sections -->
            <div class="mb-3">
              {% bootstrap_field form.problems_and_diagnosis %}
            </div>

            <div class="mb-3">{% bootstrap_field form.admission_history %}</div>

            <div class="mb-3">{% bootstrap_field form.exams_list %}</div>

            <div class="mb-3">{% bootstrap_field form.procedures_list %}</div>

            <div class="mb-3">
              {% bootstrap_field form.inpatient_medical_history %}
            </div>

            <div class="mb-3">{% bootstrap_field form.discharge_status %}</div>

            <div class="mb-3">
              {% bootstrap_field form.discharge_recommendations %}
            </div>

            <!-- Action Buttons -->
            <div class="d-flex gap-2">
              <button type="submit" name="save_draft" class="btn btn-warning">
                <i class="bi bi-floppy"></i> Salvar Rascunho
              </button>
              <button type="submit" name="save_final" class="btn btn-success">
                <i class="bi bi-check-circle"></i> Salvar Definitivo
              </button>
              <a
                href="{% url 'apps.dischargereports:dischargereport_list' %}"
                class="btn btn-secondary"
              >
                <i class="bi bi-x-circle"></i> Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

Create similar templates for:

- dischargereport_update.html (same as create but with "Editar" title)
- dischargereport_detail.html (read-only view)
- dischargereport_list.html (table of reports)
- dischargereport_confirm_delete.html (deletion confirmation)

1. REGISTER URLS IN MAIN PROJECT:
   Add to main urls.py:

```python
path('dischargereports/', include('apps.dischargereports.urls')),
```

VERIFICATION:

- All CRUD operations work
- Draft/final save buttons function
- Form validation works
- Templates display correctly
- Draft-only deletion enforced

DELIVERABLES:

- Complete CRUD interface
- Working forms with validation
- Bootstrap 5.3 templates
- Draft/final save logic
