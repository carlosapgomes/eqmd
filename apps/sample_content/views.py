from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import SampleContent
from apps.events.models import Event


class SampleContentListView(LoginRequiredMixin, ListView):
    """
    List view for sample content. All authenticated users can view.
    """
    model = SampleContent
    template_name = 'sample_content/sample_content_list.html'
    context_object_name = 'sample_contents'
    paginate_by = 20

    def get_queryset(self):
        queryset = SampleContent.objects.select_related('created_by', 'updated_by')
        
        # Filter by event type if provided
        event_type = self.request.GET.get('event_type')
        if event_type and event_type.isdigit():
            queryset = queryset.filter(event_type=int(event_type))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event_types'] = Event.EVENT_TYPE_CHOICES
        context['selected_event_type'] = self.request.GET.get('event_type', '')
        return context


@login_required
def sample_content_by_event_type(request, event_type):
    """
    API endpoint to get sample content by event type.
    Returns JSON response for AJAX requests.
    """
    from django.http import JsonResponse
    
    if not event_type.isdigit():
        return JsonResponse({'error': 'Invalid event type'}, status=400)
    
    sample_contents = SampleContent.objects.filter(
        event_type=int(event_type)
    ).values('id', 'title', 'content')
    
    return JsonResponse({
        'sample_contents': list(sample_contents)
    })