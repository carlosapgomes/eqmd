# Error Handling Implementation Plan

## Overview

This plan implements custom error handling for the EquipeMed Django application to replace debug error pages with user-friendly styled templates that maintain the project's medical theme and Bootstrap 5.3 styling conventions.

## Project Styling Analysis

Based on codebase analysis:

- **Base Templates**: Uses `base.html` and `base_app.html` structure
- **Styling Framework**: Bootstrap 5.3 with custom medical theme classes
- **Color Scheme**: Medical theme with classes like `text-medical-primary`, `btn-medical-primary`, `bg-medical-light`
- **Portuguese Localization**: All user-facing text should be in Portuguese
- **Icons**: Bootstrap Icons (`bi-*` classes) extensively used
- **Layout**: Flexbox sticky footer layout with `min-vh-100` containers

## Current Error Handling Issues

1. **DEBUG Mode**: Shows detailed Django error pages in development
2. **No Custom Templates**: Missing `403.html`, `404.html`, `500.html` templates
3. **No Error Handlers**: No custom view handlers in `config/urls.py`
4. **User Experience**: Generic error pages don't match medical application theme

## Implementation Steps

### Phase 1: Create Error Templates

#### 1.1 Create `403.html` (Permission Denied)

**Location**: `/templates/403.html`

**Features**:

- Extends `base.html` for consistent layout
- Medical theme styling with appropriate colors
- Clear Portuguese messaging about access restrictions
- Bootstrap card layout with medical icons
- Multiple return options (previous page, dashboard, login)
- Professional medical context messaging

**Return Strategy**: Use JavaScript `history.back()` with fallback to dashboard

#### 1.2 Create `404.html` (Page Not Found)

**Location**: `/templates/404.html`

**Features**:

- Extends `base.html`
- Friendly "page not found" messaging in Portuguese
- Medical-themed graphics and colors
- Search suggestion or navigation help
- Multiple return options
- Professional appearance suitable for medical staff

**Return Strategy**: Primary dashboard link, secondary browser back button

#### 1.3 Create `500.html` (Server Error)

**Location**: `/templates/500.html`

**Features**:

- Extends `base.html`
- Apologetic server error messaging
- Medical-appropriate error communication
- No dynamic content (since server may be unstable)
- Simple return to dashboard option
- Professional medical staff appropriate language

**Return Strategy**: Dashboard link only (no dynamic features)

### Phase 2: Implement Custom Error Views

#### 2.1 Add Error View Functions

**Location**: `apps/core/views.py`

Create three new view functions:

```python
def custom_permission_denied_view(request, exception)
def custom_page_not_found_view(request, exception)
def custom_server_error_view(request)
```

**Features**:

- Proper HTTP status codes (403, 404, 500)
- Error logging for debugging
- Request context preservation where safe
- Portuguese error messaging

#### 2.2 Enhanced Return Logic

Implement smart return functionality:

- **HTTP_REFERER** checking for safe returns
- **Session-based** previous page tracking
- **Fallback hierarchy**: referer → dashboard → login
- **Security validation** to prevent redirect attacks

### Phase 3: URL Configuration

#### 3.1 Add Error Handlers

**Location**: `config/urls.py`

Add handler declarations:

```python
handler403 = 'apps.core.views.custom_permission_denied_view'
handler404 = 'apps.core.views.custom_page_not_found_view'
handler500 = 'apps.core.views.custom_server_error_view'
```

### Phase 4: Styling & UX Enhancements

#### 4.1 Template Styling Standards

- **Container**: `container-fluid` or `container` with medical theme
- **Cards**: Bootstrap card components with `card-header` medical styling
- **Buttons**: `btn-medical-primary`, `btn-outline-medical-primary` classes
- **Icons**: Bootstrap icons (`bi-shield-x`, `bi-house`, `bi-arrow-left`)
- **Colors**: Medical color scheme (`text-medical-primary`, `bg-medical-light`)
- **Typography**: Professional medical typography with proper hierarchy

#### 4.2 Return Button Implementation

**Multiple Return Options**:

1. **Primary Action**: Styled medical button returning to appropriate location
2. **Secondary Actions**: Dashboard, Login (based on authentication status)
3. **Browser Back**: Subtle link using JavaScript `history.back()`

**Button Styling**:

```html
<button class="btn btn-medical-primary btn-lg">
  <i class="bi bi-arrow-left me-2"></i>
  Voltar ao Dashboard
</button>
```

### Phase 5: Testing & Validation

#### 5.1 Error Simulation Testing

- **403 Testing**: Access restricted views without permission
- **404 Testing**: Navigate to non-existent URLs
- **500 Testing**: Temporarily break server functionality

#### 5.2 User Experience Testing

- **Return Functionality**: Test all return button scenarios
- **Mobile Responsiveness**: Test on mobile devices
- **Portuguese Localization**: Verify all text is properly localized
- **Medical Theme Consistency**: Visual consistency with main application

#### 5.3 Production Validation

- **DEBUG=False**: Test with production settings
- **Error Logging**: Verify errors are properly logged
- **Performance**: Ensure error pages load quickly

## Implementation Details

### Template Structure

```
/templates/
├── 403.html          # Permission denied
├── 404.html          # Page not found
└── 500.html          # Server error
```

### View Function Signatures

```python
# Permission denied (403)
def custom_permission_denied_view(request, exception):
    # Log error, preserve safe context
    return render(request, '403.html', context, status=403)

# Page not found (404)
def custom_page_not_found_view(request, exception):
    # Log error, minimal context
    return render(request, '404.html', context, status=404)

# Server error (500)
def custom_server_error_view(request):
    # Minimal processing, no dynamic content
    return render(request, '500.html', status=500)
```

### Return Logic Priority

1. **Safe HTTP_REFERER** (same domain, authenticated routes)
2. **Dashboard** (`core:dashboard`) for authenticated users
3. **Login page** (`account_login`) for anonymous users
4. **Landing page** (`core:landing_page`) as final fallback

## Security Considerations

1. **Referer Validation**: Only allow same-domain referers
2. **Information Disclosure**: Avoid revealing system information
3. **Error Logging**: Log errors without exposing details to users
4. **CSRF Protection**: Ensure error forms maintain CSRF protection

## Medical Context Messaging

All error messages should be:

- **Professional** and appropriate for medical staff
- **Clear and actionable** with next steps
- **Portuguese localized** with medical terminology
- **Reassuring** while maintaining system security
- **Contextually appropriate** for hospital environment

## Success Criteria

✅ **User Experience**: Medical staff see branded, professional error pages  
✅ **Functionality**: All return options work correctly in all scenarios  
✅ **Security**: No sensitive information leaked, proper access controls  
✅ **Consistency**: Visual and functional consistency with main application  
✅ **Localization**: All text in Portuguese with appropriate medical language  
✅ **Performance**: Error pages load quickly even during system issues

This implementation will provide a professional, user-friendly error handling experience that maintains the medical application's professional appearance and functionality.
