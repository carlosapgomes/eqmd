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