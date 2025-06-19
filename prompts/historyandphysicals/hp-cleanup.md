# HistoryAndPhysical Templates Cleanup

## Problem

When implementing the HistoryAndPhysical feature, we created some templates that would be used for more than one purpose, like the `historyandphysical_form.html` template, which was intended to create and edit historyandphysicals, however, we ended up not using them for those multiple purposes. This has led to some confusion and clutter in the codebase. We need to cleanup the templates files of code that is used to those other purposes.

Here is a list of the templates that need to be cleaned up and their intended purposes:

- `historyandphysical_form.html`: Used only to edit/update a historyandphysical - should be renamed to `historyandphysical_update_form.html`
- `patient_historyandphysical_form.html`: Used only to create a new historyandphysical - should be renamed to `patient_historyandphysical_create_form.html`
- `historyandphysical_duplicate_form.html`: Used only to duplicate a historyandphysical

## Your Mission

Think hard and make three separate plans in markdown format, each one dedicated to cleaning up one of the above templates and rename it, when necessary as mentioned above. Each plan should contain a detailed step-by-step plan to cleanup the templates files of code that is not needed. Save each plan in a separate file in the @prompts/historyandphysicals folder, one for each template.
Do not execute any plan yet.
