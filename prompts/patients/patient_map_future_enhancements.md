# Patient Map Future Enhancements - Simple Additions

## Overview

These are minimal, practical enhancements that can be added to Phase 2 of the Patients Map implementation. They provide value without over-engineering for a hospital environment with < 100 inpatients.

## Enhancement 1: Simple CSV Export (30 minutes)

### Implementation

Add to the Phase 2 JavaScript file:

```javascript
// Add export button to existing controls
addExportButton() {
    const controlsContainer = document.querySelector('.map-controls');
    const exportBtn = document.createElement('button');
    exportBtn.className = 'btn btn-outline-primary btn-sm ms-2';
    exportBtn.innerHTML = '<i class="bi bi-download me-1"></i>Exportar CSV';
    exportBtn.onclick = () => this.exportToCSV();
    controlsContainer.appendChild(exportBtn);
}

// Simple CSV export function
exportToCSV() {
    const data = [['Ala', 'Paciente', 'Leito', 'Status', 'Registro']];
    
    document.querySelectorAll('.ward-branch').forEach(ward => {
        const wardName = ward.querySelector('.ward-header h5').textContent.split(' - ')[0];
        const patients = ward.querySelectorAll('.patient-item');
        
        if (patients.length === 0) {
            data.push([wardName, 'Nenhum paciente', '', '', '']);
        } else {
            patients.forEach(patient => {
                const name = patient.querySelector('.patient-name').textContent;
                const bed = patient.querySelector('.text-muted').textContent.replace('Leito: ', '');
                const status = patient.querySelector('.badge').textContent;
                const record = patient.href ? patient.href.split('/').pop() : '';
                
                data.push([wardName, name, bed, status, record]);
            });
        }
    });
    
    const csv = data.map(row => 
        row.map(cell => `"${cell}"`).join(',')
    ).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mapa-pacientes-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}
```

### Usage

- Single button click exports current view to CSV
- Includes ward name, patient name, bed, status, and record number
- Handles empty wards gracefully
- Filename includes current date

## Enhancement 2: Basic Hospital Stats Bar (15 minutes)

### Template Addition

Add to `ward_patient_map.html` before the tree view:

```html
<!-- Simple Hospital Statistics -->
<div class="alert alert-info mb-3 d-flex justify-content-between align-items-center">
    <div>
        <strong>{{ total_patients }}</strong> pacientes internados em <strong>{{ total_wards }}</strong> alas
        {% if emergency_count > 0 %}
            • <span class="text-warning"><strong>{{ emergency_count }}</strong> em emergência</span>
        {% endif %}
    </div>
    <div class="text-muted">
        <small>
            <i class="bi bi-clock me-1"></i>
            Atualizado em {{ last_updated|date:"d/m/Y H:i" }}
        </small>
    </div>
</div>
```

### View Updates

Add to the context in `WardPatientMapView`:

```python
# Count emergency patients
emergency_count = sum(
    1 for ward_info in ward_data 
    for patient_info in ward_info['patients']
    if patient_info['patient'].status == Patient.Status.EMERGENCY
)

context.update({
    'emergency_count': emergency_count,
    'last_updated': timezone.now(),
})
```

## Benefits

### CSV Export

- **Immediate value**: Staff can save patient lists for reports
- **No complexity**: Single file, no dependencies
- **Familiar format**: Everyone knows how to open CSV files
- **Audit trail**: Timestamped exports for records

### Stats Bar

- **Quick overview**: See totals at a glance
- **Emergency visibility**: Highlights urgent cases
- **Timestamp**: Shows data freshness
- **Minimal space**: Doesn't clutter the interface

## Why These Work for Your Scale

- **No caching needed**: < 100 patients means instant calculations
- **No real-time updates**: Manual refresh is perfectly acceptable
- **No complex analytics**: Simple counts provide sufficient insight
- **No performance optimization**: Current Django queries are fast enough
- **No infrastructure changes**: Uses existing technology stack

## Implementation Priority

1. **Phase 1**: Complete core functionality
2. **Phase 2**: Add search and tree interactions  
3. **Enhancement 1**: Add CSV export (if requested)
4. **Enhancement 2**: Add stats bar (if requested)

## Future Considerations

Only implement additional features if you actually experience:

- Page load times > 2 seconds (unlikely with < 100 patients)
- User requests for real-time updates
- Need for complex analytics
- Performance issues with current approach

**Remember**: It's easier to add features later than to maintain unnecessary complexity from day one.
