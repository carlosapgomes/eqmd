import uuid
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError


class DrugTemplate(models.Model):
    """
    Drug template model to store commonly used drug information.
    Users can create private templates or share public ones.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome do Medicamento")
    presentation = models.CharField(max_length=300, verbose_name="Apresentação")
    usage_instructions = models.TextField(
        verbose_name="Instruções de Uso",
        help_text="Instruções detalhadas de uso (suporte a markdown)"
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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('drugtemplates:detail', kwargs={'pk': self.pk})

    def clean(self):
        """Validate model fields"""
        super().clean()
        
        # Validate name is not empty after stripping whitespace
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Nome do medicamento é obrigatório.'})
        
        # Validate presentation is not empty after stripping whitespace
        if not self.presentation or not self.presentation.strip():
            raise ValidationError({'presentation': 'Apresentação é obrigatória.'})
        
        # Validate usage instructions are not empty after stripping whitespace
        if not self.usage_instructions or not self.usage_instructions.strip():
            raise ValidationError({'usage_instructions': 'Instruções de uso são obrigatórias.'})

    class Meta:
        ordering = ['name']
        verbose_name = "Template de Medicamento"
        verbose_name_plural = "Templates de Medicamentos"
        indexes = [
            models.Index(fields=['name'], name='drugtemplates_name_idx'),
            models.Index(fields=['creator'], name='drugtemplates_creator_idx'),
            models.Index(fields=['is_public'], name='drugtemplates_is_public_idx'),
            models.Index(fields=['created_at'], name='drugtemplates_created_at_idx'),
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
