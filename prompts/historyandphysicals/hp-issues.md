# History and Physicals App Implementation Issues

## Problems

1. @apps/historyandphysicals/templates/historyandphysicals/historyandphysical_duplicate_form.html
   it uses crispy forms, but it should not use it (see its analogous template in dailynotes app: @apps/dailynotes/templates/dailynotes/dailynote_duplicate_form.html).

2. @apps/historyandphysicals/templates/historyandphysicals/patient_historyandphysical_form.html
   it uses crispy forms, but it should not use it (see its analogous template in dailynotes app: @apps/dailynotes/templates/dailynotes/patient_dailynote_form.html).
   it has a patient information section that is not necessary, and does not exist in the analogous template in dailynotes app.

3. create a @apps/events/templates/events/partials/event_card_historyandphysical.html template that is similar to the @apps/events/templates/events/partials/event_card_dailynote.html template, but with the necessary changes to display the history and physical event correctly, and update @apps/events/templates/events/patient_timeline.html to use it.

## Your Mission

Think hard and make three separate plans in markdown format, each one dedicated to fix one of the issues mentioned above. Each plan should contain a step-by-step plan to fix its issue.
After that, implement implement each plant one at a time.
Remember that the look and feel of the history and physicals app should be as similar as possible to the dailynotes app.
