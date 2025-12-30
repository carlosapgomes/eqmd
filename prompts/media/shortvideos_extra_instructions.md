# Extra Instructions for the Short Video Clips Feature Plan

1. Generic navigation

As adding a short video clip is accessible only from the `Criar Evento` dropdown in the patient's timeline view, every successful or canceled video clip operation (Create, Update, Delete, Detail) should return to the patient's timeline view.

All video clip pages should have the same breadcrumb navigation, starting from the patient's detail page, followed by the timeline, and then the video clip page.

1. Styling
Follow the overall styling and structure used for the photo feature, from the @app/mediafiles.

2. Video clip detail page
Video clip details should be very similar to the photo detail page, and should let the user play, move forward and backward, replay and pause the video. Most of the video clips will be recorded with cellphones. It is not necessary to have a download button for the video. Please make sure the video player is responsive and works well on mobile devices.

3. Timeline card
The timeline card for a video clip should show the duration of the video clip, similar to the number of photos in a photoseries, and make sure the video thumbnail is generated automatically from the first frame of the video.
It should be created at @app/events/templates/events/partials/event_card_videoclip.html
Contrary to the photo event card, the video clip event card should not have a zoom (bi-zoom-in) button, only download, details and edit buttons.
Clicking on the video thumbnail should open the video in a modal, very similar to the photo modal, with play, pause, forward and backward controls.

4. Editing
Editing a video clip is similar to editing a photo, the user can only change description, datetime and caption.
