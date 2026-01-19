from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from .models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem


class DrugTemplateForm(forms.ModelForm):
    """
    Form for creating and updating DrugTemplate instances.
    Uses Bootstrap 5.3 styling and includes custom validation.
    """

    class Meta:
        model = DrugTemplate
        fields = ['name', 'concentration', 'pharmaceutical_form', 'usage_instructions', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do medicamento (ex: Dipirona)',
                'maxlength': 200
            }),
            'concentration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Concentração (ex: 500 mg, 40 mg/mL)',
                'maxlength': 100
            }),
            'pharmaceutical_form': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Forma farmacêutica (ex: comprimido, solução injetável)',
                'maxlength': 100
            }),
            'usage_instructions': forms.Textarea(attrs={
                'class': 'form-control markdown-editor',
                'placeholder': 'Instruções detalhadas de uso (suporte a markdown)...',
                'rows': 8,
                'id': 'id_usage_instructions',
                'data-easymde': 'true'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes and help text
        self.fields['name'].help_text = 'Nome do medicamento'
        self.fields['concentration'].help_text = 'Concentração do medicamento (ex: 500 mg, 40 mg/mL)'
        self.fields['pharmaceutical_form'].help_text = 'Forma farmacêutica (ex: comprimido, solução injetável, cápsula)'
        self.fields['usage_instructions'].help_text = 'Instruções detalhadas de uso (suporte a markdown)'
        self.fields['is_public'].help_text = 'Se marcado, outros usuários poderão ver este template'
        
        # Configure field labels
        self.fields['name'].label = 'Nome do Medicamento'
        self.fields['concentration'].label = 'Concentração'
        self.fields['pharmaceutical_form'].label = 'Forma Farmacêutica'
        self.fields['usage_instructions'].label = 'Instruções de Uso'
        self.fields['is_public'].label = 'Público'

    def clean_name(self):
        """Custom validation for name field to prevent duplicates by same user."""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('Nome do medicamento é obrigatório.')
        
        name = name.strip()
        if not name:
            raise ValidationError('Nome do medicamento não pode estar vazio.')
        
        # Check for duplicates by same user (only if we have a user and this is a new instance)
        if self.user and self.instance._state.adding:
            existing = DrugTemplate.objects.filter(
                creator=self.user, 
                name__iexact=name
            ).exists()
            if existing:
                raise ValidationError(
                    f'Você já possui um template com o nome "{name}". '
                    'Escolha um nome diferente.'
                )
        
        return name

    def clean_concentration(self):
        """Custom validation for concentration field."""
        concentration = self.cleaned_data.get('concentration')
        if not concentration:
            raise ValidationError('Concentração é obrigatória.')
        
        concentration = concentration.strip()
        if not concentration:
            raise ValidationError('Concentração não pode estar vazia.')
        
        # Normalize decimal separators
        concentration = concentration.replace(',', '.')
        
        return concentration

    def clean_pharmaceutical_form(self):
        """Custom validation for pharmaceutical form field."""
        pharmaceutical_form = self.cleaned_data.get('pharmaceutical_form')
        if not pharmaceutical_form:
            raise ValidationError('Forma farmacêutica é obrigatória.')
        
        pharmaceutical_form = pharmaceutical_form.strip().lower()
        if not pharmaceutical_form:
            raise ValidationError('Forma farmacêutica não pode estar vazia.')
        
        return pharmaceutical_form

    def clean_usage_instructions(self):
        """Custom validation for usage instructions field."""
        usage_instructions = self.cleaned_data.get('usage_instructions')
        
        # Check if this is an imported drug (either existing imported instance or editing an imported one)
        is_imported = (
            (self.instance and getattr(self.instance, 'is_imported', False)) or
            self.cleaned_data.get('is_imported', False)
        )
        
        # Usage instructions are optional for imported drugs
        if is_imported:
            return usage_instructions.strip() if usage_instructions else ''
        
        # Required for user-created drugs
        if not usage_instructions:
            raise ValidationError('Instruções de uso são obrigatórias para medicamentos criados por usuários.')
        
        usage_instructions = usage_instructions.strip()
        if not usage_instructions:
            raise ValidationError('Instruções de uso não podem estar vazias.')
        
        if len(usage_instructions) < 10:
            raise ValidationError('Instruções de uso devem ter pelo menos 10 caracteres.')
        
        return usage_instructions

    def save(self, commit=True):
        """Override save to set creator field for new instances."""
        instance = super().save(commit=False)
        
        # Set creator for new instances (check if creator is not already set)
        if self.user and (not hasattr(instance, 'creator') or instance.creator is None):
            instance.creator = self.user
        
        if commit:
            instance.save()
        return instance


class PrescriptionTemplateForm(forms.ModelForm):
    """
    Form for creating and updating PrescriptionTemplate instances.
    Uses Bootstrap 5.3 styling and includes custom validation.
    """

    class Meta:
        model = PrescriptionTemplate
        fields = ['name', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do template (ex: Hipertensão - Esquema Básico)',
                'maxlength': 200
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes and help text
        self.fields['name'].help_text = 'Nome descritivo para o template de prescrição'
        self.fields['is_public'].help_text = 'Se marcado, outros usuários poderão ver este template'
        
        # Configure field labels
        self.fields['name'].label = 'Nome do Template'
        self.fields['is_public'].label = 'Público'

    def clean_name(self):
        """Custom validation for name field to prevent duplicates by same user."""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('Nome do template é obrigatório.')
        
        name = name.strip()
        if not name:
            raise ValidationError('Nome do template não pode estar vazio.')
        
        # Check for duplicates by same user (only if we have a user and this is a new instance)
        if self.user and self.instance._state.adding:
            existing = PrescriptionTemplate.objects.filter(
                creator=self.user, 
                name__iexact=name
            ).exists()
            if existing:
                raise ValidationError(
                    f'Você já possui um template com o nome "{name}". '
                    'Escolha um nome diferente.'
                )
        
        return name

    def save(self, commit=True):
        """Override save to set creator field for new instances."""
        instance = super().save(commit=False)
        
        # Set creator for new instances (check if creator is not already set)
        if self.user and (not hasattr(instance, 'creator') or instance.creator is None):
            instance.creator = self.user
        
        if commit:
            instance.save()
        return instance


class PrescriptionTemplateItemForm(forms.ModelForm):
    """
    Form for creating and updating PrescriptionTemplateItem instances.
    Uses Bootstrap 5.3 styling and includes custom validation.
    """

    class Meta:
        model = PrescriptionTemplateItem
        fields = ['drug_name', 'presentation', 'usage_instructions', 'quantity', 'order']
        widgets = {
            'drug_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do medicamento',
                'maxlength': 200
            }),
            'presentation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apresentação (ex: 500mg, comprimido)',
                'maxlength': 300
            }),
            'usage_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Instruções de uso...',
                'rows': 3
            }),
            'quantity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quantidade (ex: 30 comprimidos)',
                'maxlength': 100
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure field labels and help text
        self.fields['drug_name'].label = 'Nome do Medicamento'
        self.fields['presentation'].label = 'Apresentação'
        self.fields['usage_instructions'].label = 'Instruções de Uso'
        self.fields['quantity'].label = 'Quantidade'
        self.fields['order'].label = 'Ordem'
        
        self.fields['drug_name'].help_text = 'Nome do medicamento'
        self.fields['presentation'].help_text = 'Dosagem, forma farmacêutica, concentração'
        self.fields['usage_instructions'].help_text = 'Instruções detalhadas de uso'
        self.fields['quantity'].help_text = 'Quantidade a ser dispensada'
        self.fields['order'].help_text = 'Ordem de exibição do item no template'

    def clean_drug_name(self):
        """Custom validation for drug_name field."""
        drug_name = self.cleaned_data.get('drug_name')
        if not drug_name:
            raise ValidationError('Nome do medicamento é obrigatório.')
        
        drug_name = drug_name.strip()
        if not drug_name:
            raise ValidationError('Nome do medicamento não pode estar vazio.')
        
        return drug_name

    def clean_presentation(self):
        """Custom validation for presentation field."""
        presentation = self.cleaned_data.get('presentation')
        if not presentation:
            raise ValidationError('Apresentação é obrigatória.')
        
        presentation = presentation.strip()
        if not presentation:
            raise ValidationError('Apresentação não pode estar vazia.')
        
        return presentation

    def clean_usage_instructions(self):
        """Custom validation for usage instructions field."""
        usage_instructions = self.cleaned_data.get('usage_instructions')
        if not usage_instructions:
            raise ValidationError('Instruções de uso são obrigatórias.')
        
        usage_instructions = usage_instructions.strip()
        if not usage_instructions:
            raise ValidationError('Instruções de uso não podem estar vazias.')
        
        if len(usage_instructions) < 5:
            raise ValidationError('Instruções de uso devem ter pelo menos 5 caracteres.')
        
        return usage_instructions

    def clean_quantity(self):
        """Custom validation for quantity field."""
        quantity = self.cleaned_data.get('quantity')
        if not quantity:
            raise ValidationError('Quantidade é obrigatória.')
        
        quantity = quantity.strip()
        if not quantity:
            raise ValidationError('Quantidade não pode estar vazia.')
        
        return quantity


# Create the inline formset for PrescriptionTemplateItem
PrescriptionTemplateItemFormSet = inlineformset_factory(
    PrescriptionTemplate,
    PrescriptionTemplateItem,
    form=PrescriptionTemplateItemForm,
    fields=['drug_name', 'presentation', 'usage_instructions', 'quantity', 'order'],
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)