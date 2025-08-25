from django.db import models


class DashboardCache(models.Model):
    """General dashboard statistics cache"""
    key = models.CharField(max_length=100, primary_key=True)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_dashboard_cache'

    def __str__(self):
        return f"DashboardCache({self.key})"


class WardMappingCache(models.Model):
    """Ward mapping data cache"""
    cache_key = models.CharField(max_length=100, primary_key=True)
    ward_data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_ward_mapping_cache'

    def __str__(self):
        return f"WardMappingCache({self.cache_key})"