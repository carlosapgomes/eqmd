"""
Custom OIDC claims for EQMD.

This module will be expanded in later phases to include
physician and delegation information in tokens.
"""

from oidc_provider.lib.claims import ScopeClaims


class EqmdScopeClaims(ScopeClaims):
    """Custom scope claims for EQMD delegation tokens."""
    
    # Will be implemented in Phase 06
    pass
