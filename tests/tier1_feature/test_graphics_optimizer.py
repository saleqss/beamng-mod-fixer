"""Tier 1: Feature Tests for Graphics Optimizer & Settings Deployer.

Verifies:
- Creation of settings.json.bak backup before modifying user settings
- Application of balanced reflection preset (facesPerUpdate: 2, textureSize: 512)
- Preservation of user preferences (volume, resolution, keybindings)
- Synchronization of low-level Torque3D engine preferences in game-settings.json ($pref)
- Error handling when settings directory or file does not exist
- Error handling when settings.json contains corrupt JSON
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

try:
    from beamng_mod_fixer.core.graphics_optimizer import (
        OPTIMIZATION_PRESETS,
        backup_settings_file,
        optimize_settings,
    )
    HAS_GRAPHICS_OPTIMIZER = True
except ImportError:
    HAS_GRAPHICS_OPTIMIZER = False

from beamng_mod_fixer.exceptions import SettingsCorruptedError, SettingsNotFoundError
from beamng_mod_fixer.models import OptimizationResult
from tests.fixtures.factory import create_synthetic_settings_files


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_GRAPHICS_OPTIMIZER:
        pytest.skip("beamng_mod_fixer.core.graphics_optimizer not yet implemented (Milestone M3)")


def test_backup_created_before_modification(tmp_path: Path) -> None:
    """Test that a backup .bak file is created before altering settings."""
    settings_dir = tmp_path / "settings"
    s_file, _ = create_synthetic_settings_files(settings_dir)
    original_bytes = s_file.read_bytes()

    result = optimize_settings(settings_dir, preset="balanced", backup=True)
    assert result.backup_created is True
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.backup_path.read_bytes() == original_bytes


def test_reflection_preset_applied(tmp_path: Path) -> None:
    """Test that balanced preset sets GraphicDynReflectionFacesPerupdate to 2 and Texsize to 512."""
    settings_dir = tmp_path / "settings"
    s_file, _ = create_synthetic_settings_files(settings_dir)

    result = optimize_settings(settings_dir, preset="balanced")
    assert result.success is True

    updated_data = json.loads(s_file.read_text(encoding="utf-8"))
    assert updated_data["GraphicDynReflectionFacesPerupdate"] == 2
    assert updated_data["GraphicDynReflectionTexsize"] in (2, 512)
    assert updated_data["GraphicDynReflectionDistance"] == 300


def test_user_preferences_preserved(tmp_path: Path) -> None:
    """Test that user audio volume, resolution, and custom keys are untouched."""
    settings_dir = tmp_path / "settings"
    custom_settings = {
        "AudioMasterVol": 0.42,
        "GraphicResolution": "3840 2160",
        "CustomKeyBinding_Handbrake": "Space",
    }
    s_file, _ = create_synthetic_settings_files(settings_dir, custom_settings=custom_settings)

    optimize_settings(settings_dir, preset="balanced")
    updated_data = json.loads(s_file.read_text(encoding="utf-8"))

    assert updated_data["AudioMasterVol"] == 0.42
    assert updated_data["GraphicResolution"] == "3840 2160"
    assert updated_data["CustomKeyBinding_Handbrake"] == "Space"


def test_game_settings_engine_prefs_updated(tmp_path: Path) -> None:
    """Test that low-level engine prefs in game-settings.json are synchronized."""
    settings_dir = tmp_path / "settings"
    _, gs_file = create_synthetic_settings_files(settings_dir)

    optimize_settings(settings_dir, preset="balanced")
    updated_gs = json.loads(gs_file.read_text(encoding="utf-8"))

    vehicle_prefs = updated_gs["$pref"]["BeamNGVehicle"]["dynamicReflection"]
    assert vehicle_prefs["facesPerUpdate"] == 2
    assert vehicle_prefs["textureSize"] == 512


def test_no_backup_flag_respected(tmp_path: Path) -> None:
    """Test that backup=False does not create backup files."""
    settings_dir = tmp_path / "settings"
    create_synthetic_settings_files(settings_dir)

    result = optimize_settings(settings_dir, preset="balanced", backup=False)
    assert result.backup_created is False
    bak_files = list(settings_dir.glob("*.bak*"))
    assert len(bak_files) == 0


def test_missing_settings_file_raises_error(tmp_path: Path) -> None:
    """Test that targeting an empty directory raises SettingsNotFoundError."""
    empty_dir = tmp_path / "nonexistent_settings"
    empty_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SettingsNotFoundError):
        optimize_settings(empty_dir, preset="balanced")


def test_corrupted_json_raises_settings_error(tmp_path: Path) -> None:
    """Test that invalid JSON syntax in settings.json raises SettingsCorruptedError."""
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    bad_json = settings_dir / "settings.json"
    bad_json.write_text("{ unclosed json: [1, 2, ", encoding="utf-8")

    with pytest.raises((SettingsCorruptedError, json.JSONDecodeError)):
        optimize_settings(settings_dir, preset="balanced")

