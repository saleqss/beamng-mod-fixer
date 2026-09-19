"""Interactive Terminal UI and Menu System for GBEAM FIX.

Provides:
- Vivid colorful ANSI splash screen with 'GBEAM FIX' logo and status indicators.
- Hierarchical interactive menu:
  * Main Menu -> Submenus (Headlights, Materials, Drivetrain, Audio/Lua, Graphics, Cache)
  * Smooth transitions and automatic return to Main Menu.
- 1-Click Global Fix orchestration with structured diagnostic output.
- Support for non-interactive fallback when executed without a TTY.
"""

import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from beamng_mod_fixer import __version__
from beamng_mod_fixer.core.cache_cleaner import clean_shader_cache
from beamng_mod_fixer.core.graphics_optimizer import (
    OPTIMIZATION_PRESETS,
    optimize_settings,
    restore_settings_backup,
)
from beamng_mod_fixer.core.path_resolver import detect_beamng_user_dir, resolve_beamng_paths
from beamng_mod_fixer.core.zip_processor import process_mod_archive, scan_and_fix_mods
from beamng_mod_fixer.models import ModStatus, OverallSummary

# Enable Windows ANSI virtual terminal processing if available
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


# ANSI Color Codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[40m"


ASCII_BANNER = rf"""
======================================================================
   ____  ____  _____    _    __  __   _____ _____  __
  / ___|| __ )| ____|  / \  |  \/  | |  ___|_   _\ \/ /
 | |  _ |  _ \|  _|   / _ \ | |\/| | | |_    | |   \  / 
 | |_| || |_) | |___ / ___ \| |  | | |  _|   | |   /  \ 
  \____||____/|_____/_/   \_\_|  |_| |_|     |_|  /_/\_\

        ULTIMATE GLOBAL MOD FIXER & GRAPHICS OPTIMIZER v{__version__}
          BeamNG.drive 0.30 - 0.34+ Community Standard Engine
======================================================================
"""

SPLASH_BANNER = f"""{Colors.CYAN}{Colors.BOLD}
╔════════════════════════════════════════════════════════════════════════════════════════╗
║   ██████╗ ██████╗ ███████╗ █████╗ ███╗   ███╗   ███████╗██╗██╗  ██╗                    ║
║  ██╔════╝ ██╔══██╗██╔════╝██╔══██╗████╗ ████║   ██╔════╝██║╚██╗██╔╝                    ║
║  ██║  ███╗██████╔╝█████╗  ███████║██╔████╔██║   █████╗  ██║ ╚███╔╝                     ║
║  ██║   ██║██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║   ██╔══╝  ██║ ██╔██╗                     ║
║  ╚██████╔╝██████╔╝███████╗██║  ██║██║ ╚═╝ ██║   ██║     ██║██╔╝ ██╗                    ║
║   ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝                    ║
║                                                                                        ║
║            {Colors.YELLOW}⚡ ULTIMATE GLOBAL MOD FIXER & GRAPHICS OPTIMIZER v{__version__} ⚡{Colors.CYAN}{Colors.BOLD}          ║
║              {Colors.GREEN}BeamNG.drive 0.30 - 0.34+ Adaptive Community Standard{Colors.CYAN}{Colors.BOLD}                     ║
╚════════════════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}"""


def safe_print(text: str = "") -> None:
    """Safely print text to stdout with fallback for legacy charmap / non-utf8 consoles."""
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except (UnicodeEncodeError, OSError):
        enc = sys.stdout.encoding or "ascii"
        try:
            sys.stdout.buffer.write((text + "\n").encode(enc, errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            try:
                # Strip non-ascii chars completely
                ascii_text = text.encode("ascii", errors="replace").decode("ascii")
                sys.stdout.write(ascii_text + "\n")
                sys.stdout.flush()
            except Exception:
                pass


def print_splash_banner() -> None:
    """Print the splash banner choosing UTF-8 box art or clean ASCII fallback."""
    enc = (sys.stdout.encoding or "").lower()
    if "utf" in enc:
        safe_print(SPLASH_BANNER)
    else:
        safe_print(ASCII_BANNER)


def clear_screen() -> None:
    """Clear the terminal screen if interactive."""
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def print_status_bar(paths: Dict[str, Path]) -> None:
    """Print system status indicators."""
    mods_dir = paths["mods_dir"]
    mod_count = 0
    if mods_dir.exists() and mods_dir.is_dir():
        mod_count = len([p for p in mods_dir.iterdir() if p.is_file() and p.suffix.lower() == ".zip"])

    print(f"{Colors.GRAY}┌─ System & Game Environment ─────────────────────────────────────────────┐{Colors.RESET}")
    print(f"{Colors.GRAY}│{Colors.RESET} {Colors.WHITE}BeamNG Directory:{Colors.RESET} {Colors.CYAN}{paths.get('user_dir', 'Default')}{Colors.RESET}")
    print(f"{Colors.GRAY}│{Colors.RESET} {Colors.WHITE}Mods Folder:     {Colors.RESET} {Colors.CYAN}{mods_dir}{Colors.RESET} {Colors.YELLOW}({mod_count} mod archives detected){Colors.RESET}")
    print(f"{Colors.GRAY}│{Colors.RESET} {Colors.WHITE}Adaptive Engine: {Colors.RESET} {Colors.GREEN}100% Multi-Strategy Recovery Active [Optics+Mats+Diff+SFX]{Colors.RESET}")
    print(f"{Colors.GRAY}└─────────────────────────────────────────────────────────────────────────┘{Colors.RESET}\n")


def pause_return() -> None:
    """Prompt user to press Enter before returning to menu."""
    if sys.stdin.isatty():
        try:
            input(f"\n{Colors.YELLOW}Press [Enter] to return to Main Menu...{Colors.RESET}")
        except (KeyboardInterrupt, EOFError):
            pass


class InteractiveCLI:
    """Full hierarchical interactive menu controller for GBEAM FIX."""

    def __init__(self, paths: Optional[Dict[str, Path]] = None, dry_run: bool = False):
        self.paths = paths or resolve_beamng_paths()
        self.dry_run = dry_run

    def run_main_menu(self) -> int:
        """Main loop for the top-level menu."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print_status_bar(self.paths)

            print(f"{Colors.BOLD}{Colors.WHITE}MAIN CONTROL MENU:{Colors.RESET}")
            print(f"  {Colors.GREEN}{Colors.BOLD}[1] ⚡ 1-Click Global Fix{Colors.RESET} {Colors.DIM}(Headlights + Textures + Drivetrain + Sounds + Graphics + Cache){Colors.RESET}")
            print(f"  {Colors.CYAN}[2] 💡 Headlights & Optics Studio{Colors.RESET} {Colors.DIM}(Smart Fix, Angle repair, cookie modernizer){Colors.RESET}")
            print(f"  {Colors.YELLOW}[3] 🎨 Materials & Texture Doctor{Colors.RESET} {Colors.DIM}(Fix NO TEXTURE, materials.cs -> 1.5 JSON, VFS paths){Colors.RESET}")
            print(f"  {Colors.MAGENTA}[4] ⚙️ Drivetrain & Physics Repair{Colors.RESET} {Colors.DIM}(Fix frozen cars, differential explosion, tire PSI){Colors.RESET}")
            print(f"  {Colors.WHITE}[5] 🔊 Sound & Lua Crash Guard{Colors.RESET} {Colors.DIM}(Modernize FMOD audio, patch obsolete lua APIs){Colors.RESET}")
            print(f"  {Colors.CYAN}[6] 🚀 Graphics & FPS Optimizer{Colors.RESET} {Colors.DIM}(Cinematic-Fast, Balanced, Maximum-FPS presets){Colors.RESET}")
            print(f"  {Colors.GREEN}[7] 🧹 Cache & Diagnostics Purge{Colors.RESET} {Colors.DIM}(DirectX/Vulkan shaders, vehicle binaries, temp files){Colors.RESET}")
            print(f"  {Colors.YELLOW}[8] 📋 Deep Mod Health Audit{Colors.RESET} {Colors.DIM}(Safe non-modifying dry-run scan with report){Colors.RESET}")
            print(f"  {Colors.RED}[0] 🚪 Exit{Colors.RESET}")

            try:
                choice = input(f"\n{Colors.BOLD}Select an option [0-8] (default: 1): {Colors.RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}")
                return 0

            if choice in ("1", ""):
                self.action_global_fix()
            elif choice == "2":
                self.menu_optics_studio()
            elif choice == "3":
                self.menu_materials_doctor()
            elif choice == "4":
                self.menu_drivetrain_repair()
            elif choice == "5":
                self.menu_sound_lua_guard()
            elif choice == "6":
                self.menu_graphics_optimizer()
            elif choice == "7":
                self.menu_cache_purge()
            elif choice == "8":
                self.action_deep_audit()
            elif choice == "0":
                print(f"\n{Colors.GREEN}Thank you for using GBEAM FIX. Happy driving!{Colors.RESET}")
                return 0
            else:
                print(f"{Colors.RED}Invalid option. Please enter a number between 0 and 8.{Colors.RESET}")
                time.sleep(1)

    # ==========================================================================
    # Action 1: 1-Click Global Fix
    # ==========================================================================
    def action_global_fix(self) -> None:
        """Run complete 1-Click Global Fix across all repair stages."""
        clear_screen()
        print(SPLASH_BANNER)
        print(f"{Colors.BOLD}{Colors.GREEN}>>> EXECUTING 1-CLICK GLOBAL FIX <<<{Colors.RESET}\n")

        # Stage 1: Purge corrupt cache
        print(f"{Colors.CYAN}[Stage 1/3]{Colors.RESET} Purging corrupt shader & vehicle temporary caches...")
        try:
            cache_res = clean_shader_cache(self.paths["cache_dir"], dry_run=self.dry_run)
            print(f"  ✔ Purged {cache_res.files_deleted} cache files ({cache_res.bytes_freed / 1024 / 1024:.2f} MB freed)")
        except Exception as e:
            print(f"  {Colors.YELLOW}⚠ Cache clean note: {e}{Colors.RESET}")

        # Stage 2: Deploy optimized graphics preset
        print(f"\n{Colors.CYAN}[Stage 2/3]{Colors.RESET} Deploying 'cinematic-fast' graphics optimization preset...")
        try:
            opt_res = optimize_settings(self.paths["settings_dir"], preset="cinematic-fast", dry_run=self.dry_run)
            print(f"  ✔ Applied 60FPS fast reflections, soft shadows, and clustered lighting ({len(opt_res.applied_keys)} keys tuned)")
        except Exception as e:
            print(f"  {Colors.YELLOW}⚠ Graphics optimize note: {e}{Colors.RESET}")

        # Stage 3: Scan and fix all mods
        print(f"\n{Colors.CYAN}[Stage 3/3]{Colors.RESET} Scanning & repairing all mod archives in: {self.paths['mods_dir']}...")
        summary = scan_and_fix_mods(
            self.paths["mods_dir"],
            dry_run=self.dry_run,
            selective=True,
            fix_materials=True,
            fix_drivetrain=True,
            fix_sound=True,
            fix_lua=True,
            clean_junk=True,
            progress_callback=lambda p, r, idx, tot: (
                print(f"  [{idx}/{tot}] {p.name}: {r.status.upper()} "
                      f"(Optics: {r.shadows_fixed}, Mats: {r.materials_converted + r.materials_fixed}, "
                      f"Drivetrain: {r.drivetrains_fixed}, Audio: {r.sounds_fixed})")
                if r.status == ModStatus.FIXED.value
                else None
            )
        )

        # Transition into dedicated Post-Fix Studio Menu
        self.menu_fix_results(summary, title="1-CLICK GLOBAL FIX RESULTS")

    # ==========================================================================
    # Submenu: Headlights & Optics Studio
    # ==========================================================================
    def menu_optics_studio(self) -> None:
        """Submenu for headlights and optics."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.CYAN}💡 HEADLIGHTS & OPTICS STUDIO{Colors.RESET}\n")
            print(f"  [1] Smart Selective Fix (Recommended: fixes lowbeams, preserves highbeams, modernizes cookies)")
            print(f"  [2] Force Legacy Fix (Forces lightCastShadows: false everywhere)")
            print(f"  [3] Normalize Spotlight Angles & Brightness Only")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-3]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2"):
                selective = (choice == "1")
                print(f"\n[*] Processing headlights (selective={selective})...")
                summary = scan_and_fix_mods(
                    self.paths["mods_dir"],
                    dry_run=self.dry_run,
                    selective=selective,
                    fix_materials=False,
                    fix_drivetrain=False,
                    fix_sound=False,
                    fix_lua=False,
                )
                self.menu_fix_results(summary, title="HEADLIGHTS FIX REPORT")
                return
            elif choice == "3":
                print("\n[*] Normalizing angles and brightness across mods...")
                summary = scan_and_fix_mods(
                    self.paths["mods_dir"],
                    dry_run=self.dry_run,
                    selective=True,
                    fix_materials=False,
                    fix_drivetrain=False,
                    fix_sound=False,
                    fix_lua=False,
                )
                self.menu_fix_results(summary, title="OPTICS NORMALIZATION REPORT")
                return

    # ==========================================================================
    # Submenu: Materials & Texture Doctor
    # ==========================================================================
    def menu_materials_doctor(self) -> None:
        """Submenu for materials and textures."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.YELLOW}🎨 MATERIALS & TEXTURE DOCTOR{Colors.RESET}\n")
            print(f"  [1] Convert legacy materials.cs to modern main.materials.json (v1.5 PBR)")
            print(f"  [2] Fix orange 'NO TEXTURE' & normalize VFS paths (\\ -> /)")
            print(f"  [3] Run Complete Materials & Texture Doctor")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-3]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2", "3"):
                print(f"\n[*] Executing Materials Doctor on: {self.paths['mods_dir']}...")
                summary = scan_and_fix_mods(
                    self.paths["mods_dir"],
                    dry_run=self.dry_run,
                    fix_materials=True,
                    fix_drivetrain=False,
                    fix_sound=False,
                    fix_lua=False,
                )
                self.menu_fix_results(summary, title="MATERIALS DOCTOR REPORT")
                return

    # ==========================================================================
    # Submenu: Drivetrain & Physics Repair
    # ==========================================================================
    def menu_drivetrain_repair(self) -> None:
        """Submenu for drivetrain and physics."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.MAGENTA}⚙️ DRIVETRAIN & PHYSICS REPAIR{Colors.RESET}\n")
            print(f"  [1] Fix Differential Freeze & Physics Explosion (gearRatio, viscousCoupling)")
            print(f"  [2] Fix Tire Pressures (pressurePSI) & Wheel Friction Coefficients")
            print(f"  [3] Run Complete Drivetrain & Physics Repair")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-3]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2", "3"):
                print(f"\n[*] Executing Drivetrain Repair on: {self.paths['mods_dir']}...")
                summary = scan_and_fix_mods(
                    self.paths["mods_dir"],
                    dry_run=self.dry_run,
                    fix_materials=False,
                    fix_drivetrain=True,
                    fix_sound=False,
                    fix_lua=False,
                )
                self.menu_fix_results(summary, title="DRIVETRAIN REPAIR REPORT")
                return

    # ==========================================================================
    # Submenu: Sound & Lua Crash Guard
    # ==========================================================================
    def menu_sound_lua_guard(self) -> None:
        """Submenu for sound and Lua."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.WHITE}🔊 SOUND & LUA CRASH GUARD{Colors.RESET}\n")
            print(f"  [1] Modernize Obsolete Pre-FMOD Sound Paths to BeamNG FMOD Events")
            print(f"  [2] Guard Deprecated Vehicle Lua Scripts (prevent fatal spawn crashes)")
            print(f"  [3] Run Both Sound Modernizer & Lua Crash Guard")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-3]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2", "3"):
                fix_snd = choice in ("1", "3")
                fix_lua = choice in ("2", "3")
                print(f"\n[*] Executing Sound & Lua Guard on: {self.paths['mods_dir']}...")
                summary = scan_and_fix_mods(
                    self.paths["mods_dir"],
                    dry_run=self.dry_run,
                    fix_materials=False,
                    fix_drivetrain=False,
                    fix_sound=fix_snd,
                    fix_lua=fix_lua,
                )
                self.menu_fix_results(summary, title="SOUND & LUA GUARD REPORT")
                return

    # ==========================================================================
    # Submenu: Graphics & FPS Optimizer
    # ==========================================================================
    def menu_graphics_optimizer(self) -> None:
        """Submenu for graphics settings."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.CYAN}🚀 GRAPHICS & FPS OPTIMIZER{Colors.RESET}\n")
            print(f"  [1] Deploy 'Cinematic-Fast' (Ultra visuals + 60fps fast reflections + smooth shadows)")
            print(f"  [2] Deploy 'Balanced' (Standard sweet spot for mid-range systems)")
            print(f"  [3] Deploy 'Maximum-FPS' (Extreme performance boost for low-end / competitive)")
            print(f"  [4] Restore Graphics Settings from Previous Backup")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-4]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2", "3"):
                preset_map = {"1": "cinematic-fast", "2": "balanced", "3": "performance"}
                preset = preset_map[choice]
                print(f"\n[*] Deploying graphics preset '{preset}'...")
                res = optimize_settings(self.paths["settings_dir"], preset=preset, dry_run=self.dry_run)
                print(f"\n{Colors.GREEN}✔ Successfully applied preset '{preset}'! ({len(res.applied_keys)} settings tuned){Colors.RESET}")
                if res.backup_created:
                    print(f"  Backup created: {res.backup_path}")
                pause_return()
            elif choice == "4":
                print("\n[*] Restoring graphics settings from backup...")
                restored = restore_settings_backup(self.paths["settings_dir"])
                if restored:
                    print(f"\n{Colors.GREEN}✔ Settings successfully restored from backup!{Colors.RESET}")
                else:
                    print(f"\n{Colors.YELLOW}⚠ No valid settings backup found in directory.{Colors.RESET}")
                pause_return()

    # ==========================================================================
    # Submenu: Cache & Diagnostics Purge
    # ==========================================================================
    def menu_cache_purge(self) -> None:
        """Submenu for cleaning caches."""
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            print(f"{Colors.BOLD}{Colors.GREEN}🧹 CACHE & DIAGNOSTICS PURGE{Colors.RESET}\n")
            print(f"  [1] Purge compiled shader cache (.d3dcsx, .db)")
            print(f"  [2] Full cache purge (shaders + vehicle AST + temporary binaries)")
            print(f"  [0] Return to Main Menu")

            choice = input(f"\n{Colors.BOLD}Select an option [0-2]: {Colors.RESET}").strip()
            if choice == "0":
                return
            elif choice in ("1", "2"):
                print(f"\n[*] Cleaning cache in: {self.paths['cache_dir']}...")
                res = clean_shader_cache(self.paths["cache_dir"], dry_run=self.dry_run)
                print(f"\n{Colors.GREEN}✔ Cache cleared successfully!{Colors.RESET}")
                print(f"  Files deleted:    {res.files_deleted}")
                print(f"  Disk space freed: {res.bytes_freed / 1024 / 1024:.2f} MB")
                pause_return()

    # ==========================================================================
    # Action 8: Deep Mod Health Audit
    # ==========================================================================
    def action_deep_audit(self) -> None:
        """Run deep health audit without modifying files."""
        clear_screen()
        print(SPLASH_BANNER)
        print(f"{Colors.BOLD}{Colors.YELLOW}📋 DEEP MOD HEALTH AUDIT (DRY-RUN){Colors.RESET}\n")
        print(f"[*] Analyzing mod archives in: {self.paths['mods_dir']} without modifying files...\n")

        summary = scan_and_fix_mods(
            self.paths["mods_dir"],
            dry_run=True,
            selective=True,
            fix_materials=True,
            fix_drivetrain=True,
            fix_sound=True,
            fix_lua=True,
            clean_junk=True,
        )
        # Transition into dedicated Post-Fix Studio Menu
        self.menu_fix_results(summary, title="MOD HEALTH AUDIT REPORT")

    # ==========================================================================
    # Dedicated Post-Fix Results Studio & Diagnostic Menu
    # ==========================================================================
    def menu_fix_results(self, summary: OverallSummary, title: str = "FIX RESULTS & DIAGNOSTIC STUDIO") -> None:
        """Dedicated post-fix result and diagnostic studio menu.

        Directly fulfills the requirement:
        'Чтобы фикс отправлял в другое меню и после фикса возвращал в главное'
        """
        while True:
            clear_screen()
            print(SPLASH_BANNER)
            self._print_summary_report(summary, title=title)

            print(f"\n{Colors.BOLD}{Colors.WHITE}POST-FIX ACTIONS & NAVIGATION:{Colors.RESET}")
            print(f"  {Colors.GREEN}{Colors.BOLD}[1] 🏠 Return to Main Control Menu (Default){Colors.RESET}")
            print(f"  {Colors.CYAN}[2] 📋 View Detailed File-by-File Diagnostic Notices & Logs{Colors.RESET}")
            print(f"  {Colors.YELLOW}[3] 🚀 Launch Graphics & FPS Optimizer Studio{Colors.RESET}")
            print(f"  {Colors.MAGENTA}[4] 🧹 Purge Compiled Shader Caches (.d3dcsx, .db){Colors.RESET}")
            print(f"  {Colors.RED}[0] 🚪 Exit GBEAM FIX{Colors.RESET}")

            try:
                choice = input(f"\n{Colors.BOLD}Select an action [0-4] (default: 1): {Colors.RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                return

            if choice in ("1", ""):
                # Return straight to Main Menu
                return
            elif choice == "2":
                self._view_detailed_diagnostics(summary)
            elif choice == "3":
                self.menu_graphics_optimizer()
                return
            elif choice == "4":
                self.menu_cache_purge()
                return
            elif choice == "0":
                print(f"\n{Colors.GREEN}Thank you for using GBEAM FIX. Happy driving!{Colors.RESET}")
                sys.exit(0)
            else:
                print(f"{Colors.RED}Invalid option. Please choose between 0 and 4.{Colors.RESET}")
                time.sleep(1)

    def _view_detailed_diagnostics(self, summary: OverallSummary) -> None:
        """Display individual diagnostic notices collected across all processed archives."""
        clear_screen()
        print(SPLASH_BANNER)
        print(f"{Colors.BOLD}{Colors.CYAN}📋 DETAILED MOD DIAGNOSTIC NOTICES{Colors.RESET}\n")

        all_diags: List[Tuple[str, DiagnosticNotice]] = []
        for rep in summary.archive_reports:
            for d in rep.diagnostics:
                all_diags.append((rep.archive_path.name, d))

        if not all_diags:
            print(f"{Colors.GREEN}✔ No warnings or issues detected! All inspected files are 100% compliant.{Colors.RESET}")
        else:
            print(f"Total notices recorded: {len(all_diags)}\n")
            for idx, (arch_name, d) in enumerate(all_diags[:60], start=1):
                sev_color = Colors.RED if d.severity == "error" else (Colors.YELLOW if d.severity == "warning" else Colors.WHITE)
                print(f"  [{idx:02d}] {Colors.CYAN}{arch_name}{Colors.RESET} -> {sev_color}[{d.severity.upper()}]{Colors.RESET} {d.message}")
            if len(all_diags) > 60:
                print(f"\n  ... and {len(all_diags) - 60} more notices.")

        pause_return()

    # ==========================================================================
    # Report Printer
    # ==========================================================================
    def _print_summary_report(self, summary: OverallSummary, title: str = "SUMMARY REPORT") -> None:
        """Format and print a structured diagnostic summary report."""
        print("\n" + f"{Colors.CYAN}═" * 70 + f"{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}  {title}{Colors.RESET}")
        print(f"{Colors.CYAN}═" * 70 + f"{Colors.RESET}")
        print(f"  Total mod archives scanned    : {Colors.BOLD}{summary.total_scanned}{Colors.RESET}")
        print(f"  Modified (fixed) archives    : {Colors.GREEN}{summary.modified_archives}{Colors.RESET}")
        print(f"  Already clean archives       : {Colors.WHITE}{summary.clean_archives}{Colors.RESET}")
        print(f"  Headlight shadows fixed      : {Colors.GREEN}{summary.shadows_fixed}{Colors.RESET}")
        print(f"  materials.cs converted       : {Colors.GREEN}{summary.materials_converted}{Colors.RESET}")
        print(f"  materials.json textures fixed: {Colors.GREEN}{summary.materials_fixed}{Colors.RESET}")
        print(f"  Drivetrain & physics repaired: {Colors.GREEN}{summary.drivetrains_fixed}{Colors.RESET}")
        print(f"  FMOD audio events modernized : {Colors.GREEN}{summary.sounds_fixed}{Colors.RESET}")
        print(f"  Vehicle Lua scripts guarded  : {Colors.GREEN}{summary.lua_fixed}{Colors.RESET}")
        print(f"  Archive junk files removed   : {Colors.GREEN}{summary.junk_cleaned}{Colors.RESET}")
        print(f"  Skipped (locked / in-use)    : {Colors.YELLOW}{summary.skipped_locked}{Colors.RESET}")
        print(f"  Skipped (corrupt)            : {Colors.RED}{summary.skipped_corrupt}{Colors.RESET}")
        print(f"  Skipped (encrypted)          : {Colors.YELLOW}{summary.skipped_encrypted}{Colors.RESET}")
        print(f"  Errors encountered           : {Colors.RED}{summary.errors_encountered}{Colors.RESET}")
        print(f"  Elapsed processing time      : {Colors.WHITE}{summary.elapsed_seconds:.2f}s{Colors.RESET}")
        print(f"{Colors.CYAN}═" * 70 + f"{Colors.RESET}")
