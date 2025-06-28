# Implementation Plan for Outpatient Prescription System

Based on the PRD in `/prompts/outprescriptons/requirements.md`, I need a detailed implementation plan for creating two new Django apps:

## App Structure Requirements
1. **Drug Templates App**
   - Create as an independent app in the `apps/` directory following Django conventions
   - Implement the `DrugTemplate` model with all required fields and functionality

2. **Outpatient Prescriptions App**
   - Create as an independent app in the `apps/` directory following Django conventions
   - Import and use the Drug Templates app where necessary
   - Extend the existing Event system with a new `OutpatientPrescription` model (event_type=11)

## Implementation Details
- Provide a complete scaffolding for both apps including:
  - Models with all required fields and relationships
  - Views for all CRUD operations
  - Forms with proper validation
  - URLs configuration
  - Templates following the project's design patterns
  - Admin configuration
  - Permissions implementation

## Task Breakdown
- Break down the implementation into 20-30 distinct tasks
- Each task should have 3-5 detailed sub-tasks with step-by-step instructions
- Follow the vertical slicing approach used in other event implementations

## UI/UX Requirements
- All UI components must follow the established EquipeMed design patterns
- Use Bootstrap 5.3.6 with the medical theme for consistent styling
- Reference existing apps like `apps/dailynotes`, `apps/simplenotes`, and `apps/mediafiles` for UI patterns
- Follow the styling guidelines in the `docs/` folder
- Implement the HTML+browser print strategy for prescription documents

## Integration Requirements
- Follow the existing permission system with appropriate decorators
- Integrate with the hospital context middleware
- Maintain proper audit trails using Event model's audit fields
- Ensure data independence between templates and prescriptions

Please provide this implementation plan with detailed tasks that a coding assistant like you can follow to build these features according to the project's standards and patterns.