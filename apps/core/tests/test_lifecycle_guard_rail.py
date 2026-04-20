"""
Guard rail: detect bare create_user() calls in test files.

Ensures that every ``User.objects.create_user(...)`` (or equivalent) in test
modules sets both ``password_change_required=False`` and ``terms_accepted=True``,
*unless* the file is in an explicit allowlist of lifecycle/middleware test
modules.

This prevents new tests from silently introducing false-negative 302s caused
by PasswordChangeRequiredMiddleware / TermsAcceptanceRequiredMiddleware.

Run:
    ./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
"""

import ast
import os
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Allowlist: modules that *intentionally* test lifecycle / middleware behaviour
# ---------------------------------------------------------------------------
# Paths are relative to the project root (the directory that holds apps/).
ALLOWLIST: list[str] = [
    # middleware tests
    "apps/core/tests/test_password_change_middleware.py",
    # password-change lifecycle tests
    "apps/accounts/tests/test_password_change_required.py",
    # the helpers module itself (it sets the flags, doesn't need them)
    "apps/accounts/tests/helpers.py",
    # factories — defines NavigationReadyUserFactory
    "apps/accounts/tests/factories.py",
    # signals test may verify default behaviour
    "apps/accounts/tests/test_signals.py",
    # accounts history tests may exercise lifecycle state transitions
    "apps/accounts/tests/test_history.py",
]

# Project root (the directory that holds apps/)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _is_create_user_call(node: ast.Call) -> bool:
    """Return True if *node* is a ``<something>.create_user(...)`` call."""
    # Match ``*.create_user(...)`` — handles User.objects.create_user,
    # EqmdCustomUser.objects.create_user, etc.
    if isinstance(node.func, ast.Attribute) and node.func.attr == "create_user":
        return True
    # Also match bare ``create_user(...)`` (unlikely but possible via import)
    if isinstance(node.func, ast.Name) and node.func.id == "create_user":
        return True
    return False


def _keyword_value(kw: ast.keyword):
    """Return a Python value for simple literal/constant keyword args, or a sentinel."""
    if isinstance(kw.value, ast.Constant):
        return kw.value.value
    return object()  # sentinel — not a simple literal


def _extract_create_user_violations(source: str, filepath: str) -> list[str]:
    """Parse *source* and return a list of violation messages for bare create_user calls."""
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        # Skip files that can't be parsed (e.g. template-embedded scripts)
        return []

    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_create_user_call(node):
            continue

        # Collect keyword arguments
        kw_dict = {kw.arg: _keyword_value(kw) for kw in node.keywords if kw.arg}

        has_pcr_false = kw_dict.get("password_change_required") is False
        has_ta_true = kw_dict.get("terms_accepted") is True

        if has_pcr_false and has_ta_true:
            # Properly gated — no violation
            continue

        missing: list[str] = []
        if not has_pcr_false:
            missing.append("password_change_required=False")
        if not has_ta_true:
            missing.append("terms_accepted=True")

        line = getattr(node, "lineno", "?")
        violations.append(
            f"  {filepath}:{line} — create_user() missing {', '.join(missing)}"
        )

    return violations


def scan_test_files() -> list[str]:
    """Scan all test files under apps/ and return a sorted list of violations."""
    violations: list[str] = []
    allowlist_set = set(ALLOWLIST)

    for root, _dirs, files in os.walk(PROJECT_ROOT / "apps"):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, PROJECT_ROOT)

            if relpath in allowlist_set:
                continue

            # Only scan test files
            parts = Path(relpath).parts
            if "tests" not in parts:
                continue

            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            # Quick pre-filter: skip files that don't contain create_user at all
            if "create_user" not in source:
                continue

            violations.extend(_extract_create_user_violations(source, relpath))

    violations.sort()
    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class LifecycleGuardRailHelperTest(unittest.TestCase):
    """Unit tests for AST helper functions."""

    # -- unit tests for AST helpers --

    def test_detects_bare_create_user(self):
        source = textwrap.dedent("""\
            User.objects.create_user(username='alice', password='pw')
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("password_change_required=False", violations[0])
        self.assertIn("terms_accepted=True", violations[0])

    def test_passes_when_both_flags_set(self):
        source = textwrap.dedent("""\
            User.objects.create_user(
                username='alice',
                password='pw',
                password_change_required=False,
                terms_accepted=True,
            )
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 0)

    def test_detects_missing_terms_only(self):
        source = textwrap.dedent("""\
            User.objects.create_user(
                username='bob',
                password='pw',
                password_change_required=False,
            )
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("terms_accepted=True", violations[0])
        self.assertNotIn("password_change_required=False", violations[0])

    def test_detects_missing_pcr_only(self):
        source = textwrap.dedent("""\
            User.objects.create_user(
                username='carol',
                password='pw',
                terms_accepted=True,
            )
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("password_change_required=False", violations[0])
        self.assertNotIn("terms_accepted=True", violations[0])

    def test_detects_wrong_flag_value(self):
        source = textwrap.dedent("""\
            User.objects.create_user(
                username='dave',
                password='pw',
                password_change_required=True,
                terms_accepted=False,
            )
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("password_change_required=False", violations[0])
        self.assertIn("terms_accepted=True", violations[0])

    def test_detects_create_user_with_model_alias(self):
        """EqmdCustomUser.objects.create_user should also be caught."""
        source = textwrap.dedent("""\
            EqmdCustomUser.objects.create_user(username='x', password='y')
        """)
        violations = _extract_create_user_violations(source, "test_fake.py")
        self.assertEqual(len(violations), 1)

    def test_syntax_error_file_skipped(self):
        source = "def ( broken python {{{"
        violations = _extract_create_user_violations(source, "broken.py")
        self.assertEqual(len(violations), 0)

class LifecycleGuardRailScanTest(unittest.TestCase):
    """Integration test: full scan of the codebase.

    This test reports the current violation count but does NOT fail
    (the codebase has pre-existing violations that will be migrated
    incrementally).  It serves as a living audit and ensures the scanner
    itself runs without error.

    To enforce zero violations in CI, change ``max_allowed`` below to 0.
    """

    # Maximum number of violations tolerated.
    # Decrease this as migration slices progress; target is 0.
    max_allowed: int = 9999

    def test_scan_runs_and_reports_violations(self):
        violations = scan_test_files()

        # Print the audit report for visibility in CI logs
        print(f"\n{'=' * 70}")
        print(f"Lifecycle guard rail: {len(violations)} violation(s) detected")
        print(f"Allowlist ({len(ALLOWLIST)} entries):")
        for p in ALLOWLIST:
            print(f"  ✓ {p}")
        if violations:
            # Show up to 30 violations for brevity
            shown = violations[:30]
            print(f"\nViolations (showing {len(shown)}/{len(violations)}):")
            for v in shown:
                print(v)
            if len(violations) > 30:
                print(f"  ... and {len(violations) - 30} more")
            print(
                "\nFix: add password_change_required=False, terms_accepted=True,\n"
                "or use create_navigation_user() / NavigationReadyUserFactory.\n"
                "If the file tests lifecycle behaviour, add it to the ALLOWLIST."
            )
        print(f"{'=' * 70}")

        self.assertLessEqual(
            len(violations),
            self.max_allowed,
            f"Guard rail: {len(violations)} violations exceed max_allowed="
            f"{self.max_allowed}. See report above.",
        )
