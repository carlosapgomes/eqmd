# DailyNote Templates Cleanup

## Problem

When implementing the DailyNote feature, we created some templates that would be used for more than one purpose, like the `dailynote_form.html` template, which was intended to create and edit dailynotes, however, we ended up not using them for those multiple purposes. This has led to some confusion and clutter in the codebase. We need to cleanup the templates files of code that is used to those other purposes.

Here is a list of the templates that need to be cleaned up and their intended purposes:

- `dailynote_form.html`: Used only to edit/update a dailynote
- `patient_dailynote_form.html`: Used only to create a new dailynote
- `dailynote_duplicate_form.html`: Used only to duplicate a dailynote

## Your Mission

Think hard and make three separate plans in markdown format, each one dedicated to cleaning up one of the templates mentioned above. Each plan should contain a detailed step-by-step plan to cleanup the templates files of code that is not needed. Save each plan in a separate file in the @prompts/dailynotes folder, one for each template.
Do not execute any plan yet.
