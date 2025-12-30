# Plan to implement media upload feature

## Context

We need to implement a way to users upload media files (single images,
images series, and short video clips up to 2 minutes) to be used in the
patient record. This media should be related to a patient and should
have a datetime and description fields.
For single images, their event_card should show a thumbnail of the image and
for images series, it should show a thumbnail of the first image and a
badge with the number of images in the series.
For short video clips, their event_card should show a thumbnail of the
first frame of the video and a badge with the duration of the video.
The event_card should have a button to open the media in a modal or in a
new page inside the dashboard content area.

I want to know your thoughts on how to implement this feature.

- Should we create three different models and event types for each media
  type?
- Should we create a single model and event type for all media types?
- Should we create a single model and event type for all media types and
  use a field to differentiate between them?
- Should we create a single model and event type for all media types
  and use a field to differentiate between them and another field to
  differentiate between single images, images series, and short video clips?

Please, think hard on this feature and give me your recommendations on
how to implement it considering the context, the requirements above and
the UI/UX.
