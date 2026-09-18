"""Tier 3: Combination Tests for Batch Directory Scanner & Summary Reporting.

Verifies:
- Batch scanning across directories containing mixed file types
- Accurate aggregation of OverallSummary metrics (scanned, modified, clean, skipped, errors)
- Non-zip files completely ignored during scan
- Dry-run mode produces accurate metrics while leaving 100% of files unmodified
- Idempotency across consecutive runs (second run modifies 0 archives)
"""

import hashlib
from pathlib import Path

import pytest

try:
    from beamng_mod_fixer.core.zip_processor import scan_and_fix_mods
    HAS_BATCH_SCANNER = True
except ImportError:
    HAS_BATCH_SCANNER = False

from beamng_mod_fixer.models import OverallSummary
from tests.fixtures.factory import (
    create_corrupt_zip_truncated,
    create_corrupt_zip_zero_byte,
    create_password_protected_zip,
    create_realistic_mod_zip,
)


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_BATCH_SCANNER:
        pytest.skip("beamng_mod_fixer.core.zip_processor scan_and_fix_mods not yet implemented (Milestone M2)")


def test_batch_mixed_directory_metrics(tmp_path: Path) -> None:
    """Test batch scan across 3 broken, 2 clean, 1 corrupt, 1 encrypted, and 1 non-zip."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    # 3 broken
    create_realistic_mod_zip(mods_dir / "mod_broken_1.zip", "car1")
    create_realistic_mod_zip(mods_dir / "mod_broken_2.zip", "car2", light_count=4)
    create_realistic_mod_zip(mods_dir / "mod_broken_3.zip", "car3")

    # 2 clean
    create_realistic_mod_zip(mods_dir / "mod_clean_1.zip", "clean1", already_false=True)
    create_realistic_mod_zip(mods_dir / "mod_clean_2.zip", "clean2", already_false=True)

    # 1 corrupt
    create_corrupt_zip_truncated(mods_dir / "mod_corrupt.zip")

    # 1 encrypted
    create_password_protected_zip(mods_dir / "mod_encrypted.zip")

    # 1 non-zip
    (mods_dir / "readme.txt").write_text("ignore me", encoding="utf-8")

    summary = scan_and_fix_mods(mods_dir, dry_run=False)

    assert isinstance(summary, OverallSummary)
    assert summary.total_scanned == 7  # 7 zip files (non-zip ignored)
    assert summary.modified_archives == 3
    assert summary.clean_archives == 2
    assert summary.skipped_corrupt >= 1
    assert summary.skipped_encrypted >= 1
    assert summary.jbeams_fixed >= 3


def test_batch_dry_run_leaves_disk_unmodified(tmp_path: Path) -> None:
    """Test that dry-run returns accurate predictions with zero disk modifications."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    p1 = mods_dir / "mod_1.zip"
    p2 = mods_dir / "mod_2.zip"
    create_realistic_mod_zip(p1, "car1")
    create_realistic_mod_zip(p2, "car2", already_false=True)

    hash1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    hash2 = hashlib.sha256(p2.read_bytes()).hexdigest()

    summary = scan_and_fix_mods(mods_dir, dry_run=True)
    assert summary.modified_archives == 1
    assert summary.clean_archives == 1

    # Hashes strictly unchanged
    assert hashlib.sha256(p1.read_bytes()).hexdigest() == hash1
    assert hashlib.sha256(p2.read_bytes()).hexdigest() == hash2


def test_batch_consecutive_runs_idempotent(tmp_path: Path) -> None:
    """Test that running the fixer twice modifies 0 archives on the second pass."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    create_realistic_mod_zip(mods_dir / "mod_1.zip", "car1")
    create_realistic_mod_zip(mods_dir / "mod_2.zip", "car2")

    # First pass: fixes both
    summary1 = scan_and_fix_mods(mods_dir, dry_run=False)
    assert summary1.modified_archives == 2

    # Second pass: zero modifications
    summary2 = scan_and_fix_mods(mods_dir, dry_run=False)
    assert summary2.modified_archives == 0
    assert summary2.clean_archives == 2
    assert summary2.total_scanned == 2


def test_batch_empty_directory_succeeds(tmp_path: Path) -> None:
    """Test scanning an empty mods directory produces zeroed summary without error."""
    empty_dir = tmp_path / "empty_mods"
    empty_dir.mkdir(parents=True, exist_ok=True)

    summary = scan_and_fix_mods(empty_dir, dry_run=False)
    assert summary.total_scanned == 0
    assert summary.modified_archives == 0
    assert summary.errors_encountered == 0

