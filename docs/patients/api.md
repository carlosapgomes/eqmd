# Patients API Documentation

## Available Endpoints

### Patient Endpoints

- `GET /api/patients/` - List all patients
- `POST /api/patients/` - Create a new patient
- `GET /api/patients/{id}/` - Retrieve a specific patient
- `PUT /api/patients/{id}/` - Update a patient
- `DELETE /api/patients/{id}/` - Delete a patient

### Hospital Record Endpoints

- `GET /api/hospital-records/` - List all hospital records
- `POST /api/hospital-records/` - Create a new hospital record
- `GET /api/hospital-records/{id}/` - Retrieve a specific hospital record
- `PUT /api/hospital-records/{id}/` - Update a hospital record
- `DELETE /api/hospital-records/{id}/` - Delete a hospital record

### Tag Endpoints

- `GET /api/tags/` - List all tags
- `POST /api/tags/` - Create a new tag
- `GET /api/tags/{id}/` - Retrieve a specific tag
- `PUT /api/tags/{id}/` - Update a tag
- `DELETE /api/tags/{id}/` - Delete a tag

## Authentication

All API endpoints require authentication. Use token authentication by including the token in the Authorization header:

```
Authorization: Token your-token-here
```

## Examples

### Listing Patients

```bash
curl -H "Authorization: Token your-token-here" http://example.com/api/patients/
```

### Creating a Patient

```bash
curl -X POST \
  -H "Authorization: Token your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "birthday": "1990-01-01", "status": 1}' \
  http://example.com/api/patients/
```