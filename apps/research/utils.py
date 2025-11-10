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
        # Calculate age at most recent MATCHING note (UPDATED)
        age_at_recent_match = calculate_age_at_most_recent_match(patient, notes)

        # Get top 5 matches per patient
        top_matches = sorted(notes, key=lambda x: x['rank'], reverse=True)[:5]

        patient_results.append({
            'patient': patient,
            'registration_number': patient.current_record_number or 'N/A',
            'initials': get_patient_initials(patient.name),  # UPDATED function
            'gender': patient.get_gender_display(),
            'birthday': patient.birthday,
            'age_at_most_recent_match': age_at_recent_match,  # UPDATED field name
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

def perform_fulltext_search_queryset(query_text):
    """
    Perform full text search and return patient results as a list for Django pagination.
    
    Args:
        query_text: The search query
        
    Returns:
        list: Patient results suitable for Django Paginator
    """
    # Validate query
    clean_query, error = validate_search_query(query_text)
    if error:
        raise ValueError(error)

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
        return []

    # Group notes by patient
    patient_groups = defaultdict(list)
    for note in matching_notes:
        patient_groups[note.patient].append({
            'note': note,
            'rank': note.rank,
            'headline': note.headline,
            'note_date': note.event_datetime
        })

    # Build patient results
    patient_results = []
    for patient, notes in patient_groups.items():
        # Calculate age at most recent MATCHING note
        age_at_recent_match = calculate_age_at_most_recent_match(patient, notes)

        # Get top 5 matches per patient
        top_matches = sorted(notes, key=lambda x: x['rank'], reverse=True)[:5]

        patient_results.append({
            'patient': patient,
            'registration_number': patient.current_record_number or 'N/A',
            'initials': get_patient_initials(patient.name),
            'gender': patient.get_gender_display(),
            'birthday': patient.birthday,
            'age_at_most_recent_match': age_at_recent_match,
            'matching_notes': top_matches,
            'highest_rank': max(n['rank'] for n in notes),
            'total_matches': len(notes)
        })

    # Sort by highest rank
    patient_results.sort(key=lambda x: x['highest_rank'], reverse=True)
    
    return patient_results