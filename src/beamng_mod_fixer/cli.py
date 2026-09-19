"""Command-line interface (CLI) for GBEAM FIX: BeamNG Mod Fixer & Graphics Optimizer."""

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
from beamng_mod_fixer.core.path_resolver import (
    detect_beamng_user_dir,
    get_cache_config_path,
    resolve_beamng_paths,
    save_cached_paths,
)
from beamng_mod_fixer.core.mod_watcher import ModWatcher
from beamng_mod_fixer.core.reshade_manager import (
    deploy_all_reshade_presets,
    deploy_reshade_preset,
)
from beamng_mod_fixer.core.zip_processor import scan_and_fix_mods
from beamng_mod_fixer.i18n import set_language
from beamng_mod_fixer.models import ModStatus
from beamng_mod_fixer.ui import InteractiveCLI, print_splash_banner

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the GBEAM FIX CLI."""
    parser = argparse.ArgumentParser(
        prog="agy-gbeam-fix",
        description=(
            "GBEAM FIX — Ultimate Global Mod Fixer & Graphics Optimizer for BeamNG.drive:\n"
            "Automatically repair broken headlights, convert materials.cs to JSON 1.5, fix orange NO TEXTURE,\n"
            "repair frozen differentials/physics, modernize audio to FMOD, optimize graphics settings for 60+ FPS,\n"
            "and safely clean corrupted shader caches."
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
        "-u", "--user-dir",
        type=Path,
        default=None,
        help="Path to BeamNG root user directory (e.g. %%LOCALAPPDATA%%/BeamNG/BeamNG.drive/current).",
    )
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
    paths_group.add_argument(
        "--show-paths",
        action="store_true",
        help="Display detected BeamNG directories and exit.",
    )
    paths_group.add_argument(
        "--save-paths",
        action="store_true",
        help="Save the currently resolved paths (-u, -m, etc.) to persistent cache and exit.",
    )

    # Actions
    actions_group = parser.add_argument_group("Actions")
    actions_group.add_argument(
        "--fix-mods",
        action="store_true",
        help="Scan and fix broken headlights (lightCastShadows) and optics in mod archives.",
    )
    actions_group.add_argument(
        "--fix-rear-lights",
        action="store_true",
        help="Enhance rear lights (reverse, brake, tail lights) to brightly illuminate the road/ground.",
    )
    actions_group.add_argument(
        "--fix-materials",
        action="store_true",
        help="Convert materials.cs to modern JSON 1.5 and repair texture paths (fix NO TEXTURE).",
    )
    actions_group.add_argument(
        "--fix-drivetrain",
        action="store_true",
        help="Repair broken differentials (prevent physics freeze/explosion) and tire pressures.",
    )
    actions_group.add_argument(
        "--fix-sound",
        action="store_true",
        help="Modernize pre-FMOD audio paths to official BeamNG FMOD events.",
    )
    actions_group.add_argument(
        "--fix-lua",
        action="store_true",
        help="Guard deprecated vehicle Lua calls (prevent fatal script crashes on spawn).",
    )
    actions_group.add_argument(
        "--optimize-graphics",
        action="store_true",
        help="Deploy high-performance graphics preset to BeamNG settings (fast reflections, soft shadows).",
    )
    actions_group.add_argument(
        "--clean-cache",
        action="store_true",
        help="Safely purge compiled DirectX/Vulkan shader binaries (.d3dcsx, .db) in temp/.",
    )
    actions_group.add_argument(
        "-a", "--all", "--global-fix",
        dest="all",
        action="store_true",
        help="1-Click Global Fix: Execute all repair actions and optimize graphics + clean cache.",
    )
    actions_group.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Launch background Downloads watcher to automatically install and repair newly downloaded mods.",
    )
    actions_group.add_argument(
        "--deploy-reshade",
        action="store_true",
        help="Deploy tailored ReShade preset configurations (.ini) into BeamNG directory.",
    )
    actions_group.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch the interactive hierarchical terminal UI menu.",
    )

    # Options
    options_group = parser.add_argument_group("Options")
    options_group.add_argument(
        "--preset",
        choices=list(OPTIMIZATION_PRESETS.keys()),
        default="ultra-max-fps",
        help="Graphics optimization preset (default: %(default)s).",
    )
    options_group.add_argument(
        "--lang",
        choices=["ru", "en"],
        default=None,
        help="Set user interface language ('ru' or 'en').",
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
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    # Logging setup
    log_level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Resolve active paths
    paths = resolve_beamng_paths(
        user_dir=args.user_dir,
        mods_dir=args.mods_dir,
        settings_dir=args.settings_dir,
        cache_dir=args.cache_dir,
    )

    mods_dir = paths["mods_dir"]
    settings_dir = paths["settings_dir"]
    cache_dir = paths["cache_dir"]

    if args.save_paths:
        saved = save_cached_paths(paths, force=True)
        if saved:
            print(f"Successfully saved active paths to persistent cache ({get_cache_config_path()}).")
            return 0
        else:
            logger.error("Failed saving active paths to persistent cache.")
            return 1

    if args.show_paths:
        print("Detected BeamNG.drive Paths:")
        print(f"  User Directory : {paths['user_dir']}")
        print(f"  Mods Directory : {paths['mods_dir']}")
        print(f"  Settings Dir   : {paths['settings_dir']}")
        print(f"  Cache/Temp Dir : {paths['cache_dir']}")
        user_ok = "✔ [FOUND]" if paths['user_dir'].exists() else "❌ [NOT FOUND]"
        mods_ok = "✔ [FOUND]" if paths['mods_dir'].exists() else "❌ [NOT FOUND]"
        mod_count = 0
        if paths['mods_dir'].exists() and paths['mods_dir'].is_dir():
            try:
                mod_count = len([p for p in paths['mods_dir'].iterdir() if p.is_file() and p.suffix.lower() == ".zip"])
            except OSError:
                pass
        cache_file = get_cache_config_path()
        cache_info = f"Active ({cache_file})" if cache_file.exists() else "Not cached"
        print(f"  Status         : User Dir {user_ok}, Mods Dir {mods_ok} ({mod_count} mod archives detected)")
        print(f"  Path Cache     : {cache_info}")
        return 0

    if args.lang:
        set_language(args.lang)

    # Determine actions
    has_specific_action = (
        args.fix_mods
        or args.fix_rear_lights
        or args.fix_materials
        or args.fix_drivetrain
        or args.fix_sound
        or args.fix_lua
        or args.optimize_graphics
        or args.clean_cache
        or args.all
        or args.watch
        or args.deploy_reshade
    )

    if args.deploy_reshade:
        if not args.quiet:
            print_splash_banner()
            print(f"[*] Deploying tailored ReShade presets (.ini) into: {settings_dir}")
        deployed = deploy_all_reshade_presets(settings_dir, dry_run=args.dry_run)
        if paths.get("user_dir") and paths["user_dir"] != settings_dir:
            deploy_all_reshade_presets(paths["user_dir"], dry_run=args.dry_run)
        if not args.quiet:
            print(f"  ✔ Successfully deployed {len(deployed)} ReShade presets:")
            for p in deployed:
                print(f"    - {p.name}")
        else:
            print(f"ReShade presets deployed: {len(deployed)}")
        return 0

    if args.watch:
        if not args.quiet:
            print_splash_banner()
            print("[*] Launching Mod Auto-Installer watching Downloads folder...")
            print(f"    Mods target directory: {mods_dir}")
            print("    Press Ctrl+C to stop.\n")
        watcher = ModWatcher(mods_dir=mods_dir)
        watcher.start()
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            if not args.quiet:
                print("\n[*] Mod Auto-Installer stopped cleanly.")
            return 0

    # Launch interactive menu if requested or if interactive terminal with no specific actions
    if args.interactive or (not has_specific_action and sys.stdin.isatty()):
        ui = InteractiveCLI(paths=paths, dry_run=args.dry_run)
        return ui.run_main_menu()

    if not args.quiet:
        print_splash_banner()

    run_mods = args.fix_mods or args.all or not has_specific_action
    run_rear_lights = args.fix_rear_lights or args.all or not has_specific_action
    run_materials = args.fix_materials or args.all or not has_specific_action
    run_drivetrain = args.fix_drivetrain or args.all or not has_specific_action
    run_sound = args.fix_sound or args.all or not has_specific_action
    run_lua = args.fix_lua or args.all or not has_specific_action
    run_graphics = args.optimize_graphics or args.all or not has_specific_action
    run_cache = args.clean_cache or args.all or not has_specific_action
    selective_fix = (args.mode == "smart")

    dry_run_tag = " [DRY RUN]" if args.dry_run else ""
    success = True

    # Action 1: Mod Scanning & Multi-Domain Repair
    if run_mods or run_rear_lights or run_materials or run_drivetrain or run_sound or run_lua:
        mode_tag = " (smart selective)" if selective_fix else " (legacy)"
        if not args.quiet:
            print(f"\n[*] Scanning & fixing mods in: {mods_dir}{mode_tag}{dry_run_tag}")
        try:
            summary = scan_and_fix_mods(
                mods_dir,
                dry_run=args.dry_run,
                selective=selective_fix,
                fix_rear_lights=run_rear_lights,
                fix_materials=run_materials,
                fix_drivetrain=run_drivetrain,
                fix_sound=run_sound,
                fix_lua=run_lua,
                clean_junk=True,
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
                print("\n" + "=" * 60)
                print(f"MOD SCAN & REPAIR SUMMARY{dry_run_tag}")
                print("=" * 60)
                print(f"  Total mod archives scanned  : {summary.total_scanned}")
                print(f"  Modified (fixed) archives : {summary.modified_archives}")
                print(f"  Already clean archives    : {summary.clean_archives}")
                print(f"  JBeam files inspected     : {summary.jbeams_inspected}")
                print(f"  JBeam files modified      : {summary.jbeams_fixed}")
                print(f"  Headlight shadows fixed   : {summary.shadows_fixed}")
                print(f"  Rear lights enhanced      : {summary.rear_lights_fixed}")
                print(f"  materials.cs converted    : {summary.materials_converted}")
                print(f"  materials.json repaired   : {summary.materials_fixed}")
                print(f"  Drivetrain & diff repaired: {summary.drivetrains_fixed}")
                print(f"  FMOD audio modernized     : {summary.sounds_fixed}")
                print(f"  Vehicle Lua guarded       : {summary.lua_fixed}")
                print(f"  Archive junk removed      : {summary.junk_cleaned}")
                print(f"  Skipped (locked/in-use)   : {summary.skipped_locked}")
                print(f"  Skipped (corrupt)         : {summary.skipped_corrupt}")
                print(f"  Skipped (encrypted)       : {summary.skipped_encrypted}")
                print(f"  Errors encountered        : {summary.errors_encountered}")
                print(f"  Elapsed time              : {summary.elapsed_seconds:.2f}s")
                print("=" * 60)
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

            # Deploy matching ReShade preset
            reshade_map = {
                "ultra-max-fps": "ultra-photoreal",
                "medium-60fps": "medium-optimal",
                "low-weak": "low-fast",
                "potato-ultra-weak": "potato-boost",
            }
            rk = reshade_map.get(args.preset)
            if rk:
                deploy_reshade_preset(settings_dir, preset_name=rk, dry_run=args.dry_run)
                if paths.get("user_dir") and paths["user_dir"] != settings_dir:
                    deploy_reshade_preset(paths["user_dir"], preset_name=rk, dry_run=args.dry_run)
                if not args.quiet:
                    print(f"  ReShade preset      : Deployed matching '{rk}' (.ini)")

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
