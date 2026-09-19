"""Core engine modules for GBEAM FIX."""

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
from beamng_mod_fixer.core.path_resolver import detect_beamng_user_dir, resolve_beamng_paths
from beamng_mod_fixer.core.sound_fixer import fix_sound_content
from beamng_mod_fixer.core.zip_processor import is_archive_encrypted, process_mod_archive, scan_and_fix_mods

__all__ = [
    "audit_spotlights",
    "clean_shader_cache",
    "convert_materials_cs_to_json",
    "decode_jbeam_bytes",
    "detect_beamng_user_dir",
    "detect_light_cast_shadows",
    "encode_jbeam_str",
    "fix_drivetrain_content",
    "fix_jbeam_content",
    "fix_lua_content",
    "fix_materials_json_content",
    "fix_sound_content",
    "is_archive_encrypted",
    "OPTIMIZATION_PRESETS",
    "optimize_settings",
    "parse_materials_cs",
    "patch_jbeam_text",
    "process_mod_archive",
    "resolve_beamng_paths",
    "restore_settings_backup",
    "scan_and_fix_mods",
    "smart_fix_jbeam_content",
]
