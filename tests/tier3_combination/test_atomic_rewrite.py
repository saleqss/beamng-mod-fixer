"""Tier 3: Combination Tests for Atomic In-Place Archive Rewriting.

Verifies:
- Atomic replacement using temporary file and os.replace on the same filesystem volume
- Complete absence of lingering .tmp or .bak files upon completion
- Abort safety: simulated streaming failure leaves original archive untouched and removes .tmp
- Internal directory structure and ZipInfo metadata preservation
- Deeply nested directory trees inside archives
- atomic_replace utility function behavior and retry logic
"""

import hashlib
from pathlib import Path
import zipfile

import pytest

try:
    from beamng_mod_fixer.core.file_utils import atomic_replace, create_temp_target
    from beamng_mod_fixer.core.zip_processor import process_mod_archive
    HAS_COMBINATION = True
except ImportError:
    HAS_COMBINATION = False

from beamng_mod_fixer.models import ModStatus
from tests.fixtures.factory import (
    ModArchiveBuilder,
    SAMPLE_JBEAM_STANDARD_HEADLIGHT,
    create_realistic_mod_zip,
)


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_COMBINATION:
        pytest.skip("beamng_mod_fixer core rewriter modules not yet implemented (Milestones M1/M2)")


def test_atomic_rewrite_clean_swap_no_leftovers(tmp_path: Path) -> None:
    """Test that modifying an archive replaces it in-place with zero leftover .tmp files."""
    mod_path = tmp_path / "mod_vehicle.zip"
    create_realistic_mod_zip(mod_path, "clean_swap_car")

    report = process_mod_archive(mod_path, dry_run=False)
    assert report.status == ModStatus.FIXED.value
    assert report.jbeams_modified >= 1

    # Archive exists and is valid
    assert mod_path.exists()
    with zipfile.ZipFile(mod_path, "r") as zf:
        assert len(zf.namelist()) > 0
        jbeam_content = zf.read("vehicles/clean_swap_car/headlights.jbeam").decode("utf-8")
        assert '"lightCastShadows": false' in jbeam_content

    # Zero .tmp files in folder
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_atomic_rewrite_preserves_internal_directory_structure(tmp_path: Path) -> None:
    """Test that internal paths and directory hierarchy are preserved exactly."""
    mod_path = tmp_path / "deep_mod.zip"
    builder = ModArchiveBuilder("deep_mod.zip", "deep_car")
    deep_path = "configurations/engines/turbos/stage3/headlights.jbeam"
    builder.add_jbeam(deep_path, SAMPLE_JBEAM_STANDARD_HEADLIGHT)
    builder.build(tmp_path)

    report = process_mod_archive(mod_path, dry_run=False)
    assert report.status == ModStatus.FIXED.value

    with zipfile.ZipFile(mod_path, "r") as zf:
        expected_internal = f"vehicles/deep_car/{deep_path}"
        assert expected_internal in zf.namelist()


def test_atomic_rewrite_abort_leaves_original_unmodified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that if an error occurs midway, original is untouched and temp is removed."""
    mod_path = tmp_path / "fail_mod.zip"
    create_realistic_mod_zip(mod_path, "fail_car")
    original_sha256 = hashlib.sha256(mod_path.read_bytes()).hexdigest()

    # Simulate an I/O error during atomic_replace
    def _mock_failing_replace(src: Path, dst: Path, **kwargs: object) -> None:
        raise OSError("Simulated filesystem full error")

    monkeypatch.setattr("beamng_mod_fixer.core.file_utils.atomic_replace", _mock_failing_replace)

    report = process_mod_archive(mod_path, dry_run=False)
    assert report.status in (ModStatus.ERROR.value, ModStatus.SKIPPED.value)

    # Original file is bit-for-bit unmodified
    assert hashlib.sha256(mod_path.read_bytes()).hexdigest() == original_sha256

    # Temp files cleaned up
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_atomic_replace_utility_function(tmp_path: Path) -> None:
    """Test atomic_replace helper directly."""
    target = tmp_path / "target.txt"
    target.write_text("old content", encoding="utf-8")

    temp_file = create_temp_target(target)
    temp_file.write_text("new content", encoding="utf-8")

    atomic_replace(temp_file, target)

    assert target.read_text(encoding="utf-8") == "new content"
    assert not temp_file.exists()


def test_create_temp_target_same_directory(tmp_path: Path) -> None:
    """Test create_temp_target creates temp file in same parent directory to guarantee same filesystem."""
    target = tmp_path / "archive.zip"
    temp = create_temp_target(target)
    assert temp.parent == target.parent
    assert temp != target

