"""Tier 1: Feature Tests for Safe Cache & Compiled Shader Cleaner.

Verifies:
- Purging of compiled DirectX/Vulkan shader binaries (.d3dcsx, .db) in temp/shaders/
- Purging of temporary vehicle AST and animation caches (.cani) in temp/vehicles/
- Safety guardrails: refusing to delete anything outside of temp/
- Absolute protection of mods/, settings/, screenshots/, and user data
- Dry-run mode calculating deletion statistics without touching disk
- Clean handling of already-empty cache directories
"""

from pathlib import Path

import pytest

try:
    from beamng_mod_fixer.core.cache_cleaner import clean_shader_cache
    HAS_CACHE_CLEANER = True
except ImportError:
    HAS_CACHE_CLEANER = False

from beamng_mod_fixer.exceptions import CacheCleanError
from beamng_mod_fixer.models import CacheCleanResult
from tests.fixtures.factory import create_synthetic_cache_structure


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_CACHE_CLEANER:
        pytest.skip("beamng_mod_fixer.core.cache_cleaner not yet implemented (Milestone M3)")


def test_clean_compiled_shaders(tmp_path: Path) -> None:
    """Test that .d3dcsx and .db shader files in temp/shaders are safely removed."""
    temp_dir = tmp_path / "temp"
    cache_info = create_synthetic_cache_structure(temp_dir)
    assert len(cache_info["shaders"]) > 0

    result = clean_shader_cache(tmp_path, dry_run=False)
    assert result.success is True
    assert result.files_deleted >= len(cache_info["shaders"])
    assert result.bytes_freed > 0

    # Ensure shader files no longer exist
    for p in cache_info["shaders"]:
        assert not p.exists()


def test_clean_vehicle_cache(tmp_path: Path) -> None:
    """Test that .cani cache files in temp/vehicles are removed."""
    temp_dir = tmp_path / "temp"
    cache_info = create_synthetic_cache_structure(temp_dir)
    assert len(cache_info["vehicles"]) > 0

    result = clean_shader_cache(tmp_path, dry_run=False)
    assert result.success is True

    for p in cache_info["vehicles"]:
        assert not p.exists()


def test_guardrail_refuses_outside_temp(tmp_path: Path) -> None:
    """Test that passing a directory without 'temp' raises CacheCleanError to prevent data loss."""
    unsafe_dir = tmp_path / "important_documents"
    unsafe_dir.mkdir(parents=True, exist_ok=True)
    (unsafe_dir / "my_file.txt").write_text("critical data", encoding="utf-8")

    with pytest.raises(CacheCleanError):
        clean_shader_cache(unsafe_dir, dry_run=False)

    assert (unsafe_dir / "my_file.txt").exists()


def test_guardrail_protects_mods_and_settings(tmp_path: Path) -> None:
    """Test that mods and settings folders adjacent to temp are strictly untouched."""
    mods_dir = tmp_path / "mods"
    settings_dir = tmp_path / "settings"
    temp_dir = tmp_path / "temp"

    mods_dir.mkdir(parents=True, exist_ok=True)
    settings_dir.mkdir(parents=True, exist_ok=True)
    create_synthetic_cache_structure(temp_dir)

    mod_file = mods_dir / "mod_vehicle.zip"
    mod_file.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    settings_file = settings_dir / "settings.json"
    settings_file.write_text("{}", encoding="utf-8")

    clean_shader_cache(tmp_path, dry_run=False)

    assert mod_file.exists()
    assert settings_file.exists()


def test_dry_run_leaves_files_untouched(tmp_path: Path) -> None:
    """Test that dry_run=True returns accurate deletion count but deletes nothing."""
    temp_dir = tmp_path / "temp"
    cache_info = create_synthetic_cache_structure(temp_dir)

    result = clean_shader_cache(tmp_path, dry_run=True)
    assert result.files_deleted > 0
    assert result.bytes_freed > 0

    # All files must still exist
    for p in cache_info["all"]:
        assert p.exists()


def test_clean_empty_cache_directory(tmp_path: Path) -> None:
    """Test that running on an already empty temp directory succeeds with 0 deleted files."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    result = clean_shader_cache(tmp_path, dry_run=False)
    assert result.success is True
    assert result.files_deleted == 0

