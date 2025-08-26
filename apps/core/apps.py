import os
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        """Configure Django Site object from environment variables"""
        self.configure_django_site()
    
    def configure_django_site(self):
        """Update Django Site domain and name from environment variables"""
        from django.conf import settings
        
        site_domain = os.getenv("SITE_DOMAIN")
        site_name = os.getenv("SITE_NAME") 
        
        if site_domain or site_name:
            try:
                from django.contrib.sites.models import Site
                site, created = Site.objects.get_or_create(pk=settings.SITE_ID)
                updated = False
                
                if site_domain and site.domain != site_domain:
                    site.domain = site_domain
                    updated = True
                    
                if site_name and site.name != site_name:
                    site.name = site_name
                    updated = True
                    
                if updated or created:
                    site.save()
                    
            except Exception:
                # Ignore errors during initial migrations or when database doesn't exist yet
                pass
