# Phase 2: Code Deduplication and Refactoring

## Context and Necessity

Following successful completion of Phase 1 (webpack integration), Phase 2 addresses critical code duplication issues identified in the static assets audit:

### Duplication Problems Identified

- **JavaScript utility functions** duplicated between `mediafiles.js` and `photo.js`
- **CSS pattern repetition** across media type files
- **Configuration objects** duplicated across JavaScript modules
- **Maintenance overhead** from keeping multiple copies in sync

### Specific Duplications Found

#### JavaScript Duplications

1. **`formatFileSize()` function** - Identical implementations in:
   - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 27-33)
   - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 29-35)

2. **`showToast()` function** - Identical implementations in:
   - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 59-77)
   - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 47-65)

3. **File validation configuration** - Duplicated in:
   - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 13-20)
   - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 13-22)

4. **Drag and drop handlers** - Nearly identical implementations in:
   - `apps/mediafiles/static/mediafiles/js/mediafiles.js` (lines 108-160)
   - `apps/mediafiles/static/mediafiles/js/photo.js` (lines 82-150)

#### CSS Duplications

1. **Media thumbnail styles** - Repeated patterns across files
2. **Upload area styling** - Similar implementations in photo/video/photoseries
3. **Modal control styles** - Duplicated across media types
4. **Responsive breakpoints** - Repeated media queries

## Technical Reasoning

### Why Deduplication is Critical

1. **Maintainability**: Single source of truth for shared functionality
2. **Consistency**: Ensures identical behavior across all media types
3. **Bundle Size**: Reduces JavaScript and CSS bundle size
4. **Bug Prevention**: Fixes in shared code automatically apply everywhere
5. **Developer Experience**: Clearer code organization and easier debugging

### Dependency Management Strategy

- Establish clear module hierarchy with `MediaFiles` as the base
- Create shared utility modules for common functionality
- Implement proper dependency injection patterns
- Maintain backward compatibility during transition

## Implementation Plan

### Step 1: Create Shared Utility Module

**Estimated Time: 30 minutes**

**1.1 Extract Shared Utilities from mediafiles.js**

Create new section in `apps/mediafiles/static/mediafiles/js/mediafiles.js`:

```javascript
// MediaFiles namespace - ENHANCED VERSION
window.MediaFiles = (function() {
    'use strict';

    // Shared configuration (consolidate from all files)
    const config = {
        // File size limits
        maxImageSize: 5 * 1024 * 1024, // 5MB
        maxVideoSize: 50 * 1024 * 1024, // 50MB
        
        // Allowed file types
        allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
        allowedVideoTypes: ['video/mp4', 'video/webm', 'video/quicktime'],
        allowedImageExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
        allowedVideoExtensions: ['.mp4', '.webm', '.mov'],
        
        // Photo-specific config (moved from photo.js)
        maxImageWidth: 4000,
        maxImageHeight: 4000,
        thumbnailSize: 150,
        previewMaxWidth: 800,
        previewMaxHeight: 600
    };

    // Shared utility functions (consolidate duplicates)
    const utils = {
        /**
         * Format file size in human readable format
         * CONSOLIDATED from mediafiles.js and photo.js
         */
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Get file extension from filename
         * ENHANCED version with better error handling
         */
        getFileExtension: function(filename) {
            if (!filename || typeof filename !== 'string') return '';
            return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
        },

        /**
         * Validate file type against allowed types
         * ENHANCED with better error messages
         */
        validateFileType: function(file, allowedTypes) {
            if (!file || !file.type) return false;
            return allowedTypes.includes(file.type);
        },

        /**
         * Validate file size against maximum
         * ENHANCED with better error messages
         */
        validateFileSize: function(file, maxSize) {
            if (!file || typeof file.size !== 'number') return false;
            return file.size <= maxSize;
        },

        /**
         * Show toast notification
         * CONSOLIDATED from mediafiles.js and photo.js
         * ENHANCED with better accessibility
         */
        showToast: function(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'polite');
            
            const iconMap = {
                'success': 'check-circle',
                'danger': 'exclamation-triangle',
                'error': 'exclamation-triangle',
                'warning': 'exclamation-triangle',
                'info': 'info-circle'
            };
            
            toast.innerHTML = `
                <i class="bi bi-${iconMap[type] || 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
            `;
            
            document.body.appendChild(toast);
            
            // Auto-remove after 4 seconds
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 4000);
        },

        /**
         * Debounce function
         * MOVED from mediafiles.js for shared use
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };

    // Shared drag and drop functionality
    const dragDrop = {
        /**
         * Setup drag and drop for any upload area
         * CONSOLIDATED from mediafiles.js and photo.js
         */
        setupDragAndDrop: function(selector, fileInputSelector, onFileSelect) {
            const uploadAreas = document.querySelectorAll(selector);
            
            uploadAreas.forEach(area => {
                area.addEventListener('dragover', this.handleDragOver.bind(this));
                area.addEventListener('dragleave', this.handleDragLeave.bind(this));
                area.addEventListener('drop', (e) => this.handleDrop(e, fileInputSelector, onFileSelect));
            });
        },

        handleDragOver: function(e) {
            e.preventDefault();
            e.currentTarget.classList.add('dragover');
        },

        handleDragLeave: function(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('dragover');
        },

        handleDrop: function(e, fileInputSelector, onFileSelect) {
            e.preventDefault();
            e.currentTarget.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = e.currentTarget.querySelector(fileInputSelector);
                if (fileInput) {
                    fileInput.files = files;
                    if (onFileSelect) {
                        onFileSelect({ target: fileInput });
                    }
                }
            }
        }
    };

    // Public API - ENHANCED
    return {
        config: config,
        utils: utils,
        dragDrop: dragDrop,
        
        // Existing functionality preserved
        fileUpload: fileUpload,
        photoModal: photoModal,
        
        // Initialize all MediaFiles functionality
        init: function() {
            fileUpload.init();
            photoModal.init();
        }
    };
})();
```

### Step 2: Refactor photo.js to Use Shared Utilities

**Estimated Time: 45 minutes**

**2.1 Remove Duplicate Functions from photo.js**

**File: `apps/mediafiles/static/mediafiles/js/photo.js`**

**BEFORE (lines 22-39) - REMOVE:**

```javascript
// Use shared utilities from MediaFiles
const utils = window.MediaFiles ? window.MediaFiles.utils : {
    formatFileSize: function(bytes) {
        console.warn('MediaFiles not loaded, using fallback formatFileSize');
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    getFileExtension: function(filename) {
        console.warn('MediaFiles not loaded, using fallback getFileExtension');
        return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
    },
    showToast: function(message, type = 'info') {
        console.warn('MediaFiles not loaded, using fallback showToast');
        alert(message);
    }
};
```

**AFTER - REPLACE WITH:**

```javascript
// Use shared utilities from MediaFiles (required dependency)
const utils = window.MediaFiles.utils;
const config = window.MediaFiles.config;
const dragDrop = window.MediaFiles.dragDrop;

// Validate MediaFiles dependency
if (!window.MediaFiles) {
    throw new Error('Photo module requires MediaFiles to be loaded first');
}
```

**2.2 Remove Duplicate Configuration**

**BEFORE (lines 42-46) - REMOVE:**

```javascript
// Get shared config from MediaFiles
const sharedConfig = window.MediaFiles ? window.MediaFiles.config : {
    maxImageSize: 5 * 1024 * 1024,
    allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
    allowedImageExtensions: ['.jpg', '.jpeg', '.png', '.webp']
};
```

**AFTER - ALREADY AVAILABLE via `const config = window.MediaFiles.config;`**

**2.3 Refactor Drag and Drop Implementation**

**BEFORE (lines 62-141) - REPLACE:**

```javascript
setupDragAndDrop: function() {
    const uploadAreas = document.querySelectorAll('.photo-upload-form');
    
    uploadAreas.forEach(area => {
        area.addEventListener('dragover', this.handleDragOver.bind(this));
        area.addEventListener('dragleave', this.handleDragLeave.bind(this));
        area.addEventListener('drop', this.handleDrop.bind(this));
    });
},

handleDragOver: function(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
},

handleDragLeave: function(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
},

handleDrop: function(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const fileInput = e.currentTarget.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.files = files;
            this.handleFileSelect({ target: fileInput });
        }
    }
},
```

**AFTER - REPLACE WITH:**

```javascript
setupDragAndDrop: function() {
    dragDrop.setupDragAndDrop(
        '.photo-upload-form',
        'input[type="file"]',
        this.handleFileSelect.bind(this)
    );
},
```

**2.4 Update File Validation to Use Shared Config**

**BEFORE (lines 166-187) - UPDATE:**

```javascript
validatePhoto: function(file) {
    // Check file type
    if (!sharedConfig.allowedImageTypes.includes(file.type)) {
        utils.showToast('Tipo de arquivo não permitido. Use JPG, PNG ou WebP.', 'danger');
        return false;
    }

    // Check file extension
    const extension = '.' + utils.getFileExtension(file.name);
    if (!sharedConfig.allowedImageExtensions.includes(extension)) {
        utils.showToast('Extensão de arquivo não permitida.', 'danger');
        return false;
    }

    // Check file size
    if (file.size > sharedConfig.maxImageSize) {
        const maxSizeMB = sharedConfig.maxImageSize / (1024 * 1024);
        utils.showToast(`Arquivo muito grande. Máximo: ${maxSizeMB}MB`, 'danger');
        return false;
    }

    return true;
},
```

**AFTER - REPLACE WITH:**

```javascript
validatePhoto: function(file) {
    // Check file type
    if (!utils.validateFileType(file, config.allowedImageTypes)) {
        utils.showToast('Tipo de arquivo não permitido. Use JPG, PNG ou WebP.', 'danger');
        return false;
    }

    // Check file extension
    const extension = '.' + utils.getFileExtension(file.name);
    if (!config.allowedImageExtensions.includes(extension)) {
        utils.showToast('Extensão de arquivo não permitida.', 'danger');
        return false;
    }

    // Check file size
    if (!utils.validateFileSize(file, config.maxImageSize)) {
        const maxSizeMB = config.maxImageSize / (1024 * 1024);
        utils.showToast(`Arquivo muito grande. Máximo: ${maxSizeMB}MB`, 'danger');
        return false;
    }

    return true;
},
```

### Step 3: CSS Consolidation and Deduplication

**Estimated Time: 60 minutes**

**3.1 Consolidate Common Media Styles**

**File: `apps/mediafiles/static/mediafiles/css/mediafiles.css`**

**Add new shared component section (append to end of file):**

```css
/* ==========================================================================
   SHARED MEDIA COMPONENTS - CONSOLIDATED FROM ALL MEDIA TYPES
   ========================================================================== */

/* Shared thumbnail sizing system */
.media-thumbnail-sm { width: 80px; height: 80px; }
.media-thumbnail-md { width: 150px; height: 150px; }
.media-thumbnail-lg { width: 300px; height: 200px; }

/* Shared upload form styling */
.media-upload-form {
    border-radius: 12px;
    border: 2px dashed #dee2e6;
    padding: 2rem;
    text-align: center;
    transition: border-color 0.3s ease, background-color 0.3s ease;
    background-color: #f8f9fa;
    cursor: pointer;
}

.media-upload-form:hover {
    border-color: var(--medical-primary);
    background-color: #f0f4f8;
}

.media-upload-form.dragover {
    border-color: var(--medical-teal);
    background-color: #e8f5f0;
}

/* Shared upload icons and text */
.media-upload-icon {
    font-size: 3rem;
    color: var(--medical-gray);
    margin-bottom: 1rem;
}

.media-upload-text {
    color: var(--medical-dark-gray);
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}

.media-upload-hint {
    color: var(--medical-gray);
    font-size: 0.9rem;
}

/* Shared preview container styling */
.media-preview-container {
    position: relative;
    display: inline-block;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    background: white;
    padding: 1rem;
}

.media-preview-overlay {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 0.5rem;
    border-radius: 6px;
    font-size: 0.875rem;
}

.media-preview-actions {
    margin-top: 1rem;
    display: flex;
    gap: 0.5rem;
    justify-content: center;
}

/* Shared validation feedback styling */
.media-validation-feedback {
    margin-top: 0.5rem;
    padding: 0.75rem;
    border-radius: 6px;
    font-size: 0.875rem;
}

.media-validation-feedback.valid {
    background: #d4edda;
    color: var(--medical-success);
    border: 1px solid #c3e6cb;
}

.media-validation-feedback.invalid {
    background: #f8d7da;
    color: var(--medical-error);
    border: 1px solid #f5c6cb;
}

/* Shared progress indicator styling */
.media-upload-progress {
    margin-top: 1rem;
}

.media-progress-bar {
    height: 8px;
    border-radius: 4px;
    background: #e9ecef;
    overflow: hidden;
}

.media-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--medical-primary), var(--medical-teal));
    transition: width 0.3s ease;
    border-radius: 4px;
}

.media-progress-text {
    text-align: center;
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--medical-gray);
}

/* Shared loading and error states */
.media-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: var(--medical-gray);
}

.media-loading .spinner-border {
    margin-right: 0.5rem;
}

.media-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: var(--medical-error);
    text-align: center;
}

.media-error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}
```

**3.2 Remove Duplicated Styles from Specific Files**

**File: `apps/mediafiles/static/mediafiles/css/photo.css`**

**REMOVE these duplicated sections (replace with references to shared classes):**

```css
/* REMOVE - Now in shared mediafiles.css */
.photo-upload-form { /* lines 73-76 */ }
.photo-upload-icon { /* lines 78-82 */ }
.photo-upload-text { /* lines 84-88 */ }
.photo-upload-hint { /* lines 90-93 */ }
.photo-preview-container { /* lines 96-104 */ }
.photo-preview-overlay { /* lines 113-122 */ }
.photo-preview-actions { /* lines 124-129 */ }
.photo-validation-feedback { /* lines 183-200 */ }
.photo-upload-progress { /* lines 203-205 */ }
.photo-progress-bar { /* lines 207-212 */ }
.photo-progress-fill { /* lines 214-219 */ }
.photo-progress-text { /* lines 221-226 */ }
.photo-loading { /* lines 154-164 */ }
.photo-error { /* lines 166-180 */ }
```

**REPLACE with class extensions:**

```css
/* Photo-specific extensions of shared media classes */
.photo-upload-form {
    /* Inherits from .media-upload-form */
    /* Add photo-specific overrides only */
}

.photo-preview-container {
    /* Inherits from .media-preview-container */
    /* Add photo-specific overrides only */
}

/* Keep only photo-specific styles that don't duplicate shared functionality */
.photo-thumbnail-sm { width: 80px; height: 80px; }
.photo-thumbnail-md { width: 150px; height: 150px; }
.photo-thumbnail-lg { width: 300px; height: 200px; }

/* Photo-specific modal and interaction styles remain unchanged */
.photo-modal-image { /* Keep - photo-specific */ }
.photo-metadata { /* Keep - photo-specific */ }
```

**3.3 Update VideoClip and PhotoSeries CSS**

Apply similar deduplication to:

- `apps/mediafiles/static/mediafiles/css/videoclip.css`
- `apps/mediafiles/static/mediafiles/css/photoseries.css`

Remove duplicated upload, preview, and validation styles, replacing with shared classes.

### Step 4: Update Other JavaScript Files

**Estimated Time: 30 minutes**

**4.1 Update photoseries.js and videoclip.js**

Ensure these files also use shared utilities where applicable:

```javascript
// At the top of photoseries.js and videoclip.js
const utils = window.MediaFiles.utils;
const config = window.MediaFiles.config;

// Replace any duplicate utility functions with calls to shared utils
```

### Step 5: Dependency Loading Order Verification

**Estimated Time: 15 minutes**

**5.1 Verify Webpack Entry Order**

Ensure `webpack.config.js` loads files in correct dependency order:

```javascript
entry: {
  main: [
    "./assets/index.js",
    "./assets/scss/main.scss",
    "./apps/mediafiles/static/mediafiles/js/mediafiles.js",      // ← MUST BE FIRST
    "./apps/events/static/events/js/timeline.js",
    "./apps/events/static/events/js/accessibility.js",
    "./apps/mediafiles/static/mediafiles/js/photo.js",          // ← AFTER mediafiles.js
    "./apps/mediafiles/static/mediafiles/js/photoseries.js",    // ← AFTER mediafiles.js
    "./apps/mediafiles/static/mediafiles/js/videoclip.js",      // ← AFTER mediafiles.js
    "./apps/mediafiles/static/mediafiles/css/mediafiles.css",   // ← CSS FIRST
    "./apps/mediafiles/static/mediafiles/css/photo.css",        // ← AFTER mediafiles.css
    "./apps/mediafiles/static/mediafiles/css/photoseries.css",  // ← AFTER mediafiles.css
    "./apps/mediafiles/static/mediafiles/css/videoclip.css"     // ← AFTER mediafiles.css
  ],
}
```

## Testing Procedures

### Pre-Deployment Testing

**Estimated Time: 45 minutes**

#### Test 1: Shared Utility Functions

```javascript
// Browser console testing
console.log(window.MediaFiles.utils.formatFileSize(1024)); // Should return "1 KB"
window.MediaFiles.utils.showToast('Test message', 'success'); // Should show toast
```

#### Test 2: Photo Functionality

```bash
# Test photo upload with new shared utilities
# 1. Navigate to photo upload form
# 2. Test drag and drop functionality
# 3. Test file validation messages
# 4. Verify no console errors
# 5. Confirm identical behavior to before refactoring
```

#### Test 3: PhotoSeries and VideoClip

```bash
# Test that all media types still work correctly
# 1. Test PhotoSeries carousel and controls
# 2. Test VideoClip player functionality
# 3. Verify shared styles apply correctly
# 4. Check responsive behavior
```

#### Test 4: Bundle Size Verification

```bash
# Check bundle size reduction
ls -la static/main-bundle.js static/main.css

# Compare to pre-refactoring sizes
# Should see reduction due to deduplication
```

### Automated Testing

```bash
# Run full test suite
uv run python manage.py test apps.mediafiles

# Run JavaScript unit tests (if available)
npm test

# Check for JavaScript errors in browser console
# All pages should load without errors
```

## Risk Assessment and Mitigation

### High Risk Scenarios

#### Risk 1: Dependency Loading Issues

**Probability: Medium | Impact: High**

**Symptoms:**

- "MediaFiles is not defined" errors
- Photo/PhotoSeries/VideoClip functionality broken
- Inconsistent behavior across media types

**Mitigation:**

- Webpack entry order ensures MediaFiles loads first
- Add explicit dependency checks in modules
- Comprehensive testing before deployment

**Rollback:** Restore individual utility functions in each file

#### Risk 2: CSS Specificity Conflicts

**Probability: Low | Impact: Medium**

**Symptoms:**

- Styling inconsistencies
- Media type specific styles not applying
- Layout issues on media pages

**Mitigation:**

- Maintain CSS specificity hierarchy
- Test all media types thoroughly
- Use CSS class inheritance properly

**Rollback:** Restore individual CSS files

#### Risk 3: Functionality Regressions

**Probability: Low | Impact: High**

**Symptoms:**

- Upload functionality broken
- Validation not working
- Modal interactions failing

**Mitigation:**

- Extensive manual testing
- Automated test coverage
- Gradual rollout approach

**Rollback:** Restore pre-refactoring code

## Success Criteria

### Code Quality Metrics

1. ✅ Zero duplicate utility functions across JavaScript files
2. ✅ Shared configuration object used by all modules
3. ✅ CSS duplication reduced by >50%
4. ✅ Consistent code patterns across all media types
5. ✅ Proper dependency management implemented

### Performance Metrics

1. ✅ Bundle size reduction of 10-20KB
2. ✅ No increase in page load times
3. ✅ Identical functionality performance
4. ✅ No new JavaScript errors

### Maintainability Metrics

1. ✅ Single source of truth for shared utilities
2. ✅ Clear module dependency hierarchy
3. ✅ Consistent error handling patterns
4. ✅ Improved code documentation

## Post-Implementation Actions

### Immediate (Week 1)

- [ ] Monitor for any functionality regressions
- [ ] Verify bundle size improvements
- [ ] Update developer documentation
- [ ] Create coding standards for future media modules

### Short-term (Month 1)

- [ ] Implement additional shared utilities as needed
- [ ] Consider further CSS consolidation opportunities
- [ ] Plan Phase 3 advanced optimizations

**Estimated Total Implementation Time: 3 hours**
**Recommended Implementation Window: Development/staging first**
**Required Rollback Time: 30 minutes maximum**
