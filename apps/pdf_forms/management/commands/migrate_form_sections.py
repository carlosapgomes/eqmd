from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.pdf_forms.models import PDFFormTemplate
from apps.pdf_forms.services.section_utils import SectionUtils
import json


class Command(BaseCommand):
    """Management command to migrate existing forms to section format."""
    
    help = 'Migrate existing PDF form templates to use the new section-based configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )
        parser.add_argument(
            '--create-default-sections',
            action='store_true',
            help='Create default sections for forms that have no logical grouping'
        )
        parser.add_argument(
            '--template-id',
            type=int,
            help='Migrate only a specific template by ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even for templates that already have sections'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        create_default_sections = options['create_default_sections']
        template_id = options['template_id']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('Starting PDF form template migration to section format...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get templates to migrate
        if template_id:
            try:
                templates = [PDFFormTemplate.objects.get(id=template_id)]
                self.stdout.write(f'Migrating single template: {templates[0].name}')
            except PDFFormTemplate.DoesNotExist:
                raise CommandError(f'Template with ID {template_id} does not exist')
        else:
            templates = PDFFormTemplate.objects.all()
            self.stdout.write(f'Found {templates.count()} templates to analyze')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for template in templates:
            try:
                result = self._migrate_template(
                    template, 
                    dry_run, 
                    create_default_sections, 
                    force
                )
                
                if result == 'migrated':
                    migrated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Migrated: {template.name} (ID: {template.id})')
                    )
                elif result == 'skipped':
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'- Skipped: {template.name} (ID: {template.id})')
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error migrating {template.name} (ID: {template.id}): {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Migration Summary:'))
        self.stdout.write(f'  Migrated: {migrated_count}')
        self.stdout.write(f'  Skipped:  {skipped_count}')
        self.stdout.write(f'  Errors:   {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nThis was a dry run. Use --no-dry-run to apply changes.')
            )
        elif migrated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n{migrated_count} templates successfully migrated!')
            )

    def _migrate_template(self, template, dry_run, create_default_sections, force):
        """Migrate a single template to section format."""
        
        # Check if template already has sections
        if self._has_sections(template.form_fields) and not force:
            self._log_template_status(template, 'Already has sections')
            return 'skipped'
        
        # Check if template has no fields
        if not template.form_fields:
            self._log_template_status(template, 'No form fields')
            return 'skipped'
        
        # Check if template has new format but empty sections
        if isinstance(template.form_fields, dict) and 'fields' in template.form_fields:
            if not template.form_fields.get('fields'):
                self._log_template_status(template, 'No fields in new format')
                return 'skipped'
        
        # Perform migration
        try:
            if self._has_sections(template.form_fields):
                # Already has sections - validate and potentially update
                new_config = self._validate_and_update_sections(template.form_fields)
                migration_type = 'updated'
            else:
                # Convert old format to new format
                new_config = self._convert_to_sectioned_format(
                    template.form_fields, 
                    create_default_sections
                )
                migration_type = 'converted'
            
            if not dry_run:
                with transaction.atomic():
                    template.form_fields = new_config
                    template.save(update_fields=['form_fields'])
            
            self._log_template_migration(template, migration_type, new_config)
            return 'migrated'
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to migrate {template.name}: {str(e)}')
            )
            raise

    def _has_sections(self, form_fields):
        """Check if form fields already use section format."""
        if not isinstance(form_fields, dict):
            return False
        
        return 'sections' in form_fields and 'fields' in form_fields

    def _validate_and_update_sections(self, form_fields):
        """Validate existing sections and fix any issues."""
        new_config = form_fields.copy()
        
        # Ensure sections exist
        if 'sections' not in new_config:
            new_config['sections'] = {}
        
        # Ensure fields exist
        if 'fields' not in new_config:
            new_config['fields'] = {}
        
        # Validate section references in fields
        sections = new_config.get('sections', {})
        fields = new_config.get('fields', {})
        
        for field_name, field_config in fields.items():
            if isinstance(field_config, dict) and 'section' in field_config:
                section_ref = field_config['section']
                if section_ref and section_ref not in sections:
                    # Remove invalid section reference
                    field_config.pop('section', None)
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Removed invalid section reference "{section_ref}" from field "{field_name}"'
                        )
                    )
        
        return new_config

    def _convert_to_sectioned_format(self, form_fields, create_default_sections):
        """Convert old format to new sectioned format."""
        if create_default_sections:
            return SectionUtils.migrate_unsectioned_form(form_fields)
        else:
            # Convert to new format without creating sections
            return {
                'sections': {},
                'fields': form_fields if isinstance(form_fields, dict) else {}
            }

    def _log_template_status(self, template, status):
        """Log template status."""
        field_count = 0
        if isinstance(template.form_fields, dict):
            if 'fields' in template.form_fields:
                field_count = len(template.form_fields.get('fields', {}))
            else:
                field_count = len(template.form_fields)
        
        self.stdout.write(
            f'  {template.name} (ID: {template.id}) - {field_count} fields - {status}'
        )

    def _log_template_migration(self, template, migration_type, new_config):
        """Log migration details."""
        sections_count = len(new_config.get('sections', {}))
        fields_count = len(new_config.get('fields', {}))
        
        # Count sectioned vs unsectioned fields
        sectioned_fields = 0
        unsectioned_fields = 0
        
        for field_config in new_config.get('fields', {}).values():
            if isinstance(field_config, dict) and field_config.get('section'):
                sectioned_fields += 1
            else:
                unsectioned_fields += 1
        
        details = [
            f'{fields_count} fields',
            f'{sections_count} sections',
            f'{sectioned_fields} sectioned',
            f'{unsectioned_fields} unsectioned'
        ]
        
        self.stdout.write(
            f'  {template.name} - {migration_type} - {", ".join(details)}'
        )

    def _show_migration_preview(self, template, old_config, new_config):
        """Show preview of migration changes."""
        self.stdout.write(f'\nPreview for {template.name}:')
        self.stdout.write('  Old format:')
        
        if isinstance(old_config, dict):
            if 'fields' in old_config:
                self.stdout.write(f'    Fields: {len(old_config.get("fields", {}))}')
                self.stdout.write(f'    Sections: {len(old_config.get("sections", {}))}')
            else:
                self.stdout.write(f'    Legacy fields: {len(old_config)}')
        
        self.stdout.write('  New format:')
        self.stdout.write(f'    Fields: {len(new_config.get("fields", {}))}')
        self.stdout.write(f'    Sections: {len(new_config.get("sections", {}))}')
        
        # Show section details
        for section_key, section_config in new_config.get('sections', {}).items():
            label = section_config.get('label', section_key)
            self.stdout.write(f'      Section "{label}" ({section_key})')

    def _backup_template_config(self, template):
        """Create a backup of the original configuration."""
        backup_filename = f'template_{template.id}_backup_{template.updated.strftime("%Y%m%d_%H%M%S")}.json'
        backup_data = {
            'template_id': template.id,
            'template_name': template.name,
            'original_config': template.form_fields,
            'backup_date': template.updated.isoformat()
        }
        
        try:
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'  Backup created: {backup_filename}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  Failed to create backup: {str(e)}')
            )

    def _validate_migrated_template(self, template):
        """Validate that the migrated template is correct."""
        try:
            # Try to load the form fields as JSON
            if isinstance(template.form_fields, str):
                json.loads(template.form_fields)
            
            # Check basic structure
            if not isinstance(template.form_fields, dict):
                raise ValueError('Form fields must be a dictionary')
            
            if self._has_sections(template.form_fields):
                sections = template.form_fields.get('sections', {})
                fields = template.form_fields.get('fields', {})
                
                # Validate sections structure
                for section_key, section_config in sections.items():
                    if not isinstance(section_config, dict):
                        raise ValueError(f'Section {section_key} must be a dictionary')
                    
                    if 'label' not in section_config:
                        raise ValueError(f'Section {section_key} must have a label')
                
                # Validate field section references
                for field_name, field_config in fields.items():
                    if isinstance(field_config, dict) and 'section' in field_config:
                        section_ref = field_config['section']
                        if section_ref and section_ref not in sections:
                            raise ValueError(f'Field {field_name} references non-existent section {section_ref}')
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Validation failed for {template.name}: {str(e)}')
            )
            return False