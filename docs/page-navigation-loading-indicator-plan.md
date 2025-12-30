# Page Navigation Loading Indicator Implementation Plan

## Overview

Implement a global page navigation loading indicator to improve UX during page transitions and form submissions on VPS deployment with slower response times.

## Requirements

- Show loading overlay during page navigation and form submissions
- Use existing medical theme colors and Bootstrap components
- Safe implementation that doesn't interfere with existing functionality
- Smart filtering to avoid affecting search/filter forms and AJAX operations
- Preserve existing behavior for specialized upload systems (FilePond)

## Implementation Steps

### Step 1: Add Loading Overlay HTML Structure ✅ COMPLETED

**File**: `templates/base_app.html`
**Location**: After `{% endblock %}` line and before `{% block content %}`

```html
<!-- Page Navigation Loading Overlay -->
<div id="pageLoadingOverlay" class="page-loading-overlay d-none">
  <div class="page-loading-content">
    <div
      class="spinner-border text-medical-teal"
      role="status"
      style="width: 3rem; height: 3rem;"
    >
      <span class="visually-hidden">Carregando...</span>
    </div>
    <div class="mt-3 text-medical-dark-gray fw-medium">
      Carregando página...
    </div>
  </div>
</div>
```

### Step 2: Add CSS Styles ✅ COMPLETED

**File**: `assets/scss/main.scss`
**Location**: Add at the end of the file, after existing styles

```scss
// Page Navigation Loading Indicator
// --------------------------------------------------
.page-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  z-index: 9999;
  transition: opacity 0.2s ease-in-out;

  .page-loading-content {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;

    .spinner-border {
      border-width: 0.25em;
    }
  }
}

// Ensure loading overlay doesn't interfere with existing modals
.modal.show ~ .page-loading-overlay {
  z-index: 1040; // Below Bootstrap modal backdrop (1050)
}
```

### Step 3: Create Navigation Loading JavaScript ✅ COMPLETED (Updated)

**File**: `assets/js/page-loading.js`

**Key Features:**

- Handles both link navigation and form submissions
- Smart filtering to avoid interfering with existing functionality
- Multiple escape hatch mechanisms for special cases

**Core Implementation:**

- Shows loading overlay during page navigation
- Shows loading overlay during form submissions that navigate to new pages
- Skips GET forms that don't change URL (search/filter forms)
- Provides multiple ways to opt out specific forms or links

**See current implementation in the file for complete code including form submission handling.**

### Step 4: Update Webpack Configuration ✅ COMPLETED

**File**: `webpack.config.js`
**Action**: Add the new JavaScript file to the copy patterns

Find the existing copy patterns section and add:

```javascript
{
  from: "assets/js/page-loading.js",
  to: "js/page-loading.js",
},
```

### Step 5: Include JavaScript in Base Template ✅ COMPLETED

**File**: `templates/base_app.html`
**Location**: In the script section at the bottom, before the closing `{% endblock %}`

```html
<script src="{% static 'js/page-loading.js' %}"></script>
```

### Step 6: Build and Test ✅ COMPLETED

**Commands to run:**

```bash
npm run build
uv run python manage.py runserver
```

## Escape Hatch Mechanisms (How to Opt Out)

The loading spinner includes multiple ways to prevent it from showing on specific elements or forms that have their own loading states.

### For Links (Anchor Tags)

**Method 1: CSS Class**

```html
<a href="/some-page" class="no-loading">No spinner link</a>
```

**Method 2: Data Attribute**

```html
<a href="/some-page" data-no-loading>No spinner link</a>
```

**Automatically Skipped Links:**

- External links (different hostname)
- Hash/anchor links (`#section`)
- JavaScript links (`javascript:void(0)`)
- Email links (`mailto:`)
- Phone links (`tel:`)
- Links that open in new tabs (`target="_blank"`)
- Bootstrap toggle links (`data-bs-toggle`)
- Download links (`download` attribute)
- Copy content buttons (`.copy-content-btn`)
- Dropdown toggles (`.dropdown-toggle`)

### For Forms

**Method 1: CSS Class**

```html
<form method="post" class="no-loading">
  <!-- Form won't show loading spinner -->
</form>
```

**Method 2: Data Attribute**

```html
<form method="post" data-no-loading>
  <!-- Form won't show loading spinner -->
</form>
```

**Method 3: AJAX Forms**

```html
<form method="post" class="ajax-form">
  <!-- Forms with AJAX handling -->
</form>

<form method="post" data-ajax>
  <!-- Forms with AJAX handling -->
</form>
```

**Automatically Skipped Forms:**

- GET forms that don't change URL (filter/search forms)
- Forms with `data-ajax` or `ajax-form` class
- Forms with `data-no-loading` or `no-loading` class

### Usage Examples

**Timeline Filter Form (Automatically Skipped):**

```html
<!-- This GET form to same URL won't show spinner -->
<form method="get" id="timeline-filters">
  <input type="checkbox" name="event_type" value="dailynote">
  <button type="submit">Filter</button>
</form>
```

**Custom AJAX Form:**

```html
<!-- Use data-ajax to prevent spinner -->
<form method="post" data-ajax id="quick-update-form">
  <input type="text" name="quick_note">
  <button type="submit">Quick Save</button>
</form>
```

**Form with Custom Loading State:**

```html
<!-- Use no-loading class to prevent spinner -->
<form method="post" class="no-loading" id="upload-form">
  <input type="file" name="document">
  <button type="submit">
    <span class="spinner-border spinner-border-sm d-none"></span>
    Upload
  </button>
</form>
```

## Safety Considerations

### What This Implementation Avoids

1. **MediaFiles Upload Systems**: FilePond has its own loading states and continues to work normally
2. **Bootstrap Components**: Respects modals, dropdowns, tooltips - they won't trigger loading
3. **External Links**: Won't show loading for external navigation
4. **AJAX Operations**: Doesn't interfere with existing AJAX functionality
5. **Filter/Search Forms**: GET forms to same URL are automatically skipped
6. **Specialized Libraries**: Upload widgets and other libraries maintain their own loading states

### Fallback Mechanisms

1. **Maximum Timeout**: Loading hides automatically after 15 seconds
2. **Page Show Event**: Loading hides when returning via back button
3. **Load Event**: Loading hides when page fully loads
4. **Multiple Opt-Out Methods**: CSS classes, data attributes, automatic detection

## Testing Checklist

### Basic Navigation

- [x] Dashboard to Patient List
- [x] Patient List to Patient Detail
- [x] Patient Detail to Edit Form
- [x] Sidebar navigation links
- [x] Breadcrumb navigation

### Form Submissions (NEW)

- [x] Email confirmation form shows spinner
- [x] Password change form shows spinner
- [x] Daily notes creation form shows spinner
- [x] Patient creation/edit forms show spinner
- [x] Login/logout forms show spinner
- [x] Timeline filter forms DON'T show spinner (GET forms)
- [x] MediaFiles uploads keep their FilePond loading states

### Edge Cases

- [x] Back button functionality
- [x] Dropdown menus still work
- [x] Modal triggers don't show loading
- [x] External links don't show loading
- [x] Hash/anchor links don't show loading
- [x] Copy buttons still work
- [x] File upload pages function normally

### Escape Hatch Testing

- [ ] Forms with `class="no-loading"` don't show spinner
- [ ] Forms with `data-no-loading` don't show spinner
- [ ] Links with `class="no-loading"` don't show spinner
- [ ] AJAX forms with appropriate classes don't show spinner

### Performance

- [x] No loading flicker on fast responses
- [x] Loading disappears appropriately
- [x] No console errors
- [x] Responsive design intact

## Completed Enhancements

- ✅ **Form submission loading states**: Now shows spinner for form submissions that navigate to new pages
- ✅ **Smart filtering**: Automatically skips filter forms and AJAX operations
- ✅ **Multiple escape hatches**: CSS classes, data attributes, and automatic detection

## Future Enhancements (Not in Current Scope)

- AJAX request loading indicators (with careful integration to avoid conflicts)
- Progress bars for specific operations (file uploads, data exports)
- Different loading messages for different sections
- Integration with htmx or other AJAX libraries

## Rollback Plan

If issues arise:

1. Remove `<script src="{% static 'js/page-loading.js' %}"></script>` from `base_app.html`
2. Remove CSS from `main.scss`
3. Remove HTML overlay from `base_app.html`
4. Run `npm run build`

## Quick Reference: How to Disable Loading Spinner

### For a specific link

```html
<a href="/page" class="no-loading">Link without spinner</a>
<a href="/page" data-no-loading>Link without spinner</a>
```

### For a specific form

```html
<form method="post" class="no-loading">Form without spinner</form>
<form method="post" data-no-loading>Form without spinner</form>
<form method="post" data-ajax>AJAX form without spinner</form>
```

### What gets spinner automatically

- ✅ POST/PUT/DELETE forms
- ✅ Links to different pages
- ✅ Navigation within the app

### What doesn't get spinner automatically

- ❌ GET forms (search/filter forms)
- ❌ External links
- ❌ Bootstrap modals/dropdowns
- ❌ FilePond/specialized upload widgets
- ❌ Hash/anchor links
- ❌ Email/phone links
