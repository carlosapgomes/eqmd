# Medical Specialty Implementation Options

## Requirements Summary

1. **Multi-specialty support**: Doctors and residents can have multiple specialties
2. **Admin-only management**: Only Django admin can create/modify specialties
3. **Admin-only assignment**: Only admin can assign specialties to users
4. **User self-selection**: Users can change their current/active specialty from their profile page
5. **UI display**: Show current specialty in user profile and near avatar in top-right menu

---

## Option 1: New Specialty Models with Inline Admin

### Models

Create two new models in `apps/accounts/models.py`:

```python
class MedicalSpecialty(models.Model):
    """Registry of medical specialties available in the system"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome da Especialidade",
        help_text="Ex: Cirurgia Vascular, Cirurgia Geral"
    )
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Sigla",
        help_text="Ex: CIRVASC, CIRGER"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição detalhada da especialidade"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativa",
        help_text="Se desmarcado, esta especialidade não estará disponível para seleção"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Especialidade Médica"
        verbose_name_plural = "Especialidades Médicas"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserSpecialty(models.Model):
    """Association between users and their medical specialties"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.CASCADE,
        related_name='user_specialties',
        verbose_name="Usuário"
    )
    specialty = models.ForeignKey(
        MedicalSpecialty,
        on_delete=models.PROTECT,  # Prevent deletion if assigned to users
        related_name='users',
        verbose_name="Especialidade"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Especialidade Principal",
        help_text="Marque como especialidade principal (ex: do residente)"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Atribuída em")
    assigned_by = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_specialties',
        verbose_name="Atribuída por"
    )

    class Meta:
        verbose_name = "Especialidade do Usuário"
        verbose_name_plural = "Especialidades dos Usuários"
        unique_together = ['user', 'specialty']  # One user can't have same specialty twice
        ordering = ['-is_primary', 'specialty__name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.specialty.name}"
```

### Admin Configuration (`apps/accounts/admin.py`)

```python
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'abbreviation']
    ordering = ['name']

    fieldsets = (
        (None, {'fields': ('name', 'abbreviation')}),
        ('Detalhes', {'fields': ('description', 'is_active')}),
    )


class UserSpecialtyInline(admin.TabularInline):
    model = UserSpecialty
    extra = 0
    readonly_fields = ('assigned_at',)
    fields = ('specialty', 'is_primary', 'assigned_at')


class EqmdCustomUserAdmin(UserAdmin, SimpleHistoryAdmin):
    # ... existing code ...

    inlines = (UserProfileInline, UserSpecialtyInline,)


admin.site.register(MedicalSpecialty, MedicalSpecialtyAdmin)
```

### User Model Extension

Add to `EqmdCustomUser` in `apps/accounts/models.py`:

```python
from django.db.models import Q

# In EqmdCustomUser class:
@property
def specialties(self):
    """Return all specialties assigned to this user"""
    return [us.specialty for us in self.user_specialties.filter(specialty__is_active=True)]

@property
def primary_specialty(self):
    """Return the user's primary specialty"""
    try:
        return self.user_specialties.get(is_primary=True).specialty
    except UserSpecialty.DoesNotExist:
        # Return first specialty if no primary is set
        specialties = self.specialties
        return specialties[0] if specialties else None

@property
def specialty_display(self):
    """Return display string for current/primary specialty"""
    specialty = self.primary_specialty
    return specialty.name if specialty else ""
```

### UserProfile Extension

Add to `UserProfile` in `apps/accounts/models.py`:

```python
# Add field for user-selected current specialty
current_specialty = models.ForeignKey(
    'MedicalSpecialty',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='current_users',
    verbose_name="Especialidade Atual",
    help_text="Especialidade selecionada pelo usuário para uso atual"
)

# Add property
@property
def current_specialty_display(self):
    """Return display name of current specialty"""
    if self.current_specialty:
        return self.current_specialty.name
    return self.user.specialty_display
```

### Profile Update Form

Modify `apps/accounts/forms.py`:

```python
class UserProfileForm(forms.ModelForm):
    error_css_class = "is-invalid"
    required_css_class = "required"

    class Meta:
        model = UserProfile
        fields = ("display_name", "bio", "current_specialty")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get user from instance
        user = kwargs.get('instance', None)
        if user and user.user:
            # Filter specialties to only those assigned to this user
            assigned_specialty_ids = user.user.user_specialties.filter(
                specialty__is_active=True
            ).values_list('specialty_id', flat=True)

            self.fields['current_specialty'].queryset = (
                MedicalSpecialty.objects.filter(
                    id__in=assigned_specialty_ids
                ).order_by('name')
            )
            self.fields['current_specialty'].empty_label = "Selecionar especialidade..."

        # Apply Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name != 'current_specialty':
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-select'})
```

### Profile Template

Modify `apps/accounts/templates/accounts/profile.html`:

```html
{% extends "base_app.html" %} {% block app_content %}
<div class="container mt-4">
  <div class="row">
    <div class="col-md-8 offset-md-2">
      <div class="card">
        <div class="card-header">
          <h2>{{ profile.full_name }}</h2>
          {% if profile.display_name %}
          <p class="text-muted">{{ profile.display_name }}</p>
          {% endif %}
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col-md-4 fw-bold">Email:</div>
            <div class="col-md-8">{{ profile.email }}</div>
          </div>

          {% if profile.profession %}
          <div class="row mb-3">
            <div class="col-md-4 fw-bold">Profissão:</div>
            <div class="col-md-8">{{ profile.profession }}</div>
          </div>
          {% endif %} {% if profile.current_specialty_display %}
          <div class="row mb-3">
            <div class="col-md-4 fw-bold">Especialidade Atual:</div>
            <div class="col-md-8">
              <span class="badge bg-medical-primary">
                <i class="bi bi-stethoscope me-1"></i>
                {{ profile.current_specialty_display }}
              </span>
            </div>
          </div>
          {% endif %} {% if user.specialties %}
          <div class="row mb-3">
            <div class="col-md-4 fw-bold">Especialidades Registradas:</div>
            <div class="col-md-8">
              {% for specialty in user.specialties %}
              <span
                class="badge {% if specialty == user.primary_specialty %}bg-success{% else %}bg-secondary{% endif %} me-1"
              >
                {% if specialty == user.primary_specialty %}<i
                  class="bi bi-star-fill me-1"
                ></i
                >{% endif %} {{ specialty.name }}
              </span>
              {% endfor %}
            </div>
          </div>
          {% endif %} {% if profile.bio %}
          <div class="row mb-3">
            <div class="col-md-4 fw-bold">Bio:</div>
            <div class="col-md-8">{{ profile.bio }}</div>
          </div>
          {% endif %} {% if is_owner %}
          <div class="mt-4">
            <a
              href="{% url 'apps.accounts:profile_update' public_id=profile.public_id %}"
              class="btn btn-medical-primary me-2"
            >
              <i class="bi bi-pencil-square"></i> Edit Profile
            </a>
            <a
              href="{% url 'account_change_password' %}"
              class="btn btn-medical-outline-primary"
            >
              <i class="bi bi-lock"></i> Change Password
            </a>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock app_content %}
```

### Avatar Dropdown Enhancement

Modify `templates/base_app.html`:

```html
<!-- User Avatar Dropdown -->
<div class="dropdown">
  <button
    class="btn btn-link text-medical-gray d-flex align-items-center"
    type="button"
    data-bs-toggle="dropdown"
    aria-expanded="false"
  >
    <div
      class="bg-medical-teal rounded-circle d-flex align-items-center justify-content-center me-2"
      style="width: 32px; height: 32px;"
    >
      <i class="bi bi-person-fill text-white"></i>
    </div>
    <div class="d-none d-md-inline text-medical-dark-gray text-start">
      {% if user.profile.display_name %}
      <div>{{ user.profile.display_name }}</div>
      {% else %}
      <div>{{ user.get_full_name|default:user.username }}</div>
      {% endif %} {% if user.profile.current_specialty_display %}
      <small class="text-muted d-block">
        <i class="bi bi-stethoscope me-1"></i>{{
        user.profile.current_specialty_display }}
      </small>
      {% elif user.profession %}
      <small class="text-muted d-block">{{ user.profession }}</small>
      {% endif %}
    </div>
    <i class="bi bi-chevron-down ms-1"></i>
  </button>
  <ul class="dropdown-menu dropdown-menu-end" style="min-width: 250px;">
    <li>
      <div class="px-3 py-2">
        <strong>{{ user.get_full_name|default:user.username }}</strong>
        {% if user.profile.current_specialty_display %}
        <div class="small text-muted">
          <i class="bi bi-stethoscope me-1"></i>{{
          user.profile.current_specialty_display }}
        </div>
        {% endif %}
      </div>
    </li>
    <li><hr class="dropdown-divider" /></li>
    <li>
      <a class="dropdown-item" href="{% url 'apps.accounts:profile_redirect' %}"
        ><i class="bi bi-person me-2"></i>Meu Perfil</a
      >
    </li>
    {% if user.specialties|length > 1 %}
    <li><hr class="dropdown-divider" /></li>
    <li><h6 class="dropdown-header">Trocar Especialidade</h6></li>
    {% for specialty in user.specialties %}
    <li>
      <button
        class="dropdown-item {% if specialty == user.profile.current_specialty %}active{% endif %}"
        onclick="changeSpecialty('{{ specialty.id }}')"
      >
        {% if specialty == user.primary_specialty %}<i
          class="bi bi-star-fill me-2 text-warning"
        ></i
        >{% endif %} {{ specialty.name }} {% if specialty ==
        user.profile.current_specialty %}<i class="bi bi-check float-end"></i>{%
        endif %}
      </button>
    </li>
    {% endfor %}
    <li><hr class="dropdown-divider" /></li>
    {% endif %}
    <li>
      <a class="dropdown-item" href="{% url 'account_logout' %}"
        ><i class="bi bi-box-arrow-right me-2"></i>Sair</a
      >
    </li>
  </ul>
</div>
```

With JavaScript:

```javascript
<script>
function changeSpecialty(specialtyId) {
  fetch('/accounts/api/change-specialty/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ specialty_id: specialtyId })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      location.reload();
    } else {
      alert('Erro ao alterar especialidade: ' + data.error);
    }
  });
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}
</script>
```

### Pros

- ✅ Clean separation of concerns (specialty registry separate from users)
- ✅ Flexible - easy to add/remove specialties
- ✅ Tracks who assigned specialties (audit trail)
- ✅ Can mark primary specialty (important for residents)
- ✅ Inline admin makes assignment easy for admins
- ✅ Soft delete with `is_active` flag

### Cons

- ⚠️ Requires 2 new models and migrations
- ⚠️ Extra queries for `specialties` property
- ⚠️ More complex than single field solution

---

## Option 2: JSONField for Specialties

### Models

```python
class MedicalSpecialty(models.Model):
    """Registry of medical specialties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    # ... other fields ...

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    specialty_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Especialidades",
        help_text="List of specialty IDs assigned to this user"
    )
    primary_specialty_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Especialidade Principal"
    )

    @property
    def specialties(self):
        if not self.specialty_ids:
            return []
        ids = [uuid.UUID(sid) for sid in self.specialty_ids if sid]
        return list(MedicalSpecialty.objects.filter(id__in=ids, is_active=True))

    @property
    def primary_specialty(self):
        if not self.primary_specialty_id:
            return None
        try:
            return MedicalSpecialty.objects.get(id=self.primary_specialty_id, is_active=True)
        except MedicalSpecialty.DoesNotExist:
            return None
```

### UserProfile Extension

```python
class UserProfile(models.Model):
    # ... existing fields ...

    current_specialty_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Especialidade Atual"
    )

    @property
    def current_specialty(self):
        if not self.current_specialty_id:
            return None
        try:
            return MedicalSpecialty.objects.get(id=self.current_specialty_id, is_active=True)
        except MedicalSpecialty.DoesNotExist:
            return None

    @property
    def current_specialty_display(self):
        specialty = self.current_specialty
        return specialty.name if specialty else ""
```

### Pros

- ✅ Simpler than Option 1 (only one new model + field on user)
- ✅ Flexible - easy to add/remove specialties

### Cons

- ❌ No foreign key constraints (data integrity issues)
- ❌ No audit trail for assignments
- ❌ Harder to query/filter by specialty
- ❌ No admin inline integration
- ❌ JSON field is opaque to Django ORM

---

## Option 3: Single Model with Through Model (ManyToMany)

### Models

```python
class MedicalSpecialty(models.Model):
    """Registry of medical specialties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    # ... other fields ...

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    specialties = models.ManyToManyField(
        MedicalSpecialty,
        through='UserSpecialty',
        related_name='users',
        verbose_name="Especialidades"
    )
    primary_specialty = models.ForeignKey(
        MedicalSpecialty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_users',
        verbose_name="Especialidade Principal"
    )


class UserSpecialty(models.Model):
    """Through model for user-specialty relationship"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(EqmdCustomUser, on_delete=models.CASCADE)
    specialty = models.ForeignKey(MedicalSpecialty, on_delete=models.PROTECT)
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        EqmdCustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_specialties'
    )

    class Meta:
        unique_together = ['user', 'specialty']
        ordering = ['-is_primary', 'specialty__name']
```

### Pros

- ✅ Django's standard pattern for M2M with extra data
- ✅ Clean M2M queries: `user.specialties.all()`
- ✅ Audit trail via through model
- ✅ Foreign key constraints

### Cons

- ⚠️ Same complexity as Option 1 (2-3 new models)
- ⚠️ Requires managing both M2M and primary specialty FK

---

## Option 4: New Medical App for Specialties

### Alternative Location

Instead of adding to `apps/accounts/`, create new app:

```
apps/
  ├── accounts/          # Existing user models
  └── medical/         # NEW: Medical-related models
      ├── __init__.py
      ├── models.py      # MedicalSpecialty, UserSpecialty
      ├── admin.py
      └── migrations/
```

### Directory Structure

```
apps/
  ├── accounts/          # User authentication and profiles
  ├── medical/           # Medical registries (NEW)
  │   ├── models.py      # MedicalSpecialty, MedicalCouncil, HospitalWard
  │   ├── admin.py
  │   └── migrations/
  └── patients/          # Patient management
```

### Pros

- ✅ Better organization (separation of concerns)
- ✅ Future-proof (can add more medical-related models)
- ✅ Doesn't clutter accounts app

### Cons

- ⚠️ New app to maintain
- ⚠️ May need circular import handling (if accounts needs medical)

---

## Option 5: Single StringField for User + Specialty Registry

### Models

```python
class MedicalSpecialty(models.Model):
    """Registry of medical specialties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    # ... other fields ...

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    specialty_ids_csv = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Especialidades",
        help_text="Comma-separated specialty IDs"
    )
    primary_specialty = models.ForeignKey(
        MedicalSpecialty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    @property
    def specialties(self):
        if not self.specialty_ids_csv:
            return []
        try:
            ids = [uuid.UUID(sid.strip()) for sid in self.specialty_ids_csv.split(',') if sid.strip()]
            return list(MedicalSpecialty.objects.filter(id__in=ids, is_active=True))
        except (ValueError, AttributeError):
            return []
```

### Pros

- ✅ Very simple (just a string field)

### Cons

- ❌ No foreign key constraints
- ❌ Manual parsing required
- ❌ Not query-friendly
- ❌ Hard to validate

---

## Comparison Table

| Feature        | Option 1 (Separate Models) | Option 2 (JSONField) | Option 3 (M2M Through) | Option 4 (New App) | Option 5 (String) |
| -------------- | -------------------------- | -------------------- | ---------------------- | ------------------ | ----------------- |
| Data Integrity | ✅ Excellent               | ❌ Poor              | ✅ Excellent           | ✅ Excellent       | ❌ Poor           |
| Audit Trail    | ✅ Yes                     | ❌ No                | ✅ Yes                 | ✅ Yes             | ❌ No             |
| Admin UX       | ✅ Inline                  | ⚠️ Separate          | ✅ Inline              | ✅ Inline          | ⚠️ Separate       |
| Queryability   | ✅ Excellent               | ⚠️ Difficult         | ✅ Excellent           | ✅ Excellent       | ❌ Poor           |
| Complexity     | ⚠️ Medium                  | ✅ Low               | ⚠️ Medium              | ⚠️ Medium          | ✅ Low            |
| Maintenance    | ⚠️ Medium                  | ⚠️ Medium            | ⚠️ Medium              | ⚠️ High            | ✅ Low            |
| Scalability    | ✅ High                    | ✅ High              | ✅ High                | ✅ High            | ❌ Low            |
| Django Pattern | ✅ Standard                | ❌ Non-standard      | ✅ Standard            | ✅ Standard        | ❌ Non-standard   |

---

## Recommendation: Option 1 (Separate Models)

This is the **best balance** of:

### Why Option 1 is Recommended

1. ✅ **Data Integrity** - Foreign key constraints prevent invalid data
2. ✅ **Audit Trail** - Tracks who assigned what and when
3. ✅ **Admin UX** - Inline editing in user admin
4. ✅ **Queryability** - Easy to filter/report by specialty
5. ✅ **Flexibility** - Can add more fields later (certifications, etc.)
6. ✅ **Standards** - Follows Django best practices
7. ✅ **Separation** - Clear distinction between registry and user assignments

### Implementation Summary

**New Models:**

1. `MedicalSpecialty` - Registry of specialties (admin-managed)
2. `UserSpecialty` - Assignment of specialties to users (admin-managed)

**Modified Models:**

1. `EqmdCustomUser` - Add properties for specialty access
2. `UserProfile` - Add `current_specialty` FK for user selection

**Admin:**

1. `MedicalSpecialtyAdmin` - CRUD for specialties
2. `UserSpecialtyInline` - Assign specialties in user admin

**User-Facing:**

1. Profile update form - Dropdown to change current specialty
2. Profile display - Show all specialties with primary marked
3. Avatar dropdown - Show current specialty, quick switch option
4. AJAX endpoint - Change specialty without page reload

---

## Implementation Steps

### Step 1: Create Models and Migration

Create `apps/accounts/migrations/0002_add_medical_specialty_models.py` with:

- `MedicalSpecialty` model creation
- `UserSpecialty` model creation
- Unique constraint on user+specialty

### Step 2: Add Current Specialty to UserProfile

Create `apps/accounts/migrations/0003_add_current_specialty_to_profile.py`:

- Add `current_specialty` ForeignKey to `UserProfile`

### Step 3: Update Admin

Modify `apps/accounts/admin.py`:

- Add `MedicalSpecialtyAdmin`
- Add `UserSpecialtyInline` to `EqmdCustomUserAdmin`

### Step 4: Update Models

Modify `apps/accounts/models.py`:

- Add `MedicalSpecialty` and `UserSpecialty` models
- Add `specialties` and `primary_specialty` properties to `EqmdCustomUser`
- Add `current_specialty` field and `current_specialty_display` property to `UserProfile`

### Step 5: Update Forms

Modify `apps/accounts/forms.py`:

- Filter `current_specialty` queryset to user's assigned specialties

### Step 6: Update Templates

Modify:

- `apps/accounts/templates/accounts/profile.html` - Show specialties
- `templates/base_app.html` - Show current specialty in avatar dropdown

### Step 7: Add AJAX Endpoint

Add to `apps/accounts/urls.py`:

```python
path('api/change-specialty/', views.change_specialty_api, name='change_specialty_api'),
```

Add to `apps/accounts/views.py`:

```python
@login_required
@require_http_methods(["POST"])
def change_specialty_api(request):
    specialty_id = request.POST.get('specialty_id')
    try:
        specialty_id = uuid.UUID(specialty_id)
    except (ValueError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid specialty ID'}, status=400)

    # Verify user has this specialty
    if not request.user.user_specialties.filter(
        specialty_id=specialty_id,
        specialty__is_active=True
    ).exists():
        return JsonResponse({'success': False, 'error': 'Specialty not assigned to user'}, status=403)

    # Update current specialty
    request.user.profile.current_specialty_id = specialty_id
    request.user.profile.save()

    return JsonResponse({'success': True})
```

### Step 8: Populate Sample Data

Create `apps/accounts/migrations/0004_populate_sample_specialties.py`:

- Add common specialties (Cirurgia Geral, Cirurgia Vascular, Cardiologia, etc.)

---

## Sample Data

Suggested specialties to include:

```python
specialties = [
    ('Cirurgia Geral', 'CIRGER', 'General surgery'),
    ('Cirurgia Vascular', 'CIRVASC', 'Vascular surgery'),
    ('Cirurgia Cardíaca', 'CIRCARD', 'Cardiac surgery'),
    ('Cirurgia Torácica', 'CIRTORAC', 'Thoracic surgery'),
    ('Cardiologia', 'CARDIO', 'Medical cardiology'),
    ('Pediatria', 'PED', 'Pediatrics'),
    ('Ortopedia', 'ORTO', 'Orthopedics'),
    ('Ginecologia e Obstetrícia', 'GO', 'Gynecology and obstetrics'),
    ('Clínica Médica', 'CLIN', 'Internal medicine'),
    ('Emergência', 'EMERG', 'Emergency medicine'),
    ('UTI Adulto', 'UTI', 'Intensive care - Adult'),
    ('UTI Pediátrica', 'UTIPED', 'Intensive care - Pediatric'),
    ('Otorrinolaringologia', 'ORL', 'ENT (Otolaryngology)'),
    ('Oftalmologia', 'OFTALMO', 'Ophthalmology'),
    ('Dermatologia', 'DERM', 'Dermatology'),
    ('Neurologia', 'NEURO', 'Neurology'),
    ('Psiquiatria', 'PSIQ', 'Psychiatry'),
    ('Infectologia', 'INFECTO', 'Infectious diseases'),
    ('Endocrinologia', 'ENDO', 'Endocrinology'),
    ('Nefrologia', 'NEFRO', 'Nephrology'),
    ('Gastroenterologia', 'GASTRO', 'Gastroenterology'),
    ('Pneumologia', 'PNEUMO', 'Pulmonology'),
    ('Reumatologia', 'REUMA', 'Rheumatology'),
    ('Urologia', 'URO', 'Urology'),
    ('Anestesiologia', 'ANEST', 'Anesthesiology'),
    ('Radiologia', 'RADIO', 'Radiology'),
]
```

---

## Additional Considerations

### Permission Enforcement

Consider adding permission checks:

- Only doctors and residents can have specialties assigned
- Validate profession_type before specialty assignment in admin

### Specialty-Based Filtering

Future enhancements could include:

- Filter patients by treating specialty
- Filter events by creator's specialty
- Specialty-specific dashboards
- Specialty-specific templates

### Professional Registration Tracking

Consider adding to `UserSpecialty`:

```python
registration_number = models.CharField(
    max_length=20,
    blank=True,
    verbose_name="Número de Registro",
    help_text="Ex: CRM-12345, RQE-9876"
)
council_type = models.CharField(
    max_length=10,
    blank=True,
    choices=[
        ('CRM', 'Conselho Regional de Medicina'),
        ('RQE', 'Registro de Qualificação de Especialidade'),
        ('COREN', 'Conselho Regional de Enfermagem'),
    ],
    verbose_name="Tipo de Conselho"
)
```

This allows tracking:

- Main specialty with CRM number
- Additional specialties with RQE numbers

---

## Summary

**Recommended:** Option 1 (Separate Models)

**Key Features:**

- ✅ Two new models: `MedicalSpecialty` and `UserSpecialty`
- ✅ Inline admin for easy assignment
- ✅ Audit trail (who assigned what, when)
- ✅ Users can change current specialty from profile
- ✅ Current specialty shown in avatar dropdown
- ✅ Primary specialty marking (important for residents)
- ✅ Follows Django best practices
- ✅ Scalable for future enhancements

**Implementation Effort:** Medium (2-3 days for full implementation including UI)
