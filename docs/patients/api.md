# Patients JSON API Documentation

## Available Endpoints

### Patient Information Endpoints

- `GET /patients/api/search/` - Search patients with query parameters
- `GET /patients/api/record-numbers/{patient_id}/` - Get patient record number history
- `GET /patients/api/admissions/{patient_id}/` - Get patient admission history
- `GET /patients/api/record-lookup/{record_number}/` - Find patient by record number
- `GET /patients/api/admission/{admission_id}/` - Get admission details

## Authentication

All API endpoints require authentication. Users must be logged in through Django's session authentication.

## Patient Data Fields

### Core Patient Fields

- `id` - UUID patient identifier
- `name` - Patient full name
- `gender` - Patient gender (M=Masculino, F=Feminino, O=Outro, N=Não Informado)
- `gender_display` - Human-readable gender value
- `current_record_number` - Current hospital record number
- `status` - Patient status (inpatient, outpatient, emergency, discharged, transferred, deceased)
- `is_currently_admitted` - Boolean indicating current admission status
- `bed` - Current bed assignment (if applicable)
- `healthcard_number` - Health card number
- `phone` - Contact phone number

## Examples

### Patient Search

```bash
curl -b sessionid=your-session-id \
  "http://example.com/patients/api/search/?q=John&page=1&per_page=20"
```

Response includes gender information:

```json
{
  "results": [
    {
      "id": "uuid-here",
      "name": "John Doe",
      "gender": "M",
      "gender_display": "Masculino",
      "current_record_number": "12345",
      "status": "Inpatient"
    }
  ]
}
```

### Patient Record Numbers

```bash
curl -b sessionid=your-session-id \
  "http://example.com/patients/api/record-numbers/uuid-here/"
```

Response includes gender information:

```json
{
  "patient_id": "uuid-here",
  "patient_name": "John Doe",
  "gender": "M",
  "gender_display": "Masculino",
  "current_record_number": "12345",
  "records": [...]
}
```
