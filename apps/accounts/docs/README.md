# Accounts App Documentation

The Accounts app provides user authentication and profile management for the EquipeMed application.

## Models

### EqmdCustomUser

This model extends Django's AbstractUser to add healthcare profession-specific fields:

- `profession_type`: Type of healthcare profession (doctor, nurse, etc.)
- `professional_registration_number`: Professional license number
- `country_id_number`: National ID number
- `fiscal_number`: Tax ID number
- `phone`: Contact phone number

### UserProfile

A one-to-one relationship with EqmdCustomUser that provides:

- `public_id`: UUID for public identification (instead of exposing user IDs)
- `display_name`: User's display name
- `bio`: User biography/description

#### Read-only Properties

The UserProfile model exposes these EqmdCustomUser fields as read-only properties:

- `is_active`: Whether the user account is active
- `is_staff`: Whether the user has staff privileges
- `is_superuser`: Whether the user has superuser privileges
- `email`: User's email address
- `first_name`: User's first name
- `last_name`: User's last name
- `full_name`: Convenience property combining first and last name
- `profession`: Human-readable profession type

## Features

1. **Custom User Model**: Extended user model with healthcare profession fields
2. **Profile System**: Separate profile model with public UUID
3. **Auto-Profile Creation**: Signals automatically create profiles for new users
4. **Security**: Uses public UUIDs instead of sequential IDs in URLs
5. **Property Exposure**: Safely exposes user data through profile properties

## Usage

### URL Patterns

- `/accounts/profile/<uuid>/`: View a user profile
- `/accounts/profile/<uuid>/detail/`: Detailed profile view
- `/accounts/profile/<uuid>/update/`: Update profile
- `/accounts/profile/redirect/`: Redirect to current user's profile

### In Templates

```html
<!-- Access user data through profile properties -->
<h2>{{ profile.full_name }}</h2>
<p>{{ profile.email }}</p>
<p>{{ profile.profession }}</p>

<!-- Link to profile using public_id -->
<a href="{% url 'accounts:profile' public_id=user.profile.public_id %}">
    {{ user.profile.display_name }}
</a>
```

### In Views

```python
from django.urls import reverse_lazy

# Redirect to a profile
return redirect(reverse_lazy('accounts:profile', 
                kwargs={'public_id': user.profile.public_id}))

# Check if user is viewing their own profile
context['is_owner'] = request.user == profile.user
```

## Security Considerations

1. **UUID Instead of Sequential IDs**: Prevents enumeration attacks
2. **Property Exposure**: Only exposes specific user data through profile properties
3. **Permission Checks**: Views ensure users can only edit their own profiles
