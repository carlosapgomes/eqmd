from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Setup PostgreSQL functions for full-text search optimization'

    def handle(self, *args, **options):
        self.stdout.write('Setting up PostgreSQL functions...')
        
        with connection.cursor() as cursor:
            # Create get_patient_initials function
            cursor.execute("""
                CREATE OR REPLACE FUNCTION get_patient_initials(full_name TEXT)
                RETURNS TEXT AS $$
                DECLARE
                    words TEXT[];
                    initials TEXT[];
                    word TEXT;
                BEGIN
                    IF full_name IS NULL OR trim(full_name) = '' THEN
                        RETURN '';
                    END IF;
                    
                    words := string_to_array(trim(full_name), ' ');
                    initials := ARRAY[]::TEXT[];
                    
                    FOREACH word IN ARRAY words
                    LOOP
                        IF length(word) > 0 THEN
                            initials := array_append(initials, upper(left(word, 1)));
                        END IF;
                    END LOOP;
                    
                    IF array_length(initials, 1) > 0 THEN
                        RETURN array_to_string(initials, '.') || '.';
                    ELSE
                        RETURN '';
                    END IF;
                END;
                $$ LANGUAGE plpgsql IMMUTABLE;
            """)
            
        self.stdout.write(
            self.style.SUCCESS('Successfully created get_patient_initials() function')
        )