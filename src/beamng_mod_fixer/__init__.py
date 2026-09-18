"""BeamNG.drive Mod Fixer, Headlight Restorer & Graphics Optimizer.

A high-performance Python utility and engine for BeamNG.drive that fixes
broken headlights caused by PBR self-shadow occlusion (lightCastShadows: false),
diagnoses optics/spotlights defects, deploys optimal graphics settings, and cleans
shader caches.
"""

__version__ = "1.0.0"
__author__ = "BeamNG Modding Tools Team"

from beamng_mod_fixer.core.jbeam_fixer import (
    audit_spotlights,
    decode_jbeam_bytes,
    detect_light_cast_shadows,
    encode_jbeam_str,
    fix_jbeam_content,
    patch_jbeam_text,
)
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

__all__ = [
    "__version__",
    "__author__",
    # Core Fixer APIs
    "fix_jbeam_content",
    "patch_jbeam_text",
    "detect_light_cast_shadows",
    "audit_spotlights",
    "decode_jbeam_bytes",
    "encode_jbeam_str",
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
