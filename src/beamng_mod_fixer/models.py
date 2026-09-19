"""Data models for BeamNG Mod Fixer & Graphics Optimizer."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModStatus(str, Enum):
    """Status enumeration for processed mod archives."""

    FIXED = "fixed"
    CLEAN = "clean"
    LOCKED = "locked"
    CORRUPT = "corrupt"
    ENCRYPTED = "encrypted"
    ERROR = "error"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value


@dataclass
class DiagnosticNotice:
    """Represents a diagnostic notice, warning, or fix action taken on JBeam/Optics."""

    severity: str  # "info", "warning", "error"
    message: str
    file_path: str = ""
    line_number: Optional[int] = None
    rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostic notice to a dictionary representation."""
        return asdict(self)


@dataclass
class JBeamFixResult:
    """Result of patching a single JBeam file."""

    content: str
    fix_count: int
    diagnostics: List[DiagnosticNotice] = field(default_factory=list)
    modified: bool = False

    def __post_init__(self) -> None:
        if self.fix_count > 0 or any(
            "Normalized" in d.message or d.rule.endswith("_normalized")
            for d in self.diagnostics
        ):
            self.modified = True

    @property
    def has_fixes(self) -> bool:
        """Return True if any fixes or normalizations were applied."""
        return self.modified or self.fix_count > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert fix result to a dictionary representation."""
        return {
            "fix_count": self.fix_count,
            "modified": self.modified,
            "has_fixes": self.has_fixes,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class ModArchiveReport:
    """Report for an individual mod archive scan and processing."""

    archive_path: Path
    status: str = ModStatus.CLEAN.value  # "fixed", "clean", "locked", "corrupt", "encrypted", "error", "skipped"
    jbeams_inspected: int = 0
    jbeams_modified: int = 0
    shadows_fixed: int = 0
    materials_converted: int = 0
    materials_fixed: int = 0
    drivetrains_fixed: int = 0
    sounds_fixed: int = 0
    lua_fixed: int = 0
    junk_cleaned: int = 0
    diagnostics: List[DiagnosticNotice] = field(default_factory=list)
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        """Return True if the archive was processed without fatal archive errors."""
        return self.status in (ModStatus.FIXED.value, ModStatus.CLEAN.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert archive report to a dictionary representation."""
        return {
            "archive_path": str(self.archive_path),
            "status": str(self.status),
            "jbeams_inspected": self.jbeams_inspected,
            "jbeams_modified": self.jbeams_modified,
            "shadows_fixed": self.shadows_fixed,
            "materials_converted": self.materials_converted,
            "materials_fixed": self.materials_fixed,
            "drivetrains_fixed": self.drivetrains_fixed,
            "sounds_fixed": self.sounds_fixed,
            "lua_fixed": self.lua_fixed,
            "junk_cleaned": self.junk_cleaned,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "error_message": self.error_message,
            "elapsed_seconds": self.elapsed_seconds,
        }


@dataclass
class OptimizationResult:
    """Result of applying graphics optimization presets to BeamNG settings."""

    backup_created: bool = False
    backup_path: Optional[Path] = None
    applied_keys: Dict[str, Any] = field(default_factory=dict)
    preset_name: str = "balanced"
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert optimization result to a dictionary representation."""
        return {
            "backup_created": self.backup_created,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "applied_keys": self.applied_keys,
            "preset_name": self.preset_name,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class CacheCleanResult:
    """Result of clearing shader and temporary caches."""

    files_deleted: int = 0
    bytes_freed: int = 0
    directories_cleaned: List[Path] = field(default_factory=list)
    skipped_files: List[Path] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache clean result to a dictionary representation."""
        return {
            "files_deleted": self.files_deleted,
            "bytes_freed": self.bytes_freed,
            "directories_cleaned": [str(p) for p in self.directories_cleaned],
            "skipped_files": [str(p) for p in self.skipped_files],
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class OverallSummary:
    """Comprehensive summary of all operations performed across a run."""

    total_scanned: int = 0
    modified_archives: int = 0
    clean_archives: int = 0
    jbeams_inspected: int = 0
    jbeams_fixed: int = 0
    shadows_fixed: int = 0
    materials_converted: int = 0
    materials_fixed: int = 0
    drivetrains_fixed: int = 0
    sounds_fixed: int = 0
    lua_fixed: int = 0
    junk_cleaned: int = 0
    skipped_locked: int = 0
    skipped_corrupt: int = 0
    skipped_encrypted: int = 0
    errors_encountered: int = 0
    graphics_optimized: bool = False
    cache_cleared: bool = False
    bytes_freed: int = 0
    elapsed_seconds: float = 0.0
    archive_reports: List[ModArchiveReport] = field(default_factory=list)

    @property
    def total_skipped(self) -> int:
        """Total number of archives skipped due to locks, corruptions, or passwords."""
        return self.skipped_locked + self.skipped_corrupt + self.skipped_encrypted

    def to_dict(self) -> Dict[str, Any]:
        """Convert overall summary to a dictionary representation."""
        return {
            "total_scanned": self.total_scanned,
            "modified_archives": self.modified_archives,
            "clean_archives": self.clean_archives,
            "jbeams_inspected": self.jbeams_inspected,
            "jbeams_fixed": self.jbeams_fixed,
            "shadows_fixed": self.shadows_fixed,
            "materials_converted": self.materials_converted,
            "materials_fixed": self.materials_fixed,
            "drivetrains_fixed": self.drivetrains_fixed,
            "sounds_fixed": self.sounds_fixed,
            "lua_fixed": self.lua_fixed,
            "junk_cleaned": self.junk_cleaned,
            "skipped_locked": self.skipped_locked,
            "skipped_corrupt": self.skipped_corrupt,
            "skipped_encrypted": self.skipped_encrypted,
            "errors_encountered": self.errors_encountered,
            "graphics_optimized": self.graphics_optimized,
            "cache_cleared": self.cache_cleared,
            "bytes_freed": self.bytes_freed,
            "elapsed_seconds": self.elapsed_seconds,
            "archive_reports": [r.to_dict() for r in self.archive_reports],
        }


# Type aliases for compatibility across different module versions
SummaryMetrics = OverallSummary
JBeamPatchResult = JBeamFixResult
ModProcessResult = ModArchiveReport
SettingsUpdateResult = OptimizationResult
