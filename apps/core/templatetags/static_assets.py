"""Content-versioned URLs for assets shared by changing filter markup."""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

register = template.Library()


@lru_cache(maxsize=128)
def _content_version(path: str, modified_ns: int, size: int) -> str:
    """Stat values invalidate cached hashes when the built file changes."""
    return sha256(Path(path).read_bytes()).hexdigest()[:16]


@register.simple_tag
def versioned_static(asset: str) -> str:
    """Preserve the configured storage URL while invalidating old asset bytes."""
    url = static(asset)
    try:
        location = finders.find(asset) or staticfiles_storage.path(asset)
        file = Path(location)
        metadata = file.stat()
        version = _content_version(str(file), metadata.st_mtime_ns, metadata.st_size)
    except (OSError, NotImplementedError):
        # Remote/manifest storage retains its own URL/versioning behavior.
        return url
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("v", version))
    return urlunsplit(parts._replace(query=urlencode(query)))
