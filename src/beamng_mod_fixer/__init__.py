"""GBEAM FIX: BeamNG.drive Mod Fixer, Headlight Restorer & Graphics Optimizer.

A high-performance Python utility and community engine for BeamNG.drive that fixes:
- Broken headlights and optics (PBR self-shadow occlusion, inverted angles, flares/cookies)
- Legacy materials.cs converted to modern main.materials.json 1.5 PBR
- Orange 'NO TEXTURE' and broken VFS texture paths
- Differential freeze and physics explosions, tire pressures and friction
- Obsolete audio paths modernized to BeamNG FMOD sound events
- Deprecated vehicle Lua scripts guarded against fatal spawn crashes
- 60FPS fast reflections, soft shadows, and shader cache cleaning
"""

__version__ = "1.3.0"
__author__ = "BeamNG Modding Tools Team"

from beamng_mod_fixer.core.cache_cleaner import clean_shader_cache
from beamng_mod_fixer.core.drivetrain_fixer import fix_drivetrain_content
from beamng_mod_fixer.core.graphics_optimizer import (
    OPTIMIZATION_PRESETS,
    optimize_settings,
    restore_settings_backup,
)
from beamng_mod_fixer.core.jbeam_fixer import (
    audit_spotlights,
    decode_jbeam_bytes,
    detect_light_cast_shadows,
    encode_jbeam_str,
    fix_jbeam_content,
    patch_jbeam_text,
    smart_fix_jbeam_content,
)
from beamng_mod_fixer.core.lua_fixer import fix_lua_content
from beamng_mod_fixer.core.materials_fixer import (
    convert_materials_cs_to_json,
    fix_materials_json_content,
    parse_materials_cs,
)
from beamng_mod_fixer.core.mod_watcher import ModWatcher
from beamng_mod_fixer.core.path_resolver import (
    clear_cached_paths,
    detect_beamng_user_dir,
    find_candidate_user_dirs,
    find_drive_root_candidates,
    find_steam_beamng_dirs,
    get_cache_config_path,
    load_cached_paths,
    resolve_beamng_paths,
    save_cached_paths,
    score_candidate_user_dir,
    validate_beamng_dir,
)
from beamng_mod_fixer.core.rear_light_fixer import enhance_rear_light_content
from beamng_mod_fixer.core.sound_fixer import fix_sound_content
from beamng_mod_fixer.core.zip_processor import is_archive_encrypted, process_mod_archive, scan_and_fix_mods
from beamng_mod_fixer.exceptions import (
    ArchiveCorruptedError,
    ArchiveEncryptedError,
    ArchiveLockedError,
    ArchivePermissionError,
    BeamNGModFixerError,
    BeamNGPathNotFoundError,
    CacheCleanError,
    CorruptArchiveError,
    EncryptedArchiveWarning,
    GameRunningWarning,
    JBeamError,
    JBeamSyntaxError,
    JBeamSyntaxWarning,
    ModArchiveError,
    PasswordProtectedArchiveError,
    SettingsCorruptedError,
    SettingsError,
    SettingsNotFoundError,
)
from beamng_mod_fixer.models import (
    CacheCleanResult,
    DiagnosticNotice,
    JBeamFixResult,
    JBeamPatchResult,
    ModArchiveReport,
    ModProcessResult,
    ModStatus,
    OptimizationResult,
    OverallSummary,
    SettingsUpdateResult,
    SummaryMetrics,
)
from beamng_mod_fixer.ui import InteractiveCLI

__all__ = [
    "__version__",
    "__author__",
    # Core Fixer APIs
    "fix_jbeam_content",
    "smart_fix_jbeam_content",
    "enhance_rear_light_content",
    "patch_jbeam_text",
    "detect_light_cast_shadows",
    "audit_spotlights",
    "decode_jbeam_bytes",
    "encode_jbeam_str",
    "convert_materials_cs_to_json",
    "fix_materials_json_content",
    "parse_materials_cs",
    "fix_drivetrain_content",
    "fix_sound_content",
    "fix_lua_content",
    "process_mod_archive",
    "scan_and_fix_mods",
    "clean_shader_cache",
    "clear_cached_paths",
    "detect_beamng_user_dir",
    "find_candidate_user_dirs",
    "find_drive_root_candidates",
    "find_steam_beamng_dirs",
    "get_cache_config_path",
    "load_cached_paths",
    "optimize_settings",
    "restore_settings_backup",
    "resolve_beamng_paths",
    "save_cached_paths",
    "score_candidate_user_dir",
    "validate_beamng_dir",
    "is_archive_encrypted",
    "OPTIMIZATION_PRESETS",
    "InteractiveCLI",
    # Exceptions
    "BeamNGModFixerError",
    "ModArchiveError",
    "CorruptArchiveError",
    "ArchiveCorruptedError",
    "ArchiveLockedError",
    "PasswordProtectedArchiveError",
    "ArchiveEncryptedError",
    "ArchivePermissionError",
    "JBeamError",
    "JBeamSyntaxError",
    "JBeamSyntaxWarning",
    "EncryptedArchiveWarning",
    "SettingsError",
    "SettingsNotFoundError",
    "SettingsCorruptedError",
    "BeamNGPathNotFoundError",
    "CacheCleanError",
    "GameRunningWarning",
    # Models
    "ModStatus",
    "DiagnosticNotice",
    "JBeamFixResult",
    "JBeamPatchResult",
    "ModArchiveReport",
    "ModProcessResult",
    "OptimizationResult",
    "SettingsUpdateResult",
    "CacheCleanResult",
    "OverallSummary",
    "SummaryMetrics",
]
