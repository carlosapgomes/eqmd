# Data Export for Research

## Overview

This guide explains how to use the `export_patient_data` management command to export a clean, anonymized dataset of patients and their corresponding daily notes. This is designed to facilitate research and data analysis, such as training or querying Large Language Models (LLMs).

## Command Usage

The script can be run as a Django management command.

### Using Docker Compose (Recommended for Production/Staging)

To run the command in a Docker environment, use `docker compose run --rm`:

```bash
docker compose run --rm eqmd python manage.py export_patient_data
```

### Using Local Development Environment

If you are running the application locally, you can use `manage.py`:

```bash
uv run python manage.py export_patient_data
```

### Custom Output File

By default, the script creates a file named `patient_data_export.csv` in the project's root directory. You can specify a different path:

```bash
# Docker
docker compose run --rm eqmd python manage.py export_patient_data /path/to/your/output.csv

# Local
uv run python manage.py export_patient_data /path/to/your/output.csv
```

## Output CSV Format

The command generates a CSV file where **each row represents a single daily note**.

### Columns

-   `patient_id`: The unique, anonymized UUID for the patient.
-   `patient_record_number`: The patient's official record number in the hospital EHR system.
-   `patient_gender`: The gender of the patient ('M', 'F', 'O', 'N').
-   `patient_age_at_note`: The patient's age in years at the time the note was created.
-   `patient_status`: The patient's status at the time of the note (e.g., "Inpatient", "Discharged", "Deceased").
-   `note_id`: The unique UUID for the daily note.
-   `note_event_datetime`: The full date and time the note was recorded (in ISO 8601 format).
-   `note_content`: The complete text content of the daily note.

### Sorting

The data is sorted first by `patient_id` and then chronologically by `note_event_datetime`. This groups all notes for a single patient together in the order they occurred.

## Data Anonymization & Traceability

The export includes the `patient_record_number` to allow for traceability back to the hospital's main EHR system for research validation. While this number is not direct PII, it makes the dataset **re-identifiable** by authorized personnel.

**This dataset should be handled with care and should not be shared with anyone outside the authorized research group.**

The script still **explicitly excludes** direct PII such as:

-   Names
-   Addresses
-   Phone numbers
-   Healthcard numbers
-   Fiscal or ID numbers
-   Exact birth dates (only age at the time of the note is included)
