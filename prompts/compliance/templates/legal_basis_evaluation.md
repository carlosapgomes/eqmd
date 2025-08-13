# LGPD Legal Basis Evaluation Framework

## Overview

This framework helps evaluate the legal basis for processing patient data when copying from hospital medical records, ensuring LGPD compliance for the EquipeMed parallel system.

## Legal Basis Options Under LGPD

### Article 7 - Personal Data Processing

1. **Consent (Art. 7º, I)**
   - Explicit, informed consent from data subject
   - Must be specific and unambiguous
   - Can be withdrawn at any time

2. **Legal Obligation (Art. 7º, II)**
   - Processing required by law or regulation
   - Example: CFM medical record requirements

3. **Public Administration (Art. 7º, III)**
   - Processing by public entities for public policies
   - Not applicable to private hospital systems

4. **Research Studies (Art. 7º, IV)**
   - Scientific research by research institutions
   - Requires ethics committee approval

5. **Contract Performance (Art. 7º, V)**
   - Processing necessary for contract execution
   - Example: Medical service agreements

6. **Legitimate Interest (Art. 7º, VI)**
   - Legitimate interests of controller or third parties
   - Must not violate fundamental rights

### Article 11 - Sensitive Data Processing (Health Data)

1. **Consent (Art. 11º, I)**
   - Specific and prominent consent for sensitive data
   - Higher standard than regular consent

2. **Health Protection (Art. 11º, II, a)**
   - **Most relevant for medical systems**
   - Processing by health professionals or health services
   - For health protection procedures

3. **Life Protection (Art. 11º, II, e)**
   - Vital interests protection
   - Emergency situations

4. **Judicial/Administrative Procedures (Art. 11º, II, b-d)**
   - Court orders, administrative proceedings
   - Public health surveillance

## Hospital Data Copying Scenarios

### Scenario 1: Same Institution
**Situation**: Your system is part of the same hospital/healthcare institution

**Legal Basis**: Art. 11º, II, 'a' (Health Protection)
- **Rationale**: Processing by same healthcare institution for continuity of care
- **Requirements**: 
  - Professional healthcare team
  - Medical purpose
  - Patient awareness (transparency)
- **Documentation**: 
  - Institutional relationship
  - Medical team credentials
  - Care continuity justification

### Scenario 2: Contracted Service Provider
**Situation**: Your system provides contracted services to the hospital

**Legal Basis**: Art. 11º, II, 'a' + Art. 7º, V (Health Protection + Contract)
- **Rationale**: Processing under contract for healthcare services
- **Requirements**:
  - Formal service contract
  - Data processing clause in contract
  - Hospital consent covers contracted services
- **Documentation**:
  - Service contract with data processing terms
  - Hospital authorization
  - Professional service justification

### Scenario 3: Independent Healthcare Team
**Situation**: Independent medical team using parallel system for same patients

**Legal Basis**: Art. 11º, II, 'a' (Health Protection) + Consent evaluation
- **Rationale**: Healthcare professionals providing care to same patients
- **Requirements**:
  - Licensed healthcare professionals
  - Active care relationship with patients
  - Hospital consent evaluation or supplementary consent
- **Documentation**:
  - Professional licenses
  - Care relationship evidence
  - Consent adequacy analysis

### Scenario 4: Separate Entity Copying Data
**Situation**: Completely independent system copying hospital data

**Legal Basis**: Art. 11º, I (Specific Consent) or Art. 7º, I (Consent)
- **Rationale**: No institutional relationship requires explicit consent
- **Requirements**:
  - Explicit patient consent for data copying
  - Clear purpose explanation
  - Consent for each processing activity
- **Documentation**:
  - Independent consent collection
  - Purpose specification
  - Consent management system

## Legal Basis Evaluation Process

### Step 1: Institutional Relationship Analysis

**Questions to answer:**
1. Is your system part of the same legal entity as the hospital?
2. Do you have a formal contract with the hospital for healthcare services?
3. Are your team members licensed healthcare professionals?
4. Do you provide direct care to the same patients?
5. Is your system integrated with hospital operations?

**Documentation needed:**
- Legal entity registration documents
- Service contracts (if applicable)
- Professional licenses
- Care relationship evidence
- Integration agreements

### Step 2: Processing Purpose Evaluation

**Questions to answer:**
1. What is the primary purpose of data processing?
2. Is the purpose directly related to healthcare provision?
3. Are there secondary purposes (research, quality improvement)?
4. How does processing benefit patient care?
5. Are there commercial or non-medical purposes?

**Documentation needed:**
- Purpose specification document
- Care benefit analysis
- Secondary purpose justification
- Commercial activity disclosure

### Step 3: Consent Adequacy Assessment

**For hospital consent reliance:**
1. Does hospital consent mention data sharing?
2. Is "healthcare team" or "care providers" mentioned?
3. Does consent cover "continuity of care"?
4. Are auxiliary systems or parallel records mentioned?
5. Is consent current and valid?

**For independent consent:**
1. Is consent explicit and specific?
2. Does consent cover all processing activities?
3. Is consent freely given and informed?
4. Can consent be easily withdrawn?
5. Is consent documented and verifiable?

### Step 4: Risk and Compliance Analysis

**Risk factors:**
- Patient unawareness of parallel system
- Different privacy policies between systems
- Data sharing beyond care team
- Commercial use of medical data
- Inadequate security measures
- Lack of patient rights implementation

**Compliance requirements:**
- Transparency principle compliance
- Purpose limitation adherence
- Data minimization implementation
- Security measures adequacy
- Patient rights availability
- Consent management capability

## Decision Matrix

| Relationship | Purpose | Consent Quality | Recommended Legal Basis |
|---|---|---|---|
| Same Entity | Medical Care | Hospital Adequate | Art. 11º, II, 'a' |
| Contracted Service | Medical Care | Hospital + Contract | Art. 11º, II, 'a' + Art. 7º, V |
| Independent Care Team | Medical Care | Hospital Adequate | Art. 11º, II, 'a' |
| Independent Care Team | Medical Care | Hospital Inadequate | Art. 11º, I (Specific Consent) |
| Separate Entity | Medical Care | Any | Art. 11º, I (Specific Consent) |
| Any | Research/Commercial | Any | Art. 11º, I (Specific Consent) |

## Legal Basis Documentation Template

### Document Title: Legal Basis Analysis for [SYSTEM_NAME]

**Date**: [DATE]
**Evaluator**: [NAME_TITLE]
**Review Date**: [ANNUAL_REVIEW_DATE]

#### 1. System Information
- **System Name**: 
- **Controller**: 
- **Data Sources**: 
- **Patient Population**: 

#### 2. Institutional Relationship
- **Relationship Type**: 
- **Legal Entity Status**: 
- **Contract Reference**: 
- **Professional Licenses**: 

#### 3. Processing Purposes
- **Primary Purpose**: 
- **Secondary Purposes**: 
- **Care Benefit**: 
- **Commercial Activities**: 

#### 4. Legal Basis Determination
- **Selected Legal Basis**: 
- **LGPD Article Reference**: 
- **Justification**: 
- **Supporting Evidence**: 

#### 5. Consent Analysis
- **Consent Source**: 
- **Adequacy Assessment**: 
- **Gap Analysis**: 
- **Remediation Plan**: 

#### 6. Compliance Measures
- **Transparency Implementation**: 
- **Patient Rights Procedures**: 
- **Security Measures**: 
- **Monitoring Plan**: 

#### 7. Risk Assessment
- **Identified Risks**: 
- **Mitigation Measures**: 
- **Contingency Plans**: 
- **Review Triggers**: 

#### 8. Approval
- **Legal Review**: [NAME_DATE]
- **DPO Approval**: [NAME_DATE]
- **Management Approval**: [NAME_DATE]

---

**Note**: This legal basis analysis should be reviewed annually or when processing activities change significantly. Consult with qualified legal counsel familiar with LGPD healthcare requirements for complex scenarios.