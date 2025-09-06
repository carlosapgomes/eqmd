## Phase 6 Prompt: Advanced Features & Permissions

````
Implement draft logic, permissions, and UI polish for discharge reports.

CONTEXT:
- Phases 1-5 completed: Full CRUD, timeline integration, print, Firebase import
- Draft system partially implemented (is_draft field exists)
- Need to refine draft logic, permissions, and UI polish
- Project uses standard Event permission system with 24h edit window

GOAL: Polish the discharge reports feature with proper draft logic and permissions.

TASKS:

1. UPDATE MODELS.PY - ADD DRAFT VALIDATION:
```python
# Add this method to DischargeReport model
def can_be_edited_by_user(self, user):
    """Check if report can be edited by specific user"""
    if self.is_draft:
        # Drafts can be edited by creator or users with edit permissions
        return self.created_by == user or user.has_perm('events.change_event')
    else:
        # Finalized reports follow 24h rule
        return self.can_be_edited and (self.created_by == user or user.has_perm('events.change_event'))

def can_be_deleted_by_user(self, user):
    """Check if report can be deleted by specific user"""
    # Only drafts can be deleted
    return self.is_draft and (self.created_by == user or user.has_perm('events.delete_event'))

@property
def status_display(self):
    """Get display text for report status"""
    if self.is_draft:
        return "Rascunho"
    else:
        return "Finalizado"

@property
def status_badge_class(self):
    """Get CSS class for status badge"""
    return "badge bg-warning text-dark" if self.is_draft else "badge bg-success"
````

2. UPDATE VIEWS.PY - IMPROVE PERMISSION LOGIC:

```python
# Update existing views with better permission checking

class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_update.html'

    def get_object(self):
        obj = super().get_object()
        # Check if user can edit this specific report
        if not obj.can_be_edited_by_user(self.request.user):
            if obj.is_draft:
                raise PermissionDenied("Você não tem permissão para editar este rascunho.")
            else:
                raise PermissionDenied("Este relatório não pode mais ser editado.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_finalize'] = self.object.is_draft
        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        # Handle draft vs final save
        if 'save_final' in self.request.POST and self.object.is_draft:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta finalizado com sucesso.')
        elif 'save_draft' in self.request.POST:
            form.instance.is_draft = True
            messages.success(self.request, 'Rascunho do relatório atualizado.')
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
        if not obj.can_be_deleted_by_user(self.request.user):
            raise PermissionDenied("Este relatório não pode ser excluído.")
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Rascunho do relatório de alta excluído com sucesso.')
        return super().delete(request, *args, **kwargs)
```

3. UPDATE TEMPLATES - IMPROVE DRAFT UI:

Update dischargereport_detail.html:

```html
{% extends 'base.html' %} {% load static %} {% load bootstrap5 %} {% block title
%}Relatório de Alta - {{ report.patient.name }}{% endblock %} {% block content
%}
<div class="container-fluid">
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div>
            <h3>Relatório de Alta</h3>
            <div class="d-flex align-items-center gap-2 mt-2">
              <span class="{{ report.status_badge_class }}">
                {% if report.is_draft %}
                <i class="bi bi-pencil-square"></i>
                {% else %}
                <i class="bi bi-check-circle"></i>
                {% endif %} {{ report.status_display }}
              </span>
              <small class="text-muted">
                {{ report.medical_specialty }} • {{
                report.admission_date|date:"d/m/Y" }} - {{
                report.discharge_date|date:"d/m/Y" }}
              </small>
            </div>
          </div>
          <div class="btn-group">
            <!-- Print Button -->
            <a
              href="{% url 'apps.dischargereports:dischargereport_print' pk=report.pk %}"
              class="btn btn-outline-secondary"
              target="_blank"
            >
              <i class="bi bi-printer"></i> Imprimir
            </a>

            <!-- Edit Button -->
            {% if report.can_be_edited_by_user:request.user %}
            <a
              href="{% url 'apps.dischargereports:dischargereport_update' pk=report.pk %}"
              class="btn btn-warning"
            >
              <i class="bi bi-pencil"></i>
              {% if report.is_draft %}Editar Rascunho{% else %}Editar{% endif %}
            </a>
            {% endif %}

            <!-- Delete Button (drafts only) -->
            {% if report.can_be_deleted_by_user:request.user %}
            <a
              href="{% url 'apps.dischargereports:dischargereport_delete' pk=report.pk %}"
              class="btn btn-outline-danger"
            >
              <i class="bi bi-trash"></i> Excluir Rascunho
            </a>
            {% endif %}

            <a
              href="{% url 'patients:patient_events_timeline' patient_id=report.patient.pk %}"
              class="btn btn-outline-secondary"
            >
              <i class="bi bi-arrow-left"></i> Voltar
            </a>
          </div>
        </div>

        <div class="card-body">
          <!-- Patient Info -->
          <div class="row mb-4">
            <div class="col-md-6">
              <h5>Paciente</h5>
              <p><strong>{{ report.patient.name }}</strong></p>
              <p>
                Prontuário: {{ report.patient.current_record_number|default:"—"
                }}
              </p>
            </div>
            <div class="col-md-6">
              <h5>Datas</h5>
              <p>
                <strong>Admissão:</strong> {{ report.admission_date|date:"d/m/Y"
                }}
              </p>
              <p>
                <strong>Alta:</strong> {{ report.discharge_date|date:"d/m/Y" }}
              </p>
              <p>
                <strong>Permanência:</strong> {{
                report.discharge_date|timeuntil:report.admission_date }}
              </p>
            </div>
          </div>

          <!-- Medical Content -->
          <div class="row">
            <div class="col-12">
              {% if report.problems_and_diagnosis %}
              <div class="mb-3">
                <h6>Problemas e Diagnósticos</h6>
                <div class="border p-3 bg-light">
                  {{ report.problems_and_diagnosis|linebreaks }}
                </div>
              </div>
              {% endif %}

              <!-- Add other sections similarly -->
            </div>
          </div>
        </div>

        <div class="card-footer">
          <small class="text-muted">
            Criado por {{
            report.created_by.get_full_name|default:report.created_by.username
            }} em {{ report.created_at|date:"d/m/Y H:i" }} {% if
            report.updated_at != report.created_at %} • Atualizado em {{
            report.updated_at|date:"d/m/Y H:i" }} {% endif %}
          </small>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

4. UPDATE LIST TEMPLATE - ADD STATUS COLUMN:

```html
<!-- Add to dischargereport_list.html table -->
<th>Status</th>
<th>Especialidade</th>
<th>Data da Alta</th>
<th>Ações</th>

<!-- In table body -->
<td>
  <span class="{{ report.status_badge_class }}">
    {{ report.status_display }}
  </span>
</td>
<td>{{ report.medical_specialty }}</td>
<td>{{ report.discharge_date|date:"d/m/Y" }}</td>
<td>
  <div class="btn-group btn-group-sm">
    <a href="{{ report.get_absolute_url }}" class="btn btn-outline-primary">
      <i class="bi bi-eye"></i>
    </a>
    {% if report.can_be_edited_by_user:request.user %}
    <a href="{{ report.get_edit_url }}" class="btn btn-outline-warning">
      <i class="bi bi-pencil"></i>
    </a>
    {% endif %}
  </div>
</td>
```

5. ADD HELP TEXT TO FORMS:

```python
# Update DischargeReportForm widgets with better help text
'is_draft': forms.HiddenInput(),  # Hide from form, controlled by buttons
# Add help text to other fields as needed
```

6. UPDATE EVENT CARD TEMPLATE:

```html
<!-- Update apps/events/templates/events/partials/event_card_dischargereport.html -->
<!-- Add draft status indicator -->
{% if event.is_draft %}
<span class="badge bg-warning text-dark ms-2">
  <i class="bi bi-pencil-square"></i> Rascunho
</span>
{% endif %}

<!-- Update edit button logic -->
{% if event.can_be_edited_by_user:request.user %}
<a
  href="{{ event.get_edit_url }}"
  class="btn btn-outline-warning btn-sm"
  title="{% if event.is_draft %}Editar rascunho{% else %}Editar relatório{% endif %}"
>
  <i class="bi bi-pencil"></i>
</a>
{% endif %}
```

7. ADD ADMIN IMPROVEMENTS:

```python
# Update admin.py
@admin.register(DischargeReport)
class DischargeReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medical_specialty', 'admission_date', 'discharge_date', 'status_display', 'created_at']
    list_filter = ['is_draft', 'medical_specialty', 'admission_date', 'discharge_date', 'created_at']
    search_fields = ['patient__name', 'medical_specialty', 'problems_and_diagnosis']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'status_display']

    def status_display(self, obj):
        return obj.status_display
    status_display.short_description = 'Status'
```

VERIFICATION:

- Draft/finalized status displays correctly throughout UI
- Edit permissions work properly (drafts vs 24h window)
- Delete only works for drafts
- Status badges and indicators are consistent
- Admin interface shows status properly

DELIVERABLES:

- Refined draft logic and permissions
- Improved UI with status indicators
- Better permission checking
- Enhanced admin interface

```


```
