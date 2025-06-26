# Corrected Plan: Client-Side Image Processing for Multi-Upload Component

**Objective**: Implement the standardized client-side image processing flow (HEIC conversion + compression) within the `MultiUpload` component for PhotoSeries creation, following the existing architecture patterns from the single photo upload feature.

## Analysis of Current Implementation

### Current Architecture

- **Webpack Bundle Structure**: Two separate image processing bundles are created:
  - `image-processing-859f9a89-bundle.js` - Contains `heic2any` library
  - `image-processing-c2965a6b-bundle.js` - Contains `browser-image-compression` library
- **Library Access**: Libraries are imported as ES6 modules in JavaScript files, not accessed via `window` object
- **Template Structure**: PhotoSeries creation uses `photoseries_create.html` with `multi_upload.html` partial
- **MultiUpload Component**: Self-contained component with file selection, drag-and-drop, and preview functionality

### Key Issues with Original Plan

1. **Bundle Loading**: Original plan assumed single bundle, but webpack creates two separate bundles
2. **Library Access**: Plan suggested `window.heic2any` but actual pattern uses ES6 imports
3. **Format Consistency**: Plan suggested WebP output but existing photo feature uses JPEG
4. **Architecture Mismatch**: Plan didn't account for MultiUpload's self-contained nature

## Corrected Implementation Plan

### Step 1: Load Image Processing Bundles in PhotoSeries Template

**File**: `apps/mediafiles/templates/mediafiles/photoseries_create.html`

**Change the `page_specific_scripts` block** (lines 169-170):

```html
{% block page_specific_scripts %}
<!-- Load image processing libraries (heavy dependencies loaded only when needed) -->
<script src="{% static 'image-processing-859f9a89-bundle.js' %}"></script>
<script src="{% static 'image-processing-c2965a6b-bundle.js' %}"></script>
<!-- PhotoSeries-specific functionality -->
<script src="{% static 'photoseries-bundle.js' %}"></script>
```

### Step 2: Create Image Processing Module for PhotoSeries

**File**: `apps/mediafiles/static/mediafiles/js/image-processing.js` (NEW FILE)

Create a standalone image processing utility that can be imported:

```javascript
/**
 * Image Processing Utilities for MediaFiles
 * Shared utilities for HEIC conversion and image compression
 */

import imageCompression from "browser-image-compression";
import heic2any from "heic2any";

// Configuration matching existing photo implementation
const compressionOptions = {
  maxSizeMB: 2,
  maxWidthOrHeight: 1920,
  useWebWorker: true,
  initialQuality: 0.8,
  mimeType: "image/jpeg", // Maintain consistency with photo feature
};

/**
 * Process a single image file: convert HEIC if needed, then compress
 * @param {File} file - The original image file
 * @returns {Promise<File>} - The processed file
 */
async function processImage(file) {
  console.log(`Processing ${file.name}...`);

  try {
    // Step 1: Convert HEIC/HEIF to JPEG if necessary
    const convertedFile = await convertHeicToJpeg(file);

    // Step 2: Compress the image
    const compressedBlob = await imageCompression(
      convertedFile,
      compressionOptions,
    );

    // Step 3: Create final file with proper naming
    const finalFile = new File(
      [compressedBlob],
      convertedFile.name.replace(/\.[^/.]+$/, ".jpg"),
      {
        type: "image/jpeg",
        lastModified: Date.now(),
      },
    );

    console.log(
      `Processed ${file.name}: ${formatFileSize(file.size)} → ${formatFileSize(finalFile.size)}`,
    );
    return finalFile;
  } catch (error) {
    console.error("Image processing failed:", error);
    throw new Error(`Falha ao processar ${file.name}: ${error.message}`);
  }
}

/**
 * Convert HEIC/HEIF file to JPEG
 * @param {File} file - The original file
 * @returns {Promise<File>} - JPEG file or original if not HEIC
 */
async function convertHeicToJpeg(file) {
  const fileName = file.name.toLowerCase();
  const isHeic =
    fileName.endsWith(".heic") ||
    fileName.endsWith(".heif") ||
    file.type === "image/heic" ||
    file.type === "image/heif";

  if (isHeic) {
    console.log("Converting HEIC/HEIF to JPEG...");
    try {
      const conversionResult = await heic2any({
        blob: file,
        toType: "image/jpeg",
        quality: 0.9,
      });

      const convertedBlob = Array.isArray(conversionResult)
        ? conversionResult[0]
        : conversionResult;

      const newFileName = file.name.replace(/\.(heic|heif)$/i, ".jpg");
      return new File([convertedBlob], newFileName, { type: "image/jpeg" });
    } catch (err) {
      console.error("HEIC conversion failed:", err);
      throw new Error("Falha ao converter imagem HEIC.");
    }
  }

  return file;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Export for use in other modules
export { processImage, convertHeicToJpeg, formatFileSize };
```

### Step 3: Update PhotoSeries JavaScript to Import Processing

**File**: `apps/mediafiles/static/mediafiles/js/photoseries.js`

**Add import at the top**:

```javascript
import { processImage } from "./image-processing.js";
```

**Add new method to PhotoSeries object**:

```javascript
/**
 * Initialize multi-upload with image processing
 */
function initializeMultiUploadWithProcessing() {
  // Override MultiUpload's processFiles function to include image processing
  if (window.MultiUpload && window.MultiUpload.processFiles) {
    const originalProcessFiles = window.MultiUpload.processFiles;

    window.MultiUpload.processFiles = async function (files) {
      const processedFiles = [];

      for (const file of files) {
        try {
          const processedFile = await processImage(file);
          processedFiles.push(processedFile);
        } catch (error) {
          console.error("Failed to process file:", file.name, error);
          // Optionally skip failed files or show error
          window.MultiUpload.showError(
            `Erro ao processar ${file.name}: ${error.message}`,
          );
        }
      }

      // Call original function with processed files
      return originalProcessFiles.call(this, processedFiles);
    };
  }
}
```

### Step 4: Update MultiUpload Component Integration

**File**: `apps/mediafiles/templates/mediafiles/partials/multi_upload.html`

**Update the `processFiles` function** (around line 561) to be async-ready:

```javascript
// Make processFiles async to support image processing
async function processFiles(files) {
  showProcessingOverlay(true);

  // Filter image files (including HEIC by extension)
  const imageFiles = files.filter(
    (file) =>
      file.type.startsWith("image/") || /\.(heic|heif)$/i.test(file.name),
  );

  if (imageFiles.length !== files.length) {
    showError("Alguns arquivos foram ignorados. Apenas imagens são aceitas.");
  }

  if (imageFiles.length > 0) {
    showUploadQueue(true);
  }

  // Process files one by one to avoid overwhelming the system
  for (const file of imageFiles) {
    try {
      // Check if image processing is available
      let processedFile = file;
      if (window.PhotoSeries && window.PhotoSeries.processImage) {
        processedFile = await window.PhotoSeries.processImage(file);
      }

      const fileId = generateFileId();
      const fileData = {
        id: fileId,
        file: processedFile,
        name: processedFile.name,
        size: processedFile.size,
        type: processedFile.type,
        status: "success", // Mark as success since processing completed
        progress: 100,
        preview: null,
        order: selectedFiles.length,
      };

      selectedFiles.push(fileData);
      createFilePreview(fileData);
      updateFileCount();
    } catch (error) {
      console.error("Error processing file:", file.name, error);
      showError(`Erro ao processar ${file.name}: ${error.message}`);
    }
  }

  showProcessingOverlay(false);
}
```

### Step 5: Update Webpack Configuration (If Needed)

The existing webpack configuration should work, but verify the image processing libraries are properly bundled in the photoseries entry point.

**File**: `webpack.config.js`

Add image processing to photoseries entry if needed:

```javascript
photoseries: [
    "./apps/mediafiles/static/mediafiles/js/photoseries.js",
    "./apps/mediafiles/static/mediafiles/js/image-processing.js", // Add this line
    "./apps/mediafiles/static/mediafiles/css/photoseries.css"
],
```

### Step 6: Update PhotoSeries Template Script Initialization

**File**: `apps/mediafiles/templates/mediafiles/photoseries_create.html`

**Update the initialization script** (around line 175):

```javascript
document.addEventListener("DOMContentLoaded", function () {
  try {
    if (typeof PhotoSeries !== "undefined") {
      PhotoSeries.init();
      // Initialize multi-upload with image processing
      PhotoSeries.initializeMultiUploadWithProcessing();
    } else {
      console.warn(
        "PhotoSeries module not loaded - falling back to basic functionality",
      );
    }
  } catch (error) {
    console.error("PhotoSeries initialization failed:", error);
    if (window.errorReporting) {
      window.errorReporting.captureException(error);
    }
  }

  // Rest of existing initialization code...
});
```

## Testing Plan

### Step 7: Verification Steps

1. **HEIC Conversion Test**: Upload a HEIC file and verify it's converted to JPEG
2. **Image Compression Test**: Upload a large JPEG (>5MB) and verify compression
3. **Multiple File Test**: Select multiple files of different formats and verify processing
4. **Error Handling Test**: Upload unsupported file types and verify graceful error handling
5. **UI Consistency Test**: Verify file size display shows compressed sizes
6. **Performance Test**: Upload 5+ files simultaneously and verify processing doesn't block UI

### Expected Outcomes

- All uploaded images are automatically processed (HEIC→JPEG, compression)
- File sizes are reduced while maintaining visual quality
- Processing progress is shown to users
- Errors are handled gracefully with user-friendly messages
- Consistency with existing photo upload behavior

## Benefits of This Corrected Approach

1. **Consistency**: Maintains same format (JPEG) and compression settings as single photo feature
2. **Architecture Alignment**: Follows existing webpack bundle structure and import patterns
3. **Modularity**: Creates reusable image processing utilities
4. **Performance**: Heavy libraries loaded only on pages that need them
5. **Error Handling**: Comprehensive error handling with user feedback
6. **Maintainability**: Clear separation of concerns between MultiUpload UI and image processing

This corrected plan addresses all the technical issues identified in the original plan while maintaining the project's existing architecture patterns.

