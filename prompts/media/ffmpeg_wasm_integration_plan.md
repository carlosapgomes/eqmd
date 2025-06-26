# Plan: Integrating `ffmpeg.wasm` for Client-Side Video Compression (with Web Workers)

## 1. Overview & Goal

The goal of this plan is to integrate `ffmpeg.wasm` into the videoclip upload feature. This will enable client-side video compression, which means videos are compressed in the user's browser *before* being uploaded to the server.

This revised plan uses a **Web Worker** to run the compression process in the background. This is critical to prevent the user interface from freezing, ensuring a smooth and responsive experience, especially on mobile devices where performance is limited.

**Key Benefits:**
*   **Non-Blocking UI:** The browser remains fully responsive while compression is in progress.
*   **Reduced Server Load:** The computationally expensive task of video compression is offloaded from the server to the client.
*   **Faster Uploads:** Users will upload significantly smaller files, improving the user experience.
*   **Storage Savings:** Storing smaller, optimized video files will reduce server storage costs.
*   **Standardized Format:** All uploaded videos can be converted to a web-friendly MP4 (H.264/AAC) format.

## 2. High-Level Implementation Workflow (with Web Worker)

The new upload process will be as follows:

1.  The user selects a video file in `videoclip_form.html`.
2.  The main UI thread (`videoclip.js`) disables the submit button and shows a progress indicator.
3.  `videoclip.js` sends the video file to a **Web Worker** for processing.
4.  The Web Worker runs `ffmpeg.wasm` in the background. As it works, it sends `progress` messages back to the main thread.
5.  The main thread listens for these messages and updates the progress bar in the UI.
6.  Once compression is complete, the worker sends a `done` message back to the main thread, containing the new compressed video file.
7.  The main thread receives the compressed file, places it into the form's file input, updates the UI to show "Compression complete!", and re-enables the submit button.

## 3. Detailed Implementation Steps

### Step 1: Add Frontend Dependencies

This step is unchanged.

```bash
npm install @ffmpeg/ffmpeg @ffmpeg/util
```

### Step 2: Create the Web Worker for Compression

A dedicated worker script will handle all the heavy lifting. This code runs on a separate thread.

*   **New File Location:** `assets/js/video-compressor.worker.js`
*   **Purpose:** To load `ffmpeg.wasm` and perform compression without blocking the main UI.

**Key Components of `video-compressor.worker.js`:**
```javascript
// video-compressor.worker.js

import { FFmpeg } from '@ffmpeg/ffmpeg';
import { toBlobURL } from '@ffmpeg/util';

let ffmpeg;

self.onmessage = async (event) => {
    const { file, command } = event.data;

    if (!ffmpeg) {
        ffmpeg = new FFmpeg();
        // Log loading progress
        ffmpeg.on('log', ({ message }) => {
            // Optional: post log messages back to main thread
        });
        const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/umd';
        await ffmpeg.load({
            coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
            wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
        });
    }

    // Listen for progress and post back to main thread
    ffmpeg.on('progress', ({ progress }) => {
        self.postMessage({ type: 'progress', progress: Math.round(progress * 100) });
    });

    await ffmpeg.writeFile(file.name, new Uint8Array(await file.arrayBuffer()));

    const outputFileName = `compressed-${Date.now()}-${file.name}.mp4`;
    const ffmpegCommand = command || [
        '-i', file.name,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '28',
        '-c:a', 'aac', '-b:a', '128k',
        outputFileName
    ];

    await ffmpeg.exec(ffmpegCommand);

    const data = await ffmpeg.readFile(outputFileName);

    // Post the compressed file back to the main thread
    self.postMessage({ type: 'done', data: data, name: outputFileName });
};
```

### Step 3: Create a `VideoProcessor.js` Module to Manage the Worker

This module will act as the bridge between the UI (`videoclip.js`) and the background worker.

*   **File Location:** `assets/js/VideoProcessor.js`
*   **Purpose:** To abstract the complexity of communicating with the Web Worker.

**Key Components of `VideoProcessor.js`:**
```javascript
// VideoProcessor.js

class VideoProcessor {
    constructor() {
        this.worker = new Worker(new URL('./video-compressor.worker.js', import.meta.url));
    }

    compress(file, progressCallback) {
        return new Promise((resolve, reject) => {
            this.worker.onmessage = (event) => {
                const { type, progress, data, name } = event.data;
                if (type === 'progress') {
                    if (progressCallback) {
                        progressCallback(progress);
                    }
                } else if (type === 'done') {
                    const compressedFile = new File([data.buffer], name, { type: 'video/mp4' });
                    resolve(compressedFile);
                }
            };

            this.worker.onerror = (error) => {
                reject(error);
            };

            // Send the file to the worker to start compression
            this.worker.postMessage({ file });
        });
    }
}

export const videoProcessor = new VideoProcessor();
```

### Step 4: Update `videoclip.js` to Use the Worker

The main UI script now has a much simpler job: manage the UI state and delegate the hard work to the `VideoProcessor`.

*   **File to Modify:** `apps/mediafiles/static/mediafiles/js/videoclip.js`

**Modifications:**
The logic remains very similar to the original plan, but now it's guaranteed to be non-blocking.

1.  **Import `videoProcessor`**.
2.  In the file input's `change` event listener:
    *   Disable the submit button and show the progress UI.
    *   Call `videoProcessor.compress(originalFile, (progress) => { ... })`.
    *   The progress callback updates the progress bar's width and text.
    *   Use `.then()` to handle the successful completion and `.catch()` for errors.
    *   When the promise resolves, update the file input with the new compressed file and re-enable the form.

### Step 5: Update `videoclip_form.html` for User Feedback

This step is unchanged. The same UI elements are needed to show progress.

*   **File to Modify:** `apps/mediafiles/templates/mediafiles/videoclip_form.html`
*   **Action:** Add the progress bar and status message elements, hidden by default.

### Step 6: Implement a Mobile-First Strategy (Recommended)

Given the performance constraints on mobile, it's wise to not force compression on every device.

1.  **Detect Device Type:** In `videoclip.js`, add a simple check.
    ```javascript
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    ```
2.  **Conditional Compression:**
    *   **On Desktop:** Proceed with compression automatically as planned.
    *   **On Mobile:** Check the file size. If it's large (e.g., > 20MB), **ask the user** if they want to compress it.
        > "This video is large. Compressing it first will save data and upload faster, but may take a few minutes. Compress video?" [Yes] [No, upload original]

    This gives mobile users control and sets their expectations, leading to a much better experience.

### Step 7: Backend Validation (No Changes Required)

This step is unchanged. The server-side validation remains a critical security and data integrity layer.