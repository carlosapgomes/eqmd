from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted objects by default."""

    def delete(self):
        """Soft delete all objects in queryset."""
        return super().update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

    def hard_delete(self):
        """Actually delete objects from database (admin only)."""
        return super().delete()

    def active(self):
        """Return only non-deleted objects."""
        return self.filter(is_deleted=False)

    def deleted(self):
        """Return only deleted objects."""
        return self.filter(is_deleted=True)

    def with_deleted(self):
        """Return all objects including deleted ones."""
        return self.all()


class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted objects by default."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self):
        """Get all objects including soft-deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Get only soft-deleted objects."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class AllObjectsManager(models.Manager):
    """Manager that returns all objects without filtering soft-deleted ones."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def active(self):
        """Return only non-deleted objects."""
        return self.get_queryset().active()

    def deleted(self):
        """Return only deleted objects."""
        return self.get_queryset().deleted()

    def deleted_only(self):
        """Get only soft-deleted objects."""
        return self.get_queryset().deleted()


class SoftDeleteModel(models.Model):
    """Abstract base class for soft delete functionality."""

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.EQMDCustomUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_deleted_set'
    )
    deletion_reason = models.TextField(blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()  # Manager that returns all objects without filtering

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, deleted_by=None, reason=''):
        """Soft delete this object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.deletion_reason = reason
        self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """Actually delete this object from database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self, restored_by=None):
        """Restore a soft-deleted object."""
        # Log restoration in history if available
        if hasattr(self, 'history'):
            self._change_reason = f"Restored by {restored_by.username if restored_by else 'system'}"
        
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deletion_reason = ''
        self.save()