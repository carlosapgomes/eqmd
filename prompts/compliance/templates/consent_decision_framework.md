# LGPD Consent Strategy Decision Framework

## Hospital Consent Evaluation Checklist

### Step 1: Relationship Assessment

**Question 1: What is your relationship with the hospital?**
- [ ] **Same legal entity** - Your system is part of the hospital's infrastructure
- [ ] **Contracted service** - You provide services under contract to the hospital  
- [ ] **Independent parallel system** - Separate entity copying hospital data
- [ ] **Shared care team** - Healthcare professionals serving same patients

**Legal Implication:**
- Same entity: Can use hospital consent under shared institutional processing
- Contracted: May use hospital consent if contract covers data processing
- Independent: Need separate consent evaluation
- Shared team: Can use professional relationship exception

### Step 2: Hospital Consent Document Review

**Question 2: Does the hospital consent form include:**
- [ ] Specific mention of "auxiliary systems" or "parallel medical records"
- [ ] Authorization for "data sharing with healthcare team"
- [ ] Permission for "continuity of care" activities
- [ ] General consent for "medical data processing"

**Scoring:**
- 4/4 checked: Hospital consent likely sufficient
- 3/4 checked: Hospital consent probably sufficient with documentation
- 2/4 checked: Supplementary consent recommended
- 1/4 checked: Separate consent required

### Step 3: Data Processing Activities Assessment

**Question 3: What activities does your system perform?**

**Always Covered by Hospital Consent:**
- [ ] Basic patient identification
- [ ] Medical record storage
- [ ] Care coordination
- [ ] Emergency contact procedures

**Requires Explicit Evaluation:**
- [ ] Medical photography/video
- [ ] Research activities
- [ ] Quality improvement analytics
- [ ] Data sharing with external systems

**Never Covered by Hospital Consent:**
- [ ] Marketing communications
- [ ] Commercial data sharing
- [ ] Non-medical research
- [ ] Patient contact for non-medical purposes

### Step 4: Risk Assessment

**Question 4: Risk factors present:**
- [ ] Hospital and your system have different privacy policies
- [ ] Hospital consent language is vague or outdated
- [ ] Patients are not informed about your parallel system
- [ ] Your system processes data differently than hospital
- [ ] You store data longer than hospital
- [ ] You share data with parties hospital doesn't

**Risk Level:**
- 0-1 factors: **Low risk** - Hospital consent acceptable
- 2-3 factors: **Medium risk** - Document relationship, consider supplementary consent
- 4+ factors: **High risk** - Separate consent collection required

## Decision Matrix

| Relationship | Hospital Consent Quality | Risk Level | Recommended Approach |
|---|---|---|---|
| Same Entity | High | Low | Use hospital consent |
| Same Entity | Medium | Low-Medium | Document + Use hospital consent |
| Contracted | High | Low | Use hospital consent + Contract clause |
| Contracted | Medium | Medium | Supplementary consent form |
| Independent | Any | Medium-High | Separate consent collection |
| Shared Team | High | Low | Use hospital consent + Professional basis |

## Implementation Strategies

### Strategy A: Use Hospital Consent (Lower Risk)

**When to use:**
- Same legal entity or contracted service
- High-quality hospital consent forms
- Low risk assessment score

**Implementation:**
1. Document legal relationship with hospital
2. Store scanned copies of hospital consent forms
3. Map hospital consent to system activities
4. Create consent records with `consent_source='hospital_form'`
5. Regular validation of consent adequacy

**Pros:**
- Lower administrative burden
- Familiar process for medical staff
- Reduced patient friction

**Cons:**
- Dependent on hospital consent quality
- Less granular control
- Potential gaps for specific activities

### Strategy B: Supplementary Consent (Balanced Risk)

**When to use:**
- Medium risk assessment
- Hospital consent has minor gaps
- Need explicit consent for specific activities

**Implementation:**
1. Use hospital consent for basic medical activities
2. Collect brief supplementary consent for gaps
3. Focus on high-risk activities (photos, research)
4. Create hybrid consent records

**Pros:**
- Addresses specific compliance gaps
- Maintains most existing workflow
- Provides clear legal protection

**Cons:**
- Additional administrative step
- Patient needs to provide consent twice
- More complex tracking

### Strategy C: Independent Consent Collection (Higher Compliance)

**When to use:**
- Independent parallel system
- High risk assessment score
- Poor quality hospital consent
- Need maximum legal protection

**Implementation:**
1. Design comprehensive consent form
2. Collect consent during patient onboarding
3. Train staff on consent procedures
4. Implement robust consent management

**Pros:**
- Maximum LGPD compliance
- Full control over consent quality
- Clear legal basis for all activities
- Granular consent tracking

**Cons:**
- Higher administrative burden
- Additional training required
- Patient experience friction
- Duplicate consent collection

## Documentation Requirements

Regardless of strategy chosen, document:

1. **Legal Basis Analysis**
   - Relationship assessment results
   - Hospital consent evaluation
   - Risk assessment scoring
   - Strategy decision rationale

2. **Consent Source Tracking**
   - Hospital consent reference numbers
   - Scanned document storage
   - Consent validity periods
   - Gap identification

3. **Audit Trail**
   - Decision-making process
   - Staff training records
   - Consent validation procedures
   - Compliance monitoring results

## Regular Review Process

**Quarterly Review:**
- Hospital consent form updates
- New processing activities assessment
- Risk factor changes
- Strategy effectiveness evaluation

**Annual Review:**
- Full relationship assessment
- Legal basis documentation update
- Consent strategy optimization
- Compliance audit preparation