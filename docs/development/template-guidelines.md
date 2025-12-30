# Django Template Development Guidelines

## Template Block Architecture

**Critical Rule**: When extending Django templates, ALWAYS ensure content is placed within proper template blocks.

### Event Card Template Structure

Event card templates extend `event_card_base.html` which provides these blocks:

- `{% block event_actions %}` - Action buttons (view, edit, delete, etc.)
- `{% block event_content %}` - Main event content display
- `{% block event_metadata %}` - Footer metadata (creator, timestamps, etc.)
- `{% block extra_html %}` - Additional HTML (modals, hidden elements)
- `{% block extra_css %}` - Event-specific CSS styles
- `{% block extra_js %}` - Event-specific JavaScript

### Template Development Checklist

**Before creating/modifying templates:**

1. **Identify Base Template**: Check which template is being extended
2. **Review Available Blocks**: Read the base template to see all available blocks
3. **Block Content Placement**: Ensure ALL content is within appropriate blocks
4. **Content Outside Blocks**: Verify nothing exists outside block definitions
5. **Testing**: Test that CSS, JavaScript, and HTML render correctly

### Common Mistakes to Avoid

```django
<!-- ❌ WRONG: Content outside blocks will be ignored -->
{% extends "base.html" %}
<style>/* This CSS will NOT be rendered */</style>
{% block content %}...{% endblock %}
<script>/* This JS will NOT be executed */</script>

<!-- ✅ CORRECT: All content within blocks -->
{% extends "base.html" %}
{% block content %}...{% endblock %}
{% block extra_css %}<style>/* This CSS renders */</style>{% endblock %}
{% block extra_js %}<script>/* This JS executes */</script>{% endblock %}
```

### Debugging Template Issues

If functionality doesn't work (CSS not applied, JavaScript not executing):

1. Check if content is outside template blocks
2. Verify block names match base template
3. Ensure base template defines required blocks
4. Test with browser dev tools for missing resources

## Best Practices

### Template Inheritance

- Always use `{% extends %}` for consistent layout
- Place all content within appropriate template blocks
- Use `{% load %}` tags within blocks when possible

### Static Files

- Use `{% load static %}` for static file references
- Place CSS in `{% block extra_css %}`
- Place JavaScript in `{% block extra_js %}`

### Code Organization

- Keep template logic minimal
- Use template tags for complex logic
- Prefer view-level data processing over template processing
