# Patients Map Tree View - Implementation Overview

## Project Description

Create a "Mapa de Pacientes" (Patients Map) page that displays a hierarchical tree view showing hospital wards and their currently admitted patients. This provides medical staff with a visual overview of patient distribution across the hospital.

## Visual Design Concept

```
📋 Mapa de Pacientes
├── 🏥 UTI - Unidade de Terapia Intensiva (3/12 pacientes)
│   ├── 🛏️ Leito 101 - João Silva Santos → [Ver Timeline]
│   ├── 🛏️ Leito 103 - Maria Oliveira Costa → [Ver Timeline]
│   └── 🛏️ Leito 107 - Pedro Santos Lima → [Ver Timeline]
├── 🏥 CC - Centro Cirúrgico (1/8 pacientes)
│   └── 🛏️ Sala 2 - Ana Carolina Souza → [Ver Timeline]
└── 🏥 PS - Pronto Socorro (0/20 pacientes)
    └── 📝 Nenhum paciente internado
```

## Scope Definition

### Included Patients

- **INPATIENT** status patients (status = 2)
- **EMERGENCY** status patients (status = 3)
- Only patients with assigned beds/wards

### Excluded Patients

- OUTPATIENT, DISCHARGED, TRANSFERRED, DECEASED status patients
- Patients without ward assignments

## Key Features

### Core Functionality

1. **Hierarchical Tree Structure**

   - Root level: Hospital wards (Ward model)
   - Child level: Patients in each ward with bed numbers
   - Expandable/collapsible ward sections

2. **Patient Information Display**

   - Patient name
   - Bed/room number
   - Direct link to patient timeline
   - Visual status indicators

3. **Ward Statistics**
   - Current patient count per ward
   - Capacity information (if available)
   - Empty ward handling

### User Experience

1. **Navigation Integration**

   - Accessible from main sidebar under "Gestão de Pacientes"
   - Icon: `bi-diagram-3-fill` (tree structure)
   - Label: "Mapa de Pacientes"

2. **Interactive Elements**

   - Click to expand/collapse wards
   - Quick navigation to patient timelines
   - Search/filter functionality (Phase 2)

3. **Responsive Design**
   - Mobile-friendly tree view
   - Tablet optimization
   - Desktop full-screen layout

## Technical Architecture

### Backend Components

- **View**: `WardPatientMapView` - Template view with ward/patient context
- **URL**: `patients/map/` - New route in patients app
- **Template**: `ward_patient_map.html` - Tree view template
- **Permissions**: Reuse existing `patients.view_patient` permission

### Frontend Components

- **Base Template**: Extend `patients/patient_base.html`
- **CSS Framework**: Bootstrap 5.3 + existing medical theme
- **JavaScript**: Progressive enhancement for tree interactions
- **Icons**: Bootstrap Icons for ward/patient/bed indicators

### Data Structure

```python
{
    'wards': [
        {
            'ward': Ward object,
            'patient_count': int,
            'capacity_estimate': int|None,
            'patients': [
                {
                    'patient': Patient object,
                    'bed': str,
                    'tags': [Tag objects],
                    'admission_duration': str
                }
            ]
        }
    ]
}
```

## Implementation Phases

### Phase 1: Core Functionality (MVP)

- Backend view and URL configuration
- Basic template with static tree structure
- Navigation menu integration
- Basic responsive design

### Phase 2: Enhanced UI & Interactivity

- JavaScript tree expand/collapse
- Search and filter functionality
- Enhanced styling and animations
- Real-time patient counts

### Phase 3: Advanced Features & Optimization

- Performance optimizations
- Advanced filtering (by tags, admission date, etc.)
- Print-friendly view
- Export functionality
- WebSocket real-time updates (future consideration)

## Success Criteria

### Functional Requirements

- ✅ Display all active wards with current patient counts
- ✅ Show inpatient and emergency patients with bed assignments
- ✅ Provide direct navigation to patient timelines
- ✅ Handle empty wards gracefully
- ✅ Maintain consistent UI with existing application

### Performance Requirements

- ✅ Page load time < 2 seconds for 50+ patients
- ✅ Smooth tree interactions on mobile devices
- ✅ Efficient database queries (minimize N+1 problems)

### Usability Requirements

- ✅ Intuitive tree navigation
- ✅ Clear visual hierarchy
- ✅ Accessible on all device sizes
- ✅ Follows existing application patterns

## Files to Create/Modify

### New Files

1. `prompts/patients/patients_map_tree_view_phase1.md`
2. `prompts/patients/patients_map_tree_view_phase2.md`
3. `prompts/patients/patients_map_tree_view_phase3.md`

### Modified Files (Implementation)

1. `apps/patients/views.py` - Add `WardPatientMapView`
2. `apps/patients/urls.py` - Add map route
3. `templates/base_app.html` - Add navigation menu item
4. `apps/patients/templates/patients/ward_patient_map.html` - New template

### Optional Files (Future Enhancements)

1. `static/js/ward_patient_map.js` - Tree interactivity
2. `static/css/ward_patient_map.css` - Custom styling

## Related Documentation

- [Ward Management Implementation Plan](ward_management_implementation_plan.md)
- [Patient Implementation Plan](patient_implementation_plan.md)
- [docs/apps/patients.md](../../docs/apps/patients.md)
- [docs/permissions/](../../docs/permissions/)
