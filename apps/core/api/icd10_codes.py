"""
API endpoints for ICD-10 (CID) codes search.
Provides dynamic search functionality for form fields.
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.core.models import Icd10Code

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
def icd10_search(request):
    """
    Search ICD-10 codes for dynamic form field population.

    GET /api/icd10/search/?q=query&limit=10

    Query Parameters:
        q (str): Search query (required, min 2 characters)
        limit (int): Maximum results to return (default: 20, max: 100)
        active_only (bool): Only return active codes (default: true)
    """

    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'error': 'Query parameter "q" is required',
                'results': []
            }, status=400)

        if len(query) < 2:
            return JsonResponse({
                'error': 'Query must be at least 2 characters',
                'results': []
            }, status=400)

        try:
            limit = int(request.GET.get('limit', 20))
            if limit <= 0:
                limit = 20
            elif limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 20

        active_only = request.GET.get('active_only', 'true').lower() in ['true', '1', 'yes']

        if active_only:
            base_qs = Icd10Code.active()
        else:
            base_qs = Icd10Code.objects.all()

        from django.db import connection
        if connection.vendor == 'postgresql':
            try:
                if active_only:
                    codes = Icd10Code.search(query)[:limit]
                else:
                    from django.contrib.postgres.search import SearchQuery, SearchRank
                    search_query = SearchQuery(query)
                    codes = (
                        base_qs
                        .filter(search_vector=search_query)
                        .annotate(rank=SearchRank('search_vector', search_query))
                        .order_by('-rank', 'code')[:limit]
                    )
                search_method = 'fulltext'
            except Exception as e:
                logger.warning(f"Full-text search failed, using simple search: {str(e)}")
                if active_only:
                    codes = Icd10Code.simple_search(query)[:limit]
                else:
                    codes = (
                        base_qs
                        .filter(
                            Q(code__icontains=query) |
                            Q(description__icontains=query)
                        )
                        .order_by('code')[:limit]
                    )
                search_method = 'simple'
        else:
            if active_only:
                codes = Icd10Code.simple_search(query)[:limit]
            else:
                codes = (
                    base_qs
                    .filter(
                        Q(code__icontains=query) |
                        Q(description__icontains=query)
                    )
                    .order_by('code')[:limit]
                )
            search_method = 'simple'

        results = []
        for code in codes:
            results.append({
                'id': str(code.id),
                'code': code.code,
                'description': code.description,
                'short_description': code.short_description,
                'display_text': code.get_display_text(),
                'is_active': code.is_active
            })

        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results),
            'search_method': search_method,
            'has_more': len(results) == limit
        })

    except ValidationError as e:
        logger.warning(f"Validation error in ICD-10 search: {str(e)}")
        return JsonResponse({
            'error': f'Validation error: {str(e)}',
            'results': []
        }, status=400)

    except Exception as e:
        logger.error(f"Unexpected error in ICD-10 search: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while searching ICD-10 codes',
            'results': []
        }, status=500)


@require_http_methods(["GET"])
@login_required
def icd10_detail(request, code_id):
    """
    Get details for a specific ICD-10 code.

    GET /api/icd10/<uuid:code_id>/
    """

    try:
        code = Icd10Code.objects.get(id=code_id)

        return JsonResponse({
            'id': str(code.id),
            'code': code.code,
            'description': code.description,
            'short_description': code.short_description,
            'display_text': code.get_display_text(),
            'is_active': code.is_active,
            'created_at': code.created_at.isoformat(),
            'updated_at': code.updated_at.isoformat()
        })

    except Icd10Code.DoesNotExist:
        return JsonResponse({
            'error': 'ICD-10 code not found'
        }, status=404)

    except Exception as e:
        logger.error(f"Error retrieving ICD-10 code {code_id}: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while retrieving the ICD-10 code'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def icd10_list(request):
    """
    List ICD-10 codes with pagination and filtering.

    GET /api/icd10/?page=1&limit=50&active=true&search=query
    """

    try:
        try:
            page = max(1, int(request.GET.get('page', 1)))
            limit = min(100, max(1, int(request.GET.get('limit', 50))))
        except (ValueError, TypeError):
            page = 1
            limit = 50

        active_filter = request.GET.get('active')
        search_term = request.GET.get('search', '').strip()

        queryset = Icd10Code.objects.all()

        if active_filter is not None:
            is_active = active_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active)

        if search_term:
            queryset = queryset.filter(
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        total_count = queryset.count()

        start_index = (page - 1) * limit
        end_index = start_index + limit
        codes = queryset.order_by('code')[start_index:end_index]

        results = []
        for code in codes:
            results.append({
                'id': str(code.id),
                'code': code.code,
                'description': code.description,
                'short_description': code.short_description,
                'display_text': code.get_display_text(),
                'is_active': code.is_active
            })

        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_previous = page > 1

        return JsonResponse({
            'results': results,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_previous': has_previous,
                'count': len(results)
            },
            'filters': {
                'active': active_filter,
                'search': search_term
            }
        })

    except Exception as e:
        logger.error(f"Error listing ICD-10 codes: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while listing ICD-10 codes',
            'results': []
        }, status=500)
