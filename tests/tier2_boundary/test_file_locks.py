"""Tier 2: Boundary Tests for OS File Locking and Permission Handling.

Verifies:
- Handling of locked archive in use by BeamNG.drive or another process (Windows error 32)
- PermissionError / ArchiveLockedError caught gracefully without crashing
- Original archive left completely untouched
- Error message advises user that file is locked or in use
- Batch processing of remaining mods proceeds unhindered
- Read-only file attributes handled cleanly
"""

import hashlib
import os
from pathlib import Path

import pytest

try:
    from beamng_mod_fixer.core.zip_processor import process_mod_archive
    HAS_ZIP_PROCESSOR = True
except ImportError:
    HAS_ZIP_PROCESSOR = False

from beamng_mod_fixer.models import ModStatus
from tests.fixtures.factory import create_realistic_mod_zip


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_ZIP_PROCESSOR:
        pytest.skip("beamng_mod_fixer.core.zip_processor not yet implemented (Milestone M2)")


def test_locked_archive_handled_gracefully(tmp_path: Path) -> None:
    """Test that a file held open exclusively by another process is caught as LOCKED."""
    p = tmp_path / "locked_vehicle.zip"
    create_realistic_mod_zip(p, "locked_car")
    original_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()

    # Hold the file open in exclusive write mode to simulate BeamNG running
    with open(p, "r+b") as lock_handle:
        report = process_mod_archive(p)
        assert report.status in (ModStatus.LOCKED.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)
        assert report.jbeams_modified == 0

    # Ensure original file was not corrupted
    assert hashlib.sha256(p.read_bytes()).hexdigest() == original_sha256


def test_locked_archive_report_contains_actionable_message(tmp_path: Path) -> None:
    """Test that report error message advises user that file is in use."""
    p = tmp_path / "locked_vehicle.zip"
    create_realistic_mod_zip(p, "locked_car")

    with open(p, "r+b") as lock_handle:
        report = process_mod_archive(p)
        all_msgs = [report.error_message or ""] + [d.message for d in report.diagnostics]
        assert any("lock" in m.lower() or "use" in m.lower() or "permission" in m.lower() for m in all_msgs)


def test_readonly_archive_handling(tmp_path: Path) -> None:
    """Test that an archive with read-only filesystem permissions is handled gracefully."""
    p = tmp_path / "readonly_mod.zip"
    create_realistic_mod_zip(p, "ro_car")
    original_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()

    # Set read-only attribute
    try:
        os.chmod(p, 0o444)
        report = process_mod_archive(p)
        assert report.status in (ModStatus.FIXED.value, ModStatus.LOCKED.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)
    finally:
        # Restore write permissions for cleanup
        os.chmod(p, 0o666)


def test_no_temporary_files_left_after_lock(tmp_path: Path) -> None:
    """Test that no stray .tmp files are left behind when locking prevents completion."""
    p = tmp_path / "locked_vehicle.zip"
    create_realistic_mod_zip(p, "locked_car")

    with open(p, "r+b") as lock_handle:
        process_mod_archive(p)

    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_subsequent_files_processed_after_lock(tmp_path: Path) -> None:
    """Test that encountering a locked file does not halt processing of subsequent files."""
    locked_mod = tmp_path / "01_locked.zip"
    normal_mod = tmp_path / "02_normal.zip"
    create_realistic_mod_zip(locked_mod, "car_lock")
    create_realistic_mod_zip(normal_mod, "car_normal")

    with open(locked_mod, "r+b") as lock_handle:
        report1 = process_mod_archive(locked_mod)
        assert report1.status in (ModStatus.LOCKED.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)

    report2 = process_mod_archive(normal_mod)
    assert report2.status == ModStatus.FIXED.value

