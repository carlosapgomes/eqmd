from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.utils.cache import get_cache_status


class Command(BaseCommand):
    help = 'Check cache health and staleness'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed cache information',
        )

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] Checking cache health...")
        
        status = get_cache_status()
        
        all_healthy = True
        
        for cache_name, cache_status in status.items():
            if not cache_status['exists']:
                self.stdout.write(
                    self.style.ERROR(f"✗ {cache_name}: Cache missing")
                )
                all_healthy = False
            elif cache_status['stale']:
                age_minutes = cache_status['age_seconds'] / 60
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ {cache_name}: Cache is stale ({age_minutes:.1f} minutes old)"
                    )
                )
                all_healthy = False
            else:
                age_minutes = cache_status['age_seconds'] / 60
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {cache_name}: Healthy ({age_minutes:.1f} minutes old)"
                    )
                )
        
        if all_healthy:
            self.stdout.write(
                self.style.SUCCESS("All caches are healthy!")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Some caches need attention")
            )
        
        if options['verbose']:
            self.stdout.write("\nDetailed status:")
            for cache_name, cache_status in status.items():
                self.stdout.write(f"{cache_name}: {cache_status}")
        
        self.stdout.write(f"[{timezone.now()}] Cache health check completed.")