# Static Files in Apps Folders - Investigation Report

## Overview

This investigation analyzed static files located within Django app folders instead of the global static directory. The analysis found three apps with static files and identified several areas of concern regarding code duplication and organization.

## Apps with Static Files

### 1. **apps/core/static/**

- **Location**: `apps/core/static/core/hero-medical-team.svg`
- **Content**: Single SVG file (235 lines) containing medical team illustration
- **Usage**: Referenced in `apps/core/templates/core/landing_page.html` for the hero section
- **Webpack Integration**: ❌ Not included in webpack bundle
- **Assessment**: ✅ **Appropriate** - This is a core app-specific asset used only in the landing page

### 2. **apps/events/static/**

- **Location**: `apps/events/static/events/`
- **Content**:
  - `css/timeline.css` (206 lines) - Timeline-specific styles
  - `css/print.css` (114 lines) - Print-specific styles for timeline
  - `js/timeline.js` (209 lines) - Timeline interactions and modal handling
  - `js/accessibility.js` (163 lines) - Accessibility enhancements for timeline
- **Webpack Integration**: ✅ **Included** in webpack entry points
- **Assessment**: ⚠️ **Problematic** - Contains duplicated CSS and should be consolidated

### 3. **apps/mediafiles/static/**

- **Location**: `apps/mediafiles/static/mediafiles/`
- **Content**:
  - `css/mediafiles.css` (403 lines) - General media file styles
  - `css/photo.css` (352 lines) - Photo-specific styles
  - `js/mediafiles.js` (750 lines) - Media file interactions
  - `js/photo.js` (382 lines) - Photo-specific functionality
- **Webpack Integration**: ✅ **Included** in webpack entry points
- **Assessment**: ⚠️ **Problematic** - Contains duplicated CSS and JavaScript code

## Webpack Integration Analysis

The webpack configuration (`webpack.config.js`) correctly includes static files from apps folders:

```javascript
entry: {
  main: [
    "./assets/index.js", 
    "./assets/scss/main.scss",
    "./apps/mediafiles/static/mediafiles/js/mediafiles.js",
    "./apps/events/static/events/js/timeline.js",
    "./apps/events/static/events/js/accessibility.js",
    "./apps/mediafiles/static/mediafiles/js/photo.js",
    "./apps/mediafiles/static/mediafiles/css/mediafiles.css",
    "./apps/mediafiles/static/mediafiles/css/photo.css"
  ],
}
```

**Status**: ✅ All relevant static files are properly bundled by webpack into `static/main-bundle.js` and `static/main.css`.

## Code Duplication Analysis

### 1. **CSS Class Duplications**

#### Timeline-related duplications

- **`.timeline-card`** styles are duplicated between:
  - `apps/events/static/events/css/timeline.css` (lines 2-6)
  - `apps/events/templates/events/patient_timeline.html` (lines 12-15)

- **`.event-type-badge`** styles are duplicated between:
  - `apps/events/static/events/css/timeline.css` (lines 26-30)
  - `apps/events/templates/events/patient_timeline.html` (lines 20-23)

- **`.event-excerpt`** styles are duplicated between:
  - `apps/events/static/events/css/timeline.css` (lines 32-37)
  - `apps/events/templates/events/patient_timeline.html` (lines 24-28)

- **`.filter-panel`** styles are duplicated between:
  - `apps/events/static/events/css/timeline.css` (lines 39-45)
  - `apps/events/templates/events/patient_timeline.html` (lines 29-33)

#### Media-related duplications

- **`.media-thumbnail`** styles are duplicated between:
  - `apps/mediafiles/static/mediafiles/css/mediafiles.css` (lines 80-89)
  - `apps/mediafiles/templates/mediafiles/base.html` (lines 10-19)

- **`.media-upload-area`** styles are duplicated between:
  - `apps/mediafiles/static/mediafiles/css/mediafiles.css` (lines 221-224)
  - `apps/mediafiles/templates/mediafiles/base.html` (lines 21-38)

### 2. **JavaScript Code Duplications**

#### Configuration duplications

- **File validation config** is duplicated between:
  - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 13-20)
  - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 13-22)

#### Utility function duplications

- **`formatFileSize`** function is duplicated between:
  - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 27-33)
  - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 29-35)

- **`showToast`** function is duplicated between:
  - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 59-77)
  - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 47-65)

#### Drag and drop functionality

- **Drag and drop handlers** are duplicated between:
  - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 108-160)
  - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 82-150)

## Recommendations

### 1. **Immediate Actions**

1. **Remove CSS duplications** from templates:
   - Move all timeline-related styles from `patient_timeline.html` to `timeline.css`
   - Move all media-related styles from `base.html` to `mediafiles.css`

2. **Consolidate JavaScript utilities**:
   - Create a shared utilities module for common functions like `formatFileSize` and `showToast`
   - Remove duplicated drag-and-drop implementations

### 2. **Long-term Improvements**

1. **Reorganize static files structure**:
   - Keep app-specific assets in app folders (✅ current approach is correct)
   - Ensure webpack properly bundles all files (✅ already working)

2. **Establish coding standards**:
   - Prevent inline styles in templates when external CSS files exist
   - Use CSS custom properties for shared values
   - Implement a component-based approach for JavaScript modules

### 3. **File Organization Assessment**

**Current approach is generally correct**:

- ✅ App-specific static files belong in app folders
- ✅ Webpack correctly bundles these files
- ✅ Core app SVG is appropriately placed
- ⚠️ Need to eliminate duplications between static files and templates

## Conclusion

The static files are appropriately located within app folders and are correctly integrated with webpack. However, there are significant code duplications between static files and template inline styles/scripts that should be addressed to improve maintainability and reduce bundle size.

**Priority**: **Medium** - The current setup works but needs cleanup to prevent future maintenance issues.

---

*Investigation completed on: 2025-06-22*
*Files analyzed: 3 apps, 8 static files, 2 templates with inline styles*
