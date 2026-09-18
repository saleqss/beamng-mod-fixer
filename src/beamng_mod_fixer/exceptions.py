"""Typed exception hierarchy for BeamNG Mod Fixer & Graphics Optimizer."""

from typing import Optional


class BeamNGModFixerError(Exception):
    """Base exception for all errors within the beamng_mod_fixer package."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


# Archive related exceptions
class ModArchiveError(BeamNGModFixerError):
    """Base exception for failures involving mod archive (.zip) manipulation."""


class CorruptArchiveError(ModArchiveError):
    """Raised when an archive is corrupted, truncated, or has an invalid ZIP structure."""


# Alias for CorruptArchiveError for compatibility
ArchiveCorruptedError = CorruptArchiveError


class ArchiveLockedError(ModArchiveError):
    """Raised when an archive file is locked by the game or another process (e.g. WinError 32)."""


class PasswordProtectedArchiveError(ModArchiveError):
    """Raised when an archive contains password-protected or encrypted entries."""


# Alias for PasswordProtectedArchiveError for compatibility
ArchiveEncryptedError = PasswordProtectedArchiveError


class ArchivePermissionError(ModArchiveError):
    """Raised when an archive cannot be accessed due to OS permission restrictions."""


# JBeam related exceptions and warnings
class JBeamError(BeamNGModFixerError):
    """Base exception for failures involving JBeam parsing or patching."""


class JBeamSyntaxError(JBeamError):
    """Raised when a JBeam file contains irrecoverably corrupted syntax."""


class JBeamSyntaxWarning(UserWarning, BeamNGModFixerError):
    """Warning emitted when a JBeam file contains syntax anomalies that were safely handled."""


class EncryptedArchiveWarning(UserWarning, BeamNGModFixerError):
    """Warning emitted when skipping an encrypted archive."""


# Settings and Configuration exceptions
class SettingsError(BeamNGModFixerError):
    """Base exception for failures modifying BeamNG settings."""


class SettingsNotFoundError(SettingsError):
    """Raised when settings.json or game-settings.json cannot be found in the target directory."""


class SettingsCorruptedError(SettingsError):
    """Raised when settings.json exists but contains invalid or unparseable JSON."""


# Environment and Path exceptions
class BeamNGPathNotFoundError(BeamNGModFixerError):
    """Raised when BeamNG user directory or mods folder cannot be located."""


# Cache cleaner exceptions
class CacheCleanError(BeamNGModFixerError):
    """Raised when cache cleaning fails or encounters a safety guardrail violation."""


# Process warnings
class GameRunningWarning(UserWarning):
    """Warning emitted when BeamNG.drive executable is detected running during operations."""
