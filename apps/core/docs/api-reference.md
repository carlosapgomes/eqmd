# Core App API Reference

This document provides a comprehensive API reference for the Core app, including current functionality and planned future APIs.

## Overview

The Core app currently provides web-based views and will potentially include REST API endpoints for mobile applications and third-party integrations.

## Current Web APIs

### Landing Page API

**Endpoint**: `/`
**Method**: GET
**Authentication**: Not required
**Content-Type**: text/html

#### Request
```http
GET / HTTP/1.1
Host: app.sispep.com
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
```

#### Response
```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: [length]

<!DOCTYPE html>
<html lang="pt-br">
<!-- Landing page HTML content -->
</html>
```

#### Response Data
- **Type**: HTML document
- **Template**: `core/landing_page.html`
- **Context**: Page metadata and content

### Dashboard API

**Endpoint**: `/dashboard/`
**Method**: GET
**Authentication**: Required (session-based)
**Content-Type**: text/html

#### Request
```http
GET /dashboard/ HTTP/1.1
Host: app.sispep.com
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Cookie: sessionid=abc123...
```

#### Response (Authenticated)
```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: [length]

<!DOCTYPE html>
<html lang="pt-br">
<!-- Dashboard HTML content -->
</html>
```

#### Response (Unauthenticated)
```http
HTTP/1.1 302 Found
Location: /accounts/login/?next=/dashboard/
```

## Future REST API Endpoints

### Dashboard Data API

**Endpoint**: `/api/v1/dashboard/`
**Method**: GET
**Authentication**: Required (Token/Session)
**Content-Type**: application/json

#### Request
```http
GET /api/v1/dashboard/ HTTP/1.1
Host: app.sispep.com
Accept: application/json
Authorization: Bearer [token]
```

#### Response
```json
{
    "user": {
        "id": 123,
        "username": "dr.silva",
        "first_name": "João",
        "last_name": "Silva",
        "profession": "Médico"
    },
    "stats": {
        "total_patients": 45,
        "active_cases": 12,
        "pending_tasks": 3,
        "recent_activities": 8
    },
    "recent_activity": [
        {
            "id": 1,
            "type": "patient_created",
            "description": "Novo paciente adicionado",
            "timestamp": "2024-01-15T10:30:00Z",
            "patient_id": 67
        }
    ],
    "notifications": [
        {
            "id": 1,
            "type": "info",
            "message": "Exame concluído para paciente #67",
            "timestamp": "2024-01-15T09:15:00Z",
            "read": false
        }
    ]
}
```

### Dashboard Stats API

**Endpoint**: `/api/v1/dashboard/stats/`
**Method**: GET
**Authentication**: Required
**Content-Type**: application/json

#### Request
```http
GET /api/v1/dashboard/stats/ HTTP/1.1
Host: app.sispep.com
Accept: application/json
Authorization: Bearer [token]
```

#### Response
```json
{
    "stats": {
        "patients": {
            "total": 45,
            "active": 12,
            "new_this_week": 3
        },
        "activities": {
            "total": 156,
            "this_week": 23,
            "pending": 8
        },
        "performance": {
            "response_time_avg": "2.3 hours",
            "completion_rate": 94.5
        }
    },
    "charts": {
        "patient_growth": [
            {"date": "2024-01-01", "count": 42},
            {"date": "2024-01-08", "count": 43},
            {"date": "2024-01-15", "count": 45}
        ],
        "activity_distribution": [
            {"type": "consultation", "count": 23},
            {"type": "examination", "count": 12},
            {"type": "prescription", "count": 8}
        ]
    }
}
```

### Search API

**Endpoint**: `/api/v1/search/`
**Method**: GET
**Authentication**: Required
**Content-Type**: application/json

#### Request
```http
GET /api/v1/search/?q=patient&type=all&limit=10 HTTP/1.1
Host: app.sispep.com
Accept: application/json
Authorization: Bearer [token]
```

#### Query Parameters
- `q` (string, required): Search query
- `type` (string, optional): Search type (patients, activities, all)
- `limit` (integer, optional): Maximum results (default: 10)
- `offset` (integer, optional): Pagination offset (default: 0)

#### Response
```json
{
    "query": "patient",
    "total_results": 25,
    "results": [
        {
            "type": "patient",
            "id": 67,
            "title": "João Santos",
            "description": "Paciente #67 - Cardiologia",
            "url": "/patients/67/",
            "relevance": 0.95
        },
        {
            "type": "activity",
            "id": 123,
            "title": "Consulta - João Santos",
            "description": "Consulta cardiológica realizada em 15/01/2024",
            "url": "/activities/123/",
            "relevance": 0.87
        }
    ],
    "facets": {
        "types": {
            "patients": 15,
            "activities": 8,
            "reports": 2
        }
    }
}
```

## Authentication

### Session Authentication (Current)
Used for web interface:

```python
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    # User available as request.user
    pass
```

### Token Authentication (Future)
For API endpoints:

```python
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

class DashboardAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

#### Token Usage
```http
Authorization: Bearer your-api-token-here
```

### JWT Authentication (Future)
For mobile applications:

```python
from rest_framework_simplejwt.authentication import JWTAuthentication

class DashboardAPIView(APIView):
    authentication_classes = [JWTAuthentication]
```

## Error Responses

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful GET request |
| 201 | Created | Successful POST request |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request data",
        "details": {
            "field": "email",
            "issue": "Invalid email format"
        }
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | User must be authenticated |
| `PERMISSION_DENIED` | User lacks required permissions |
| `VALIDATION_ERROR` | Request data validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

## Rate Limiting

### Future Implementation
API endpoints will include rate limiting:

```python
# Rate limiting configuration
RATE_LIMITS = {
    'dashboard': '100/hour',
    'search': '1000/hour',
    'stats': '50/hour'
}
```

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## Pagination

### Future Pagination Format
```json
{
    "count": 150,
    "next": "/api/v1/search/?offset=20&limit=10",
    "previous": "/api/v1/search/?offset=0&limit=10",
    "results": [...]
}
```

### Pagination Parameters
- `limit`: Number of results per page (max: 100)
- `offset`: Number of results to skip

## Versioning

### API Versioning Strategy
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: Maintain previous versions
- **Deprecation**: 6-month deprecation notice

### Version Headers
```http
API-Version: 1.0
Deprecated: false
Sunset: 2025-01-01
```

## Content Types

### Supported Content Types

#### Request
- `application/json` (API endpoints)
- `application/x-www-form-urlencoded` (forms)
- `multipart/form-data` (file uploads)

#### Response
- `application/json` (API endpoints)
- `text/html` (web pages)
- `text/csv` (data exports)
- `application/pdf` (reports)

## CORS Configuration

### Future CORS Settings
```python
CORS_ALLOWED_ORIGINS = [
    "https://app.sispep.com",
    "https://mobile.sispep.com",
]

CORS_ALLOW_CREDENTIALS = True
```

## API Documentation

### Future Interactive Documentation
- **Swagger/OpenAPI**: Interactive API documentation
- **Redoc**: Alternative documentation interface
- **Postman Collection**: API testing collection

### Documentation URLs
- `/api/docs/` - Swagger UI
- `/api/redoc/` - ReDoc interface
- `/api/schema/` - OpenAPI schema

## Security Considerations

### API Security Measures
1. **Authentication**: Required for all protected endpoints
2. **HTTPS**: All API traffic over HTTPS
3. **CSRF Protection**: For session-based authentication
4. **Input Validation**: Strict input validation
5. **Rate Limiting**: Prevent abuse
6. **Logging**: Comprehensive API logging

### Security Headers
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

## Monitoring and Analytics

### Future Monitoring
- **Response Times**: Track API performance
- **Error Rates**: Monitor error frequency
- **Usage Patterns**: Analyze API usage
- **User Behavior**: Track user interactions

### Metrics Endpoints
```http
GET /api/v1/metrics/health/
GET /api/v1/metrics/performance/
```

## Related Documentation

- [Views Documentation](views.md)
- [Templates Documentation](templates.md)
- [URL Patterns Documentation](urls.md)
- [Core App Overview](README.md)
