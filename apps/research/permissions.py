from django.core.exceptions import PermissionDenied

def check_researcher_access(user):
    """
    Check if user has researcher access via is_researcher field.

    Args:
        user: The user to check

    Returns:
        bool: True if user has researcher access

    Raises:
        PermissionDenied: If user doesn't have access
    """
    if not user.is_authenticated:
        raise PermissionDenied("Você deve estar logado para acessar a pesquisa clínica.")

    # Check the is_researcher field
    if not getattr(user, 'is_researcher', False):
        raise PermissionDenied(
            "Você não tem permissão para acessar as funcionalidades de pesquisa clínica. "
            "Entre em contato com o administrador do sistema."
        )

    return True

def is_researcher(user):
    """
    Check if user is a researcher (non-raising version).

    Args:
        user: The user to check

    Returns:
        bool: True if user has researcher access, False otherwise
    """
    if not user.is_authenticated:
        return False

    return getattr(user, 'is_researcher', False)