"""Tier 1 Feature Tests: Interactive UI and Menus.

Verifies:
- Rendering of splash screens (UTF-8 block and ASCII fallback).
- Status bar generation with detected paths.
- Hierarchical menu transitions and graceful exits.
- Submenu navigation and returning to main menu.
"""

from pathlib import Path
import unittest.mock as mock

import pytest

from beamng_mod_fixer.ui import (
    ASCII_BANNER,
    InteractiveCLI,
    SPLASH_BANNER,
    print_splash_banner,
    print_status_bar,
    safe_print,
)


def test_splash_banners_defined() -> None:
    """Ensure both rich and ASCII banners are non-empty and formatted."""
    assert "GBEAM" in SPLASH_BANNER or "MOD FIXER" in SPLASH_BANNER
    assert "GBEAM" in ASCII_BANNER or "MOD FIXER" in ASCII_BANNER


def test_safe_print_does_not_crash(capsys: pytest.CaptureFixture[str]) -> None:
    """Test safe_print executes cleanly without crashing."""
    safe_print("Test message with special unicode: ╔═╗ ⚡")
    out = capsys.readouterr().out
    assert "Test message" in out


def test_print_splash_banner(capsys: pytest.CaptureFixture[str]) -> None:
    """Test print_splash_banner outputs application header."""
    print_splash_banner()
    out = capsys.readouterr().out
    assert "MOD FIXER" in out or "GBEAM" in out


def test_print_status_bar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test print_status_bar outputs environment information."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "user_dir": tmp_path,
        "mods_dir": mods_dir,
        "settings_dir": tmp_path / "settings",
        "cache_dir": tmp_path / "temp",
    }
    print_status_bar(paths)
    out = capsys.readouterr().out
    assert "System & Game Environment" in out or "Mods Folder" in out


def test_interactive_cli_exit_main_menu(tmp_path: Path) -> None:
    """Test selecting '0' exits main menu cleanly."""
    paths = {
        "user_dir": tmp_path,
        "mods_dir": tmp_path / "mods",
        "settings_dir": tmp_path / "settings",
        "cache_dir": tmp_path / "temp",
    }
    cli = InteractiveCLI(paths=paths, dry_run=True)

    with mock.patch("builtins.input", return_value="0"):
        ret = cli.run_main_menu()
        assert ret == 0


def test_interactive_cli_submenu_return(tmp_path: Path) -> None:
    """Test entering submenus and returning via '0' to main menu."""
    paths = {
        "user_dir": tmp_path,
        "mods_dir": tmp_path / "mods",
        "settings_dir": tmp_path / "settings",
        "cache_dir": tmp_path / "temp",
    }
    cli = InteractiveCLI(paths=paths, dry_run=True)

    # Submenu: Optics Studio -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_optics_studio()

    # Submenu: Materials Doctor -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_materials_doctor()

    # Submenu: Drivetrain Repair -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_drivetrain_repair()

    # Submenu: Sound & Lua -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_sound_lua_guard()

    # Submenu: Graphics -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_graphics_optimizer()

    # Submenu: Cache Purge -> Return
    with mock.patch("builtins.input", return_value="0"):
        cli.menu_cache_purge()


def test_interactive_cli_menu_fix_results(tmp_path: Path) -> None:
    """Test that menu_fix_results displays report and returns to main menu on choice 1 or Enter."""
    from beamng_mod_fixer.models import OverallSummary, ModArchiveReport, DiagnosticNotice

    summary = OverallSummary()
    rep = ModArchiveReport(archive_path=tmp_path / "test.zip")
    rep.diagnostics.append(DiagnosticNotice(severity="info", message="Fixed spotlight angles"))
    summary.archive_reports.append(rep)

    cli = InteractiveCLI(dry_run=True)

    # Choice "1" returns to main menu
    with mock.patch("builtins.input", return_value="1"):
        cli.menu_fix_results(summary, title="TEST FIX RESULTS")

    # Default Enter ("") returns to main menu
    with mock.patch("builtins.input", return_value=""):
        cli.menu_fix_results(summary, title="TEST FIX RESULTS")


def test_interactive_cli_view_detailed_diagnostics(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test displaying detailed diagnostic notices list."""
    from beamng_mod_fixer.models import OverallSummary, ModArchiveReport, DiagnosticNotice

    summary = OverallSummary()
    rep = ModArchiveReport(archive_path=tmp_path / "my_mod.zip")
    rep.diagnostics.append(DiagnosticNotice(severity="warning", message="Unstable tire pressure"))
    summary.archive_reports.append(rep)

    cli = InteractiveCLI(dry_run=True)
    with mock.patch("builtins.input", return_value=""):
        cli._view_detailed_diagnostics(summary)

    out = capsys.readouterr().out
    assert "DETAILED MOD DIAGNOSTIC NOTICES" in out
    assert "my_mod.zip" in out
    assert "Unstable tire pressure" in out
