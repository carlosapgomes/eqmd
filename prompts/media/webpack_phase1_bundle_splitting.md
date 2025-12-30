# Phase 1: Webpack Bundle Splitting Configuration

## Objective

Configure webpack to create separate bundles for each mediafiles JavaScript module instead of bundling everything into main-bundle.js.

## Prerequisites

- Current webpack.config.js working properly
- All JavaScript files in apps/mediafiles/static/mediafiles/js/ are functional
- Backup current webpack configuration

## Step-by-Step Implementation

### Step 1: Analyze Current Webpack Configuration

1. **Read current webpack.config.js**
   - Identify current entry point structure
   - Note output configuration
   - Document any existing optimization settings

### Step 2: Create New Entry Point Structure

1. **Backup current configuration**

   ```bash
   cp webpack.config.js webpack.config.js.backup
   ```

2. **Modify webpack.config.js entry points:**
   - Remove mediafiles JS from main bundle
   - Create separate entries for each module:

     ```javascript
     entry: {
       main: ["./assets/index.js", "./assets/scss/main.scss"],
       mediafiles: ["./apps/mediafiles/static/mediafiles/js/mediafiles.js"],
       photo: ["./apps/mediafiles/static/mediafiles/js/photo.js"],
       photoseries: ["./apps/mediafiles/static/mediafiles/js/photoseries.js"],
       videoclip: ["./apps/mediafiles/static/mediafiles/js/videoclip.js"]
     }
     ```

### Step 3: Configure Output Settings

1. **Update output configuration:**
   - Ensure proper filename pattern for multiple bundles
   - Set up chunk naming for clarity

   ```javascript
   output: {
     filename: '[name]-bundle.js',
     chunkFilename: '[name]-chunk.js',
     // ... other existing settings
   }
   ```

### Step 4: Update Optimization Settings

1. **Configure code splitting optimization:**

   ```javascript
   optimization: {
     splitChunks: {
       chunks: 'all',
       cacheGroups: {
         vendor: {
           test: /[\\/]node_modules[\\/]/,
           name: 'vendors',
           chunks: 'all',
         },
         mediafiles: {
           test: /[\\/]apps[\\/]mediafiles[\\/]/,
           name: 'mediafiles-common',
           chunks: 'all',
           minChunks: 2,
         }
       }
     }
   }
   ```

### Step 5: Build and Verify

1. **Run webpack build:**

   ```bash
   npm run build
   ```

2. **Verify output files generated:**
   - main-bundle.js (core application)
   - mediafiles-bundle.js (shared mediafiles utilities)
   - photo-bundle.js (photo-specific code)
   - photoseries-bundle.js (photoseries-specific code)
   - videoclip-bundle.js (videoclip-specific code)

3. **Check bundle sizes:**

   ```bash
   ls -la static/ | grep bundle
   ```

### Step 6: Test Basic Loading

1. **Temporarily test bundle loading in browser console:**
   - Load main-bundle.js - should work normally
   - Load photo-bundle.js - should define window.Photo
   - Verify no JavaScript errors in console

## Expected Outcomes

- ✅ Webpack generates separate bundles for each module
- ✅ Main bundle no longer contains mediafiles code
- ✅ Each bundle is properly named and accessible
- ✅ No build errors or warnings

## Rollback Plan

If issues occur:

```bash
cp webpack.config.js.backup webpack.config.js
npm run build
```

## Next Phase Dependencies

- All bundles must build successfully
- Bundle file sizes should be reasonable
- No JavaScript errors during build process

## Testing Checklist

- [ ] Webpack build completes without errors
- [ ] All expected bundle files are generated
- [ ] Bundle file sizes are reasonable
- [ ] Browser can load individual bundles without errors
- [ ] No missing dependencies or import errors

## Notes

- This phase only changes webpack configuration
- Templates still load old bundles (will be fixed in Phase 2)
- JavaScript modules still auto-initialize (will be fixed in Phase 3)
- This is a foundational change - thorough testing required before proceeding
