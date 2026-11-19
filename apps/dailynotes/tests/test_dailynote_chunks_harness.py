"""Regression coverage for the DailyNote copy-dialog splitter (design D6)."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase


class DailyNoteChunksHarnessTests(SimpleTestCase):
    """Run the real splitter with table-driven fixtures through ``node``."""

    @skipUnless(shutil.which("node"), "node runtime unavailable; run host harness")
    def test_dailynote_chunks_harness(self) -> None:
        harness = Path(__file__).with_name("dailynote_chunks_harness.cjs")
        result = subprocess.run(
            [str(shutil.which("node")), str(harness)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["failed"], [])
        self.assertGreaterEqual(len(summary["passed"]), 10)
