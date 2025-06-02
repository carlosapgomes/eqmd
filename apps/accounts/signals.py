from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EqmdCustomUser, UserProfile

@receiver(post_save, sender=EqmdCustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=EqmdCustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)