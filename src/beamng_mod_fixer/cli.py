"""Command-line interface (CLI) for BeamNG Mod Fixer & Graphics Optimizer."""

import argparse
import logging
from pathlib import Path
import sys
from typing import List, Optional

from beamng_mod_fixer import __version__
from beamng_mod_fixer.core.cache_cleaner import clean_shader_cache
from beamng_mod_fixer.core.graphics_optimizer import (
    OPTIMIZATION_PRESETS,
    optimize_settings,
)
from beamng_mod_fixer.core.path_resolver import detect_beamng_user_dir, resolve_beamng_paths
from beamng_mod_fixer.core.zip_processor import scan_and_fix_mods
from beamng_mod_fixer.models import ModStatus

logger = logging.getLogger(__name__)

BANNER = r"""
======================================================================
  ____  _____    _    __  __ _   _  ____      ____  ____  _____     __
 | __ )| ____|  / \  |  \/  | \ | |/ ___|    |  _ \|  _ \|_ _\ \   / /
 |  _ \|  _|   / _ \ | |\/| |  \| | |  _ ____| | | | |_) || | \ \ / / 
 | |_) | |___ / ___ \| |  | | |\  | |_| |____| |_| |  _ < | |  \ V /  
 |____/|_____/_/   \_\_|  |_|_| \_|\____|    |____/|_| \_\___|  \_/   
             Mod Headlight Fixer & Graphics Optimizer v{version}
======================================================================
""".format(version=__version__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the BeamNG Mod Fixer CLI."""
    parser = argparse.ArgumentParser(
        prog="beamng-mod-fixer",
        description=(
            "BeamNG.drive Mod Headlight Fixer & Graphics Optimizer: "
            "Automatically fix broken headlights (lightCastShadows) in mod ZIP archives, "
            "optimize graphics settings for high FPS, and safely clean shader caches."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Display application version and exit.",
    )

    # Path overrides
    paths_group = parser.add_argument_group("Path Configuration")
    paths_group.add_argument(
        "-m", "--mods-dir",
        type=Path,
        default=None,
        help="Path to BeamNG mods directory (e.g. %%LOCALAPPDATA%%/BeamNG/BeamNG.drive/current/mods).",
    )
    paths_group.add_argument(
        "-s", "--settings-dir",
        type=Path,
        default=None,
        help="Path to BeamNG settings directory (contains settings.json, game-settings.json).",
    )
    paths_group.add_argument(
        "-c", "--cache-dir",
        type=Path,
        default=None,
        help="Path to BeamNG temporary cache directory (temp/ or cache/).",
    )

    # Actions
    actions_group = parser.add_argument_group("Actions")
    actions_group.add_argument(
        "--fix-mods",
        action="store_true",
        help="Scan and fix broken headlights (lightCastShadows: true -> false) in mod archives.",
    )
    actions_group.add_argument(
        "--optimize-graphics",
        action="store_true",
        help="Deploy balanced high-performance graphics preset to BeamNG settings.",
    )
    actions_group.add_argument(
        "--clean-cache",
        action="store_true",
        help="Safely purge compiled DirectX/Vulkan shader binaries (.d3dcsx, .db) in temp/.",
    )
    actions_group.add_argument(
        "-a", "--all",
        action="store_true",
        help="Execute all actions: fix mods, optimize graphics, and clean shader cache.",
    )

    # Options
    options_group = parser.add_argument_group("Options")
    options_group.add_argument(
        "--preset",
        choices=list(OPTIMIZATION_PRESETS.keys()),
        default="balanced",
        help="Graphics optimization preset (default: %(default)s).",
    )
    options_group.add_argument(
        "--mode",
        choices=["smart", "legacy"],
        default="smart",
        help="Fixing mode: 'smart' selectively fixes lowbeams and modernizes cookies/flares while preserving highbeam shadows; 'legacy' forces lightCastShadows: false everywhere (default: %(default)s).",
    )
    options_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions and output metrics without modifying files on disk.",
    )
    options_group.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .bak settings backups during graphics optimization.",
    )
    options_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress banner and decorative output; print minimal summary.",
    )
    options_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed diagnostic and debug logging.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Logging setup
    log_level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not args.quiet:
        print(BANNER)

    # Resolve active paths
    paths = resolve_beamng_paths(
        mods_dir=args.mods_dir,
        settings_dir=args.settings_dir,
        cache_dir=args.cache_dir,
    )

    mods_dir = paths["mods_dir"]
    settings_dir = paths["settings_dir"]
    cache_dir = paths["cache_dir"]

    # Determine actions to run
    run_mods = args.fix_mods or args.all
    run_graphics = args.optimize_graphics or args.all
    run_cache = args.clean_cache or args.all
    selective_fix = (args.mode == "smart")

    # If no specific action was requested and running interactively, ask or default to --all
    if not (run_mods or run_graphics or run_cache):
        if sys.stdin.isatty():
            detected = detect_beamng_user_dir()
            print(f"Detected BeamNG User Directory: {detected or 'Not found (using defaults)'}")
            print("\nSelect an action to perform:")
            print("  1) Smart Fix: Fix broken headlights selectively (recommended — preserves highbeams & modernizes cookies)")
            print("  2) Legacy Fix: Convert all lightCastShadows to false everywhere")
            print("  3) Optimize graphics settings (high FPS + crisp visuals)")
            print("  4) Clean shader and texture cache")
            print("  5) Perform ALL actions (Smart Fix + Optimize + Clean cache)")
            print("  6) Exit")
            try:
                choice = input("\nEnter choice [1-6] (default: 5): ").strip()
                if choice == "1":
                    run_mods = True
                    selective_fix = True
                elif choice == "2":
                    run_mods = True
                    selective_fix = False
                elif choice == "3":
                    run_graphics = True
                elif choice == "4":
                    run_cache = True
                elif choice in ("5", ""):
                    run_mods = True
                    selective_fix = True
                    run_graphics = True
                    run_cache = True
                else:
                    print("Exiting.")
                    return 0
            except (KeyboardInterrupt, EOFError):
                print("\nAborted by user.")
                return 0
        else:
            # Non-interactive without action flags: default to all with smart mode
            run_mods = True
            run_graphics = True
            run_cache = True
            selective_fix = True

    dry_run_tag = " [DRY RUN]" if args.dry_run else ""
    success = True

    # Action 1: Fix mods
    if run_mods:
        mode_tag = " (smart selective)" if selective_fix else " (legacy)"
        if not args.quiet:
            print(f"\n[*] Scanning and fixing mods in: {mods_dir}{mode_tag}{dry_run_tag}")
        try:
            summary = scan_and_fix_mods(
                mods_dir,
                dry_run=args.dry_run,
                selective=selective_fix,
                progress_callback=(
                    None
                    if args.quiet
                    else (
                        lambda p, r, idx, tot: (
                            print(f"  [{idx}/{tot}] {p.name}: {r.status.upper()}" + (f" ({r.jbeams_modified} jbeams fixed)" if r.jbeams_modified else ""))
                            if r.status == ModStatus.FIXED.value or r.status == ModStatus.ERROR.value
                            else None
                        )
                    )
                ),
            )
            if not args.quiet:
                print("\n" + "=" * 50)
                print(f"MOD SCAN SUMMARY{dry_run_tag}")
                print("=" * 50)
                print(f"  Total mod archives scanned : {summary.total_scanned}")
                print(f"  Modified (fixed) archives : {summary.modified_archives}")
                print(f"  Already clean archives    : {summary.clean_archives}")
                print(f"  JBeam files inspected     : {summary.jbeams_inspected}")
                print(f"  JBeam files modified      : {summary.jbeams_fixed}")
                print(f"  Headlight shadows fixed   : {summary.shadows_fixed}")
                print(f"  Skipped (locked/in-use)   : {summary.skipped_locked}")
                print(f"  Skipped (corrupt)         : {summary.skipped_corrupt}")
                print(f"  Skipped (encrypted)       : {summary.skipped_encrypted}")
                print(f"  Errors encountered        : {summary.errors_encountered}")
                print(f"  Elapsed time              : {summary.elapsed_seconds:.2f}s")
                print("=" * 50)
            else:
                print(f"Mods fixed: {summary.modified_archives}/{summary.total_scanned}, JBeams fixed: {summary.jbeams_fixed}")
        except Exception as e:
            logger.error("Error processing mods directory '%s': %s", mods_dir, e)
            success = False

    # Action 2: Optimize graphics
    if run_graphics:
        if not args.quiet:
            print(f"\n[*] Deploying graphics optimization in: {settings_dir}{dry_run_tag}")
        try:
            opt_res = optimize_settings(
                settings_dir,
                preset=args.preset,
                backup=not args.no_backup,
                dry_run=args.dry_run,
            )
            if not args.quiet:
                print(f"  Optimization status : {'SUCCESS' if opt_res.success else 'FAILED'}")
                print(f"  Preset applied      : {opt_res.preset_name}")
                if opt_res.backup_created:
                    print(f"  Settings backup     : {opt_res.backup_path}")
                print(f"  Settings keys tuned : {len(opt_res.applied_keys)}")
            else:
                print(f"Graphics optimized: preset={opt_res.preset_name}, keys={len(opt_res.applied_keys)}")
            if not opt_res.success:
                success = False
        except Exception as e:
            logger.error("Error optimizing graphics in '%s': %s", settings_dir, e)
            success = False

    # Action 3: Clean cache
    if run_cache:
        if not args.quiet:
            print(f"\n[*] Cleaning temporary shader caches in: {cache_dir}{dry_run_tag}")
        try:
            clean_res = clean_shader_cache(cache_dir, dry_run=args.dry_run)
            if not args.quiet:
                print(f"  Cache clean status  : {'SUCCESS' if clean_res.success else 'FAILED'}")
                print(f"  Files removed       : {clean_res.files_deleted}")
                print(f"  Disk space freed    : {clean_res.bytes_freed / 1024 / 1024:.2f} MB")
            else:
                print(f"Cache cleared: files={clean_res.files_deleted}, freed={clean_res.bytes_freed}B")
            if not clean_res.success:
                success = False
        except Exception as e:
            logger.error("Error cleaning cache in '%s': %s", cache_dir, e)
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
