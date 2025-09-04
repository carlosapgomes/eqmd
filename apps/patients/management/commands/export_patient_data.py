import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient

class Command(BaseCommand):
    help = 'Exports anonymized patient and daily note data to a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'output_file',
            type=str,
            help='The path to the output CSV file.',
            nargs='?',
            default=os.path.join(settings.BASE_DIR, 'patient_data_export.csv')
        )

    def handle(self, *args, **options):
        output_file = options['output_file']
        self.stdout.write(self.style.SUCCESS(f'Starting data export to {output_file}...'))

        # Eager load related patient data and order chronologically by patient
        notes_queryset = DailyNote.objects.select_related('patient').order_by('patient__id', 'event_datetime')

        total_notes = notes_queryset.count()
        self.stdout.write(f'Found {total_notes} daily notes to export.')

        header = [
            'patient_id',
            'patient_record_number',
            'patient_gender',
            'patient_age_at_note',
            'patient_status',
            'note_id',
            'note_event_datetime',
            'note_content'
        ]

        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)

                # Use iterator() for memory efficiency with large datasets
                for i, note in enumerate(notes_queryset.iterator()):
                    patient = note.patient

                    # Calculate age at the time of the note
                    age_at_note = (
                        note.event_datetime.year - patient.birthday.year -
                        ((note.event_datetime.month, note.event_datetime.day) <
                         (patient.birthday.month, patient.birthday.day))
                    )

                    writer.writerow([
                        patient.id,
                        patient.current_record_number,
                        patient.gender,
                        age_at_note,
                        patient.get_status_display(),
                        note.id,
                        note.event_datetime.isoformat(),
                        note.content,
                    ])

                    if (i + 1) % 10000 == 0:
                        self.stdout.write(f'Processed {i + 1}/{total_notes} notes...')

            self.stdout.write(self.style.SUCCESS(f'Successfully exported {total_notes} notes to {output_file}'))

        except IOError as e:
            self.stderr.write(self.style.ERROR(f'Error writing to file {output_file}: {e}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An unexpected error occurred: {e}'))
