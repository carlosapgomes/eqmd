# SimpleNotes App Implementation

Create a new app in the @apps/ folder that has exactly the same
structure and features of the @apps/dailynotes/ app, however it should have
another name (simplenotes), because it will have a different semantic in the
patient record. "Simple Notes" exist to keep track of more eventual observations
and information about a patient that are added not during a routine visit, rather
when something out of the ordinary happens. It is more related to the day-to-day
management of a patient, rather than the medical evolution of a patient.
Correct me if I am wrong, but if you agree with this approach, make a
detailed step-by-step plan to duplicate all the structure and features
of @apps/dailynotes into a new app called "simplenotes" to be created in a folder
with the same name @apps/simplenotes/.

The event_type for the simplenotes app should be Event.SIMPLE_NOTE_EVENT.

Create also an event_card_simplenote.html template at
@apps/events/templates/events/partials/
that is similar to the
@apps/events/templates/events/partials/event_card_dailynote.html template,
but with the necessary changes to display the simplenote event correctly,
and update
@apps/events/templates/events/patient_timeline.html to use it.
