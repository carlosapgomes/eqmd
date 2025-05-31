from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def landing_page(request):
    """
    Renders the landing page for EquipeMed.
    """
    context = {
        'page_title': 'Bem-vindo ao EquipeMed',
    }
    return render(request, 'core/landing_page.html', context)

@login_required
def dashboard_view(request):
    """
    Renders the main dashboard page for authenticated users.
    """
    context = {
        'page_title': 'Painel Principal',
    }
    return render(request, 'core/dashboard.html', context)
