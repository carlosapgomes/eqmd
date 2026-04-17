"""
Contract harness and characterization tests for easymd_v1 dialect.

These tests validate the fixture corpus and contract metadata
without exercising production rendering code.
"""

from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.markdown_pipeline.profile import (
    get_supported_constructs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / (
    "tests/fixtures/markdown/easymd_v1"
)

# Supported constructs are now centralized in the profile descriptor.
# This alias keeps the test code readable while eliminating duplication.
SUPPORTED_CONSTRUCTS: list[str] = list(get_supported_constructs())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _discover_fixture_cases() -> dict[str, dict]:
    """Load every .md fixture and its companion .meta.json metadata."""
    cases: dict[str, dict] = {}
    if not FIXTURES_DIR.exists():
        return cases

    for md_file in sorted(FIXTURES_DIR.glob("*.md")):
        stem = md_file.stem
        meta_file = md_file.with_suffix(".meta.json")
        markdown_text = md_file.read_text(encoding="utf-8")

        if meta_file.exists():
            import json

            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        else:
            meta = {}

        cases[stem] = {
            "name": stem,
            "markdown": markdown_text,
            "meta": meta,
        }
    return cases


# ---------------------------------------------------------------------------
# Tests (TDD – written first, RED phase)
# ---------------------------------------------------------------------------


class TestFixtureSetCoversSupportedConstructs(SimpleTestCase):
    """Ensure the fixture corpus covers every declared construct family."""

    def test_fixture_set_covers_supported_constructs(self) -> None:
        """Every SUPPORTED_CONSTRUCTS entry must be covered by at least one
        fixture's metadata ``constructs`` list."""
        cases = _discover_fixture_cases()
        self.assertGreater(len(cases), 0, "No fixture cases found")

        covered: set[str] = set()
        for case in cases.values():
            constructs = case["meta"].get("constructs", [])
            covered.update(constructs)

        missing = set(SUPPORTED_CONSTRUCTS) - covered
        self.assertSetEqual(
            missing,
            set(),
            f"The following constructs are not covered by any fixture: "
            f"{sorted(missing)}",
        )

    def test_no_extra_constructs_in_metadata(self) -> None:
        """Fixture metadata should not declare constructs outside the
        supported set (typos / drift detection)."""
        cases = _discover_fixture_cases()
        allowed = set(SUPPORTED_CONSTRUCTS)

        for case_name, case in cases.items():
            constructs = set(case["meta"].get("constructs", []))
            extra = constructs - allowed
            self.assertSetEqual(
                extra,
                set(),
                f"Fixture '{case_name}' declares unknown constructs: "
                f"{sorted(extra)}",
            )


class TestContractHarnessLoadsAllFixtureCases(SimpleTestCase):
    """Validate that the harness can load every fixture without errors."""

    def test_contract_harness_loads_all_fixture_cases(self) -> None:
        cases = _discover_fixture_cases()
        self.assertGreater(len(cases), 0, "Expected at least one fixture case")

        for case_name, case in cases.items():
            with self.subTest(fixture=case_name):
                self.assertIn("name", case)
                self.assertIn("markdown", case)
                self.assertIn("meta", case)
                self.assertIsInstance(case["markdown"], str)
                self.assertGreater(
                    len(case["markdown"].strip()),
                    0,
                    f"Fixture '{case_name}' is empty",
                )

    def test_fixtures_directory_exists(self) -> None:
        self.assertTrue(
            FIXTURES_DIR.is_dir(),
            f"Fixtures directory not found: {FIXTURES_DIR}",
        )


class TestContractCasesDefineExpectedSemanticTokens(SimpleTestCase):
    """Each fixture must declare expected_semantic_tokens in its metadata so
    that future parser/renderer tests can assert deterministic output."""

    def test_contract_cases_define_expected_semantic_tokens(self) -> None:
        cases = _discover_fixture_cases()
        self.assertGreater(len(cases), 0, "No fixture cases found")

        for case_name, case in cases.items():
            with self.subTest(fixture=case_name):
                meta = case["meta"]
                self.assertIn(
                    "expected_semantic_tokens",
                    meta,
                    f"Fixture '{case_name}' missing 'expected_semantic_tokens' "
                    f"in metadata",
                )
                tokens = meta["expected_semantic_tokens"]
                self.assertIsInstance(
                    tokens,
                    list,
                    f"Fixture '{case_name}': expected_semantic_tokens must be "
                    f"a list",
                )
                self.assertGreater(
                    len(tokens),
                    0,
                    f"Fixture '{case_name}': expected_semantic_tokens is empty",
                )
