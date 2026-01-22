# Admin Guide: Managing Medical Specialties

This guide explains how administrators can manage medical specialties and assign them to users in the EquipeMed system.

## Table of Contents

1. [Creating Medical Specialties](#creating-medical-specialties)
2. [Managing Existing Specialties](#managing-existing-specialties)
3. [Assigning Specialties to Users](#assigning-specialties-to-users)
4. [Understanding Primary vs Current Specialty](#understanding-primary-vs-current-specialty)
5. [Troubleshooting](#troubleshooting)

---

## Creating Medical Specialties

### Access the Specialty Management

1. Log in to Django Admin
2. Navigate to **Especialidades Médicas** under the Accounts section

### Adding a New Specialty

1. Click **Adicionar Especialidade Médica** (Add Medical Specialty)
2. Fill in the required fields:
   - **Nome da Especialidade**: Full name (e.g., "Cirurgia Vascular")
   - **Sigla**: Abbreviation (e.g., "CIRVASC") - max 10 characters
3. Optionally add a **Descrição**: Detailed description of the specialty
4. Ensure **Ativa** checkbox is checked (default)
5. Click **Salvar** (Save)

### Field Requirements

| Field | Required | Max Length | Description |
|-------|-----------|-------------|-------------|
| Nome da Especialidade | Yes | 100 | Full specialty name (unique) |
| Sigla | Yes | 10 | Abbreviation (unique) |
| Descrição | No | Unlimited | Optional detailed description |
| Ativa | No | - | If unchecked, specialty won't be available for selection |

### Naming Conventions

- Use Portuguese names (e.g., "Cirurgia Vascular", not "Vascular Surgery")
- Abbreviations should be uppercase and concise (e.g., "CIRVASC", "CIRGER")
- Specialties are ordered alphabetically by name in the UI

### Pre-populated Specialties

The system comes with 30 common Brazilian medical specialties pre-loaded:

| Specialty | Abbreviation |
|----------|-------------|
| Anestesiologia | ANEST |
| Cardiologia | CARDIO |
| Cirurgia Cardíaca | CIRCARD |
| Cirurgia Geral | CIRGER |
| Cirurgia Pediátrica | CIRPED |
| Cirurgia Plástica | CIRPLAST |
| Cirurgia Torácica | CIRTORAC |
| Cirurgia Vascular | CIRVASC |
| Clínica Médica | CLIN |
| Dermatologia | DERM |
| Emergência | EMERG |
| Endocrinologia | ENDO |
| Gastroenterologia | GASTRO |
| Ginecologia e Obstetrícia | GO |
| Infectologia | INFECTO |
| Nefrologia | NEFRO |
| Neurocirurgia | NEUROCIR |
| Neurologia | NEURO |
| Oncologia Clínica | ONCO |
| Ortopedia | ORTO |
| Oftalmologia | OFTALMO |
| Otorrinolaringologia | ORL |
| Pediatria | PED |
| Pneumologia | PNEUMO |
| Psiquiatria | PSIQ |
| Reumatologia | REUMA |
| Radiologia | RADIO |
| Urologia | URO |
| UTI Adulto | UTI |
| UTI Pediátrica | UTIPED |

---

## Managing Existing Specialties

### Viewing All Specialties

The specialties list shows:
- **Name**: Full specialty name
- **Sigla**: Abbreviation
- **Ativa**: Status (yes/no)
- **Criado em**: Creation date

### Filtering Specialties

Use the sidebar filters to:
- Show only active specialties: Click **Ativa** → **Sim**
- Show all specialties: Click **Ativa** → **Todos**

### Searching Specialties

Use the search bar to find specialties by:
- Name (e.g., "Cirurgia")
- Abbreviation (e.g., "CIR")

### Deactivating a Specialty (Soft Delete)

**Do NOT hard delete** specialties that have been assigned to users!

1. Open the specialty for editing
2. Uncheck **Ativa**
3. Click **Salvar** (Save)

**What happens when deactivated:**
- ✅ Specialty stays in database (for historical records)
- ✅ Existing user assignments are preserved
- ❌ Specialty no longer appears in dropdowns
- ❌ Users cannot select it as their current specialty
- ⚠️ Admins can still see and reactivate it

### Why Not Hard Delete?

Django will **prevent** deletion if:
- Any users have this specialty assigned
- The specialty is set as a user's current specialty

If you try to delete a used specialty, you'll see:
```
Cannot delete MedicalSpecialty because it is referenced
through a protected foreign key
```

**Use soft delete (uncheck "Ativa") instead.**

---

## Assigning Specialties to Users

### Accessing User Management

1. Navigate to **Usuários**
2. Click on a user's username to edit

### Using the Inline Form

Scroll down to the **Especialidades do Usuário** (User Specialties) section:

![Specialty Inline](https://example.com/specialty-inline-screenshot.png)

### Adding a Specialty to a User

1. Click **Adicionar outra Especialidade do Usuário** (Add another User Specialty)
2. Select the **Especialidade** from the dropdown (only active specialties shown)
3. **Optionally** check **Especialidade Principal** if this is the user's main/residency specialty
4. Click **Salvar** (Save) at the bottom of the page

### Assigning Multiple Specialties

A user can have **multiple specialties** assigned:

1. Add one specialty (e.g., Cirurgia Geral)
2. Click **Adicionar outra Especialidade do Usuário** again
3. Add another specialty (e.g., Cirurgia Vascular)
4. Repeat as needed

**Example:** A surgeon might have:
- Primary: Cirurgia Geral (main residency)
- Secondary: Cirurgia Vascular (additional certification)

### Marking a Primary Specialty

For **residents** and medical students, mark the **training specialty** as primary:

1. Check **Especialidade Principal** for the residency specialty
2. Leave secondary specialties unchecked

**Why this matters:**
- The primary specialty is used as the default when no current specialty is set
- It helps identify the user's main area of training/practice
- It's displayed with a star icon ⭐ in the profile

### Viewing Assignment History

Each specialty assignment shows:
- **Especialidade**: Name of assigned specialty
- **Especialidade Principal**: Whether it's the primary one
- **Atribuída em**: When the assignment was created

---

## Understanding Specialty Concepts

The system has **three related concepts** for managing medical specialties:

### 1. Multiple Assigned Specialties

**What it means:** A user can have **multiple specialties** assigned to their account.

**Who manages it:** Administrators only (via User Admin → "Especialidades do Usuário")

**Use cases:**
- A surgeon with multiple certifications (e.g., General Surgery + Vascular Surgery)
- A doctor with additional qualifications (e.g., Cardiology + Internal Medicine)
- Residents with rotations through different departments

**How it works:**
1. Admin goes to User Admin
2. Scrolls to "Especialidades do Usuário" section
3. Clicks "Adicionar outra Especialidade do Usuário"
4. Selects specialty from dropdown
5. Repeats for each additional specialty
6. Clicks "Salvar" at bottom of page

**In the UI:**
- Shown as badges on user's profile page
- All assigned specialties listed in avatar dropdown
- Primary specialty marked with star icon (⭐)

### 2. Primary Specialty (Especialidade Principal)

**What it means:** The **main/training specialty** for a user.

**Who manages it:** Administrators only (via User Admin → check "Especialidade Principal")

**Use cases:**
- **Residents:** Mark their main residency specialty
- **Medical Students:** Mark their primary area of training
- **Doctors with multiple certifications:** Mark their main specialization

**How it works:**
1. Admin goes to User Admin
2. Scrolls to "Especialidades do Usuário" section
3. Checks **"Especialidade Principal"** checkbox for the appropriate specialty
4. Clicks "Salvar" at bottom of page

**In the UI:**
- Displayed with a star icon (⭐) on profile
- Displayed with a star icon (⭐) in avatar dropdown
- Used as **default** when user hasn't selected a "current" specialty

**Important notes:**
- ⚠️ Only ONE specialty should be marked as primary per user
- ⚠️ If multiple are marked, the system uses the first alphabetically
- ⚠️ Primary is **not** automatically updated when user changes current specialty

### 3. Current Specialty (Especialidade Atual)

**What it means:** The specialty the user is **currently working with** or wants to use.

**Who manages it:** Users themselves (via Profile page)

**Use cases:**
- A vascular surgeon switching context to general surgery
- A cardiologist covering for an internist rotation
- A multi-specialty doctor selecting appropriate specialty for documentation

**How it works:**
1. User clicks their name in top-right avatar dropdown
2. Scroll to "Trocar Especialidade" section
3. Clicks on desired specialty
4. Page automatically reloads with new selection

**Alternative method (Profile page):**
1. User goes to their profile (Meu Perfil)
2. Clicks "Editar Perfil"
3. Selects specialty from "Especialidade Atual" dropdown
4. Clicks "Update Profile" button

**In the UI:**
- Displayed below user name in avatar dropdown
- Shown with checkmark (✓) in dropdown when selected
- Filtered in profile form dropdown to only show assigned specialties

**Important notes:**
- ✅ User can change it anytime without admin approval
- ✅ Only shows specialties that are **assigned** to user
- ✅ Only shows specialties that are **active**
- ✅ Changes are logged/audited in database

---

## Relationship Between the Three Concepts

```
┌─────────────────────────────────────────────────────────────┐
│              User: Dr. João Silva                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Multiple Assigned Specialties:                     │
│    ✓ Cirurgia Geral      (Primary: ⭐)            │
│    ✓ Cirurgia Vascular  (Secondary)                 │
│    ✓ Cardiologia         (Secondary)                 │
├─────────────────────────────────────────────────────────────┤
│ 2. Primary Specialty:                                 │
│    → Cirurgia Geral                                 │
│      (Set by admin, marked with ⭐)                  │
├─────────────────────────────────────────────────────────────┤
│ 3. Current Specialty:                                  │
│    → Cirurgia Vascular                                │
│      (Selected by user, shows ✓ checkmark)             │
└─────────────────────────────────────────────────────────────┘
```

### When Each Concept is Used

| Situation | Which Specialties Appear | Primary Used | Current Used |
|-----------|-------------------------|---------------|--------------|
| Profile page | All assigned badges | ⭐ icon shows on primary | Highlighted separately |
| Avatar dropdown | All assigned with checkmarks | ⭐ icon shows on primary | ✓ checkmark on selected |
| Default display (no current set) | Shows first assigned | Primary if exists | Falls back to primary |
| User changes selection | No change | No change | Updates to selection |
| Admin adds/removes | Updates list | Updates if removed | May need new selection |

---

## Understanding Primary vs Current Specialty

The system has **two concepts** for specialties:

### Primary Specialty (Especialidade Principal)

**Purpose:** Identifies the user's main training or practice area

**Who sets it:** Admin only (via inline form)

**When it's used:**
- As the default when user has no "current" specialty selected
- Shown with a star icon (⭐) in the profile and dropdown
- Important for residents (marks their residency specialty)

**Analogy:** Like "major" in college - your main area of study

### Current Specialty (Especialidade Atual)

**Purpose:** What the user is currently working with

**Who sets it:** User can change it themselves via their profile

**When it's used:**
- Displayed in avatar dropdown (top-right of every page)
- Filters/views based on user's current context
- Shown with checkmark (✓) in dropdown when selected

**Analogy:** Like "current course" - what you're taking this semester

### Example Scenarios

#### Scenario 1: Multi-Specialty Surgeon

**Dr. Ana Costa** (Vascular and General Surgeon)

| Concept | Value | Set By | When Used |
|---------|-------|----------|------------|
| Multiple Assigned | Cirurgia Vascular, Cirurgia Geral, Cardiologia | Admin | Always |
| Primary Specialty | Cirurgia Vascular | Admin (⭐) | Default display |
| Current Specialty | Cirurgia Geral | User (self-selected) | Current context |

**Workflow:**
1. Admin creates specialties: Cirurgia Vascular, Cirurgia Geral, Cardiologia
2. Admin assigns all three to Ana (during residency + certifications)
3. Admin marks Cirurgia Vascular as Primary (her residency specialty)
4. Ana logs in → sees Cirurgia Vascular as default
5. Ana goes to profile → sees all three with star on Vascular
6. Ana switches to Cirurgia Geral for General Surgery rotation
7. Avatar dropdown shows Cirurgia Geral with checkmark

#### Scenario 2: Resident

**Dr. Pedro Santos** (Surgery Resident)

| Concept | Value | Set By | When Used |
|---------|-------|----------|------------|
| Multiple Assigned | Cirurgia Geral | Admin | Always |
| Primary Specialty | Cirurgia Geral | Admin (⭐) | Default display |
| Current Specialty | (not set) | — | Falls back to Primary |

**Workflow:**
1. Admin creates Cirurgia Geral specialty
2. Admin assigns to Pedro and marks as Primary
3. Pedro logs in → sees Cirurgia Geral as current (fallback)
4. Pedro profile shows Cirurgia Geral with star icon

#### Scenario 3: Multi-department Doctor

**Dr. Carlos Lima** (Intensivist with multiple certifications)

| Concept | Value | Set By | When Used |
|---------|-------|----------|------------|
| Multiple Assigned | Clínica Médica, UTI Adulto, Cardiologia | Admin | Always |
| Primary Specialty | Clínica Médica | Admin (⭐) | Default display |
| Current Specialty | UTI Adulto | User (self-selected) | ICU rotation |

**Workflow:**
1. Admin assigns Clínica Médica as Primary (main area)
2. Admin adds UTI Adulto and Cardiologia as additional certifications
3. Carlos starts ICU rotation → switches to UTI Adulto
4. Carlos goes to Cardiology rotation → switches to Cardiologia
5. Carlos returns to General Medicine → switches back to Clínica Médica
6. All switches logged in database for audit trail

---

## Troubleshooting

### Issue: Specialty Not Appearing in User Dropdown

**Symptom:** User cannot see a specialty in their profile dropdown

**Possible Causes:**

1. **Specialty not assigned to user**
   - Check: User admin → scroll to "Especialidades do Usuário"
   - Fix: Add the specialty via the inline form

2. **Specialty is inactive**
   - Check: Specialties list → look at "Ativa" column
   - Fix: Edit specialty and check "Ativa"

3. **User is not a doctor/resident**
   - Check: User's "Tipo de Profissão" in user admin
   - Note: All user types can have specialties, but typically only doctors/residents use them

### Issue: Cannot Delete a Specialty

**Symptom:** Error when trying to delete a specialty

**Error Message:**
```
Cannot delete MedicalSpecialty because it is referenced
through a protected foreign key
```

**Solution:**
- Do NOT delete
- Uncheck "Ativa" instead (soft delete)
- This preserves historical assignments

### Issue: Duplicate Specialty Names

**Symptom:** Cannot create specialty with existing name or abbreviation

**Error Message:**
```
Especialidade Médica with this Nome da Especialidade already exists.
```

**Solution:**
1. Check existing specialties for a similar one
2. Edit the existing one instead
3. Or use a different name/abbreviation

### Issue: User Has Two Primary Specialties

**Symptom:** Multiple specialties marked as primary for a user

**Impact:**
- The system uses the first one alphabetically
- Both show with star icons (confusing)

**Solution:**
1. Go to User Admin
2. Edit the user
3. In "Especialidades do Usuário", uncheck all but the real primary
4. Save

---

## Best Practices

### For Creating Specialties

✅ Use standard Brazilian medical terminology
✅ Keep abbreviations short (2-10 characters)
✅ Always add a description for clarity
✅ Only deactivate unused specialties (don't delete)

### For Assigning Specialties

✅ Mark residency/training specialty as primary
✅ Assign additional certifications as non-primary
✅ Re-verify user specialties after account renewals
✅ Document specialty assignments for audit purposes

### For User Training

✅ Show users how to change their current specialty via profile
✅ Explain the difference between primary and current specialty
✅ Train users to select their current context for accurate records

---

## Getting Help

If you encounter issues not covered in this guide:

1. Check Django logs for error messages
2. Review the OpenSpec proposal: `openspec/changes/add-medical-specialty/`
3. Contact technical support with:
   - User account affected
   - Specialty name and abbreviation
   - Screenshot of error

---

## Quick Reference: Inline Form Fields

| Field | Description | Required |
|-------|-------------|----------|
| Especialidade | Dropdown of all active specialties | Yes |
| Especialidade Principal | Checkbox to mark as main specialty | No |
| Atribuída em | Auto-populated timestamp (read-only) | N/A |

---

## Related Documentation

- [User Guide: Managing Your Specialty](./user_guide_specialties.md) *(not yet created)*
- [API Documentation: Specialty Endpoints](./api_specialties.md) *(not yet created)*
- [OpenSpec Proposal](../openspec/changes/add-medical-specialty/proposal.md)
