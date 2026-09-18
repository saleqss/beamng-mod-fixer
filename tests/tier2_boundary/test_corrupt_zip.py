"""Tier 2: Boundary Tests for Corrupted ZIP Archive Handling.

Verifies:
- 0-byte archive handling without crashes
- Truncated ZIP files (interrupted download or disk write)
- Bad CRC-32 checksums within archive entries
- Corrupted or damaged End of Central Directory (EOCD) records
- Non-ZIP files with .zip extension (plain text, image files)
- Valid empty ZIP archives with 0 entries
"""

from pathlib import Path
import zipfile

import pytest

try:
    from beamng_mod_fixer.core.zip_processor import process_mod_archive
    HAS_ZIP_PROCESSOR = True
except ImportError:
    HAS_ZIP_PROCESSOR = False

from beamng_mod_fixer.exceptions import CorruptArchiveError
from beamng_mod_fixer.models import ModStatus
from tests.fixtures.factory import (
    create_corrupt_zip_bad_central_dir,
    create_corrupt_zip_bad_crc,
    create_corrupt_zip_non_zip,
    create_corrupt_zip_truncated,
    create_corrupt_zip_zero_byte,
    create_empty_zip,
)


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_ZIP_PROCESSOR:
        pytest.skip("beamng_mod_fixer.core.zip_processor not yet implemented (Milestone M2)")


def test_corrupt_zero_byte_archive(tmp_path: Path) -> None:
    """Test that an empty 0-byte file with .zip extension is skipped without crashing."""
    p = tmp_path / "zero_byte.zip"
    create_corrupt_zip_zero_byte(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CORRUPT.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)
    assert report.error_message is not None


def test_corrupt_truncated_header_archive(tmp_path: Path) -> None:
    """Test that a ZIP file cut off abruptly is caught and skipped safely."""
    p = tmp_path / "truncated.zip"
    create_corrupt_zip_truncated(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CORRUPT.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)
    assert report.jbeams_modified == 0


def test_corrupt_bad_crc_archive(tmp_path: Path) -> None:
    """Test that an entry with mismatched CRC32 checksum is caught safely."""
    p = tmp_path / "bad_crc.zip"
    create_corrupt_zip_bad_crc(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CORRUPT.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)


def test_corrupt_damaged_central_directory(tmp_path: Path) -> None:
    """Test that a ZIP with damaged central directory record is handled cleanly."""
    p = tmp_path / "bad_cd.zip"
    create_corrupt_zip_bad_central_dir(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CORRUPT.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)


def test_corrupt_non_zip_file(tmp_path: Path) -> None:
    """Test that plain text or binary files masquerading as .zip are detected and skipped."""
    p = tmp_path / "fake.zip"
    create_corrupt_zip_non_zip(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CORRUPT.value, ModStatus.SKIPPED.value, ModStatus.ERROR.value)


def test_corrupt_empty_archive_valid_structure(tmp_path: Path) -> None:
    """Test that a valid 22-byte ZIP archive with 0 entries succeeds cleanly without error."""
    p = tmp_path / "empty_valid.zip"
    create_empty_zip(p)

    report = process_mod_archive(p)
    assert report.status in (ModStatus.CLEAN.value, ModStatus.SKIPPED.value)
    assert report.jbeams_inspected == 0
    assert report.jbeams_modified == 0

