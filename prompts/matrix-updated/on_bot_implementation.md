# Matrix Bot Implementation Plan

## Overview

This document outlines the bot implementation strategy based on the Matrix integration documentation and specific use case requirements for EquipeMed.

## Bot Implementation Prescription (from Phase 5)

### 1. Bot Account Creation

- **Matrix User ID**: `@eqmd_bot:${MATRIX_FQDN}`
- **Creation Method**: Use Synapse admin API or registration shared secret
- **Access Token**: Generate long-lived access token and store securely
- **Storage**: Store as environment variable/secret, not in git

### 2. Bot Functionality Requirements

#### Core Matrix Capabilities

- **DM Room Creation**: Bot creates one DM room per EquipeMed user containing exactly the user and the bot
- **Room Management**: Only bot (and admin) can create rooms and send invites
- **Global Room Management**: Bot can create/manage the "all users" global room

#### EquipeMed-Specific Capabilities

- **Patient Search**: Search inpatients by full name/partial name/record number/bed number/ward name
- **Patient Information**: Display basic demographic data (full name, birthdate, gender, record number, admission date, length of stay)
- **Interactive Selection**: Present multiple results and allow user selection
- **Future Extensions**: Document drafting, LLM interactions

### 3. Implementation Architecture

#### Django App Structure

**Recommended**: `apps/matrix_integration/` with:

```
apps/matrix_integration/
├── __init__.py
├── models.py                   # Matrix user/room mappings
├── admin.py                    # Admin interface
├── bot/
│   ├── __init__.py
│   ├── bot_service.py          # Main bot logic
│   ├── patient_search.py       # Patient search functionality
│   ├── message_handlers.py     # Command parsing
│   └── responses.py            # Response formatting
├── management/commands/
│   ├── run_matrix_bot.py       # Start bot service
│   ├── provision_bot.py        # Setup bot user/rooms
│   ├── provision_dm_rooms.py   # Create user DM rooms
│   └── sync_deactivations.py   # User lifecycle sync
└── migrations/
```

#### Models

- **Matrix user id mapping**: Link EquipeMed users to Matrix users
- **DM room id storage**: Store room IDs for reliable "user thread" lookup
- **Global room id storage**: Track global communication rooms
- **Bot state**: Store conversation context for multi-step interactions

#### Management Commands

- **Provision bot user/token**: Initial bot setup
- **Provision DM rooms for active users**: Create user communication channels
- **Sync user deactivations**: Handle user lifecycle changes
- **Run bot service**: Main bot process

#### Admin Actions

- **"Provision now" functionality**: Manual trigger for room/user provisioning

## 4. User Lifecycle Integration

### User Activation Flow

1. Create Matrix user account
2. Create DM room with bot
3. Invite to global room (optional)
4. Store room mappings in EquipeMed DB

### User Deactivation Flow

1. Call Synapse admin API to deactivate account
2. Kick from all rooms
3. Update local status records

### Reactivation Flow

1. Reactivate Matrix user account
2. Re-invite to global room
3. Restore DM room access

## 5. Bot Framework Selection

### Matrix Library

- **Primary**: `matrix-nio` - Modern async Matrix client library for Python
- **Alternative**: `matrix-bot-sdk` - Higher-level bot framework

### Interaction Framework

- **MVP**: Custom simple state machine for basic patient search
- **Future**: LangGraph for complex conversation flows with LLM integration
- **Alternative**: LangChain for extensive LLM tooling needs

### Patient Search Implementation

#### Command Interface

**Single `/buscar` Command with Smart Prefixes:**

```bash
/buscar João Silva              # Search by name (default)
/buscar reg:12345              # Search by record number
/buscar leito:101              # Search by bed number
/buscar enf:uti                # Search by ward name
/buscar João leito:101 enf:uti # Combined search criteria
```

#### Available Prefixes

- **`reg:` or `registro:`** - Search by record number
- **`leito:` or `cama:`** - Search by bed/room number
- **`enf:`, `enfermaria:`, or `setor:`** - Search by ward name

#### Technical Implementation

```python
# Smart query parser with prefix support
import re
from typing import Dict, List, Tuple
from django.db.models import Q
from apps.patients.models import Patient

SEARCH_PREFIXES = {
    'reg': 'record_number',
    'registro': 'record_number', 
    'leito': 'bed',
    'cama': 'bed',
    'enf': 'ward',
    'enfermaria': 'ward',
    'setor': 'ward'
}

def parse_search_query(query: str) -> Tuple[Dict[str, str], str]:
    """Parse search query with prefixes"""
    prefixed_terms = {}
    remaining_parts = []
    
    parts = query.strip().split()
    
    for part in parts:
        if ':' in part:
            prefix, value = part.split(':', 1)
            prefix = prefix.lower()
            
            if prefix in SEARCH_PREFIXES:
                field_name = SEARCH_PREFIXES[prefix]
                prefixed_terms[field_name] = value
                continue
        
        remaining_parts.append(part)
    
    remaining_text = ' '.join(remaining_parts)
    return prefixed_terms, remaining_text

def search_patients_smart(prefixed_terms: Dict[str, str], name_query: str):
    """Smart patient search with multiple criteria"""
    queryset = Patient.objects.select_related('current_admission', 'current_admission__ward')
    filters = Q()
    
    # Apply prefixed search terms
    if 'record_number' in prefixed_terms:
        filters &= Q(record_number__icontains=prefixed_terms['record_number'])
    
    if 'bed' in prefixed_terms:
        bed_value = prefixed_terms['bed']
        filters &= Q(
            Q(current_admission__bed__icontains=bed_value) |
            Q(current_admission__room__icontains=bed_value)
        )
    
    if 'ward' in prefixed_terms:
        ward_value = prefixed_terms['ward']
        filters &= Q(
            Q(current_admission__ward__name__icontains=ward_value) |
            Q(current_admission__ward__short_name__icontains=ward_value)
        )
    
    # Apply name search if provided
    if name_query.strip():
        name_filters = Q(
            Q(first_name__icontains=name_query) |
            Q(last_name__icontains=name_query) |
            Q(full_name__icontains=name_query)
        )
        filters &= name_filters
    
    return queryset.filter(filters).distinct()[:10]
```

## 6. Deployment Strategy

### Integration Approach

**Django Integration** (Recommended):

- Bot logic lives inside the existing EquipeMed Django app
- Uses Django ORM to store Matrix room mappings
- Uses Django management commands for operations
- Integrates directly with EquipeMed user lifecycle
- Scheduled via cron/systemd timers

### NOT a Separate Docker Container

- Integration is tightly coupled with EquipeMed's user management
- Bot operations are triggered by EquipeMed events (user activation/deactivation)
- Direct access to patient models and permission system

### Process Management

- **Avoid Celery dependency**: Use explicit management commands + cron/systemd timers
- **Long-running process**: Bot service runs as Django management command
- **Monitoring**: Integrate with existing EquipeMed monitoring

## 7. Simple Use Case Implementation

### User Interaction Flow

#### Example Interactions

**Simple Name Search:**
```
User: /buscar João Silva
Bot:  🔍 Busca por: Nome: João Silva
      
      Encontrados 3 pacientes:
      1️⃣ João Silva Santos (Leito 101, UTI)
      2️⃣ João da Silva (Leito 205, Clínica Médica)  
      3️⃣ Maria João Silva (Leito 310, Cardiologia)
      
      Digite o número (1-3) ou /ajuda

User: 1
Bot:  📋 João Silva Santos
      📅 Nascimento: 15/03/1975 (49 anos)
      👤 Sexo: Masculino
      🆔 Registro: 12345
      🏥 Internação: 10/01/2024 (7 dias)
      🛏️ Localização: Leito 101, UTI
```

**Advanced Search with Prefixes:**
```
User: /buscar Silva leito:205 enf:cardio
Bot:  🔍 Busca por: Nome: Silva | Leito: 205 | Enfermaria: cardio
      
      Encontrado 1 paciente:
      1️⃣ Maria Silva (Leito 205, Cardiologia)

User: 1
Bot:  📋 [Patient details...]
```

**Help System:**
```
User: /buscar
Bot:  🔍 **Comando /buscar** - Como usar:

      **Busca Simples:**
      • `/buscar João Silva` - Buscar por nome

      **Busca com Prefixos:**
      • `/buscar reg:12345` - Por número de registro
      • `/buscar leito:101` - Por número do leito
      • `/buscar enf:uti` - Por enfermaria

      **Busca Combinada:**
      • `/buscar João reg:12345` - Nome + registro
      • `/buscar leito:101 enf:cardio` - Leito + enfermaria

      **Prefixos Disponíveis:**
      • `reg:` ou `registro:` - Número de registro
      • `leito:` ou `cama:` - Número do leito/cama
      • `enf:`, `enfermaria:` ou `setor:` - Nome da enfermaria

      **Exemplo:** `/buscar João leito:205 enf:cardio`
```

### Technical Implementation

```python
async def handle_search_command(room_id, user_id, query):
    """Handle /buscar command with smart parsing"""
    if not query.strip():
        await send_search_help(room_id)
        return
    
    # 1. Validate user permissions
    if not can_user_search_patients(user_id):
        await send_message(room_id, "❌ Você não tem permissão para buscar pacientes")
        return
    
    # 2. Parse the query with smart prefix detection
    prefixed_terms, name_query = parse_search_query(query)
    
    # 3. Search patients using existing EquipeMed models
    patients = search_patients_smart(prefixed_terms, name_query)
    
    if not patients:
        search_desc = format_search_description(prefixed_terms, name_query)
        await send_message(room_id, f"❌ Nenhum paciente encontrado para: {search_desc}")
        return
    
    # 4. Format search description
    search_desc = format_search_description(prefixed_terms, name_query)
    
    if len(patients) == 1:
        # Direct result
        await send_patient_details(room_id, patients[0])
    else:
        # 5. Store user state for follow-up selection and show options
        await store_user_state(user_id, 'selecting_patient', patients)
        await send_patient_list(room_id, patients, search_desc)

def format_search_description(prefixed_terms: Dict[str, str], name_query: str) -> str:
    """Format search criteria for display"""
    parts = []
    
    if name_query.strip():
        parts.append(f"Nome: {name_query}")
    
    if 'record_number' in prefixed_terms:
        parts.append(f"Registro: {prefixed_terms['record_number']}")
    
    if 'bed' in prefixed_terms:
        parts.append(f"Leito: {prefixed_terms['bed']}")
    
    if 'ward' in prefixed_terms:
        parts.append(f"Enfermaria: {prefixed_terms['ward']}")
    
    return " | ".join(parts)

async def handle_selection(room_id, user_id, selection):
    """Handle patient selection from search results"""
    state = await get_user_state(user_id)
    if not state or state.get('action') != 'selecting_patient':
        await send_message(room_id, "❌ Nenhuma seleção ativa. Use /buscar para pesquisar pacientes.")
        return
    
    try:
        index = int(selection) - 1
        patients = state['data']
        if 0 <= index < len(patients):
            patient = patients[index]
            await send_patient_details(room_id, patient)
            await clear_user_state(user_id)
        else:
            await send_message(room_id, f"❌ Seleção inválida. Digite um número entre 1 e {len(patients)}")
    except ValueError:
        await send_message(room_id, "❌ Seleção inválida. Digite o número do paciente ou /buscar para nova pesquisa")
```

## 8. Key Technical Notes

- **Server-side Policy Enforcement**: Bot requires Synapse module to prevent normal users from creating rooms/invites
- **Security**: Bot acts on behalf of admin for global room management
- **Performance**: Direct database access through Django ORM
- **Scalability**: Stateless design with context stored in database
- **Future Ready**: Architecture supports LLM integration for document drafting

## 9. Implementation Phases

### Phase A (MVP - Patient Search)

1. Setup `matrix-nio` bot service within `matrix_integration` app
2. Implement text-based patient search with existing models
3. Add simple state management for multi-step interactions
4. Deploy as Django management command

### Phase B (Enhanced Features)

1. Add LangGraph for complex conversation flows
2. Integrate document drafting capabilities
3. Add sophisticated search filters and permissions
4. Implement advanced patient data visualization

## 10. Benefits of This Approach

✅ **Direct EquipeMed Integration**: Bot runs within Django app, direct access to models  
✅ **DM Room Architecture**: Perfect for 1:1 user-bot interactions  
✅ **Simple Deployment**: No separate bot infrastructure needed  
✅ **Future LLM Ready**: Easy to add LangGraph/LangChain later  
✅ **Security**: Bot inherits EquipeMed's permission system  
✅ **Development Speed**: Leverage existing patient search code
