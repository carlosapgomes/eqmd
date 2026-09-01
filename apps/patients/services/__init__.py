"""Service layer for the patients app."""

from .temporary_record import (
    generate_temporary_record_number,
    is_temporary_record_number,
)

__all__ = [
    "generate_temporary_record_number",
    "is_temporary_record_number",
]
