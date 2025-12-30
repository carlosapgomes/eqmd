# Extra Instructions for Photo Series Feature Plan

1. Generic navigation

As adding a photoseries is accessible only from the `Criar Evento` dropdown in the patient's timeline view, every successful or canceled photoseries operation (Create, Update, Delete, Detail) should return to the patient's timeline view.

All photoseries pages should have the same breadcrumb navigation, starting from the patient's detail page, followed by the timeline, and then the photoseries page.

1. Styling
Follow the overall styling and structure used for the photo feature, from the @app/mediafiles.

2. Photoseries detail page
Photoseries details should be very similar to the photo detail page, but should show the photoseries as a Carrousel, with the ability to navigate between photos. Also, each photo should have an action buttons group like the ones in the photo feature: zoom in, zoom out, original size, full page, download.

3. Timeline card
The timeline card for a photoseries should show the number of photos in the series, and the first photo as a thumbnail.
It should be created at @app/events/templates/events/partials/event_card_photoseries.html
Contrary to the photo event card, the photoseries event card should not have an zoom (bi-zoom-in) button, only download, details and edit buttons.

4. Editing
Editing a photoseries is similar to editing a photo, the user can only change description, datetime and caption.
