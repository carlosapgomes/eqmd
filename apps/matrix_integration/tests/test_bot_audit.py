import json
import logging.config
import os
import tempfile

from django.test import TestCase

from apps.matrix_integration.bot.audit import log_event


class BotAuditLogTests(TestCase):
    def test_audit_log_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "matrix_bot_audit.log")
            logging.config.dictConfig(
                {
                    "version": 1,
                    "disable_existing_loggers": False,
                    "handlers": {
                        "matrix_bot_audit": {
                            "class": "logging.FileHandler",
                            "filename": log_path,
                            "level": "INFO",
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

            log_event(
                direction="inbound",
                user_id=1,
                matrix_user="@joao:matrix.test",
                room_id="!room:matrix.test",
                action="patient_search",
                message="/buscar Joao",
                results_count=2,
            )

            with open(log_path, "r", encoding="utf-8") as handle:
                line = handle.readline()

            data = json.loads(line)
            self.assertEqual(data["action"], "patient_search")
            self.assertEqual(data["direction"], "inbound")
            self.assertEqual(data["results_count"], 2)
