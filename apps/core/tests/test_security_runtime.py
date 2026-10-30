"""Runtime dependency floors and declaration/lock/installation parity (S2/S3a).

The security slice ``eqmd-sec-002`` raises three dependency floors and requires
the running interpreter to match ``uv.lock`` exactly, instead of checking only a
Django minor. Slice ``eqmd-sec-003a`` promotes Pillow to a fourth floor
(``>=13.0.0,<14``) and pins pypdf at its accepted ``5.8.0``. These tests fail on
the pre-hardening runtime (old declarations and old installed versions) and pass
only in a lock-backed environment rebuilt from the updated lock.
"""

from __future__ import annotations

import importlib.metadata
import re
import tomllib
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
LOCK_PATH = PROJECT_ROOT / "uv.lock"

TARGET_FLOORS: dict[str, str] = {
    "django": "5.2.17",
    "djangorestframework": "3.18.2",
    "certifi": "2026.10.18",
    "pillow": "13.0.0",
}

TARGET_UPPER_EXCLUSIVE: dict[str, str] = {
    "django": "5.3",
    "djangorestframework": "3.19",
    "pillow": "14",
}

EXPECTED_DECLARATIONS: dict[str, str] = {
    "django": ">=5.2.17,<5.3",
    "djangorestframework": ">=3.18.2,<3.19",
    "certifi": ">=2026.10.18",
    "pillow": ">=13.0.0,<14",
}

# Pillow moved from "preserved at 12.x" (S2) to a floor target in S3a, so only
# pypdf remains an untouched distribution with an exact accepted version.
PRESERVED_DISTRIBUTIONS: tuple[str, ...] = ("pypdf",)

# R1 of eqmd-sec-003a: pypdf must not be upgraded alongside the Pillow bump.
PRESERVED_PINS: dict[str, str] = {"pypdf": "5.8.0"}

_REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<specifier>.*)$"
)
_VERSION_RE = re.compile(r"^\s*v?(?P<release>\d+(?:\.\d+)*)")


def canonicalize(name: str) -> str:
    """Return the PEP 503 canonical form of a distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_version(version: str) -> tuple[int, ...]:
    """Parse the numeric release segment of *version*."""
    match = _VERSION_RE.match(version)
    if match is None:
        raise ValueError(f"cannot parse version: {version!r}")
    return tuple(int(part) for part in match.group("release").split("."))


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0 or 1 when *left* is lower, equal or higher than *right*."""
    width = max(len(parse_version(left)), len(parse_version(right)))
    left_release = parse_version(left) + (0,) * (width - len(parse_version(left)))
    right_release = parse_version(right) + (0,) * (width - len(parse_version(right)))
    return (left_release > right_release) - (left_release < right_release)


def declared_requirements() -> dict[str, str]:
    """Map canonical names to specifiers declared in ``pyproject.toml``."""
    with PYPROJECT_PATH.open("rb") as handle:
        pyproject = tomllib.load(handle)
    requirements: dict[str, str] = {}
    for entry in pyproject["project"]["dependencies"]:
        match = _REQUIREMENT_RE.match(entry)
        if match is None:
            raise ValueError(f"cannot parse requirement: {entry!r}")
        requirements[canonicalize(match.group("name"))] = match.group(
            "specifier"
        ).strip()
    return requirements


def locked_packages() -> dict[str, dict[str, Any]]:
    """Map canonical names to their ``uv.lock`` package entries."""
    with LOCK_PATH.open("rb") as handle:
        lock = tomllib.load(handle)
    packages: dict[str, dict[str, Any]] = {}
    for package in lock["package"]:
        version = package.get("version")
        if version is None:
            continue
        packages[canonicalize(package["name"])] = package
    return packages


def locked_versions() -> dict[str, str]:
    """Map canonical names to the versions resolved in ``uv.lock``."""
    return {name: package["version"] for name, package in locked_packages().items()}


class DependencyContractTests(unittest.TestCase):
    """Executable contract for the dependency floors of S2 and S3a."""

    def test_targets_are_direct_dependencies(self) -> None:
        declared = declared_requirements()
        for target in TARGET_FLOORS:
            with self.subTest(target=target):
                self.assertIn(
                    target,
                    declared,
                    f"{target} must be an explicit dependency, not transitive",
                )

    def test_declared_requirements_match_approved_floors(self) -> None:
        declared = declared_requirements()
        for target, expected in EXPECTED_DECLARATIONS.items():
            with self.subTest(target=target):
                self.assertEqual(
                    declared.get(target),
                    expected,
                    f"{target} declaration must be {expected!r}",
                )

    def test_lock_versions_satisfy_approved_floors(self) -> None:
        locked = locked_versions()
        for target, floor in TARGET_FLOORS.items():
            with self.subTest(target=target):
                version = locked.get(target)
                if version is None:
                    self.fail(f"{target} must be resolved in uv.lock")
                self.assertGreaterEqual(
                    compare_versions(version, floor),
                    0,
                    f"uv.lock resolves {target} {version}, below floor {floor}",
                )
                upper = TARGET_UPPER_EXCLUSIVE.get(target)
                if upper is not None:
                    self.assertLess(
                        compare_versions(version, upper),
                        0,
                        f"uv.lock resolves {target} {version}, above {upper}",
                    )

    def test_installed_versions_satisfy_approved_floors(self) -> None:
        for target, floor in TARGET_FLOORS.items():
            with self.subTest(target=target):
                version = importlib.metadata.version(target)
                self.assertGreaterEqual(
                    compare_versions(version, floor),
                    0,
                    f"installed {target} {version} is below floor {floor}",
                )
                upper = TARGET_UPPER_EXCLUSIVE.get(target)
                if upper is not None:
                    self.assertLess(
                        compare_versions(version, upper),
                        0,
                        f"installed {target} {version} is above {upper}",
                    )

    def test_installed_versions_match_lock_exactly(self) -> None:
        locked = locked_versions()
        for target in TARGET_FLOORS:
            with self.subTest(target=target):
                self.assertEqual(
                    importlib.metadata.version(target),
                    locked.get(target),
                    f"installed {target} must match uv.lock exactly",
                )

    def test_preserved_distributions_match_lock_exactly(self) -> None:
        locked = locked_versions()
        for name in PRESERVED_DISTRIBUTIONS:
            with self.subTest(distribution=name):
                self.assertEqual(
                    importlib.metadata.version(name),
                    locked.get(name),
                    f"installed {name} must match uv.lock exactly",
                )

    def test_preserved_pins_hold_in_lock_and_installation(self) -> None:
        locked = locked_versions()
        for name, expected in PRESERVED_PINS.items():
            with self.subTest(distribution=name):
                self.assertEqual(
                    locked.get(name),
                    expected,
                    f"uv.lock must keep {name} at {expected} (no sibling upgrade)",
                )
                self.assertEqual(
                    importlib.metadata.version(name),
                    expected,
                    f"installed {name} must stay at {expected}",
                )

    def test_lock_entries_have_resolved_artifacts(self) -> None:
        packages = locked_packages()
        for target in TARGET_FLOORS:
            with self.subTest(target=target):
                entry = packages.get(target, {})
                self.assertTrue(
                    entry.get("sdist") or entry.get("wheels"),
                    f"{target} lock entry must carry sdist or wheel artifacts",
                )
