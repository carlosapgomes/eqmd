"""
API endpoints for medical procedures search.
Provides dynamic search functionality for form fields.
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.core.models import MedicalProcedure

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
def procedures_search(request):
    """
    Search medical procedures for dynamic form field population.
    
    GET /api/procedures/search/?q=query&limit=10
    
    Query Parameters:
        q (str): Search query (required, min 2 characters)
        limit (int): Maximum results to return (default: 20, max: 100)
        active_only (bool): Only return active procedures (default: true)
    
    Returns:
        JSON response with procedures list or error message
    """
    
    try:
        # Get and validate query parameter
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
        
        # Get and validate limit parameter
        try:
            limit = int(request.GET.get('limit', 20))
            if limit <= 0:
                limit = 20
            elif limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 20
        
        # Get active_only parameter
        active_only = request.GET.get('active_only', 'true').lower() in ['true', '1', 'yes']
        
        # Perform search
        if active_only:
            base_qs = MedicalProcedure.active()
        else:
            base_qs = MedicalProcedure.objects.all()
        
        # Try PostgreSQL full-text search first, fallback to simple search
        try:
            if active_only:
                procedures = MedicalProcedure.search(query)[:limit]
            else:
                # For inactive search, use queryset filtering
                from django.contrib.postgres.search import SearchQuery, SearchRank
                search_query = SearchQuery(query)
                procedures = (
                    base_qs
                    .filter(search_vector=search_query)
                    .annotate(rank=SearchRank('search_vector', search_query))
                    .order_by('-rank', 'code')[:limit]
                )
            search_method = 'fulltext'
        except Exception as e:
            logger.warning(f"Full-text search failed, using simple search: {str(e)}")
            if active_only:
                procedures = MedicalProcedure.simple_search(query)[:limit]
            else:
                from django.db.models import Q
                procedures = (
                    base_qs
                    .filter(
                        Q(code__icontains=query) |
                        Q(description__icontains=query)
                    )
                    .order_by('code')[:limit]
                )
            search_method = 'simple'
        
        # Format results
        results = []
        for procedure in procedures:
            results.append({
                'id': str(procedure.id),
                'code': procedure.code,
                'description': procedure.description,
                'short_description': procedure.short_description,
                'display_text': procedure.get_display_text(),
                'is_active': procedure.is_active
            })
        
        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results),
            'search_method': search_method,
            'has_more': len(results) == limit  # Indicate if there might be more results
        })
    
    except ValidationError as e:
        logger.warning(f"Validation error in procedures search: {str(e)}")
        return JsonResponse({
            'error': f'Validation error: {str(e)}',
            'results': []
        }, status=400)
    
    except Exception as e:
        logger.error(f"Unexpected error in procedures search: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while searching procedures',
            'results': []
        }, status=500)


@require_http_methods(["GET"])
@login_required
def procedure_detail(request, procedure_id):
    """
    Get details for a specific procedure.
    
    GET /api/procedures/<uuid:procedure_id>/
    
    Returns:
        JSON response with procedure details
    """
    
    try:
        procedure = MedicalProcedure.objects.get(id=procedure_id)
        
        return JsonResponse({
            'id': str(procedure.id),
            'code': procedure.code,
            'description': procedure.description,
            'short_description': procedure.short_description,
            'display_text': procedure.get_display_text(),
            'is_active': procedure.is_active,
            'created_at': procedure.created_at.isoformat(),
            'updated_at': procedure.updated_at.isoformat()
        })
    
    except MedicalProcedure.DoesNotExist:
        return JsonResponse({
            'error': 'Procedure not found'
        }, status=404)
    
    except Exception as e:
        logger.error(f"Error retrieving procedure {procedure_id}: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while retrieving the procedure'
        }, status=500)


@require_http_methods(["GET"])
@login_required
def procedures_list(request):
    """
    List procedures with pagination and filtering.
    
    GET /api/procedures/?page=1&limit=50&active=true&search=query
    
    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 50, max: 100)
        active (bool): Filter by active status (default: all)
        search (str): Filter by search term (optional)
    
    Returns:
        JSON response with paginated procedures list
    """
    
    try:
        # Get pagination parameters
        try:
            page = max(1, int(request.GET.get('page', 1)))
            limit = min(100, max(1, int(request.GET.get('limit', 50))))
        except (ValueError, TypeError):
            page = 1
            limit = 50
        
        # Get filter parameters
        active_filter = request.GET.get('active')
        search_term = request.GET.get('search', '').strip()
        
        # Build queryset
        queryset = MedicalProcedure.objects.all()
        
        if active_filter is not None:
            is_active = active_filter.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active)
        
        if search_term:
            # Use simple search for listing
            queryset = queryset.filter(
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        # Get total count
        total_count = queryset.count()
        
        # Apply pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        procedures = queryset.order_by('code')[start_index:end_index]
        
        # Format results
        results = []
        for procedure in procedures:
            results.append({
                'id': str(procedure.id),
                'code': procedure.code,
                'description': procedure.description,
                'short_description': procedure.short_description,
                'display_text': procedure.get_display_text(),
                'is_active': procedure.is_active
            })
        
        # Calculate pagination info
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
        logger.error(f"Error listing procedures: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred while listing procedures',
            'results': []
        }, status=500)