# Plan: Client-Side Image Processing for Multi-Upload Component

**Objective**: Implement the standardized client-side image processing flow (as defined in `docs/image_processing_flow.md`) within the `MultiUpload` component. This will ensure all images uploaded through this component are automatically converted (from HEIC), resized, and compressed before being sent to the server.

**Final Corrected Plan**

## Step-by-Step Implementation Plan

### Step 1: Load the Image Processing Bundle in the Correct Template

The project's `webpack.config.js` bundles `heic2any` and `browser-image-compression` into a dedicated chunk named `image-processing-bundle.js`. We must load this bundle on any page that uses the `MultiUpload` component, following the established pattern seen in `photo_form.html`.

1. **Edit the relevant template**: Open the template where the `MultiUpload` component is used. For this task, it is `apps/mediafiles/templates/mediafiles/photoseries_create.html`.
2. **Load the script**: In the `page_specific_scripts` block, add a `<script>` tag to load the `image-processing-bundle.js`. It must be loaded _before_ the main page script (`photoseries-bundle.js`) to ensure the libraries are available when the `MultiUpload` component is initialized.

```html
{% block page_specific_scripts %}
<!-- Load the image processing libraries first, making them globally available -->
<script src="{% static 'image-processing-bundle.js' %}"></script>

<!-- Load the main script for this page -->
<script src="{% static 'photoseries-bundle.js' %}"></script>

<script>
  document.addEventListener("DOMContentLoaded", function () {
    // ... existing script that initializes PhotoSeries and MultiUpload ...
  });
</script>
{% endblock page_specific_scripts %}
```

### Step 2: Create a Dedicated Image Processing Function

To keep the code modular and clean, we will create a new asynchronous helper function inside the `MultiUpload` JavaScript module (which is part of the inline script in `apps/mediafiles/templates/mediafiles/partials/multi_upload.html`).

1. **Edit the `MultiUpload` script**: Open `apps/mediafiles/templates/mediafiles/partials/multi_upload.html`.
2. **Add the new function**: Inside the `window.MultiUpload` IIFE, add the following `async` function. It will correctly reference `heic2any` and `imageCompression` from the global `window` object, where they are placed by the webpack bundle.

```javascript
async function processAndResizeImage(file) {
  console.log(`Processing ${file.name}...`);

  let processedFile = file;
  const fileName = file.name.toLowerCase();

  // Step 1: Convert HEIC/HEIF to JPEG if necessary
  if (
    (fileName.endsWith(".heic") || fileName.endsWith(".heif")) &&
    window.heic2any
  ) {
    try {
      console.log("Converting HEIC/HEIF to JPEG...");
      const conversionResult = await heic2any({
        blob: file,
        toType: "image/jpeg",
        quality: 0.9, // High quality for intermediate conversion
      });
      const convertedBlob = Array.isArray(conversionResult)
        ? conversionResult[0]
        : conversionResult;
      processedFile = new File(
        [convertedBlob],
        file.name.replace(/\.(heic|heif)$/i, ".jpg"),
        { type: "image/jpeg" },
      );
      console.log(
        `Converted to ${processedFile.name}, size: ${formatFileSize(processedFile.size)}`,
      );
    } catch (error) {
      console.error("HEIC conversion failed:", error);
      return null; // Return null to indicate failure
    }
  }

  // Step 2: Resize and compress the image using browser-image-compression
  if (window.imageCompression) {
    const compressionOptions = {
      maxSizeMB: 2,
      maxWidthOrHeight: 1920,
      useWebWorker: true,
      initialQuality: 0.8,
      fileType: "image/webp", // Convert to WebP for modern compression
    };

    try {
      console.log("Compressing and resizing image...");
      const compressedFile = await imageCompression(
        processedFile,
        compressionOptions,
      );
      console.log(
        `Compression complete. New size: ${formatFileSize(compressedFile.size)}`,
      );
      return compressedFile;
    } catch (error) {
      console.error("Image compression failed:", error);
      return null; // Return null to indicate failure
    }
  }

  // Return the processed (or original) file if compression library isn't loaded
  return processedFile;
}
```

### Step 3: Integrate Processing into the `processFiles` Function

Now, we will modify the existing `processFiles` function to use our new helper. This ensures every file goes through the processing pipeline before being added to the upload queue.

1. **Modify `processFiles`**: Make the function `async` and update its loop to `await` the result of our new processing function.
2. **Implement Error Handling**: Add a `try...catch` block to gracefully handle any file that fails to process.

**Here is the updated `processFiles` function:**

```javascript
// Make the function async
async function processFiles(files) {
  showProcessingOverlay(true);

  // Update filter to also catch HEIC/HEIF by extension
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

  // Use a modern for...of loop to handle async operations correctly
  for (const originalFile of imageFiles) {
    try {
      // AWAIT the result of the new processing function
      const processedFile = await processAndResizeImage(originalFile);

      // If processing failed, skip this file and continue
      if (!processedFile) {
        showError(`Falha ao processar o arquivo: ${originalFile.name}.`);
        continue;
      }

      const fileId = generateFileId();
      const fileData = {
        id: fileId,
        file: processedFile, // Use the PROCESSED file
        name: processedFile.name, // Use the new name (e.g., .webp)
        size: processedFile.size, // The new, smaller size
        type: processedFile.type, // The new MIME type (e.g., image/webp)
        status: "pending",
        progress: 0,
        preview: null,
        order: selectedFiles.length,
      };

      selectedFiles.push(fileData);
      createFilePreview(fileData); // This function will generate the preview
      updateFileCount();
    } catch (error) {
      console.error("Error processing file:", originalFile.name, error);
      showError(
        `Erro ao processar ${originalFile.name}. O arquivo pode estar corrompido.`,
      );
    }
  }

  // Hide processing overlay after all files are done
  showProcessingOverlay(false);
}
```

### Step 4: Final Verification

After implementing the changes, perform the following checks:

1. **Test with a large JPEG file**: Verify the uploaded file is smaller and has been converted to WebP.
2. **Test with a PNG file**: Verify it's converted to WebP and resized.
3. **Test with a HEIC file**: Verify it is converted and compressed.
4. **Test with a non-image file**: Verify it is ignored.
5. **Check the UI**: Ensure the file queue correctly displays the new file size and the preview renders correctly.
6. **Review Console Logs**: Check for any errors during processing.

This revised plan correctly leverages the existing project architecture for a clean and efficient implementation.

