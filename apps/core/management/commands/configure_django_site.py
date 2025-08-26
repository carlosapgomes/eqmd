import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Configure Django Site object from environment variables'
    
    def handle(self, *args, **options):
        """Update Django Site domain and name from environment variables"""
        site_domain = os.getenv("SITE_DOMAIN")
        site_name = os.getenv("SITE_NAME") 
        
        if not site_domain and not site_name:
            self.stdout.write(
                self.style.WARNING('No SITE_DOMAIN or SITE_NAME environment variables found')
            )
            return
        
        try:
            site, created = Site.objects.get_or_create(pk=settings.SITE_ID)
            updated = False
            
            if site_domain and site.domain != site_domain:
                old_domain = site.domain
                site.domain = site_domain
                updated = True
                self.stdout.write(f'Updated site domain: {old_domain} → {site_domain}')
                
            if site_name and site.name != site_name:
                old_name = site.name
                site.name = site_name
                updated = True
                self.stdout.write(f'Updated site name: {old_name} → {site_name}')
                
            if updated or created:
                site.save()
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created new Django Site: {site.name} ({site.domain})')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated Django Site: {site.name} ({site.domain})')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Django Site already configured: {site.name} ({site.domain})')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to configure Django Site: {e}')
            )
            raise