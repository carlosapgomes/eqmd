# Sample Content API Reference

This document describes the API endpoints available for the Sample Content app.

## Authentication

All API endpoints require authentication. Users must be logged in to access any sample content data.

## Endpoints

### Get Sample Content by Event Type

Retrieve all sample content templates for a specific event type.

**Endpoint:** `GET /sample-content/api/event-type/<event_type>/`

**Parameters:**
- `event_type` (path parameter): Integer representing the event type ID

**Response Format:**
```json
{
    "sample_contents": [
        {
            "id": "uuid-string",
            "title": "Template Title",
            "content": "Template content text..."
        }
    ]
}
```

**Event Type IDs:**
- `0` - History and Physical Event (Anamnese e Exame Físico)
- `1` - Daily Note Event (Evolução)
- `2` - Simple Note Event (Nota/Observação)
- `3` - Photo Event (Imagem)
- `4` - Exam Result Event (Resultado de Exame)
- `5` - Exams Request Event (Requisição de Exame)
- `6` - Discharge Report Event (Relatório de Alta)
- `7` - Outpatient Prescription Event (Receita)
- `8` - Report Event (Relatório)
- `9` - Photo Series Event (Série de Fotos)

**Example Request:**
```http
GET /sample-content/api/event-type/1/ HTTP/1.1
Host: example.com
Cookie: sessionid=your-session-id
```

**Example Response:**
```json
{
    "sample_contents": [
        {
            "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "title": "Template de Evolução Diária",
            "content": "Paciente apresenta-se em estado geral [bom/regular/grave].\n\nSinais vitais:\n- PA: ___/___ mmHg\n- FC: ___ bpm..."
        },
        {
            "id": "6eb69570-6ddb-4c4c-9e94-9b4af6b2e4a2",
            "title": "Evolução Pós-Cirúrgica",
            "content": "Paciente no pós-operatório de ___.\n\nEstado geral: ___\nFerida operatória: ___..."
        }
    ]
}
```

**Error Responses:**

**401 Unauthorized** - User not authenticated
```json
{
    "error": "Authentication required"
}
```

**400 Bad Request** - Invalid event type
```json
{
    "error": "Invalid event type"
}
```

**Example Usage in JavaScript:**

```javascript
async function getSampleContentByEventType(eventType) {
    try {
        const response = await fetch(`/sample-content/api/event-type/${eventType}/`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.sample_contents;
    } catch (error) {
        console.error('Error fetching sample content:', error);
        return [];
    }
}

// Usage
getSampleContentByEventType(1).then(templates => {
    templates.forEach(template => {
        console.log(`${template.title}:`);
        console.log(template.content);
        console.log('---');
    });
});
```

**Example Usage in Python:**

```python
import requests

def get_sample_content_by_event_type(event_type, session_cookie):
    url = f'/sample-content/api/event-type/{event_type}/'
    headers = {
        'Cookie': f'sessionid={session_cookie}'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()['sample_contents']
    else:
        return []

# Usage
templates = get_sample_content_by_event_type(1, 'your-session-id')
for template in templates:
    print(f"{template['title']}:")
    print(template['content'])
    print("---")
```

## Integration Examples

### Form Auto-Population

```javascript
// Populate form field with selected template
function populateFormWithTemplate(templateId) {
    fetch(`/sample-content/api/event-type/1/`)
        .then(response => response.json())
        .then(data => {
            const template = data.sample_contents.find(t => t.id === templateId);
            if (template) {
                document.getElementById('content-field').value = template.content;
            }
        });
}
```

### Template Selector

```javascript
// Populate template selector dropdown
function populateTemplateSelector(eventType, selectElementId) {
    fetch(`/sample-content/api/event-type/${eventType}/`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById(selectElementId);
            select.innerHTML = '<option value="">Selecione um template...</option>';
            
            data.sample_contents.forEach(template => {
                const option = document.createElement('option');
                option.value = template.id;
                option.textContent = template.title;
                select.appendChild(option);
            });
        });
}
```

## Rate Limiting

Currently, no rate limiting is implemented. However, best practices suggest:
- Cache responses when possible
- Avoid excessive API calls in loops
- Implement client-side caching for frequently accessed templates

## Error Handling

Always implement proper error handling when consuming the API:

```javascript
async function fetchSampleContent(eventType) {
    try {
        const response = await fetch(`/sample-content/api/event-type/${eventType}/`);
        
        if (response.status === 401) {
            // Redirect to login
            window.location.href = '/accounts/login/';
            return [];
        }
        
        if (response.status === 400) {
            console.error('Invalid event type:', eventType);
            return [];
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.sample_contents;
    } catch (error) {
        console.error('Network error:', error);
        return [];
    }
}
```

## Security Considerations

- All endpoints require authentication
- No sensitive data is exposed through the API
- UUID identifiers prevent enumeration attacks
- Content is returned as-is (ensure proper escaping in client applications)
- CSRF protection is handled by Django middleware for web requests