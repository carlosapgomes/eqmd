# Issue: Timeline in Desktop Screens

## Overview

This issue addresses the display of the timeline in desktop screens, ensuring it looks good and functions well on larger devices.

Here is a screenshot of the old timeline in desktop mode:
@prompts/events/timeline-desktop-old.png

After making some adjustments to improve the timeline on the mobile from:
@prompts/events/timeline-mobile.png
to:
@prompts/events/timeline-mobile-current.png

the timeline in desktop mode is not looking good anymore, see this:
@prompts/events/timeline-desktop-current.png

See also these relevant files:
@apps/patients/urls.py
@apps/events/views.py
@apps/events/templates/events/patient_timeline.html
@apps/events/templates/events/patient_events_list.html
@apps/events/static/events/css/timeline.css
@apps/events/static/events/js/timeline.js

## Your Mission

Try to restore as much as possible the original look and feel of the timeline in desktop mode, but keeping the changes that you did to make it look good in mobile mode.
