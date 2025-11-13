import re
import os
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMessage
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient


class Command(BaseCommand):
    help = 'Export all dailynotes for a patient to markdown format for LLM processing'

    def add_arguments(self, parser):
        # Patient identification (mutually exclusive)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--patient-id',
            type=str,
            help='Patient UUID to export notes for (internal use only)'
        )
        group.add_argument(
            '--record-number',
            type=str,
            help='Patient medical record number (e.g., PRN524600) - RECOMMENDED'
        )
        group.add_argument(
            '--patient-name',
            type=str,
            help='Patient name (partial match supported, e.g., "João Vitor")'
        )
        
        # Output options (mutually exclusive)
        output_group = parser.add_mutually_exclusive_group()
        output_group.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout if no email specified)'
        )
        output_group.add_argument(
            '--email',
            type=str,
            help='Send export as email attachment to this address'
        )
        
        # Anonymization options
        parser.add_argument(
            '--anonymize-staff',
            action='store_true',
            help='Replace staff names with generic roles (Doctor, Nurse, etc.)'
        )
        parser.add_argument(
            '--anonymize-content',
            action='store_true',
            help='Attempt to remove personal identifiers from note content'
        )
        parser.add_argument(
            '--include-metadata',
            action='store_true',
            help='Include creation timestamps and edit history'
        )

    def handle(self, *args, **options):
        try:
            # Validate email if provided
            if options['email']:
                try:
                    validate_email(options['email'])
                except ValidationError:
                    raise CommandError(f'Invalid email address: {options["email"]}')
            
            # Find patient
            patient = self._get_patient(options)
            
            # Get all dailynotes for the patient
            dailynotes = DailyNote.objects.filter(
                patient=patient
            ).order_by('event_datetime').select_related('created_by', 'updated_by')
            
            if not dailynotes.exists():
                raise CommandError('No dailynotes found for the specified patient')
            
            # Generate markdown content
            markdown_content = self._generate_markdown(
                patient, dailynotes, options
            )
            
            # Output based on options
            if options['email']:
                self._send_email(markdown_content, options['email'], dailynotes.count())
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully emailed {dailynotes.count()} notes to {options["email"]}'
                    )
                )
            else:
                output_file = options.get('output') or '-'
                self._write_output(markdown_content, output_file)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully exported {dailynotes.count()} notes'
                    )
                )
            
        except Exception as e:
            raise CommandError(f'Error exporting notes: {str(e)}')

    def _get_patient(self, options):
        """Find patient by ID, record number, or name"""
        try:
            if options['patient_id']:
                return Patient.objects.get(id=options['patient_id'])
            elif options['record_number']:
                # Find by current record number
                patient = Patient.objects.filter(
                    record_numbers__record_number=options['record_number'],
                    record_numbers__is_current=True
                ).first()
                if not patient:
                    raise Patient.DoesNotExist()
                return patient
            elif options['patient_name']:
                # Find by name (partial match, case insensitive)
                patients = Patient.objects.filter(
                    name__icontains=options['patient_name']
                )
                
                if not patients.exists():
                    raise Patient.DoesNotExist()
                elif patients.count() == 1:
                    return patients.first()
                else:
                    # Multiple matches - show options
                    self.stdout.write(self.style.WARNING(
                        f"Multiple patients found for '{options['patient_name']}':"
                    ))
                    for p in patients[:10]:  # Show max 10 matches
                        record = p.record_numbers.filter(is_current=True).first()
                        record_num = record.record_number if record else 'No record'
                        self.stdout.write(f"  - {p.name} (Record: {record_num})")
                    
                    raise CommandError(
                        "Multiple patients found. Please use --record-number for exact match."
                    )
        except Patient.DoesNotExist:
            identifier = (options.get('patient_id') or 
                         options.get('record_number') or 
                         options.get('patient_name'))
            raise CommandError(f'Patient not found: {identifier}')

    def _generate_markdown(self, patient, dailynotes, options):
        """Generate markdown content from dailynotes"""
        lines = []
        
        # Header - Never include patient name (PII)
        export_date = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        
        lines.extend([
            f"# Exportação de Evoluções - Paciente",
            f"**Data da Exportação:** {export_date}",
            f"**Total de Evoluções:** {dailynotes.count()}",
            "",
            "---",
            ""
        ])
        
        # Process each note
        for note in dailynotes:
            lines.extend(self._format_note(note, options))
            lines.append("")  # Add spacing between notes
        
        return "\n".join(lines)

    def _format_note(self, note, options):
        """Format a single dailynote as markdown"""
        lines = []
        
        # Note header with date
        date_str = note.event_datetime.strftime('%d/%m/%Y %H:%M')
        lines.append(f"## {date_str}")
        
        # Author information
        if options['anonymize_staff']:
            author = self._anonymize_author(note.created_by)
        else:
            author = note.created_by.get_full_name() or note.created_by.username
        
        lines.append(f"**Autor:** {author}")
        
        # Metadata if requested
        if options['include_metadata']:
            lines.extend([
                f"**Criado em:** {note.created_at.strftime('%d/%m/%Y %H:%M:%S')}",
                f"**Atualizado em:** {note.updated_at.strftime('%d/%m/%Y %H:%M:%S')}",
            ])
            if note.updated_by != note.created_by:
                updated_by = self._anonymize_author(note.updated_by) if options['anonymize_staff'] else note.updated_by.get_full_name()
                lines.append(f"**Atualizado por:** {updated_by}")
        
        lines.append("")  # Empty line before content
        
        # Note content
        content = note.content
        if options['anonymize_content']:
            content = self._anonymize_content(content)
        
        lines.append(content)
        
        return lines

    def _anonymize_author(self, user):
        """Convert user to generic role based on user type"""
        # Map user roles to generic titles in Portuguese
        role_mapping = {
            'doctor': 'Médico',
            'resident': 'Residente', 
            'nurse': 'Enfermeiro',
            'physiotherapist': 'Fisioterapeuta',
            'student': 'Estudante',
        }
        
        # Get user profession if available
        if hasattr(user, 'profession'):
            return role_mapping.get(user.profession, 'Profissional de Saúde')
        
        # Fallback to generic title
        return 'Profissional de Saúde'

    def _anonymize_content(self, content):
        """Remove or replace personal identifiers in content"""
        if not content:
            return content
        
        # Common patterns to anonymize (basic implementation)
        anonymized = content
        
        # Remove potential names (sequences of capitalized words)
        anonymized = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NOME]', anonymized)
        
        # Remove phone numbers
        anonymized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[TELEFONE]', anonymized)
        
        # Remove potential CPF/medical record numbers (sequences of digits)
        anonymized = re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '[DOCUMENTO]', anonymized)
        
        # Remove email addresses
        anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', anonymized)
        
        return anonymized

    def _write_output(self, content, output_path):
        """Write content to file or stdout"""
        if output_path == '-':
            self.stdout.write(content)
        else:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except IOError as e:
                raise CommandError(f'Could not write to file {output_path}: {str(e)}')

    def _send_email(self, content, email_address, note_count):
        """Send markdown content as email attachment"""
        try:
            # Create temporary file with the content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Generate filename with timestamp
            timestamp = timezone.now().strftime('%d-%m-%Y_%H-%M')
            filename = f'evolucoes_paciente_{timestamp}.md'
            
            # Prepare email
            subject = f'Exportação de Evoluções - {note_count} evolução(ões)'
            message = f"""Exportação de evoluções médicas em anexo.

📊 **Resumo da Exportação:**
- **Total de evoluções:** {note_count}
- **Data da exportação:** {timezone.now().strftime('%d/%m/%Y às %H:%M:%S')}
- **Formato:** Markdown (.md)

⚠️ **Aviso de Confidencialidade:**
Este arquivo contém informações médicas. Mantenha a confidencialidade e delete após o processamento.

---
Sistema EquipeMed - Exportação Automática"""

            email = EmailMessage(
                subject=subject,
                body=message,
                to=[email_address],
            )
            
            # Attach the markdown file
            email.attach_file(temp_file_path, mimetype='text/markdown')
            
            # Send email
            email.send()
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            raise CommandError(f'Failed to send email: {str(e)}')