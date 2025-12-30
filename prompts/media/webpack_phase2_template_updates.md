# Phase 2: Template Updates for Bundle Loading

## Objective

Update Django templates to load specific JavaScript bundles based on page requirements instead of loading the global main-bundle.js.

## Prerequisites

- Phase 1 completed successfully
- All webpack bundles generating properly
- Backup of template files

## Step-by-Step Implementation

### Step 1: Analyze Current Template Structure

1. **Map template inheritance hierarchy:**
   - base.html (loads main-bundle.js globally)
   - mediafiles/base.html (extends base.html)
   - Individual form templates (photo_form.html, photoseries_form.html, etc.)

2. **Document current JavaScript loading patterns:**
   - Global JavaScript in base.html
   - Page-specific JavaScript in individual templates
   - Any redundant loading

### Step 2: Create JavaScript Loading Template Block System

1. **Update base.html:**

   ```django
   {% block extra_scripts %}
   <!-- Page-specific JavaScript bundles loaded here -->
   {% endblock extra_scripts %}
   
   {% block mediafiles_scripts %}
   <!-- Mediafiles-specific bundles loaded here -->
   {% endblock mediafiles_scripts %}
   ```

2. **Create template tag for bundle loading (optional enhancement):**

   ```django
   <!-- In templatetags/bundle_tags.py -->
   {% load bundle_tags %}
   {% bundle 'photo' %}  <!-- Loads photo-bundle.js -->
   ```

### Step 3: Update Mediafiles Base Template

1. **Modify apps/mediafiles/templates/mediafiles/base.html:**
   - Add block for common mediafiles JavaScript
   - Load mediafiles-bundle.js if needed globally within mediafiles

   ```django
   {% block mediafiles_scripts %}
   <script src="{% static 'mediafiles-bundle.js' %}"></script>
   {% endblock mediafiles_scripts %}
   
   {% block page_specific_scripts %}
   <!-- Individual pages override this -->
   {% endblock page_specific_scripts %}
   ```

### Step 4: Update Individual Form Templates

#### Step 4a: Photo Form Template

1. **Update apps/mediafiles/templates/mediafiles/photo_form.html:**

   ```django
   {% block page_specific_scripts %}
   <script src="{% static 'photo-bundle.js' %}"></script>
   <script>
   document.addEventListener('DOMContentLoaded', function() {
       if (typeof Photo !== 'undefined') {
           Photo.init();
       }
       // ... existing form handlers
   });
   </script>
   {% endblock page_specific_scripts %}
   ```

#### Step 4b: PhotoSeries Form Templates

1. **Update photoseries_form.html and photoseries_create.html:**

   ```django
   {% block page_specific_scripts %}
   <script src="{% static 'photoseries-bundle.js' %}"></script>
   <script>
   document.addEventListener('DOMContentLoaded', function() {
       if (typeof PhotoSeries !== 'undefined') {
           PhotoSeries.init();
       }
       // ... existing form handlers
   });
   </script>
   {% endblock page_specific_scripts %}
   ```

#### Step 4c: VideoClip Form Template

1. **Update videoclip_form.html:**

   ```django
   {% block page_specific_scripts %}
   <script src="{% static 'videoclip-bundle.js' %}"></script>
   <script>
   document.addEventListener('DOMContentLoaded', function() {
       if (typeof VideoClip !== 'undefined') {
           VideoClip.init();
       }
       // ... existing form handlers
   });
   </script>
   {% endblock page_specific_scripts %}
   ```

### Step 5: Update Timeline Template

1. **Update apps/events/templates/events/patient_timeline.html:**
   - This template displays all media types, so needs multiple bundles

   ```django
   {% block page_specific_scripts %}
   <!-- Load all mediafiles bundles for timeline functionality -->
   <script src="{% static 'photo-bundle.js' %}"></script>
   <script src="{% static 'photoseries-bundle.js' %}"></script>
   <script src="{% static 'videoclip-bundle.js' %}"></script>
   <script>
   document.addEventListener('DOMContentLoaded', function() {
       // Initialize all mediafiles functionality for timeline
       if (typeof Photo !== 'undefined') Photo.init();
       if (typeof PhotoSeries !== 'undefined') PhotoSeries.initializeTimelinePhotoSeries();
       if (typeof VideoClip !== 'undefined') VideoClip.init();
   });
   </script>
   {% endblock page_specific_scripts %}
   ```

### Step 6: Remove Global Bundle Loading

1. **Update base.html:**
   - Remove or comment out main-bundle.js mediafiles loading
   - Keep only core application JavaScript in main-bundle.js

   ```django
   <!-- Remove this line or modify to exclude mediafiles -->
   <!-- <script src="{% static 'main-bundle.js' %}"></script> -->
   
   <!-- Load only core main bundle without mediafiles -->
   <script src="{% static 'main-bundle.js' %}"></script>
   ```

### Step 7: Handle Template Partials and Includes

1. **Update photo lightbox and gallery partials:**
   - apps/mediafiles/templates/mediafiles/partials/photo_lightbox.html
   - apps/mediafiles/templates/mediafiles/partials/photo_gallery.html

2. **Ensure partials don't duplicate JavaScript loading:**
   - Remove any direct script includes from partials
   - Rely on parent template to load required bundles

### Step 8: Testing and Verification

1. **Test each page type:**
   - Photo create/edit page: Only photo-bundle.js should load
   - PhotoSeries create/edit page: Only photoseries-bundle.js should load
   - VideoClip create/edit page: Only videoclip-bundle.js should load
   - Patient timeline: All bundles should load

2. **Verify JavaScript functionality:**
   - Upload functionality works on each page
   - No console errors about missing objects
   - No duplicate initialization messages

3. **Check network tab:**
   - Confirm only expected bundles are loaded per page
   - Verify bundle sizes are reasonable
   - No 404 errors for JavaScript files

## Expected Outcomes

- ✅ Each page loads only the JavaScript it needs
- ✅ No more PhotoSeries messages on photo pages
- ✅ Faster page loading due to smaller JavaScript payload
- ✅ Clean console output with page-specific debugging only

## Rollback Plan

1. **Revert template changes:**

   ```bash
   git checkout HEAD -- apps/mediafiles/templates/
   git checkout HEAD -- apps/events/templates/events/patient_timeline.html
   ```

2. **Restore global bundle loading in base.html**

## Common Issues and Solutions

1. **Bundle not found (404 error):**
   - Verify webpack build completed successfully
   - Check static file collection: `python manage.py collectstatic`

2. **JavaScript object undefined:**
   - Verify bundle loading order
   - Check that bundle actually contains expected code

3. **Duplicate initialization:**
   - Ensure Phase 3 auto-initialization removal is completed
   - Check that templates don't call init() multiple times

## Testing Checklist

- [ ] Photo pages load only photo-bundle.js
- [ ] PhotoSeries pages load only photoseries-bundle.js  
- [ ] VideoClip pages load only videoclip-bundle.js
- [ ] Timeline pages load all required bundles
- [ ] All upload functionality works correctly
- [ ] No JavaScript console errors
- [ ] No 404 errors for bundle files
- [ ] Page load times improved
- [ ] Clean browser network tab showing only required bundles

## Notes

- This phase changes how JavaScript is loaded but not how it initializes
- Auto-initialization patterns still exist (will be removed in Phase 3)
- Template changes are the most visible part of this refactor
- Thorough testing required as this affects all mediafiles functionality
