import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def safe_timed_rotating_file_handler(
    *,
    filename,
    when="h",
    interval=1,
    backupCount=0,
    encoding=None,
    delay=False,
    utc=False,
    atTime=None,
    errors=None,
    level="INFO",
):
    """
    Return a rotating file handler and gracefully degrade when the log file is not writable.
    """
    try:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        return TimedRotatingFileHandler(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
            errors=errors,
        )
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Falling back to NullHandler for matrix audit log %s: %s",
            filename,
            exc,
        )
        fallback_handler = logging.StreamHandler()
        fallback_handler.setLevel(level)
        return fallback_handler
