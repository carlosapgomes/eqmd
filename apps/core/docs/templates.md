# Core App Templates Documentation

This document provides detailed information about all templates in the Core app and their relationship with the base template system.

## Overview

The Core app uses a hierarchical template system with shared base templates and app-specific templates:

- **Base Templates**: Located in `templates/` (project root)
- **App Templates**: Located in `apps/core/templates/core/`

## Template Hierarchy

```
templates/
├── base.html                    # Root base template
└── base_app.html               # App-specific base template
    └── core/
        ├── landing_page.html   # Public landing page
        └── dashboard.html      # Authenticated dashboard
```

## Base Templates

### `templates/base.html`

**Purpose**: Root template providing basic HTML structure and common elements.

#### Features
- HTML5 document structure
- Bootstrap CSS and JavaScript
- Bootstrap Icons
- Responsive viewport meta tag
- Flexbox layout for sticky footer
- Common blocks for customization

#### Block Structure
```django
{% block title %}EquipeMed{% endblock title %}
{% block extra_head %}{% endblock extra_head %}
{% block header %}{% endblock header %}
{% block content %}{% endblock content %}
{% block footer %}{% endblock footer %}
{% block extra_scripts %}{% endblock extra_scripts %}
```

#### CSS Framework
- **Bootstrap**: Latest version via CDN
- **Bootstrap Icons**: Icon library
- **Custom CSS**: Medical-themed color scheme
- **Flexbox Layout**: Sticky footer implementation

#### Footer Implementation
```html
<footer class="mt-auto py-3 bg-light">
    <div class="container text-center">
        <span class="text-muted">&copy; {% now "Y" %} EquipeMed. Todos os direitos reservados.</span>
    </div>
</footer>
```

### `templates/base_app.html`

**Purpose**: Application-specific base template extending `base.html` with navigation and layout.

#### Features
- Fixed top navigation bar
- Collapsible sidebar navigation
- Mobile-responsive offcanvas menu
- User profile dropdown
- Notification system
- Main content area

#### Block Structure
```django
{% extends "base.html" %}
{% block extra_head %}{% endblock %}
{% block header %}{% endblock %}
{% block content %}
    <!-- App layout with sidebar and main content -->
    {% block app_content %}{% endblock app_content %}
{% endblock %}
```

#### Navigation Features
- **Top Bar**: Brand, notifications, user menu
- **Sidebar**: Main navigation menu (desktop)
- **Offcanvas**: Mobile navigation menu
- **User Menu**: Profile, settings, logout

## App Templates

### `core/landing_page.html`

**Location**: `apps/core/templates/core/landing_page.html`
**Extends**: `base.html`
**Purpose**: Public-facing homepage for EquipeMed

#### Template Structure
```django
{% extends "base.html" %}

{% block header %}
    <!-- Custom navigation for landing page -->
{% endblock %}

{% block content %}
    <!-- Hero Section -->
    <!-- Features Section -->
    <!-- Benefits Section -->
    <!-- CTA Section -->
{% endblock %}
```

#### Sections

##### Hero Section
- **Purpose**: Main value proposition and call-to-action
- **Features**: 
  - Compelling headline
  - Feature description
  - Primary and secondary CTAs
  - Visual element (icon/illustration)

```html
<section class="bg-medical-light py-5">
    <div class="container">
        <div class="row align-items-center min-vh-50">
            <div class="col-lg-6">
                <h1 class="display-4 fw-bold text-medical-primary mb-4">
                    Conecte sua equipe médica em todos os hospitais
                </h1>
                <!-- Content continues... -->
            </div>
        </div>
    </div>
</section>
```

##### Features Section
- **Purpose**: Showcase key application features
- **Layout**: Card-based grid layout
- **Features**:
  - Patient tracking
  - Clinical events management
  - Team collaboration
  - Security and compliance

##### Benefits Section
- **Purpose**: Highlight value propositions
- **Features**:
  - Efficiency improvements
  - Better patient care
  - Streamlined workflows
  - Cost savings

##### CTA Section
- **Purpose**: Final conversion opportunity
- **Features**:
  - Strong call-to-action
  - Contact information
  - Trust indicators

#### Responsive Design
- **Mobile-first**: Optimized for mobile devices
- **Breakpoints**: Bootstrap responsive breakpoints
- **Navigation**: Collapsible mobile menu
- **Content**: Stacked layout on small screens

### `core/dashboard.html`

**Location**: `apps/core/templates/core/dashboard.html`
**Extends**: `base_app.html`
**Purpose**: Main interface for authenticated users

#### Template Structure
```django
{% extends "base_app.html" %}
{% load static %}

{% block page_title %}{{ page_title }}{% endblock page_title %}

{% block app_content %}
    <!-- Welcome Section -->
    <!-- Stats Cards -->
    <!-- Recent Activity -->
    <!-- Quick Actions -->
{% endblock app_content %}
```

#### Sections

##### Welcome Section
- **Purpose**: Personalized greeting and context
- **Features**:
  - User name display
  - Last login information
  - Current date/time

```html
<div class="row mb-4">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h1 class="h3 text-medical-primary mb-1">Bem-vindo, Dr. Silva</h1>
                <p class="text-medical-gray mb-0">Painel de controle - EquipeMed</p>
            </div>
            <div class="text-end">
                <small class="text-muted">Último acesso: Hoje, 14:30</small>
            </div>
        </div>
    </div>
</div>
```

##### Stats Cards
- **Purpose**: Key metrics overview
- **Features**:
  - Patient count
  - Recent activities
  - Pending tasks
  - System status

##### Recent Activity
- **Purpose**: Latest user actions and system events
- **Features**:
  - Activity timeline
  - Action descriptions
  - Timestamps
  - Quick actions

##### Quick Actions
- **Purpose**: Common tasks and shortcuts
- **Features**:
  - Add new patient
  - Create clinical event
  - View reports
  - Access settings

## Styling and Design System

### Color Scheme
The templates use a medical-themed color palette:

```css
/* Primary Colors */
.text-medical-primary { color: #2c5aa0; }
.bg-medical-primary { background-color: #2c5aa0; }

/* Accent Colors */
.text-medical-teal { color: #20c997; }
.bg-medical-teal { background-color: #20c997; }

/* Neutral Colors */
.text-medical-gray { color: #6c757d; }
.text-medical-dark-gray { color: #495057; }
.bg-medical-light { background-color: #f8f9fa; }
```

### Typography
- **Font Family**: System font stack (Bootstrap default)
- **Headings**: Bold weights for hierarchy
- **Body Text**: Regular weight, good contrast
- **Small Text**: Muted colors for secondary information

### Components
- **Cards**: Consistent card styling with shadows
- **Buttons**: Medical-themed button variants
- **Navigation**: Consistent navigation styling
- **Icons**: Bootstrap Icons throughout

## Template Tags and Filters

### Django Template Tags Used
```django
{% load static %}          # Static files
{% url 'namespace:name' %} # URL generation
{% now "Y" %}             # Current year
{% block %}{% endblock %} # Template inheritance
{% extends "template" %}  # Template extension
```

### Custom Context Variables
```django
{{ page_title }}          # Page title
{{ user.first_name }}     # User information
```

## Responsive Behavior

### Breakpoints
Following Bootstrap 5 breakpoints:
- **xs**: <576px (mobile)
- **sm**: ≥576px (mobile landscape)
- **md**: ≥768px (tablet)
- **lg**: ≥992px (desktop)
- **xl**: ≥1200px (large desktop)

### Mobile Optimizations
- **Navigation**: Offcanvas sidebar for mobile
- **Content**: Stacked layouts on small screens
- **Touch**: Appropriate touch targets
- **Performance**: Optimized images and assets

## Accessibility

### Current Implementation
- **Semantic HTML**: Proper heading hierarchy
- **ARIA Labels**: Basic ARIA attributes
- **Keyboard Navigation**: Standard browser behavior
- **Color Contrast**: Good contrast ratios

### Recommended Improvements
1. **ARIA Landmarks**: Add landmark roles
2. **Focus Management**: Improve focus indicators
3. **Screen Readers**: Add more descriptive text
4. **Keyboard Navigation**: Custom keyboard shortcuts

## Performance Considerations

### Current Optimizations
- **CSS/JS**: Minified Bootstrap from CDN
- **Images**: Optimized image sizes
- **Caching**: Browser caching headers

### Recommended Improvements
1. **Critical CSS**: Inline critical CSS
2. **Lazy Loading**: Implement lazy loading for images
3. **Code Splitting**: Split JavaScript bundles
4. **Compression**: Enable gzip compression

## Future Enhancements

### Planned Features
1. **Dark Mode**: Theme switching capability
2. **PWA**: Progressive Web App features
3. **Animations**: Smooth transitions and animations
4. **Customization**: User-customizable themes

### Template Improvements
1. **Component Library**: Reusable template components
2. **Template Fragments**: Smaller, reusable template pieces
3. **Dynamic Content**: AJAX-loaded content areas
4. **Real-time Updates**: WebSocket integration

## Related Documentation

- [Views Documentation](views.md)
- [URL Patterns Documentation](urls.md)
- [Core App Overview](README.md)
