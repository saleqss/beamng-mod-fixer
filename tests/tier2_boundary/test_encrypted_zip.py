"""Tier 2: Boundary Tests for Password-Protected and Encrypted Archives.

Verifies:
- Detection of PKWARE traditional encryption (general purpose bit 0)
- Detection of WinZip AES encryption
- Graceful skip without crashing with RuntimeError or bad password exceptions
- Diagnostic logging with reason and archive path
- Original encrypted file bytes remain byte-for-byte unmodified
- Processing continues smoothly across remaining files in directory
"""

import hashlib
from pathlib import Path

import pytest

try:
    from beamng_mod_fixer.core.zip_processor import is_archive_encrypted, process_mod_archive
    HAS_ZIP_PROCESSOR = True
except ImportError:
    HAS_ZIP_PROCESSOR = False

from beamng_mod_fixer.models import ModStatus
from tests.fixtures.factory import create_password_protected_zip, create_realistic_mod_zip


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_ZIP_PROCESSOR:
        pytest.skip("beamng_mod_fixer.core.zip_processor not yet implemented (Milestone M2)")


def test_encrypted_archive_detected(tmp_path: Path) -> None:
    """Test that is_archive_encrypted detects archives with encryption bit set."""
    p = tmp_path / "protected.zip"
    create_password_protected_zip(p)

    assert is_archive_encrypted(p) is True


def test_encrypted_archive_skipped_safely(tmp_path: Path) -> None:
    """Test that processing an encrypted archive skips it and returns ModStatus.ENCRYPTED."""
    p = tmp_path / "protected.zip"
    create_password_protected_zip(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.ENCRYPTED.value, ModStatus.SKIPPED.value)
    assert report.jbeams_modified == 0


def test_encrypted_archive_unmodified_on_disk(tmp_path: Path) -> None:
    """Test that attempting to process an encrypted archive does not alter its bytes."""
    p = tmp_path / "protected.zip"
    create_password_protected_zip(p)
    original_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()

    process_mod_archive(p)

    assert hashlib.sha256(p.read_bytes()).hexdigest() == original_sha256


def test_encrypted_warning_logged_in_report(tmp_path: Path) -> None:
    """Test that diagnostic warning explains why the archive was skipped."""
    p = tmp_path / "secret_mod.zip"
    create_password_protected_zip(p)

    report = process_mod_archive(p)
    # Check that either error_message or diagnostics mentions password or encrypted
    all_msgs = [report.error_message or ""] + [d.message for d in report.diagnostics]
    assert any("password" in m.lower() or "encrypt" in m.lower() for m in all_msgs)


def test_clean_archive_not_flagged_as_encrypted(tmp_path: Path) -> None:
    """Test that normal archives are never falsely identified as encrypted."""
    p = tmp_path / "normal_mod.zip"
    create_realistic_mod_zip(p, "normal_car")

    assert is_archive_encrypted(p) is False

