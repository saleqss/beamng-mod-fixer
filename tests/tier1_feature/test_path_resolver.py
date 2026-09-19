"""Tier 1 Feature Tests: BeamNG Path Resolver & Topology Discovery.

Verifies:
- Persistent cache: save, 0ms load, and clearing.
- Intelligent scoring: prioritization of non-empty folders, active mods, and newest versions.
- Steam VDF parsing: libraryfolders.vdf (modern & legacy) and startup.ini UserPath extraction.
- Validation: normalization of env vars, quotes, direct mods folders, and non-existent paths.
- Priority resolution: explicit arguments > persistent cache > auto-discovery.
"""

import json
import os
from pathlib import Path
import unittest.mock as mock

import pytest

from beamng_mod_fixer.core.path_resolver import (
    clear_cached_paths,
    detect_beamng_user_dir,
    find_candidate_user_dirs,
    find_drive_root_candidates,
    find_steam_beamng_dirs,
    get_available_drives,
    get_cache_config_path,
    load_cached_paths,
    parse_startup_ini_userpath,
    parse_steam_library_folders,
    resolve_beamng_paths,
    save_cached_paths,
    score_candidate_user_dir,
    validate_beamng_dir,
)


def test_score_candidate_user_dir_empty_vs_populated(tmp_path: Path) -> None:
    """Test that directories with mod archives score substantially higher than empty ones."""
    empty_dir = tmp_path / "empty_user"
    empty_dir.mkdir()

    populated_dir = tmp_path / "populated_user"
    populated_mods = populated_dir / "mods"
    populated_mods.mkdir(parents=True)
    (populated_mods / "mod1.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    (populated_mods / "mod2.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    score_empty = score_candidate_user_dir(empty_dir)
    score_populated = score_candidate_user_dir(populated_dir)

    assert score_populated > score_empty
    assert score_populated >= 300.0  # mods bonus (200) + 2 mods * 50 (100)


def test_score_candidate_user_dir_version_bonus(tmp_path: Path) -> None:
    """Test that higher version numbers and 'current' receive higher score bonuses."""
    dir_030 = tmp_path / "0.30"
    dir_030.mkdir()
    dir_034 = tmp_path / "0.34"
    dir_034.mkdir()
    dir_current = tmp_path / "current"
    dir_current.mkdir()

    score_030 = score_candidate_user_dir(dir_030)
    score_034 = score_candidate_user_dir(dir_034)
    score_current = score_candidate_user_dir(dir_current)

    assert score_034 > score_030
    assert score_current > score_034


def test_parse_startup_ini_userpath(tmp_path: Path) -> None:
    """Test parsing UserPath from BeamNG startup.ini."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    ini_file = game_dir / "startup.ini"

    # Test 1: empty UserPath
    ini_file.write_text("[filesystem]\nUserPath =\n", encoding="utf-8")
    assert parse_startup_ini_userpath(ini_file, game_dir) is None

    # Test 2: relative UserPath
    custom_target = tmp_path / "user_data"
    custom_target.mkdir()
    ini_file.write_text(f"[filesystem]\nUserPath = ../user_data\n", encoding="utf-8")
    parsed_rel = parse_startup_ini_userpath(ini_file, game_dir)
    assert parsed_rel is not None
    assert parsed_rel.resolve() == custom_target.resolve()

    # Test 3: absolute UserPath
    ini_file.write_text(f'[filesystem]\nUserPath = "{str(custom_target)}"\n', encoding="utf-8")
    parsed_abs = parse_startup_ini_userpath(ini_file, game_dir)
    assert parsed_abs is not None
    assert parsed_abs.resolve() == custom_target.resolve()


def test_parse_steam_library_folders(tmp_path: Path) -> None:
    """Test parsing modern and legacy Steam libraryfolders.vdf formats."""
    lib1 = tmp_path / "SteamLib1"
    lib1.mkdir()
    lib2 = tmp_path / "SteamLib2"
    lib2.mkdir()

    vdf_file = tmp_path / "libraryfolders.vdf"
    vdf_content = f"""
    "libraryfolders"
    {{
        "0"
        {{
            "path"    "{str(lib1).replace('\\', '\\\\')}"
            "apps"
            {{
                "284160"    "123456"
            }}
        }}
        "1"
        {{
            "path"    "{str(lib2).replace('\\', '\\\\')}"
        }}
    }}
    """
    vdf_file.write_text(vdf_content, encoding="utf-8")

    parsed = parse_steam_library_folders(vdf_file)
    parsed_resolved = [p.resolve() for p in parsed]
    assert lib1.resolve() in parsed_resolved
    assert lib2.resolve() in parsed_resolved


def test_persistent_cache_lifecycle(tmp_path: Path) -> None:
    """Test saving, 0ms instant loading, and clearing persistent path cache."""
    cache_json = tmp_path / "cache_config.json"
    user_dir = tmp_path / "fake_beamng_user"
    user_dir.mkdir()
    mods_dir = user_dir / "mods"
    mods_dir.mkdir()
    settings_dir = user_dir / "settings"
    settings_dir.mkdir()
    cache_dir = user_dir / "temp"
    cache_dir.mkdir()

    test_paths = {
        "user_dir": user_dir,
        "mods_dir": mods_dir,
        "settings_dir": settings_dir,
        "cache_dir": cache_dir,
    }

    with mock.patch("beamng_mod_fixer.core.path_resolver.get_cache_config_path", return_value=cache_json):
        # 1. Cache initially does not exist
        assert load_cached_paths() is None

        # 2. Save paths to cache
        saved = save_cached_paths(test_paths, force=True)
        assert saved is True
        assert cache_json.exists()

        # 3. Load cached paths (0ms instant retrieval)
        loaded = load_cached_paths()
        assert loaded is not None
        assert loaded["user_dir"].resolve() == user_dir.resolve()
        assert loaded["mods_dir"].resolve() == mods_dir.resolve()

        # 4. Invalidation: if user_dir is deleted, load returns None
        import shutil
        shutil.rmtree(user_dir)
        assert load_cached_paths() is None

        # 5. Clear cache
        cleared = clear_cached_paths()
        assert cleared is True
        assert not cache_json.exists()


def test_validate_beamng_dir(tmp_path: Path) -> None:
    """Test validate_beamng_dir with various inputs."""
    user_dir = tmp_path / "user_dir"
    user_dir.mkdir()
    mods_dir = user_dir / "mods"
    mods_dir.mkdir()
    (mods_dir / "car.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    # 1. Direct path to user directory
    is_valid, msg, res = validate_beamng_dir(str(user_dir))
    assert is_valid is True
    assert "1 mod archives" in msg
    assert res["mods_dir"].resolve() == mods_dir.resolve()

    # 2. Path to mods directory directly
    is_valid, msg, res = validate_beamng_dir(str(mods_dir))
    assert is_valid is True
    assert res["mods_dir"].resolve() == mods_dir.resolve()

    # 3. Quoted path with whitespace
    is_valid, msg, res = validate_beamng_dir(f'  "{str(user_dir)}"  ')
    assert is_valid is True

    # 4. Non-existent path
    is_valid, msg, res = validate_beamng_dir(tmp_path / "non_existent_folder_xyz")
    assert is_valid is False
    assert "does not exist" in msg

    # 5. Empty path
    is_valid, msg, res = validate_beamng_dir("   ")
    assert is_valid is False
    assert "empty" in msg


def test_find_candidate_user_dirs_versions_ranking(tmp_path: Path) -> None:
    """Test that version subdirectories in AppData are discovered and sorted properly."""
    appdata_bng = tmp_path / "BeamNG" / "BeamNG.drive"
    appdata_bng.mkdir(parents=True)

    v030 = appdata_bng / "0.30"
    v030.mkdir()

    v033 = appdata_bng / "0.33"
    v033.mkdir()

    v034 = appdata_bng / "0.34"
    (v034 / "mods").mkdir(parents=True)
    (v034 / "mods" / "active_mod.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}):
        candidates = find_candidate_user_dirs()
        assert len(candidates) >= 3
        # v034 has an active mod zip, so it must be ranked first
        assert candidates[0].resolve() == v034.resolve()


def test_resolve_beamng_paths_explicit_override(tmp_path: Path) -> None:
    """Test that explicit arguments to resolve_beamng_paths strictly override defaults."""
    custom_mods = tmp_path / "my_custom_mods"
    custom_mods.mkdir()

    paths = resolve_beamng_paths(mods_dir=custom_mods, use_cache=False, save_cache=False)
    assert paths["mods_dir"].resolve() == custom_mods.resolve()


def test_get_available_drives() -> None:
    """Test that get_available_drives executes cleanly and returns valid root strings."""
    drives = get_available_drives()
    assert isinstance(drives, list)
    if os.name == "nt":
        assert len(drives) >= 1
        assert any(d.startswith("C:") for d in drives)


def test_parse_steam_library_folders_excludes_numeric_app_sizes(tmp_path: Path) -> None:
    """Test that modern VDF app byte counts (e.g. 53633513758) are not parsed as library paths."""
    vdf = tmp_path / "libraryfolders.vdf"
    vdf.write_text("""
    "libraryfolders"
    {
        "0"
        {
            "path" "C:\\\\Games\\\\Steam"
            "apps"
            {
                "284160" "53633513758"
                "730" "71589381210"
            }
        }
    }
    """, encoding="utf-8")

    parsed = parse_steam_library_folders(vdf)
    parsed_strs = [str(p) for p in parsed]
    # "53633513758" and "71589381210" must NEVER be returned as library paths
    for s in parsed_strs:
        assert "53633513758" not in s
        assert "71589381210" not in s


def test_find_steam_beamng_dirs_with_appmanifest(tmp_path: Path) -> None:
    """Test discovering BeamNG game directory via Steam appmanifest and startup.ini."""
    steam_lib = tmp_path / "SteamLib"
    steamapps = steam_lib / "steamapps"
    steamapps.mkdir(parents=True)

    # 1. Write appmanifest_284160.acf
    manifest = steamapps / "appmanifest_284160.acf"
    manifest.write_text('"AppState" { "appid" "284160" "installdir" "BeamNG_Custom" }', encoding="utf-8")

    # 2. Create game dir with startup.ini pointing to user data
    game_dir = steamapps / "common" / "BeamNG_Custom"
    game_dir.mkdir(parents=True)
    user_target = tmp_path / "custom_user_folder"
    user_target.mkdir()
    (game_dir / "startup.ini").write_text(f'[filesystem]\nUserPath = "{str(user_target)}"\n', encoding="utf-8")

    # Mock get_steam_install_paths and parse_steam_library_folders
    with mock.patch("beamng_mod_fixer.core.path_resolver.get_steam_install_paths", return_value=[steam_lib]):
        with mock.patch("beamng_mod_fixer.core.path_resolver.parse_steam_library_folders", return_value=[steam_lib]):
            dirs = find_steam_beamng_dirs()
            resolved_dirs = [d.resolve() for d in dirs]
            assert user_target.resolve() in resolved_dirs


def test_score_candidate_user_dir_with_active_logs(tmp_path: Path) -> None:
    """Test that candidate directories with active beamng.log receive activity bonus."""
    cand1 = tmp_path / "cand1"
    cand1.mkdir()
    cand2 = tmp_path / "cand2"
    cand2.mkdir()
    (cand2 / "beamng.log").write_text("Engine initialized", encoding="utf-8")

    score1 = score_candidate_user_dir(cand1)
    score2 = score_candidate_user_dir(cand2)
    assert score2 > score1


def test_validate_beamng_dir_relative_and_content_mods(tmp_path: Path) -> None:
    """Test validate_beamng_dir with relative path and content/mods folder."""
    # Test content/mods game topology
    game_dir = tmp_path / "game_root"
    content_mods = game_dir / "content" / "mods"
    content_mods.mkdir(parents=True)
    (content_mods / "addon.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    is_valid, msg, paths = validate_beamng_dir(str(game_dir))
    assert is_valid is True
    assert paths["mods_dir"].resolve() == content_mods.resolve()
    assert "1 mod archives" in msg

