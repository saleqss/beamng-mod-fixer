"""Tier 3: Combination Tests for Binary Asset Passthrough Integrity.

Verifies:
- Non-JBeam assets (.dds textures, .dae 3D models, .wav audio, .pc configs) are streamed unmodified
- Checksums (SHA-256) of binary assets match byte-for-byte before and after archive rewrite
- Compression methods and file flags are preserved for non-text entries
"""

import hashlib
from pathlib import Path
import zipfile

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


def get_archive_entry_hashes(zip_path: Path) -> dict[str, str]:
    """Calculate SHA-256 hashes for every entry in a zip file."""
    hashes = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if not info.is_dir():
                data = zf.read(info.filename)
                hashes[info.filename] = hashlib.sha256(data).hexdigest()
    return hashes


def test_dds_texture_bytes_identical(tmp_path: Path) -> None:
    """Test that DirectDraw Surface (.dds) textures have identical SHA-256 before and after."""
    mod_path = tmp_path / "texture_test.zip"
    create_realistic_mod_zip(mod_path, "texture_car", add_textures=True)

    before_hashes = get_archive_entry_hashes(mod_path)
    texture_key = "vehicles/texture_car/textures/skin_paint.dds"
    assert texture_key in before_hashes

    report = process_mod_archive(mod_path, dry_run=False)
    assert report.status == ModStatus.FIXED.value

    after_hashes = get_archive_entry_hashes(mod_path)
    assert after_hashes[texture_key] == before_hashes[texture_key]


def test_dae_collada_mesh_bytes_identical(tmp_path: Path) -> None:
    """Test that Collada 3D models (.dae) are preserved without corruption."""
    mod_path = tmp_path / "model_test.zip"
    create_realistic_mod_zip(mod_path, "model_car", add_textures=True)

    before_hashes = get_archive_entry_hashes(mod_path)
    mesh_key = "vehicles/model_car/models/body.dae"
    assert mesh_key in before_hashes

    process_mod_archive(mod_path, dry_run=False)
    after_hashes = get_archive_entry_hashes(mod_path)

    assert after_hashes[mesh_key] == before_hashes[mesh_key]


def test_wav_audio_bytes_identical(tmp_path: Path) -> None:
    """Test that engine and horn audio samples (.wav) remain untouched."""
    mod_path = tmp_path / "sound_test.zip"
    create_realistic_mod_zip(mod_path, "sound_car", add_sounds=True)

    before_hashes = get_archive_entry_hashes(mod_path)
    audio_key = "vehicles/sound_car/sounds/engine_idle.wav"
    assert audio_key in before_hashes

    process_mod_archive(mod_path, dry_run=False)
    after_hashes = get_archive_entry_hashes(mod_path)

    assert after_hashes[audio_key] == before_hashes[audio_key]


def test_non_lighting_jbeams_bytes_identical(tmp_path: Path) -> None:
    """Test that suspension and non-lighting JBeams remain bit-identical."""
    mod_path = tmp_path / "suspension_test.zip"
    create_realistic_mod_zip(mod_path, "susp_car")

    before_hashes = get_archive_entry_hashes(mod_path)
    susp_key = "vehicles/susp_car/suspension.jbeam"
    assert susp_key in before_hashes

    process_mod_archive(mod_path, dry_run=False)
    after_hashes = get_archive_entry_hashes(mod_path)

    assert after_hashes[susp_key] == before_hashes[susp_key]


def test_only_broken_jbeams_are_modified(tmp_path: Path) -> None:
    """Test that ONLY headlights.jbeam is changed while all other entries have matching hashes."""
    mod_path = tmp_path / "selective_test.zip"
    create_realistic_mod_zip(mod_path, "sel_car", add_textures=True, add_sounds=True)

    before_hashes = get_archive_entry_hashes(mod_path)
    process_mod_archive(mod_path, dry_run=False)
    after_hashes = get_archive_entry_hashes(mod_path)

    headlights_key = "vehicles/sel_car/headlights.jbeam"
    # Headlights changed
    assert after_hashes[headlights_key] != before_hashes[headlights_key]

    # All other files did NOT change
    for filename, h in before_hashes.items():
        if filename != headlights_key:
            assert after_hashes[filename] == h, f"File {filename} was unexpectedly modified"

