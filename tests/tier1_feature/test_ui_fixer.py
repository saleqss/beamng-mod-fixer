"""Tier 1 Feature Tests: UI & Loading Screen Error Fixer.

Verifies:
- Detection and neutralization of rogue core UI files (e.g. ui/modules/loading/loading.js).
- Repair of malformed info.json files (BOM, comments, unquoted keys, trailing commas).
- Unpacking of nested container ZIP archives (*_UNZIP.zip).
- Purging of CEF browser and UI cache files in temp/ui and temp/cef.
- Integration into mod processing pipeline and CLI/interactive menus.
"""

import json
from pathlib import Path
import unittest.mock as mock
import zipfile

import pytest

from beamng_mod_fixer.core.cache_cleaner import clean_ui_cef_cache
from beamng_mod_fixer.core.ui_fixer import (
    fix_info_json_content,
    is_rogue_ui_entry,
    strip_json_comments,
    unpack_container_mod_archives,
)
from beamng_mod_fixer.core.zip_processor import process_mod_archive
from beamng_mod_fixer.models import ModStatus
from beamng_mod_fixer.ui import InteractiveCLI


def test_is_rogue_ui_entry_detection() -> None:
    """Ensure rogue core UI files are identified while preserving legitimate mod files."""
    # Critical culprit that causes 'UI error while loading'
    assert is_rogue_ui_entry("ui/modules/loading/loading.js") is True
    assert is_rogue_ui_entry("UI/Modules/Loading/Loading.JS") is True
    assert is_rogue_ui_entry(r"ui\modules\loading\loading.js") is True

    # Core bootloader / entrypoints
    assert is_rogue_ui_entry("ui/entrypoints/main/boot.js") is True
    assert is_rogue_ui_entry("ui/index.html") is True
    assert is_rogue_ui_entry("ui/ui-vue/dist/app.js") is True

    # Allowed files in mods
    assert is_rogue_ui_entry("ui/modules/loading/drive/loading_bg.jpg") is False
    assert is_rogue_ui_entry("ui/modules/loading/drive/screen.png") is False
    assert is_rogue_ui_entry("vehicles/my_car/gauges.html") is False
    assert is_rogue_ui_entry("vehicles/my_car/my_car.jbeam") is False


def test_strip_json_comments() -> None:
    """Ensure comments are stripped without breaking URLs or string content."""
    sample = """{
        // Single line comment
        "url": "http://beamng.com/api?param=1", /* inline comment */
        /* multi-line
           comment */
        "key": "value"
    }"""
    clean = strip_json_comments(sample)
    assert "// Single line comment" not in clean
    assert "/* inline comment */" not in clean
    assert "http://beamng.com/api?param=1" in clean
    assert '"key": "value"' in clean


def test_fix_info_json_content_various_corruptions() -> None:
    """Ensure fix_info_json_content repairs BOM, trailing commas, comments, and unquoted keys."""
    # 1. Clean valid JSON returns unmodified
    clean_json = '{\n  "name": "Super Car",\n  "version": 1.0\n}'
    res, mod, diags = fix_info_json_content(clean_json)
    assert mod is False
    assert json.loads(res)["name"] == "Super Car"

    # 2. Corrupted JSON with BOM, comments, unquoted keys, and trailing comma
    corrupt_json = (
        "\ufeff{\n"
        "  // Vehicle info\n"
        "  name: 'Corrupt Cruiser',\n"
        '  "brand": "Gavril",\n'
        '  "Author": "Modder",\n'
        "}\n"
    )
    res, mod, diags = fix_info_json_content(corrupt_json, filename="info.json")
    assert mod is True
    parsed = json.loads(res)
    assert parsed["name"] == "Corrupt Cruiser"
    assert parsed["brand"] == "Gavril"
    assert parsed["Author"] == "Modder"
    assert len(diags) > 0


def test_unpack_container_mod_archives(tmp_path: Path) -> None:
    """Ensure container ZIP archives containing inner mod ZIPs are unpacked."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True)

    # Create inner mod zip
    inner_zip_bytes = b"PK\x05\x06" + b"\x00" * 18

    # Create container zip: Nissan_Silvia_S15_v1.7_UNZIP.zip containing Wheels.zip and Body.zip
    container_zip = mods_dir / "Nissan_Silvia_S15_v1.7_UNZIP.zip"
    with zipfile.ZipFile(container_zip, "w") as zf:
        zf.writestr("Wheels Pack.zip", inner_zip_bytes)
        zf.writestr("Body Kit.zip", inner_zip_bytes)
        zf.writestr("readme.txt", "Extract before playing")

    # Dry-run inspection
    dry_results = unpack_container_mod_archives(mods_dir, dry_run=True)
    assert len(dry_results) == 1
    assert "Wheels Pack.zip" in dry_results[0][1]
    assert "Body Kit.zip" in dry_results[0][1]
    assert not (mods_dir / "Wheels Pack.zip").exists()

    # Live run extraction
    results = unpack_container_mod_archives(mods_dir, dry_run=False)
    assert len(results) == 1
    assert (mods_dir / "Wheels Pack.zip").exists()
    assert (mods_dir / "Body Kit.zip").exists()
    assert (mods_dir / "Nissan_Silvia_S15_v1.7_UNZIP.zip.extracted").exists()
    assert not container_zip.exists()


def test_clean_ui_cef_cache(tmp_path: Path) -> None:
    """Ensure clean_ui_cef_cache safely purges temp/ui and temp/cef while protecting .pc files."""
    user_dir = tmp_path / "user"
    temp_dir = user_dir / "temp"
    cef_dir = temp_dir / "cef"
    cef_dir.mkdir(parents=True)
    ui_dir = temp_dir / "ui"
    ui_dir.mkdir(parents=True)

    # Create cache files
    (cef_dir / "cache_data.bin").write_bytes(b"x" * 1024)
    (ui_dir / "rendered.html").write_text("<html></html>", encoding="utf-8")
    # Create protected file
    (cef_dir / "default.pc").write_text("{}", encoding="utf-8")

    # Clean cache
    res = clean_ui_cef_cache(user_dir, dry_run=False)
    assert res.files_deleted == 2
    assert res.bytes_freed >= 1024
    assert not (cef_dir / "cache_data.bin").exists()
    assert not (ui_dir / "rendered.html").exists()
    # Protected .pc file must remain intact
    assert (cef_dir / "default.pc").exists()


def test_process_mod_archive_fixes_ui_errors(tmp_path: Path) -> None:
    """Test process_mod_archive neutralizes rogue loading.js and fixes info.json."""
    zip_path = tmp_path / "hachi_mod.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("vehicles/hachi/hachi.jbeam", '{"hachi": {"refNodes": [["ref:"]], "glowMap": {}}}')
        # Ancient Angular loading.js override that triggers UI error
        zf.writestr("ui/modules/loading/loading.js", "angular.module('beamng.stuff', []);")
        # Malformed info.json with comments and trailing commas
        zf.writestr("vehicles/hachi/info.json", '{\n  // Hachi info\n  "Name": "Hachi",\n}')

    rep = process_mod_archive(zip_path, dry_run=False, fix_ui=True)
    assert rep.status == ModStatus.FIXED.value
    assert rep.ui_conflicts_fixed == 1
    assert rep.info_json_fixed == 1

    # Verify inside the repaired zip
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "ui/modules/loading/loading.js" not in namelist
        fixed_info = json.loads(zf.read("vehicles/hachi/info.json").decode("utf-8"))
        assert fixed_info["Name"] == "Hachi"


def test_interactive_cli_menu_ui_error_fixer(tmp_path: Path) -> None:
    """Test navigating menu_ui_error_fixer options (return, clean cef, unpack containers)."""
    user_dir = tmp_path / "user"
    mods_dir = user_dir / "mods"
    mods_dir.mkdir(parents=True)
    cache_dir = user_dir / "temp"
    cache_dir.mkdir(parents=True)

    paths = {
        "user_dir": user_dir,
        "mods_dir": mods_dir,
        "settings_dir": user_dir / "settings",
        "cache_dir": cache_dir,
    }
    cli = InteractiveCLI(paths=paths, dry_run=True)

    # 1. Option 0: Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_ui_error_fixer()

    # 2. Option 4: Unpack containers scan -> then 0 to return
    with mock.patch("builtins.input", side_effect=["4", "0"]):
        cli.menu_ui_error_fixer()

    # 3. Option 5: Purge CEF cache -> then 0 to return
    with mock.patch("builtins.input", side_effect=["5", "0"]):
        cli.menu_ui_error_fixer()
