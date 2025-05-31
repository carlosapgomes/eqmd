from django.shortcuts import render

def landing_page(request):
    """
    Renders the landing page for EquipeMed.
    """
    context = {
        'page_title': 'Bem-vindo ao EquipeMed',
    }
    return render(request, 'core/landing_page.html', context)
