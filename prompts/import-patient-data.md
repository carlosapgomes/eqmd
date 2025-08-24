I have a big json file with patient data that I need to import to this project. The sample.json file has an example of the input data.
I need you to create a command to import this data into the project, much like the populate_sample_data.py file does when creating patients.
the input -> output data mapping should be as follow:

- name -> name
- birth_date (DD/MM/YYYY) -> birthday
- gender (male/female/"") -> gender (male -> M, female -> F, "" -> N)
- unified_healthcare_system-number -> healthcard_number
- phone -> phone
- address -> address
- city -> city
- state -> state
- zip -> zip_code
- patient_key -> current_record_number (you should create a proper record number object for this initial record number)

all patients should get a status of outpatient.

id_number and fiscal_number should be empty.

the fields updated_by and created_by should be set to the admin user (user name:admin, email: <admin@test.com>)

after the user and the initial record number are inserted in the system, you should create a new record number object from the
input property "medical_record_number" and set is as the current_record_number.

this script will be run in a live deployed docker system, so give me the correct command to run it within docker and passing the json file.

ask me any clarification questions before writing this script.
⎿  Read prompts/sample.json (45 lines)
⎿  Read apps/core/management/commands/populate_sample_data.py (934 lines)

● Looking at your requirements, I need some clarifications before creating the import script:

1. Gender mapping: You mentioned "" -> N, but looking at the Patient model in the populate_sample_data.py, I see it uses Patient.GenderChoices
   with options like MALE, FEMALE, OTHER, NOT_INFORMED. Should empty gender map to NOT_INFORMED?
2. Admin user: You specified admin user as "<admin@test.com>" but in the populate_sample_data.py I see "<admin@example.com>". Should I use
   "<admin@test.com>" or look for existing admin user?
3. Date format: The birth_date is in DD/MM/YYYY format. Should I handle potential parsing errors gracefully?
4. Record number sequence:

   - First create patient with patient_key as current_record_number
   - Then create a PatientRecordNumber object for this initial record
   - Then create another PatientRecordNumber object from medical_record_number and set it as current
   - Is this correct? So each patient will have 2 record number entries?

5. File path: For the Docker command, should the JSON file be mounted as a volume or should I assume it's already inside the container at a
   specific path?
6. Error handling: How should I handle:

   - Missing required fields in JSON?
   - Duplicate patient_key or medical_record_number values?
   - Invalid date formats?

7. Command name: What would you like to name this management command? Something like import_patient_data?

Please clarify these points so I can create the most appropriate import script for your needs.

> answers:

1. yes, empty gender maps to NOT_INFORMED
2. look for the first admin user you find in the system
3. yes, the data has been cleared and properly formated as DD/MM/YYYY. Try to create a date object from there.
4. yes, the first record number is the old database patient key, that I need to keep so that we can import dailynotes later, the second record
   number is the real hospital record number, and should be set to current_record_number.
5. I plan to download the json file in the same folder where the docker-compose.yml file is, and I think I could pass or pipe it into the
   command. Correct me if it is not possible.
6. skip the patient insertion and generate a report listing all json objects that were not inserted
7. yes: import_patient_data sounds good.

Basic Command Structure

docker compose run --rm eqmd python manage.py import_patient_data [options]

Usage Examples

Import from a file:

docker compose run --rm eqmd python manage.py import_patient_data --file /path/to/patients.json

Import from stdin (pipe JSON data):

cat patients.json | docker compose run --rm --no-TTY eqmd python manage.py import_patient_data

Dry run (preview what would be imported):

docker compose run --rm eqmd python manage.py import_patient_data --file /path/to/patients.json --dry-run

File Access Options

If your JSON file is on the host system, you need to mount it into the container:

Option 1: Copy file to container first

# Copy file to running container

docker cp patients.json $(docker compose ps -q eqmd):/app/patients.json

# Then run import

docker compose run --rm eqmd python manage.py import_patient_data --file /app/patients.json

Option 2: Use stdin (recommended)

cat /path/to/your/patients.json | docker compose run --rm --no-TTY eqmd python manage.py import_patient_data

Option 3: Mount volume temporarily

docker compose run --rm -v /host/path/to/data:/data eqmd python manage.py import_patient_data --file /data/patients.json

The stdin approach (Option 2) is usually the most convenient for one-time imports.
