from collections import defaultdict
import math
from django.db import connection
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import Q
from apps.dailynotes.models import DailyNote

def get_patient_initials(full_name):
    """
    Extract first letter of each word (including prepositions).
    Example: "João da Silva Santos" → "J.D.S.S."
    """
    if not full_name:
        return ""

    words = full_name.strip().split()

    # Get first letter of ALL words (including prepositions per user request)
    initials = []
    for word in words:
        if word:  # Only if word is not empty
            initials.append(word[0].upper())

    return '.'.join(initials) + '.' if initials else ""

def calculate_age_at_date(birthday, reference_date):
    """
    Calculate age at a specific reference date.
    """
    if not birthday or not reference_date:
        return None

    # Ensure reference_date is a date object
    if hasattr(reference_date, 'date'):
        reference_date = reference_date.date()

    age = reference_date.year - birthday.year

    # Adjust if birthday hasn't occurred yet in the reference year
    if (reference_date.month, reference_date.day) < (birthday.month, birthday.day):
        age -= 1

    return age

def calculate_age_at_most_recent_match(patient, matching_notes):
    """
    Calculate age at the most recent matching dailynote date.

    Args:
        patient: Patient object
        matching_notes: List of matching note dictionaries

    Returns:
        int: Age at most recent match, or None if no notes
    """
    if not matching_notes:
        return None

    # Get the most recent note from the matching results
    most_recent_note = max(matching_notes, key=lambda n: n['note_date'])
    most_recent_date = most_recent_note['note_date']

    # Ensure we have a date object
    if hasattr(most_recent_date, 'date'):
        most_recent_date = most_recent_date.date()

    return calculate_age_at_date(patient.birthday, most_recent_date)

def validate_search_query(query_text):
    """
    Validate and sanitize search query.

    Returns:
        tuple: (cleaned_query, error_message)
    """
    if not query_text or not query_text.strip():
        return None, "Query cannot be empty"

    # Remove excessive whitespace
    query_text = ' '.join(query_text.split())

    # Minimum length check
    if len(query_text) < 3:
        return None, "Query must be at least 3 characters"

    # Maximum length check
    if len(query_text) > 200:
        return None, "Query too long (maximum 200 characters)"

    return query_text, None

def perform_fulltext_search(query_text, page=1, per_page=25):
    """
    Perform full text search and return patient-grouped results.

    Args:
        query_text: The search query
        page: Page number for pagination
        per_page: Results per page

    Returns:
        dict: Search results with pagination info
    """
    # Validate query
    clean_query, error = validate_search_query(query_text)
    if error:
        return {'error': error}

    # Create PostgreSQL search query
    search_query = SearchQuery(clean_query, config='portuguese')

    # Query matching notes with ranking and headlines
    matching_notes = DailyNote.objects.annotate(
        rank=SearchRank('search_vector', search_query),
        headline=SearchHeadline(
            'content',
            search_query,
            config='portuguese',
            max_words=30,
            min_words=10,
            start_sel='<b>',
            stop_sel='</b>'
        )
    ).filter(
        search_vector=search_query
    ).select_related('patient').order_by('-rank')

    if not matching_notes.exists():
        return {
            'patients': [],
            'total_patients': 0,
            'query': query_text,
            'message': f'Nenhum resultado encontrado para "{query_text}"'
        }

    # Group notes by patient
    patient_groups = defaultdict(list)
    for note in matching_notes:
        patient_groups[note.patient].append({
            'note': note,
            'rank': note.rank,
            'headline': note.headline,
            'note_date': note.event_datetime
        })

    # Build patient results (UPDATED)
    patient_results = []
    for patient, notes in patient_groups.items():
        # Skip age calculation for performance

        # Get top 1 match per patient
        top_matches = sorted(notes, key=lambda x: x['rank'], reverse=True)[:1]

        patient_results.append({
            'patient': patient,
            'registration_number': patient.current_record_number or 'N/A',
            'initials': get_patient_initials(patient.name),  # UPDATED function
            'gender': patient.get_gender_display(),
            'birthday': patient.birthday,
            'matching_notes': top_matches,
            'highest_rank': max(n['rank'] for n in notes),
            'total_matches': len(notes)
        })

    # Sort by highest rank
    patient_results.sort(key=lambda x: x['highest_rank'], reverse=True)

    # Implement pagination
    total_patients = len(patient_results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_results = patient_results[start_idx:end_idx]

    return {
        'patients': paginated_results,
        'total_patients': total_patients,
        'current_page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_patients / per_page),
        'has_next': end_idx < total_patients,
        'has_previous': page > 1,
        'query': query_text
    }

def perform_fulltext_search_queryset(query_text, max_patients=100):
    """
    Fast full-text search using raw SQL: groups by patient, limits early.
    
    Args:
        query_text: The search query
        max_patients: Maximum number of patients to return
        
    Returns:
        list: Patient results suitable for Django Paginator
    """
    from django.db import connection
    import json
    
    # Validate query
    clean_query, error = validate_search_query(query_text)
    if error:
        raise ValueError(error)

    with connection.cursor() as cursor:
        cursor.execute("""
            WITH search_query AS (
                SELECT plainto_tsquery('portuguese', %s) AS q
            ),
            ranked_notes AS (
                SELECT
                    dn.event_ptr_id,
                    e.patient_id,
                    e.event_datetime,
                    dn.content,
                    p.name AS patient_name,
                    p.current_record_number,
                    p.gender,
                    p.birthday,
                    ts_rank(dn.search_vector, sq.q) AS rank,
                    ts_headline(
                        'portuguese',
                        dn.content,
                        sq.q,
                        'MaxFragments=1, MinWords=10, MaxWords=30, StartSel=<b>, StopSel=</b>'
                    ) AS headline
                FROM dailynotes_dailynote dn
                CROSS JOIN search_query sq
                JOIN events_event e ON e.id = dn.event_ptr_id
                JOIN patients_patient p ON p.id = e.patient_id
                WHERE dn.search_vector @@ sq.q
            ),
            patient_stats AS (
                SELECT
                    patient_id,
                    MAX(rank) AS highest_rank,
                    COUNT(*) AS total_matches,
                    MAX(event_datetime) AS most_recent_match
                FROM ranked_notes
                GROUP BY patient_id
            ),
            top_patients AS (
                SELECT patient_id
                FROM patient_stats
                ORDER BY highest_rank DESC, total_matches DESC
                LIMIT %s
            ),
            final_results AS (
                SELECT
                    rn.*,
                    ps.highest_rank,
                    ps.total_matches,
                    ps.most_recent_match
                FROM ranked_notes rn
                JOIN top_patients tp ON rn.patient_id = tp.patient_id
                JOIN patient_stats ps ON ps.patient_id = tp.patient_id
            )
            SELECT
                patient_id,
                current_record_number AS registration_number,
                get_patient_initials(patient_name) AS initials,
                patient_name,
                CASE 
                    WHEN gender = 'M' THEN 'Masculino'
                    WHEN gender = 'F' THEN 'Feminino'
                    ELSE 'Não informado'
                END AS gender_display,
                gender,
                birthday,
                total_matches,
                highest_rank,
                most_recent_match,
                (array_agg(
                    jsonb_build_object(
                        'note_date', event_datetime,
                        'headline', headline,
                        'rank', rank
                    ) ORDER BY rank DESC
                ))[1:1] AS matching_notes
            FROM final_results
            GROUP BY
                patient_id, current_record_number, patient_name,
                gender, birthday, total_matches, highest_rank, most_recent_match
            ORDER BY highest_rank DESC, total_matches DESC;
        """, [clean_query, max_patients])

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Post-process: format results (no age calculation, use dictionaries)
    patient_results = []
    for r in results:
        # Snippets already limited to 1 in SQL
        matching_notes = r['matching_notes']

        patient_results.append({
            'patient': {
                'pk': r['patient_id'],
                'name': r['patient_name']
            },
            'registration_number': r['registration_number'] or 'N/A',
            'initials': r['initials'],
            'gender': r['gender_display'],
            'birthday': r['birthday'],
            'matching_notes': matching_notes,
            'highest_rank': r['highest_rank'],
            'total_matches': r['total_matches']
        })

    return patient_results