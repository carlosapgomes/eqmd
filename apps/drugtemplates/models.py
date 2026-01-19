import uuid
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError


class DrugTemplateManager(models.Manager):
    """Custom manager for DrugTemplate with source filtering methods."""
    
    def user_created(self):
        """Return templates created by users (not imported)."""
        return self.filter(is_imported=False)
    
    def imported(self):
        """Return imported templates."""
        return self.filter(is_imported=True)
    
    def from_source(self, source):
        """Return templates from a specific import source."""
        return self.filter(import_source=source, is_imported=True)


class DrugTemplate(models.Model):
    """
    Drug template model to store commonly used drug information.
    Users can create private templates or share public ones.
    
    Supports both user-created templates and imported reference medications
    with separate concentration and pharmaceutical form fields.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome do Medicamento")
    
    # New separate fields for better structured data
    concentration = models.CharField(
        max_length=200,  # Increased for complex concentrations
        verbose_name="Concentração",
        help_text="Concentração do medicamento (ex: 500 mg, 40 mg/mL)",
        default="",  # Temporary default for migration
        blank=True
    )
    pharmaceutical_form = models.CharField(
        max_length=200,  # Increased for complex forms
        verbose_name="Forma Farmacêutica", 
        help_text="Forma farmacêutica (ex: comprimido, solução injetável, cápsula)",
        default="",  # Temporary default for migration
        blank=True
    )
    
    # Legacy presentation field removed - now computed property
    
    usage_instructions = models.TextField(
        verbose_name="Instruções de Uso",
        help_text="Instruções detalhadas de uso (suporte a markdown)",
        blank=True,  # Made optional for imported drugs
        null=True
    )
    
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="drug_templates",
        verbose_name="Criado por"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Público",
        help_text="Se marcado, outros usuários poderão ver este template"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Contador de Uso",
        help_text="Número de vezes que este template foi utilizado em prescrições"
    )
    
    # Import tracking fields
    is_imported = models.BooleanField(
        default=False,
        verbose_name="Importado",
        help_text="True se o medicamento foi importado de fonte externa"
    )
    import_source = models.CharField(
        max_length=200,
        verbose_name="Fonte de Importação",
        help_text="Fonte da importação (ex: MERGED_medications.csv)",
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    objects = DrugTemplateManager()

    @property
    def presentation(self):
        """
        Computed presentation field for backward compatibility.
        Combines concentration and pharmaceutical form.
        """
        if self.concentration and self.pharmaceutical_form:
            return f"{self.concentration} {self.pharmaceutical_form}"
        elif self.concentration:
            return self.concentration
        elif self.pharmaceutical_form:
            return self.pharmaceutical_form
        return ""

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('drugtemplates:detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Save the drug template."""
        super().save(*args, **kwargs)

    def clean(self):
        """Validate model fields"""
        super().clean()
        
        # Validate name is not empty after stripping whitespace
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Nome do medicamento é obrigatório.'})
        
        # Validate concentration is not empty after stripping whitespace (skip during migration)
        if not getattr(self, '_skip_validation', False):
            if not self.concentration or not self.concentration.strip():
                raise ValidationError({'concentration': 'Concentração é obrigatória.'})
        
        # Validate pharmaceutical form is not empty after stripping whitespace (skip during migration)
        if not getattr(self, '_skip_validation', False):
            if not self.pharmaceutical_form or not self.pharmaceutical_form.strip():
                raise ValidationError({'pharmaceutical_form': 'Forma farmacêutica é obrigatória.'})
        
        # Validate usage instructions for user-created templates only
        if not self.is_imported:
            if not self.usage_instructions or not self.usage_instructions.strip():
                raise ValidationError({'usage_instructions': 'Instruções de uso são obrigatórias para templates criados por usuário.'})

    class Meta:
        ordering = ['name']
        verbose_name = "Template de Medicamento"
        verbose_name_plural = "Templates de Medicamentos"
        indexes = [
            models.Index(fields=['name'], name='drugtpl_name_idx'),
            models.Index(fields=['creator'], name='drugtpl_creator_idx'),
            models.Index(fields=['is_public'], name='drugtpl_public_idx'),
            models.Index(fields=['created_at'], name='drugtpl_created_idx'),
            # New indexes for refactored fields
            models.Index(fields=['concentration'], name='drugtpl_conc_idx'),
            models.Index(fields=['pharmaceutical_form'], name='drugtpl_form_idx'),
            models.Index(fields=['is_imported'], name='drugtpl_imported_idx'),
            models.Index(fields=['import_source'], name='drugtpl_source_idx'),
            # Composite indexes for common queries
            models.Index(fields=['is_imported', 'name'], name='drugtpl_imp_name_idx'),
            models.Index(fields=['name', 'concentration'], name='drugtpl_name_conc_idx'),
        ]


class PrescriptionTemplate(models.Model):
    """
    Prescription template model to store reusable prescription templates.
    Users can create private templates or share public ones.
    Each template can contain multiple prescription items.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200, 
        verbose_name="Nome do Template",
        help_text="Nome descritivo para o template de prescrição"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="prescription_templates",
        verbose_name="Criado por"
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Público",
        help_text="Se marcado, outros usuários poderão ver este template"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('drugtemplates:prescription_detail', kwargs={'pk': self.pk})

    def clean(self):
        """Validate model fields"""
        super().clean()
        
        # Validate name is not empty after stripping whitespace
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Nome do template é obrigatório.'})

    class Meta:
        ordering = ['name']
        verbose_name = "Template de Prescrição"
        verbose_name_plural = "Templates de Prescrições"
        indexes = [
            models.Index(fields=['name'], name='presc_tmpl_name_idx'),
            models.Index(fields=['creator'], name='presc_tmpl_creator_idx'),
            models.Index(fields=['is_public'], name='presc_tmpl_public_idx'),
            models.Index(fields=['created_at'], name='presc_tmpl_created_idx'),
        ]


class PrescriptionTemplateItem(models.Model):
    """
    Individual prescription item within a prescription template.
    Each item represents a medication with its specific instructions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Template"
    )
    drug_name = models.CharField(
        max_length=200, 
        verbose_name="Nome do Medicamento"
    )
    presentation = models.CharField(
        max_length=300, 
        verbose_name="Apresentação",
        help_text="Dosagem, forma farmacêutica, concentração"
    )
    usage_instructions = models.TextField(
        verbose_name="Instruções de Uso",
        help_text="Instruções detalhadas de uso"
    )
    quantity = models.CharField(
        max_length=100,
        verbose_name="Quantidade",
        help_text="Quantidade a ser dispensada"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Ordem de exibição do item no template"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return f"{self.drug_name} - {self.presentation}"

    def clean(self):
        """Validate model fields"""
        super().clean()
        
        # Validate drug_name is not empty after stripping whitespace
        if not self.drug_name or not self.drug_name.strip():
            raise ValidationError({'drug_name': 'Nome do medicamento é obrigatório.'})
        
        # Validate presentation is not empty after stripping whitespace
        if not self.presentation or not self.presentation.strip():
            raise ValidationError({'presentation': 'Apresentação é obrigatória.'})
        
        # Validate usage instructions are not empty after stripping whitespace
        if not self.usage_instructions or not self.usage_instructions.strip():
            raise ValidationError({'usage_instructions': 'Instruções de uso são obrigatórias.'})
        
        # Validate quantity is not empty after stripping whitespace
        if not self.quantity or not self.quantity.strip():
            raise ValidationError({'quantity': 'Quantidade é obrigatória.'})

    class Meta:
        ordering = ['template', 'order', 'drug_name']
        verbose_name = "Item do Template de Prescrição"
        verbose_name_plural = "Itens dos Templates de Prescrições"
        indexes = [
            models.Index(fields=['template'], name='presc_item_tmpl_idx'),
            models.Index(fields=['drug_name'], name='presc_item_drug_idx'),
            models.Index(fields=['order'], name='presc_item_order_idx'),
        ]
