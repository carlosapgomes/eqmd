"""Text normalization helpers used by accent-insensitive searches."""

import unicodedata


def normalize_text_for_search(value):
    """Normalize text for case- and accent-insensitive comparisons."""
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_accents.casefold()
