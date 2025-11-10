from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from .forms import ClinicalSearchForm
from .permissions import check_researcher_access
from .utils import perform_fulltext_search_queryset

@login_required
def clinical_search(request):
    """
    Clinical research full text search view with Django pagination.
    """
    # Check researcher permissions
    try:
        check_researcher_access(request.user)
    except PermissionDenied as e:
        messages.error(request, str(e))
        return render(request, 'research/access_denied.html')

    form = ClinicalSearchForm()
    patients = None
    query = None

    if request.method == 'POST' or request.GET.get('q'):
        # Handle both POST (new search) and GET (pagination)
        if request.method == 'POST':
            form = ClinicalSearchForm(request.POST)
        else:
            # For pagination, get query from URL parameter
            query = request.GET.get('q', '')
            form = ClinicalSearchForm({'query': query})
        
        if form.is_valid():
            query = form.cleaned_data['query']

            # Get the queryset of patient results
            try:
                patients = perform_fulltext_search_queryset(query)
                if not patients:
                    messages.info(request, f'Nenhum resultado encontrado para "{query}"')
            except Exception as e:
                messages.error(request, f'Erro na busca: {str(e)}')
                patients = None

    # Apply pagination using Django's Paginator
    page_obj = None
    if patients is not None:
        paginator = Paginator(patients, 10)  # 10 results per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'patients': page_obj.object_list if page_obj else None,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages() if page_obj else False,
        'query': query,
        'page_title': 'Pesquisa Clínica'
    }

    return render(request, 'research/search.html', context)

@login_required
def search_ajax(request):
    """
    AJAX endpoint for search (optional for future enhancement).
    """
    try:
        check_researcher_access(request.user)
    except PermissionDenied:
        return JsonResponse({'error': 'Access denied'}, status=403)

    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))

    if not query:
        return JsonResponse({'error': 'Query required'}, status=400)

    results = perform_fulltext_search(query, page=page)

    # Convert results to JSON-serializable format
    if 'patients' in results:
        for patient_result in results['patients']:
            patient_result['patient'] = {
                'id': str(patient_result['patient'].pk),
                'name': patient_result['patient'].name
            }
            for match in patient_result['matching_notes']:
                match['note_date'] = match['note_date'].isoformat()

    return JsonResponse(results)
