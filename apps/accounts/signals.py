"""
Signal handlers for the accounts app.

This module handles automatic profile creation and group assignment
based on user profession types.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group

from .models import EqmdCustomUser, UserProfile


@receiver(post_save, sender=EqmdCustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when a new user is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=EqmdCustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Ensure user profile exists and is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=EqmdCustomUser)
def assign_user_to_profession_group(sender, instance, created, **kwargs):
    """
    Assign user to appropriate group based on profession type.

    This signal handler automatically assigns users to groups when:
    1. A new user is created with a profession type
    2. An existing user's profession type is changed
    """
    if instance.profession_type is not None:
        # Map profession types to group names
        profession_group_map = {
            EqmdCustomUser.MEDICAL_DOCTOR: 'Medical Doctors',
            EqmdCustomUser.RESIDENT: 'Residents',
            EqmdCustomUser.NURSE: 'Nurses',
            EqmdCustomUser.PHYSIOTERAPIST: 'Physiotherapists',
            EqmdCustomUser.STUDENT: 'Students',
        }

        # Get the group name for this profession
        group_name = profession_group_map.get(instance.profession_type)

        if group_name:
            try:
                # Get or create the group
                group, created_group = Group.objects.get_or_create(name=group_name)

                # Remove user from all profession-based groups first
                profession_groups = Group.objects.filter(
                    name__in=profession_group_map.values()
                )
                instance.groups.remove(*profession_groups)

                # Add user to the appropriate group
                instance.groups.add(group)

            except Exception as e:
                # Log the error but don't fail the user creation/update
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to assign user {instance.username} to group {group_name}: {e}")
    else:
        # If profession type is None, remove from all profession groups
        profession_group_names = [
            'Medical Doctors',
            'Residents',
            'Nurses',
            'Physiotherapists',
            'Students',
        ]

        profession_groups = Group.objects.filter(name__in=profession_group_names)
        instance.groups.remove(*profession_groups)