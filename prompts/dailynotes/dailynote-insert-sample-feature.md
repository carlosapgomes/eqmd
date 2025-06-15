# DailyNote Insert Sample Content Feature Implementation

## Your Mission

Create a detailed step-by-step plan to implement a feature that allows users to insert sample content into a dailynote.

This feature should be available in the following templates:

- @apps/dailynotes/templates/dailynotes/dailynote_form.html
- @apps/dailynotes/templates/dailynotes/patient_dailynote_form.html
- @apps/dailynotes/templates/dailynotes/dailynote_duplicate_form.html

The sample content should be a button or dropdown that shows a list of `SampleContent` objects from the @apps/sample_content app filtered by `event_type` = `Event.DAILY_NOTE_EVENT` or it can open a modal with the list of sample content. When clicked, the content should be inserted into the `content` field of the dailynote form.

Ideally the content should be inserted in the current cursor position in the easyMDE editor element, however if this is not possible, it should be inserted at the end of the content or replace the current content.

Do not write any code, show me your plan, and ask for permission to proceed.
