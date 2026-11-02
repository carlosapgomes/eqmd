# Patients JSON API Documentation

## Available Endpoints

### Patient Information Endpoints

- `GET /patients/api/search/` - Search patients with query parameters
- `GET /patients/tags/lookup/` - Paginated, visibility-checked tag lookup
- `GET /patients/api/record-numbers/{patient_id}/` - Get patient record number history
- `GET /patients/api/admissions/{patient_id}/` - Get patient admission history
- `GET /patients/api/record-lookup/{record_number}/` - Find patient by record number
- `GET /patients/api/admission/{admission_id}/` - Get admission details

## Authentication

All API endpoints require authentication. Users must be logged in through
Django's session authentication.

## Patient Data Fields

### Core Patient Fields

- `id` - UUID patient identifier
- `name` - Patient full name
- `gender` - Patient gender (M=Masculino, F=Feminino, O=Outro, N=Não Informado)
- `gender_display` - Human-readable gender value
- `current_record_number` - Current hospital record number
- `status` - Patient status (inpatient, outpatient, emergency, discharged,
  transferred, deceased)
- `is_currently_admitted` - Boolean indicating current admission status
- `bed` - Current bed assignment (if applicable)
- `healthcard_number` - Health card number
- `phone` - Contact phone number

## Patient list tag filtering

`GET /patients/` accepts the explicit multi-tag filter parameters below. All
other parameters (`q`, `status`, `admission`) stay conjunctive and patient rows
remain distinct.

| Parameter               | Meaning                                          |
| ----------------------- | ------------------------------------------------ |
| `tags` (repeated)       | Manual selection; duplicate ids removed.         |
| `tag_mode`              | `any` matches one tag; `all` requires every tag. |
| `tag_filter=manual`     | Explicit manual state, including empty.          |
| `tag=<id>`              | Legacy bookmark; treated as explicit ANY.        |
| `tag=` (present, empty) | Legacy explicit manual-empty selection.          |

An inaccessible, unknown or malformed explicit id returns HTTP 200 with no
patients and the generic message `Filtro de tag inválido.`; it never silently
returns an unfiltered list. Repeated values and mode are preserved through
pagination and filter-removal links with URL-encoded parameters.

## Tag lookup endpoint

`GET /patients/tags/lookup/` is a read-only, paginated, visibility-checked
search used by the multi-tag selector. It never creates or mutates catalogue
rows.

| Parameter              | Meaning                              |
| ---------------------- | ------------------------------------ |
| `q`                    | Name or team abbreviation search.    |
| `include_historical=1` | Include visible historical tags.     |
| `page`                 | 1-based result page.                 |
| `page_size`            | Results per page, 1-50 (default 20). |
| `selected` (repeated)  | Echo selected visible tags.          |

```json
{
  "results": [
    {
      "id": 12,
      "name": "Estável CIRGER",
      "display_name": "Estável CIRGER [CIRGER]",
      "color": "#007bff",
      "team_abbreviation": "CIRGER",
      "state": "active",
      "state_label": "",
      "is_historical": false,
      "is_restricted": true
    }
  ],
  "selected": [],
  "count": 1,
  "page": 1,
  "num_pages": 1,
  "page_size": 20,
  "has_next": false,
  "has_previous": false,
  "include_historical": false
}
```

Only tags readable by the requesting user appear in `results`, `count` or
`selected`. Invalid lookup parameters and forged/inaccessible `selected` ids
return HTTP 400 with `{"error": "Filtro de tag inválido."}` and no catalogue
metadata. The endpoint has no create operation (`POST` returns 405).

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
