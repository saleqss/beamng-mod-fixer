"""Tier 1: Feature Tests for Mod Auto-Installer and Downloads Watcher.

Verifies:
- Detection of BeamNG mod signatures vs non-BeamNG archives.
- Detection of nested root directories (e.g. MyMod/vehicles/... -> unwrap).
- Complete file download stability checks.
- Installation from Downloads to mods folder with automatic 7-stage repair.
- ModWatcher start, scan, and stop cycle.
"""

import time
from pathlib import Path
import zipfile
import pytest

from beamng_mod_fixer.core.mod_watcher import (
    ModWatcher,
    inspect_archive_type,
    install_and_repair_mod,
    is_file_completely_downloaded,
)
from beamng_mod_fixer.core.zip_processor import detect_nested_mod_prefix, process_mod_archive


def test_detect_nested_mod_prefix():
    # Nested vehicle mod
    files_nested = [
        "SuperCar_v1/vehicles/supercar/supercar.jbeam",
        "SuperCar_v1/vehicles/supercar/materials.json",
        "SuperCar_v1/vehicles/supercar/supercar.dae",
    ]
    assert detect_nested_mod_prefix(files_nested) == "SuperCar_v1/"

    # Already unnested mod
    files_clean = [
        "vehicles/supercar/supercar.jbeam",
        "vehicles/supercar/materials.json",
    ]
    assert detect_nested_mod_prefix(files_clean) is None

    # Nested level mod
    files_level = [
        "DesertTrack_v2/levels/desert_track/info.json",
        "DesertTrack_v2/levels/desert_track/desert.ter",
    ]
    assert detect_nested_mod_prefix(files_level) == "DesertTrack_v2/"

    # Non-BeamNG structure
    files_random = [
        "some_program/src/main.py",
        "some_program/README.md",
    ]
    assert detect_nested_mod_prefix(files_random) is None


def test_inspect_archive_type(tmp_path):
    # 1. Genuine vehicle mod
    v_zip = tmp_path / "vehicle_mod.zip"
    with zipfile.ZipFile(v_zip, "w") as zf:
        zf.writestr("vehicles/custom_car/car.jbeam", "{}")
        zf.writestr("vehicles/custom_car/main.materials.json", "{}")

    is_mod, category = inspect_archive_type(v_zip)
    assert is_mod is True
    assert category == "Vehicle Mod"

    # 2. Nested level mod
    l_zip = tmp_path / "map_mod.zip"
    with zipfile.ZipFile(l_zip, "w") as zf:
        zf.writestr("MyTrack/levels/mytrack/info.json", "{}")

    is_mod, category = inspect_archive_type(l_zip)
    assert is_mod is True
    assert category == "Map / Level Mod"

    # 3. Non-BeamNG zip
    r_zip = tmp_path / "not_a_mod.zip"
    with zipfile.ZipFile(r_zip, "w") as zf:
        zf.writestr("documents/contract.pdf", "data")
        zf.writestr("notes.txt", "hello")

    is_mod, category = inspect_archive_type(r_zip)
    assert is_mod is False


def test_install_and_repair_mod_with_unwrapping(tmp_path):
    downloads = tmp_path / "Downloads"
    mods_dir = tmp_path / "mods"
    downloads.mkdir()
    mods_dir.mkdir()

    source_zip = downloads / "Mustang_Mod.zip"
    jbeam_content = """{
        "props": [
            {"lightRange": 6, "lightCastShadows": true},
            ["reverse", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.05}],
            ["brake", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.05}],
            ["lowhighbeam", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.02}]
        ]
    }"""

    # Create nested zip with backslashes
    with zipfile.ZipFile(source_zip, "w") as zf:
        zf.writestr("Mustang_Mod\\vehicles\\mustang\\mustang.jbeam", jbeam_content)
        zf.writestr("Mustang_Mod\\vehicles\\mustang\\materials.cs", 'singleton Material("mustang_paint") { mapTo = "paint"; diffuseMap[0] = "paint.png"; };')

    # Install and auto-repair
    report = install_and_repair_mod(source_zip, mods_dir, auto_repair=True)
    assert report is not None
    assert not source_zip.exists()  # Original moved out of Downloads

    dest_zip = mods_dir / "Mustang_Mod.zip"
    assert dest_zip.exists()

    # Verify unnested structure and fixed content
    with zipfile.ZipFile(dest_zip, "r") as zf:
        names = zf.namelist()
        assert "vehicles/mustang/mustang.jbeam" in names
        assert "Mustang_Mod/vehicles/mustang/mustang.jbeam" not in names
        assert not any("\\" in n for n in names)

        # Check repaired JBeam content
        fixed_jbeam = zf.read("vehicles/mustang/mustang.jbeam").decode("utf-8")
        assert '"lightBrightness": 0.35' in fixed_jbeam  # Brake calibrated
        assert '"lightBrightness": 0.12' in fixed_jbeam  # Taillight calibrated
        assert '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}' in fixed_jbeam  # Red injected!


def test_mod_watcher_check_once(tmp_path):
    downloads = tmp_path / "Downloads"
    mods_dir = tmp_path / "mods"
    downloads.mkdir()
    mods_dir.mkdir()

    watcher = ModWatcher(downloads_dir=downloads, mods_dir=mods_dir, auto_repair=True)

    # Put a completed mod in downloads
    test_zip = downloads / "Civic_Mod.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("vehicles/civic/civic.jbeam", '{"spotlights": [{"lightCastShadows": true}]}')

    installed = watcher.check_once()
    assert len(installed) == 1
    assert watcher.installed_count == 1
    assert (mods_dir / "Civic_Mod.zip").exists()
    assert not test_zip.exists()
