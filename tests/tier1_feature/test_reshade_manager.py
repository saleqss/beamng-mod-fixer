"""Tier 1: Feature Tests for ReShade Preset Manager.

Verifies:
- All 4 presets (medium-optimal, low-fast, potato-boost, ultra-photoreal) are defined and structured.
- Deployment of individual presets and all presets.
- Atomic write and correct .ini content.
- Update of ReShade.ini CurrentPresetPath.
- Detection of ReShade installation.
"""

from pathlib import Path
import pytest

from beamng_mod_fixer.core.reshade_manager import (
    RESHADE_PRESETS,
    deploy_all_reshade_presets,
    deploy_reshade_preset,
    detect_reshade_installation,
)


def test_reshade_presets_defined():
    """Verify all 4 core presets are properly configured."""
    required_keys = ["medium-optimal", "low-fast", "potato-boost", "ultra-photoreal"]
    for k in required_keys:
        assert k in RESHADE_PRESETS
        preset = RESHADE_PRESETS[k]
        assert "filename" in preset and preset["filename"].endswith(".ini")
        assert "content" in preset and "Techniques=" in preset["content"]


def test_deploy_reshade_preset_medium_optimal(tmp_path: Path):
    """Test deploying the 'medium-optimal' (most beautiful yet optimal) preset."""
    ok, msg, p = deploy_reshade_preset(tmp_path, "medium-optimal")
    assert ok is True
    assert p is not None
    assert p.exists()
    assert p.name == "BeamNG_Medium_Optimal.ini"

    content = p.read_text(encoding="utf-8")
    assert "CAS.fx" in content
    assert "Tonemap.fx" in content
    assert "Curves.fx" in content
    assert "AmbientLight.fx" in content


def test_deploy_reshade_preset_dry_run(tmp_path: Path):
    """Test dry_run simulates without writing."""
    target = tmp_path / "presets"
    ok, msg, p = deploy_reshade_preset(target, "low-fast", dry_run=True)
    assert ok is True
    assert not target.exists()


def test_deploy_all_reshade_presets(tmp_path: Path):
    """Test deploying all 4 presets at once."""
    files = deploy_all_reshade_presets(tmp_path)
    assert len(files) == 4
    names = {f.name for f in files}
    assert "BeamNG_Medium_Optimal.ini" in names
    assert "BeamNG_Low_Fast.ini" in names
    assert "BeamNG_Potato_Boost.ini" in names
    assert "BeamNG_Ultra_Photoreal.ini" in names


def test_reshade_ini_current_preset_update(tmp_path: Path):
    """Test updating existing ReShade.ini with newly deployed preset."""
    reshade_ini = tmp_path / "ReShade.ini"
    reshade_ini.write_text("CurrentPresetPath=old_preset.ini\nEffectSearchPaths=.\n", encoding="utf-8")

    ok, _, p = deploy_reshade_preset(tmp_path, "medium-optimal")
    assert ok is True

    updated_text = reshade_ini.read_text(encoding="utf-8")
    assert f"CurrentPresetPath={p.resolve()}" in updated_text
    assert "EffectSearchPaths=." in updated_text


def test_detect_reshade_installation(tmp_path: Path):
    """Test detecting ReShade in directory with dxgi.dll."""
    game_dir = tmp_path / "BeamNG"
    bin_dir = game_dir / "Bin64"
    bin_dir.mkdir(parents=True)

    assert detect_reshade_installation([bin_dir]) is None

    (bin_dir / "dxgi.dll").write_text("mock")
    detected = detect_reshade_installation([bin_dir])
    assert detected == bin_dir
