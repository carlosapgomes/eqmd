from django.contrib import admin
from .models import Hospital, Ward


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'city', 'state']
    search_fields = ['name', 'short_name', 'city', 'state']
    list_filter = ['state', 'city']


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'hospital', 'capacity', 'is_active')
    list_filter = ('hospital', 'is_active')
    search_fields = ('name', 'description', 'hospital__name')
