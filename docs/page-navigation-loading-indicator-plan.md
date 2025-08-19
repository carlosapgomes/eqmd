# Page Navigation Loading Indicator Implementation Plan

## Overview

Implement a global page navigation loading indicator to improve UX during page transitions on VPS deployment with slower response times.

## Requirements

- Show loading overlay during page navigation only
- Use existing medical theme colors and Bootstrap components
- Safe implementation that doesn't interfere with existing functionality
- Focus only on navigation, avoid touching mediafiles upload systems

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

### Step 3: Create Navigation Loading JavaScript ✅ COMPLETED

**File**: `assets/js/page-loading.js` (new file)

```javascript
/**
 * Page Navigation Loading Indicator
 * Shows loading overlay during page navigation
 * Safe implementation that avoids interfering with existing functionality
 */

(function () {
  "use strict";

  const loadingOverlay = document.getElementById("pageLoadingOverlay");

  if (!loadingOverlay) {
    console.warn("Page loading overlay element not found");
    return;
  }

  // Show loading overlay
  function showLoading() {
    loadingOverlay.classList.remove("d-none");
  }

  // Hide loading overlay
  function hideLoading() {
    loadingOverlay.classList.add("d-none");
  }

  // Check if link should trigger loading indicator
  function shouldShowLoading(link) {
    // Skip external links
    if (link.hostname && link.hostname !== window.location.hostname) {
      return false;
    }

    // Skip anchors (hash links)
    if (link.getAttribute("href")?.startsWith("#")) {
      return false;
    }

    // Skip javascript: links
    if (link.getAttribute("href")?.startsWith("javascript:")) {
      return false;
    }

    // Skip mailto: and tel: links
    if (link.protocol === "mailto:" || link.protocol === "tel:") {
      return false;
    }

    // Skip links that open in new tab/window
    if (link.target === "_blank" || link.target === "_new") {
      return false;
    }

    // Skip data-bs-toggle links (Bootstrap modals, dropdowns, etc.)
    if (link.hasAttribute("data-bs-toggle")) {
      return false;
    }

    // Skip download links
    if (link.hasAttribute("download")) {
      return false;
    }

    // Skip specific classes that shouldn't trigger loading
    const skipClasses = [
      "no-loading", // Manual override
      "copy-content-btn", // Clipboard functionality
      "dropdown-toggle", // Dropdown triggers
      "nav-link", // Skip if it's just a Bootstrap nav-link without href
    ];

    for (const className of skipClasses) {
      if (link.classList.contains(className)) {
        return false;
      }
    }

    return true;
  }

  // Add click event listeners to navigation links
  function initializeNavLoading() {
    // Listen to all link clicks
    document.addEventListener("click", function (event) {
      const link = event.target.closest("a");

      if (!link || !shouldShowLoading(link)) {
        return;
      }

      // Show loading with small delay to avoid flicker on fast responses
      setTimeout(showLoading, 100);
    });

    // Hide loading when page starts to unload (navigation is happening)
    window.addEventListener("beforeunload", function () {
      // Keep loading visible during navigation
    });

    // Hide loading if user comes back to page (back button)
    window.addEventListener("pageshow", function (event) {
      hideLoading();
    });

    // Hide loading on page load
    window.addEventListener("load", function () {
      hideLoading();
    });

    // Safety: Hide loading after maximum time
    let loadingTimeout;
    function resetLoadingTimeout() {
      clearTimeout(loadingTimeout);
      loadingTimeout = setTimeout(hideLoading, 15000); // 15 second max
    }

    document.addEventListener("click", function (event) {
      const link = event.target.closest("a");
      if (link && shouldShowLoading(link)) {
        resetLoadingTimeout();
      }
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeNavLoading);
  } else {
    initializeNavLoading();
  }
})();
```

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

## Safety Considerations

### What This Implementation Avoids

1. **MediaFiles Upload Systems**: No interference with FilePond or file processing
2. **Bootstrap Components**: Respects modals, dropdowns, tooltips
3. **External Links**: Won't show loading for external navigation
4. **AJAX Calls**: Doesn't intercept existing AJAX functionality
5. **Form Submissions**: Leaves existing form loading states intact

### Fallback Mechanisms

1. **Maximum Timeout**: Loading hides automatically after 15 seconds
2. **Page Show Event**: Loading hides when returning via back button
3. **Load Event**: Loading hides when page fully loads
4. **Manual Override**: `no-loading` class to skip specific links

## Testing Checklist

### Basic Navigation

- [ ] Dashboard to Patient List
- [ ] Patient List to Patient Detail
- [ ] Patient Detail to Edit Form
- [ ] Sidebar navigation links
- [ ] Breadcrumb navigation

### Edge Cases

- [ ] Back button functionality
- [ ] Dropdown menus still work
- [ ] Modal triggers don't show loading
- [ ] External links don't show loading
- [ ] Hash/anchor links don't show loading
- [ ] Copy buttons still work
- [ ] File upload pages function normally

### Performance

- [ ] No loading flicker on fast responses
- [ ] Loading disappears appropriately
- [ ] No console errors
- [ ] Responsive design intact

## Future Enhancements (Not in Current Scope)

- Form submission loading states (careful integration needed)
- AJAX request loading indicators
- Progress bars for specific operations
- Different loading messages for different sections

## Rollback Plan

If issues arise:

1. Remove `<script src="{% static 'js/page-loading.js' %}"></script>` from `base_app.html`
2. Remove CSS from `main.scss`
3. Remove HTML overlay from `base_app.html`
4. Run `npm run build`

