# EquipeMed - Style Guide

## Overview

EquipeMed uses a custom Bootstrap 5.3.6 theme specifically designed for medical applications. The styling emphasizes trust, security, and professionalism through a carefully curated color palette and component design.

## Technology Stack

- **CSS Framework**: Bootstrap 5.3.6
- **Preprocessor**: Sass/SCSS
- **Icons**: Bootstrap Icons 1.13.1
- **Font**: Inter (with system font fallbacks)
- **Build Tool**: Webpack with Sass-loader

## Color Palette

### Medical Color System

The application uses a medical-focused color palette designed to convey trust and professionalism:

```scss
// Primary Medical Colors
$medical-deep-blue: #1e3a8a;     // Primary brand color
$medical-blue: #1e40af;          // Secondary blue
$medical-teal: #0891b2;          // Accent/interactive color
$medical-dark-teal: #0e7490;     // Hover states
$medical-green: #059669;         // Success states
$medical-dark-green: #047857;    // Success hover states

// Neutral Colors
$medical-light-gray: #f8fafc;    // Light backgrounds
$medical-gray: #64748b;          // Secondary text
$medical-dark-gray: #334155;     // Primary text

// Status Colors
$medical-warning-orange: #ea580c; // Warning states
$medical-danger-red: #dc2626;     // Error/danger states
```

### Bootstrap Variable Overrides

```scss
$primary: $medical-deep-blue;
$secondary: $medical-gray;
$success: $medical-green;
$info: $medical-teal;
$warning: $medical-warning-orange;
$danger: $medical-danger-red;
$light: $medical-light-gray;
$dark: $medical-dark-gray;
```

## Typography

### Font Family
- **Primary**: Inter
- **Fallbacks**: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif

### Font Weights
- **Headings**: 600 (Semi-bold)
- **Buttons**: 500 (Medium)
- **Navigation**: 500 (Medium)
- **Body**: 400 (Regular)

### Heading Colors
All headings use `$medical-dark-gray` for consistency and readability.

## Component Styling

### Buttons

#### Medical Button Variants
```scss
.btn-medical-primary      // Deep blue primary button
.btn-medical-teal         // Teal accent button
.btn-medical-outline-primary  // Outlined primary button
.btn-medical-outline-teal     // Outlined teal button
```

#### Button Properties
- **Border Radius**: 0.375rem
- **Font Weight**: 500

### Forms

#### Medical Form Class
Use `.form-medical` wrapper for consistent form styling:

```html
<form class="form-medical">
  <div class="mb-3">
    <label class="form-label">Label Text</label>
    <input type="text" class="form-control">
  </div>
</form>
```

#### Form Properties
- **Border Color**: #d1d5db
- **Focus Border**: $medical-teal
- **Focus Shadow**: rgba(8, 145, 178, 0.25)
- **Border Radius**: 0.375rem

### Cards

#### Medical Card Class
Use `.card-medical` for enhanced card styling:

```html
<div class="card card-medical">
  <div class="card-header">Header Content</div>
  <div class="card-body">Body Content</div>
</div>
```

#### Card Properties
- **Border**: 1px solid #e5e7eb
- **Border Radius**: 0.5rem
- **Box Shadow**: Subtle elevation shadow
- **Header Background**: $medical-light-gray

### Navigation

#### Medical Navbar
Use `.navbar-medical` class for the main navigation:

```html
<nav class="navbar navbar-expand-lg navbar-medical fixed-top">
  <!-- Navigation content -->
</nav>
```

#### Navbar Properties
- **Background**: White (#ffffff)
- **Border Bottom**: 1px solid #e5e7eb
- **Box Shadow**: Subtle shadow for elevation
- **Brand Weight**: 700 (Bold)
- **Link Weight**: 500 (Medium)

### Sidebar Navigation

#### Desktop Sidebar
- **Class**: `.app-sidebar`
- **Position**: Fixed, below navbar
- **Width**: 250px
- **Background**: $medical-light-gray

#### Mobile Sidebar
- **Class**: `.offcanvas-app-menu`
- **Type**: Bootstrap offcanvas component
- **Responsive**: Hidden on large screens

### Tables

#### Medical Table Class
Use `.table-medical` with `.thead-medical` for table headers:

```html
<table class="table table-medical">
  <thead class="thead-medical">
    <tr><th>Header</th></tr>
  </thead>
  <tbody>
    <tr><td>Data</td></tr>
  </tbody>
</table>
```

### Alerts

#### Medical Alert Variants
```scss
.alert-medical-info       // Blue info alerts
.alert-medical-success    // Green success alerts
.alert-medical-warning    // Orange warning alerts
.alert-medical-danger     // Red danger alerts
```

### Badges

#### Medical Badge Variants
```scss
.badge-medical-primary    // Deep blue badges
.badge-medical-teal       // Teal badges
.badge-medical-success    // Green badges
.badge-medical-light      // Light gray badges
```

## Layout System

### App Layout Structure

```html
<body class="app-layout">
  <nav class="navbar navbar-medical fixed-top">...</nav>
  
  <div class="container-fluid">
    <div class="row">
      <nav class="col-lg-2 d-none d-lg-block app-sidebar">...</nav>
      <main class="col-lg-10 offset-lg-2 app-main-content">...</main>
    </div>
  </div>
</body>
```

### Layout Properties
- **Body Padding Top**: 56px (navbar height)
- **Sidebar Width**: 250px
- **Main Content Margin**: 250px left offset on large screens
- **Responsive**: Sidebar becomes offcanvas on mobile

## Utility Classes

### Background Colors
```scss
.bg-medical-primary       // Deep blue background
.bg-medical-teal          // Teal background
.bg-medical-light         // Light gray background
```

### Text Colors
```scss
.text-medical-primary     // Deep blue text
.text-medical-teal        // Teal text
.text-medical-green       // Green text
```

## Responsive Design

### Breakpoints
Following Bootstrap's standard breakpoints:
- **sm**: 576px and up
- **md**: 768px and up
- **lg**: 992px and up (sidebar becomes visible)
- **xl**: 1200px and up
- **xxl**: 1400px and up

### Mobile Considerations
- Sidebar converts to offcanvas menu
- Navigation items stack vertically
- Touch-friendly button sizes maintained
- Proper spacing for mobile interactions

## Accessibility

### Focus States
- All interactive elements have visible focus indicators
- Focus colors use sufficient contrast ratios
- Focus shadows provide clear visual feedback

### Color Contrast
- All text meets WCAG AA contrast requirements
- Interactive elements maintain proper contrast
- Status colors are distinguishable for colorblind users

## File Structure

```
assets/scss/
└── main.scss           // Main stylesheet with all customizations

static/
├── main.css           // Compiled CSS output
└── css/
    └── bootstrap-icons.min.css  // Bootstrap Icons
```

## Usage Guidelines

### When to Use Medical Classes
- Use medical-specific classes for core application components
- Prefer medical variants over standard Bootstrap classes for consistency
- Use standard Bootstrap classes for generic layout and spacing

### Class Naming Convention
- Medical classes follow the pattern: `.{component}-medical-{variant}`
- Utility classes follow: `.{property}-medical-{color}`
- Layout classes use: `.app-{component}`

### Best Practices
1. Always use the medical color palette for brand consistency
2. Maintain proper spacing using Bootstrap's spacing utilities
3. Use semantic HTML elements with appropriate ARIA labels
4. Test components across different screen sizes
5. Ensure sufficient color contrast for accessibility
