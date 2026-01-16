"""
Custom OIDC claims for EQMD.

Provides claims for both bot delegation and Synapse SSO integration.
"""

from oidc_provider.lib.claims import ScopeClaims


def eqmd_sub_generator(user):
    """Return stable subject identifier based on profile public_id."""
    try:
        profile = user.profile
    except Exception:
        from apps.accounts.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=user)
    return str(getattr(profile, "public_id", user.pk))


class EqmdScopeClaims(ScopeClaims):
    """Custom scope claims for EQMD delegation tokens and Synapse SSO."""
    
    info_openid = [
        'sub',
        'name', 
        'preferred_username',
        'eqmd_active',
        'eqmd_role',
    ]

    def scope_openid(self):
        """OpenID Connect standard claims for user identity."""
        user = self.user
        
        public_id = eqmd_sub_generator(user)
        
        # Build full name with fallbacks
        full_name = user.get_full_name()
        if not full_name.strip():
            full_name = user.email or user.username
        
        # Get preferred username (email-based login)
        preferred_username = user.email or user.username
        
        # Map profession type to stable ASCII slugs
        profession_mapping = {
            user.MEDICAL_DOCTOR: 'medical_doctor',
            user.RESIDENT: 'resident', 
            user.NURSE: 'nurse',
            user.PHYSIOTERAPIST: 'physiotherapist',
            user.STUDENT: 'student',
        }
        
        eqmd_role = profession_mapping.get(user.profession_type, 'unknown') if user.profession_type is not None else 'unknown'
        
        return {
            'sub': public_id,
            'name': full_name,
            'preferred_username': preferred_username,
            'eqmd_active': user.is_active,
            'eqmd_role': eqmd_role,
        }
