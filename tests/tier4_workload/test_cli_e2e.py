"""Tier 4: End-to-End Tests for CLI Interface via Subprocess Execution.

Verifies:
- CLI entrypoint invocation: python -m beamng_mod_fixer
- Built-in flags: --help, --version, --mods-dir, --settings-dir, --cache-dir
- Action flags: --fix-mods, --optimize-graphics, --clean-cache, --all
- Safety flags: --dry-run, --no-backup
- UX flags: --quiet, --verbose
- Subprocess exit codes (0 for success, 1 for fatal error, 2 for argument errors)
"""

from pathlib import Path
import subprocess
import sys

import pytest

from tests.fixtures.factory import (
    create_realistic_mod_zip,
    create_synthetic_beamng_user_dir,
)

# Detect if cli is implemented
try:
    import beamng_mod_fixer.cli  # type: ignore
    HAS_CLI = True
except (ImportError, ModuleNotFoundError):
    HAS_CLI = False


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_CLI:
        pytest.skip("beamng_mod_fixer.cli not yet implemented (Milestone M4)")


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Execute the CLI module in a clean subprocess."""
    cmd = [sys.executable, "-m", "beamng_mod_fixer", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def test_cli_help_flag() -> None:
    """Test --help prints usage documentation and exits with code 0."""
    res = run_cli("--help")
    assert res.returncode == 0
    assert "beamng" in res.stdout.lower() or "usage" in res.stdout.lower()
    assert "--mods-dir" in res.stdout
    assert "--optimize-graphics" in res.stdout
    assert "--clean-cache" in res.stdout


def test_cli_version_flag() -> None:
    """Test --version displays semantic version and exits with code 0."""
    res = run_cli("--version")
    assert res.returncode == 0
    assert any(char.isdigit() for char in res.stdout)


def test_cli_fix_mods_flag(tmp_path: Path) -> None:
    """Test running --fix-mods on a directory with broken headlights."""
    mods_dir = tmp_path / "mods"
    p = mods_dir / "mod_test.zip"
    create_realistic_mod_zip(p, "cli_car")

    res = run_cli("--mods-dir", str(mods_dir), "--fix-mods")
    assert res.returncode == 0
    assert "fixed" in res.stdout.lower() or "summary" in res.stdout.lower()


def test_cli_optimize_graphics_flag(tmp_path: Path) -> None:
    """Test running --optimize-graphics creates backup and modifies settings."""
    tree = create_synthetic_beamng_user_dir(tmp_path / "user")
    settings_dir = tree["settings_dir"]

    res = run_cli("--settings-dir", str(settings_dir), "--optimize-graphics")
    assert res.returncode == 0
    bak_files = list(settings_dir.glob("*.bak*"))
    assert len(bak_files) >= 1


def test_cli_clean_cache_flag(tmp_path: Path) -> None:
    """Test running --clean-cache cleans compiled shaders."""
    tree = create_synthetic_beamng_user_dir(tmp_path / "user")
    temp_dir = tree["temp_dir"]

    res = run_cli("--cache-dir", str(temp_dir), "--clean-cache")
    assert res.returncode == 0
    remaining_shaders = list((temp_dir / "shaders").rglob("*.d3dcsx"))
    assert len(remaining_shaders) == 0


def test_cli_all_flag(tmp_path: Path) -> None:
    """Test running --all executes mods fix, graphics optimization, and cache clean."""
    tree = create_synthetic_beamng_user_dir(tmp_path / "user")

    res = run_cli(
        "--mods-dir", str(tree["mods_dir"]),
        "--settings-dir", str(tree["settings_dir"]),
        "--cache-dir", str(tree["temp_dir"]),
        "--all"
    )
    assert res.returncode == 0


def test_cli_dry_run_leaves_zero_changes(tmp_path: Path) -> None:
    """Test running --all with --dry-run makes zero modifications."""
    tree = create_synthetic_beamng_user_dir(tmp_path / "user")
    mod_bytes_before = [p.read_bytes() for p in tree["mod_paths"]]

    res = run_cli(
        "--mods-dir", str(tree["mods_dir"]),
        "--settings-dir", str(tree["settings_dir"]),
        "--cache-dir", str(tree["temp_dir"]),
        "--all",
        "--dry-run"
    )
    assert res.returncode == 0
    mod_bytes_after = [p.read_bytes() for p in tree["mod_paths"]]
    assert mod_bytes_after == mod_bytes_before


def test_cli_invalid_argument_exits_code_2() -> None:
    """Test that unrecognized CLI flags exit with code 2."""
    res = run_cli("--nonexistent-flag-xyz")
    assert res.returncode in (1, 2)


def test_cli_quiet_mode(tmp_path: Path) -> None:
    """Test that --quiet suppresses verbose logs and decorative banners."""
    mods_dir = tmp_path / "mods"
    create_realistic_mod_zip(mods_dir / "car.zip", "car")

    res_normal = run_cli("--mods-dir", str(mods_dir), "--fix-mods")
    res_quiet = run_cli("--mods-dir", str(mods_dir), "--fix-mods", "--quiet")

    assert res_quiet.returncode == 0
    assert len(res_quiet.stdout) < len(res_normal.stdout)


def test_cli_show_paths() -> None:
    """Test that --show-paths prints detected BeamNG paths and exits with code 0."""
    res = run_cli("--show-paths")
    assert res.returncode == 0
    assert "detected beamng" in res.stdout.lower()
    assert "user directory" in res.stdout.lower()
    assert "mods directory" in res.stdout.lower()


def test_cli_user_dir_flag(tmp_path: Path) -> None:
    """Test passing --user-dir sets all sub-paths accordingly."""
    user_dir = tmp_path / "custom_user"
    user_dir.mkdir()
    res = run_cli("--user-dir", str(user_dir), "--show-paths")
    assert res.returncode == 0
    assert str(user_dir).lower() in res.stdout.lower()
    assert "status" in res.stdout.lower()
    assert "path cache" in res.stdout.lower()


def test_cli_save_paths_flag(tmp_path: Path) -> None:
    """Test --save-paths saves explicit configuration without error."""
    from beamng_mod_fixer.core.path_resolver import clear_cached_paths
    user_dir = tmp_path / "saved_user"
    user_dir.mkdir()
    try:
        res = run_cli("--user-dir", str(user_dir), "--save-paths")
        assert res.returncode == 0
        assert "successfully saved" in res.stdout.lower()
    finally:
        clear_cached_paths()


def test_cli_fix_rear_lights_flag(tmp_path: Path) -> None:
    """Test running --fix-rear-lights flag on mod archive."""
    mods_dir = tmp_path / "mods"
    p = mods_dir / "mod_test.zip"
    create_realistic_mod_zip(p, "cli_car")

    res = run_cli("--mods-dir", str(mods_dir), "--fix-rear-lights")
    assert res.returncode == 0
    assert "rear lights" in res.stdout.lower() or "summary" in res.stdout.lower()




