# Custom Logout Page Implementation Plan

## Overview

This plan details the implementation of a custom logout page to replace the default allauth logout.html template. The new page will extend base.html and follow the EquipeMed design system established in the login page.

## Current State Analysis

- [ ] **Current logout URL**: Uses allauth's default `account_logout` URL
- [ ] **Current template**: Uses allauth's default logout.html template
- [ ] **Current behavior**: Basic logout confirmation with minimal styling
- [ ] **Integration points**: Logout link exists in `templates/base_app.html` navigation dropdown

## Implementation Plan

### Phase 1: Template Creation

- [ ] **Create custom logout template**
  - [ ] Create `templates/account/logout.html` file
  - [ ] Extend `base.html` template (not `base_app.html` since user is logging out)
  - [ ] Follow the design pattern established in `templates/account/login.html`
  - [ ] Use medical color scheme and styling from the project's SCSS

### Phase 2: Template Structure Design

- [ ] **Header section**
  - [ ] Create navigation bar similar to login page
  - [ ] Include EquipeMed branding with medical icon
  - [ ] Add "Voltar ao Dashboard" button for authenticated users
  - [ ] Use `.navbar-medical` or similar styling class

- [ ] **Main content area**
  - [ ] Center the logout confirmation card
  - [ ] Use `.card-medical` styling for consistency
  - [ ] Include medical-themed icon (e.g., `bi-box-arrow-right`)
  - [ ] Add professional logout confirmation message

- [ ] **Logout form**
  - [ ] Implement POST form with CSRF token
  - [ ] Use `{% url 'account_logout' %}` as form action
  - [ ] Include hidden redirect field if needed
  - [ ] Style submit button with `.btn-medical-primary`

### Phase 3: Content and Messaging

- [ ] **Portuguese localization**
  - [ ] Use Portuguese text throughout the template
  - [ ] Maintain professional medical tone
  - [ ] Include appropriate confirmation message

- [ ] **User experience elements**
  - [ ] Add logout confirmation question
  - [ ] Include security-related messaging
  - [ ] Provide clear action buttons
  - [ ] Add option to cancel and return to dashboard

### Phase 4: Styling Implementation

- [ ] **CSS styling**
  - [ ] Use existing medical color palette
  - [ ] Apply consistent spacing and typography
  - [ ] Ensure responsive design for mobile devices
  - [ ] Add hover effects and transitions

- [ ] **Icon integration**
  - [ ] Use Bootstrap Icons for consistency
  - [ ] Include logout-related icons (`bi-box-arrow-right`)
  - [ ] Add security/shield icons for trust indicators

### Phase 5: Form Functionality

- [ ] **Form implementation**
  - [ ] Ensure proper CSRF protection
  - [ ] Handle POST request correctly
  - [ ] Include redirect field handling
  - [ ] Test form submission

- [ ] **Button actions**
  - [ ] Primary logout button (POST form submission)
  - [ ] Secondary cancel/return button (link to dashboard)
  - [ ] Proper button styling and accessibility

### Phase 6: Integration and Testing

- [ ] **Template integration**
  - [ ] Verify template overrides allauth default
  - [ ] Test template inheritance from base.html
  - [ ] Ensure all template tags load correctly

- [ ] **Navigation integration**
  - [ ] Verify logout link in `base_app.html` works correctly
  - [ ] Test logout flow from authenticated pages
  - [ ] Ensure proper redirect after logout

### Phase 7: Responsive Design

- [ ] **Mobile optimization**
  - [ ] Test on mobile devices
  - [ ] Ensure card layout works on small screens
  - [ ] Verify button sizes are touch-friendly

- [ ] **Cross-browser testing**
  - [ ] Test in major browsers
  - [ ] Verify styling consistency
  - [ ] Check form functionality

### Phase 8: Security and Accessibility

- [ ] **Security considerations**
  - [ ] Verify CSRF token implementation
  - [ ] Test logout functionality
  - [ ] Ensure session cleanup

- [ ] **Accessibility features**
  - [ ] Add proper ARIA labels
  - [ ] Ensure keyboard navigation
  - [ ] Verify screen reader compatibility
  - [ ] Check color contrast ratios

### Phase 9: Documentation and Cleanup

- [ ] **Code documentation**
  - [ ] Add template comments
  - [ ] Document any custom styling
  - [ ] Update relevant documentation files

- [ ] **Testing verification**
  - [ ] Manual testing of logout flow
  - [ ] Verify redirect behavior
  - [ ] Test with different user states

## Technical Requirements

### Template Structure

```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}Sair - EquipeMed{% endblock title %}

{% block header %}
<!-- Custom navigation for logout page -->
{% endblock %}

{% block content %}
<!-- Logout confirmation content -->
{% endblock %}

{% block extra_styles %}
<!-- Custom CSS for logout page -->
{% endblock %}
```

### Required Template Tags

- [ ] `{% load i18n %}` for internationalization
- [ ] `{% csrf_token %}` for form security
- [ ] `{% url 'account_logout' %}` for form action
- [ ] `{{ redirect_field }}` for redirect handling

### Styling Classes to Use

- [ ] `.navbar-medical` for navigation
- [ ] `.card-medical` for main content card
- [ ] `.btn-medical-primary` for logout button
- [ ] `.btn-outline-secondary` for cancel button
- [ ] `.text-medical-primary` for branding
- [ ] `.bg-medical-light` for background

## Success Criteria

- [ ] **Functional requirements met**
  - [ ] Logout functionality works correctly
  - [ ] Template overrides allauth default
  - [ ] Proper redirect behavior after logout

- [ ] **Design requirements met**
  - [ ] Consistent with EquipeMed design system
  - [ ] Professional medical appearance
  - [ ] Responsive across devices

- [ ] **User experience requirements met**
  - [ ] Clear logout confirmation
  - [ ] Easy to understand interface
  - [ ] Accessible to all users

## Files to be Created/Modified

- [ ] **New file**: `templates/account/logout.html`
- [ ] **Verify**: `templates/base_app.html` (logout link should work)
- [ ] **Test**: Navigation flow and user experience

## Dependencies

- [ ] Django allauth (already installed)
- [ ] Bootstrap 5.3.6 (already available)
- [ ] Bootstrap Icons (already available)
- [ ] Medical SCSS theme (already implemented)

## Estimated Timeline

- [ ] **Phase 1-3**: Template creation and structure (2-3 hours)
- [ ] **Phase 4-5**: Styling and functionality (2-3 hours)
- [ ] **Phase 6-8**: Integration and testing (2-3 hours)
- [ ] **Phase 9**: Documentation and cleanup (1 hour)

**Total estimated time**: 7-10 hours
