from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from django.db.models import Count
from apps.events.models import Event
from apps.patients.models import Patient
import time

class Command(BaseCommand):
    help = 'Analyze timeline performance and suggest optimizations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['analyze', 'test', 'report'],
            default='analyze',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--patient-id',
            help='Specific patient ID to test'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'analyze':
            self.analyze_query_performance()
        elif action == 'test':
            self.test_timeline_performance(options.get('patient_id'))
        elif action == 'report':
            self.generate_performance_report()
    
    def analyze_query_performance(self):
        """Analyze common timeline queries for performance issues."""
        self.stdout.write("Analyzing timeline query performance...")
        
        # Test various query patterns
        queries = [
            ('Basic timeline query', lambda p: Event.objects.filter(patient=p).order_by('-created_at')[:15]),
            ('Optimized timeline query', lambda p: Event.objects.filter(patient=p).select_related('created_by').order_by('-created_at')[:15]),
            ('With prefetch', lambda p: Event.objects.filter(patient=p).select_related('created_by').prefetch_related('created_by__groups').order_by('-created_at')[:15]),
        ]
        
        patient = Patient.objects.first()
        if not patient:
            self.stdout.write(self.style.ERROR("No patients found for testing"))
            return
        
        for query_name, query_func in queries:
            start_time = time.time()
            start_queries = len(connection.queries)
            
            list(query_func(patient))  # Force evaluation
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            self.stdout.write(
                f"{query_name}: {end_time - start_time:.3f}s, "
                f"{end_queries - start_queries} queries"
            )
    
    def test_timeline_performance(self, patient_id=None):
        """Test timeline performance with real data."""
        if patient_id:
            try:
                patient = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Patient {patient_id} not found"))
                return
        else:
            # Find patient with most events
            patient = Patient.objects.annotate(
                event_count=Count('events')
            ).order_by('-event_count').first()
            
            if not patient:
                self.stdout.write(self.style.ERROR("No patients found"))
                return
        
        self.stdout.write(f"Testing timeline performance for patient: {patient}")
        
        # Simulate timeline view query
        start_time = time.time()
        start_queries = len(connection.queries)
        
        events = Event.objects.filter(
            patient=patient
        ).select_related(
            'created_by',
            'updated_by'
        ).order_by('-created_at')[:15]
        
        # Force evaluation and permission checks
        for event in events:
            _ = event.get_excerpt()
            _ = event.can_be_edited
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        self.stdout.write(
            f"Timeline loaded in {end_time - start_time:.3f}s with "
            f"{end_queries - start_queries} database queries"
        )
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        self.stdout.write("Generating timeline performance report...")
        
        # Database statistics
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT patient_id) as patients_with_events,
                    AVG(LENGTH(COALESCE(description, ''))) as avg_content_length
                FROM events_event
            """)
            stats = cursor.fetchone()
        
        self.stdout.write("=== Timeline Performance Report ===")
        self.stdout.write(f"Total events: {stats[0]:,}")
        self.stdout.write(f"Patients with events: {stats[1]:,}")
        avg_length = stats[2] if stats[2] is not None else 0
        self.stdout.write(f"Average content length: {avg_length:.0f} characters")
        
        # Index usage analysis (PostgreSQL specific)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE tablename = 'events_event'
                    ORDER BY idx_scan DESC
                """)
                indexes = cursor.fetchall()
            
            if indexes:
                self.stdout.write("\n=== Index Usage ===")
                for index in indexes:
                    self.stdout.write(f"{index[2]}: {index[3]} scans, {index[4]} tuples read")
        except Exception as e:
            self.stdout.write(f"\nIndex analysis not available (non-PostgreSQL): {e}")
        
        # Recommendations
        self.stdout.write("\n=== Recommendations ===")
        if stats[0] > 10000:
            self.stdout.write("• Consider implementing pagination cache for large datasets")
        if avg_length > 1000:
            self.stdout.write("• Consider truncating content in list views")
        
        self.stdout.write("• Enable query caching for filter options")
        self.stdout.write("• Use database connection pooling in production")
        self.stdout.write("• Consider CDN for static assets")