from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Hospital, Ward
from .forms import HospitalForm, WardForm
from .middleware import HospitalContextMiddleware


class HospitalListView(ListView):
    model = Hospital
    template_name = 'hospitals/hospital_list.html'
    context_object_name = 'hospitals'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Hospital.objects.all()
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(short_name__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(state__icontains=search_query)
            )
        
        # Filter by state
        state_filter = self.request.GET.get('state')
        if state_filter:
            queryset = queryset.filter(state__iexact=state_filter)
            
        # Filter by city
        city_filter = self.request.GET.get('city')
        if city_filter:
            queryset = queryset.filter(city__icontains=city_filter)
            
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search and filter values to context
        context['search_query'] = self.request.GET.get('q', '')
        context['state_filter'] = self.request.GET.get('state', '')
        context['city_filter'] = self.request.GET.get('city', '')
        
        # Get available states and cities for filter dropdowns
        context['available_states'] = Hospital.objects.exclude(
            state__isnull=True
        ).exclude(
            state__exact=''
        ).values_list('state', flat=True).distinct().order_by('state')
        
        context['available_cities'] = Hospital.objects.exclude(
            city__isnull=True
        ).exclude(
            city__exact=''
        ).values_list('city', flat=True).distinct().order_by('city')
        
        return context


class HospitalDetailView(DetailView):
    model = Hospital
    template_name = 'hospitals/hospital_detail.html'
    context_object_name = 'hospital'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Future: Add related wards when Ward model is available
        # context['related_wards'] = self.object.ward_set.all()
        context['related_wards'] = []  # Placeholder
        
        # Future: Add related users when HospitalUser model is available  
        # context['related_users'] = self.object.hospitaluser_set.all()
        context['related_users'] = []  # Placeholder
        
        # Future: Add statistics when related models are available
        context['statistics'] = {
            'total_wards': 0,  # len(context['related_wards'])
            'active_users': 0,  # context['related_users'].filter(is_active=True).count()
            'current_patients': 0,  # Future patient count
            'occupancy_rate': 0,  # Future occupancy calculation
        }
        
        return context


class HospitalCreateView(LoginRequiredMixin, CreateView):
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'Hospital "{form.instance.name}" foi criado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Criar Novo Hospital'
        context['submit_text'] = 'Criar Hospital'
        return context


class HospitalUpdateView(LoginRequiredMixin, UpdateView):
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/hospital_form.html'
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'Hospital "{form.instance.name}" foi atualizado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Editar Hospital: {self.object.name}'
        context['submit_text'] = 'Salvar Alterações'
        return context


class HospitalDeleteView(LoginRequiredMixin, DeleteView):
    model = Hospital
    template_name = 'hospitals/hospital_confirm_delete.html'
    success_url = reverse_lazy('apps.hospitals:list')
    
    def delete(self, request, *args, **kwargs):
        hospital = self.get_object()
        hospital_name = hospital.name
        messages.success(request, f'Hospital "{hospital_name}" foi excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


class WardListView(LoginRequiredMixin, ListView):
    model = Ward
    context_object_name = 'wards'
    template_name = 'hospitals/ward_list.html'

    def get_queryset(self):
        return Ward.objects.select_related('hospital').all()


class WardDetailView(LoginRequiredMixin, DetailView):
    model = Ward
    template_name = 'hospitals/ward_detail.html'

    def get_queryset(self):
        return Ward.objects.select_related('hospital')


class WardCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Ward
    form_class = WardForm
    template_name = 'hospitals/ward_form.html'
    permission_required = 'hospitals.add_ward'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('hospitals:ward_detail', kwargs={'pk': self.object.pk})


class WardUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Ward
    form_class = WardForm
    template_name = 'hospitals/ward_form.html'
    permission_required = 'hospitals.change_ward'

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('hospitals:ward_detail', kwargs={'pk': self.object.pk})


class WardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Ward
    template_name = 'hospitals/ward_confirm_delete.html'
    permission_required = 'hospitals.delete_ward'
    success_url = reverse_lazy('hospitals:ward_list')


@login_required
def hospital_selection_view(request):
    """View for selecting current hospital context."""
    if request.method == 'POST':
        hospital_id = request.POST.get('hospital_id')
        if hospital_id:
            hospital = HospitalContextMiddleware.set_hospital_context(request, hospital_id)
            if hospital:
                messages.success(request, f'Hospital "{hospital.name}" selecionado como contexto atual.')
                # Redirect to next page or dashboard
                next_url = request.GET.get('next', '/dashboard/')
                return redirect(next_url)
            else:
                messages.error(request, 'Hospital não encontrado.')
        else:
            # Clear hospital context
            HospitalContextMiddleware.clear_hospital_context(request)
            messages.info(request, 'Contexto de hospital removido.')
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
    
    # Get available hospitals for the user
    hospitals = HospitalContextMiddleware.get_available_hospitals(request.user)
    current_hospital = getattr(request.user, 'current_hospital', None)
    
    context = {
        'hospitals': hospitals,
        'current_hospital': current_hospital,
        'next_url': request.GET.get('next', '/dashboard/'),
    }
    
    return render(request, 'hospitals/hospital_selection.html', context)


@login_required
@require_http_methods(["POST"])
def hospital_context_switch_ajax(request):
    """AJAX endpoint for switching hospital context."""
    hospital_id = request.POST.get('hospital_id')
    
    if hospital_id:
        try:
            hospital = HospitalContextMiddleware.set_hospital_context(request, hospital_id)
            if hospital:
                return JsonResponse({
                    'success': True,
                    'message': f'Hospital "{hospital.name}" selecionado.',
                    'hospital': {
                        'id': str(hospital.id),
                        'name': hospital.name,
                        'short_name': hospital.short_name or '',
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Hospital não encontrado ou você não tem acesso.'
                })
        except (ValueError, Hospital.DoesNotExist):
            return JsonResponse({
                'success': False,
                'message': 'Hospital não encontrado ou você não tem acesso.'
            })
    else:
        # Clear hospital context
        HospitalContextMiddleware.clear_hospital_context(request)
        return JsonResponse({
            'success': True,
            'message': 'Contexto de hospital removido.',
            'hospital': None
        })


def test_ward_tags(request):
    wards = Ward.objects.select_related('hospital').all()
    return render(request, 'hospitals/tests/test_tags.html', {'wards': wards})
