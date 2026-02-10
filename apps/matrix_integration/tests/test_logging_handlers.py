import logging
import logging.config
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from config.logging_handlers import safe_timed_rotating_file_handler


class SafeTimedRotatingFileHandlerTests(SimpleTestCase):
    def test_returns_rotating_file_handler_when_writable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "matrix_bot_audit.log"
            handler = safe_timed_rotating_file_handler(filename=str(log_path))

        self.assertEqual(handler.__class__.__name__, "TimedRotatingFileHandler")
        handler.close()

    def test_returns_stream_handler_when_file_open_fails(self):
        with mock.patch(
            "config.logging_handlers.TimedRotatingFileHandler",
            side_effect=PermissionError("denied"),
        ):
            handler = safe_timed_rotating_file_handler(
                filename="/tmp/eqmd_test_matrix_audit.log"
            )

        self.assertIsInstance(handler, logging.StreamHandler)

    def test_dictconfig_uses_fallback_handler_without_raising(self):
        with mock.patch(
            "config.logging_handlers.TimedRotatingFileHandler",
            side_effect=PermissionError("denied"),
        ):
            logging.config.dictConfig(
                {
                    "version": 1,
                    "disable_existing_loggers": False,
                    "handlers": {
                        "matrix_bot_audit": {
                            "level": "INFO",
                            "()": "config.logging_handlers.safe_timed_rotating_file_handler",
                            "filename": "/root/forbidden.log",
                            "when": "D",
                            "interval": 1,
                            "backupCount": 60,
                            "encoding": "utf-8",
                        }
                    },
                    "loggers": {
                        "matrix.bot.audit": {
                            "handlers": ["matrix_bot_audit"],
                            "level": "INFO",
                            "propagate": False,
                        }
                    },
                }
            )

        logger = logging.getLogger("matrix.bot.audit")
        self.assertFalse(logger.propagate)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
