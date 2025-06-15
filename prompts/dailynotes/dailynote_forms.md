# DailyNote Forms Implementation

## Problems

We have two different templates for the DailyNote form: one for creating and another one for updating. The problem is that they have slightly different HTML layouts and information.
The update layout has breadcrumbs but the first link redirect to a broken link (it should redirect to the patient's timeline), and it also has a markdown help section at the bottom, while the create layout does not have any of these features.
The "Voltar" button in the update template should redirect to the patient's timeline as well, but it's currently redirecting to the daily note list.

The create template has no bread crumbs and the "Voltar" button should redirect to the patient's timeline as well. Its cancel button also should redirect to the patient's timeline.

There are some font sizes differences between the two templates.

## Your Mission

Take a look at the two snapshots bellow and identify the differences between them, and make them look as similar as possible.

- @prompts/dailynotes/dailynote_create_form.png corresponds to the template @apps/dailynotes/templates/dailynotes/patient_dailynote_form.html
- @prompts/dailynotes/dailynote_update_form.png corresponds to the template @apps/dailynotes/templates/dailynotes/dailynote_form.html

Please, make a detailed step-by-step plan to implement its features using a vertical slicing approach. Think hard to be as detailed as possible and follow the testing, styling, and all the additional recommendations from CLAUDE.md and from @docs/ folder.
