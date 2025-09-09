# Phase 4 Prompt: Print/PDF Generation

Create professional Portuguese PDF reports for discharge reports with hospital branding.

CONTEXT:

- Phase 3 completed: Basic print template exists
- Project uses hospital template tags for branding
- Need professional Portuguese layout with pagination
- Similar to outpatient prescriptions print system
- Bootstrap 5.3 available, but print uses custom CSS

GOAL: Create professional print/PDF discharge reports in Portuguese.

TASKS:

1. CREATE COMPREHENSIVE PRINT TEMPLATE:
   apps/dischargereports/templates/dischargereports/dischargereport_print.html:

```html
{% load static %} {% load hospital_tags %}
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>
      Relatório de Alta - {{ report.patient.name }} - {{
      report.discharge_date|date:"d/m/Y" }}
    </title>
    <link
      rel="stylesheet"
      href="{% static 'dischargereports/css/print.css' %}"
    />
  </head>
  <body>
    <button class="print-button no-print" onclick="window.print()">
      🖨️ Imprimir
    </button>

    <!-- Header (appears on every page) -->
    <div class="header">
      <div class="hospital-branding">
        {% hospital_logo as logo_url %} {% if logo_url %}
        <img
          src="{{ logo_url }}"
          alt="Logo do Hospital"
          class="hospital-logo"
        />
        {% endif %}
        <div class="hospital-info">
          <div class="hospital-name">{% hospital_name %}</div>
          <div class="hospital-details">
            {% hospital_address %} | {% hospital_phone %} | {% hospital_email %}
          </div>
        </div>
      </div>
      <div class="document-title">
        <h1>Relatório de Alta</h1>
        <h2>{{ report.medical_specialty }}</h2>
      </div>
    </div>

    <!-- Patient Information -->
    <div class="patient-info-section">
      <h3>Identificação do Paciente</h3>
      <div class="patient-info-grid">
        <div class="info-row">
          <div class="info-cell">
            <span class="info-label">Nome:</span>
            <span class="info-value">{{ report.patient.name }}</span>
          </div>
          <div class="info-cell">
            <span class="info-label">Prontuário:</span>
            <span class="info-value"
              >{{ report.patient.current_record_number|default:"—" }}</span
            >
          </div>
        </div>
        <div class="info-row">
          <div class="info-cell">
            <span class="info-label">Data de Nascimento:</span>
            <span class="info-value"
              >{{ report.patient.birthday|date:"d/m/Y"|default:"—" }}</span
            >
          </div>
          <div class="info-cell">
            <span class="info-label">Gênero:</span>
            <span class="info-value"
              >{{ report.patient.get_gender_display|default:"—" }}</span
            >
          </div>
          <div class="info-cell">
            <span class="info-label">Idade:</span>
            <span class="info-value">{{ report.patient.age }} anos</span>
          </div>
        </div>
        <div class="info-row">
          <div class="info-cell">
            <span class="info-label">Data de Admissão:</span>
            <span class="info-value"
              >{{ report.admission_date|date:"d/m/Y" }}</span
            >
          </div>
          <div class="info-cell">
            <span class="info-label">Data de Alta:</span>
            <span class="info-value"
              >{{ report.discharge_date|date:"d/m/Y" }}</span
            >
          </div>
        </div>
      </div>
    </div>

    <!-- Medical Content Sections -->
    <div class="content-section">
      <h3>Problemas e Diagnósticos</h3>
      <div class="content-text">
        {{ report.problems_and_diagnosis|linebreaks }}
      </div>
    </div>

    <div class="content-section">
      <h3>História da Admissão</h3>
      <div class="content-text">{{ report.admission_history|linebreaks }}</div>
    </div>

    <div class="content-section">
      <h3>Lista de Exames</h3>
      <div class="content-text">{{ report.exams_list|linebreaks }}</div>
    </div>

    <div class="content-section">
      <h3>Lista de Procedimentos</h3>
      <div class="content-text">{{ report.procedures_list|linebreaks }}</div>
    </div>

    <div class="content-section">
      <h3>História Médica da Internação</h3>
      <div class="content-text">
        {{ report.inpatient_medical_history|linebreaks }}
      </div>
    </div>

    <div class="content-section">
      <h3>Status da Alta</h3>
      <div class="content-text">{{ report.discharge_status|linebreaks }}</div>
    </div>

    <div class="content-section">
      <h3>Recomendações de Alta</h3>
      <div class="content-text">
        {{ report.discharge_recommendations|linebreaks }}
      </div>
    </div>

    <!-- Footer (appears on every page) -->
    <div class="page-footer">
      <div class="generation-info">
        <p>
          <strong>Relatório gerado em:</strong> {{ now|date:"d/m/Y às H:i" }}
        </p>
        <p>
          <strong>Gerado por:</strong> {{
          user.get_full_name|default:user.username }}
        </p>
      </div>

      <div class="hospital-footer">
        <div class="hospital-footer-info">
          {% hospital_name %} - {% hospital_address %}<br />
          Tel: {% hospital_phone %} | Email: {% hospital_email %}
        </div>
        <div class="sistema-credit">criado por EquipeMed</div>
      </div>
    </div>

    <script>
      // Auto-print functionality
      document.addEventListener("DOMContentLoaded", function () {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get("print") === "true") {
          window.print();
        }
      });
    </script>
  </body>
</html>
```

2. CREATE PRINT CSS FILE:
   Create directory and file:

```bash
mkdir -p apps/dischargereports/static/dischargereports/css
```

apps/dischargereports/static/dischargereports/css/print.css:

```css
/* Print Styles for Discharge Reports */

/* General Styles */
* {
  box-sizing: border-box;
}

body {
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  font-size: 12pt;
  line-height: 1.4;
  color: #333;
  margin: 0;
  padding: 20px;
  background: white;
}

/* Print-specific styles */
@media print {
  body {
    margin: 0;
    padding: 15px;
    font-size: 11pt;
  }

  .no-print {
    display: none !important;
  }

  .page-break {
    page-break-before: always;
  }

  .avoid-break {
    page-break-inside: avoid;
  }

  /* Page numbering */
  @page {
    margin: 2cm;

    @top-right {
      content: "Página " counter(page) " de " counter(pages);
      font-size: 9pt;
      color: #666;
    }
  }
}

/* Header Styles */
.header {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #0066cc;
  page-break-inside: avoid;
}

.hospital-branding {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-bottom: 15px;
}

.hospital-logo {
  max-height: 60px;
  width: auto;
}

.hospital-name {
  font-size: 18pt;
  font-weight: bold;
  color: #0066cc;
  margin-bottom: 5px;
}

.hospital-details {
  font-size: 10pt;
  color: #666;
  margin-bottom: 10px;
}

.document-title h1 {
  font-size: 16pt;
  font-weight: bold;
  color: #0066cc;
  margin: 10px 0 5px 0;
}

.document-title h2 {
  font-size: 14pt;
  font-weight: normal;
  color: #333;
  margin: 0;
}

/* Patient Info Styles */
.patient-info-section {
  margin-bottom: 25px;
  page-break-inside: avoid;
}

.patient-info-section h3 {
  font-size: 14pt;
  font-weight: bold;
  color: #0066cc;
  margin-bottom: 10px;
  padding-bottom: 5px;
  border-bottom: 1px solid #ccc;
}

.patient-info-grid {
  background: #f8f9fa;
  padding: 15px;
  border: 1px solid #dee2e6;
  border-radius: 5px;
}

.info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-cell {
  flex: 1;
  min-width: 200px;
}

.info-label {
  font-weight: bold;
  color: #495057;
}

.info-value {
  color: #212529;
  margin-left: 5px;
}

/* Content Section Styles */
.content-section {
  margin-bottom: 20px;
  page-break-inside: avoid;
}

.content-section h3 {
  font-size: 13pt;
  font-weight: bold;
  color: #0066cc;
  margin-bottom: 10px;
  padding-bottom: 5px;
  border-bottom: 1px solid #ccc;
}

.content-text {
  text-align: justify;
  line-height: 1.5;
  margin-bottom: 10px;
}

.content-text p {
  margin-bottom: 8px;
}

/* Print Button */
.print-button {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #0066cc;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 5px;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 1000;
}

.print-button:hover {
  background: #0052a3;
}

/* Footer Styles */
.page-footer {
  margin-top: 30px;
  padding-top: 15px;
  border-top: 1px solid #ccc;
  page-break-inside: avoid;
}

.generation-info {
  margin-bottom: 15px;
  font-size: 10pt;
  color: #666;
}

.generation-info p {
  margin: 2px 0;
}

.hospital-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 9pt;
  color: #666;
}

.hospital-footer-info {
  text-align: left;
}

.sistema-credit {
  text-align: right;
  font-style: italic;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .hospital-branding {
    flex-direction: column;
    gap: 10px;
  }

  .info-row {
    flex-direction: column;
    gap: 5px;
  }

  .info-cell {
    min-width: unset;
  }

  .hospital-footer {
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }
}

/* Long Content Handling */
.content-text {
  overflow-wrap: break-word;
  word-wrap: break-word;
}

/* Table styles if needed for structured data */
.info-table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
}

.info-table td {
  padding: 5px 8px;
  border: 1px solid #dee2e6;
  vertical-align: top;
}

.info-table .label-cell {
  background: #f8f9fa;
  font-weight: bold;
  width: 30%;
}
```

3. UPDATE STATIC FILES:
   Run webpack build to process the new CSS:

```bash
npm run build
```

4. ADD PRINT BUTTON TO DETAIL TEMPLATE:
   Update apps/dischargereports/templates/dischargereports/dischargereport_detail.html to add print button:

```html
<!-- Add this button to the detail template -->
<a
  href="{% url 'apps.dischargereports:dischargereport_print' pk=report.pk %}"
  class="btn btn-outline-secondary"
  target="_blank"
>
  <i class="bi bi-printer"></i> Imprimir Relatório
</a>
```

VERIFICATION:

- Print template displays all sections correctly
- Hospital branding appears properly
- CSS styling works in print preview
- Multi-page reports paginate correctly
- Print button works from detail view and event card

DELIVERABLES:

- Professional Portuguese print template
- Print-specific CSS styling
- Hospital branding integration
- Print buttons in UI

```

---


```
