"""Safe cache and compiled shader cleaning engine for BeamNG.drive.

Provides:
- Purging of compiled DirectX 11, DirectX 12, and Vulkan shader binaries (.d3dcsx, .db) in temp/shaders/
- Purging of temporary vehicle AST and animation caches (.cani, collision binaries) in temp/vehicles/
- Purging of temporary art, UI, and font caches in temp/
- Strict safety guardrails: refusing to delete anything outside of temp/
- Absolute protection of mods/, settings/, screenshots/, and user configurations (vehicles/*.pc)
- Dry-run mode for previewing deletion statistics with zero disk side-effects
- Graceful handling of locked files (e.g. game running)
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from beamng_mod_fixer.exceptions import CacheCleanError
from beamng_mod_fixer.models import CacheCleanResult

logger = logging.getLogger(__name__)

# Provide alias property on CacheCleanResult if directories_cleared is accessed
if not hasattr(CacheCleanResult, "directories_cleared"):
    CacheCleanResult.directories_cleared = property(
        lambda self: self.directories_cleaned
    )


def _resolve_temp_directory(path: Path) -> Path:
    """Resolve and validate the BeamNG temp cache directory from a given path.

    Args:
        path: Path to BeamNG user folder or direct temp/ cache directory.

    Returns:
        Validated Path to the temp directory.

    Raises:
        CacheCleanError: If the path does not contain or point to a temp directory.
    """
    path_name = path.name.lower()

    # Case 1: Direct path to temp or cache directory
    if path_name in ("temp", "cache") or any(
        path_name.startswith(p) for p in ("temp", "cache.", "cache_")
    ):
        target_temp = path
    # Case 2: User directory containing a temp/ or cache/ subdirectory
    elif (path / "temp").exists() and (path / "temp").is_dir():
        target_temp = path / "temp"
    elif (path / "cache").exists() and (path / "cache").is_dir():
        target_temp = path / "cache"
    elif any(k in path_name for k in ("temp", "cache")):
        target_temp = path
    else:
        raise CacheCleanError(
            f"Safety guardrail violation: '{path}' is not a valid BeamNG cache directory "
            f"and does not contain a 'temp' folder. Cache cleaning strictly refuses to delete files outside temp/."
        )

    # Resolve symlinks and check root guardrails
    resolved = target_temp.resolve()

    # Guardrail: Never allow filesystem root (e.g. C:\ or /)
    if resolved == resolved.anchor or len(resolved.parts) <= 1:
        raise CacheCleanError(
            f"Safety guardrail violation: Refusing to clean root filesystem directory: {resolved}"
        )

    # Guardrail: Target directory name must contain 'temp' or 'cache'
    if not any(k in resolved.name.lower() for k in ("temp", "cache")):
        raise CacheCleanError(
            f"Safety guardrail violation: Target directory '{resolved.name}' is not named 'temp' or 'cache'."
        )

    # Guardrail: Target must not be or be inside mods or settings
    lower_parts = [p.lower() for p in resolved.parts]
    if "mods" in lower_parts or "settings" in lower_parts or "screenshots" in lower_parts:
        raise CacheCleanError(
            f"Safety guardrail violation: Refusing to clean directory inside protected folder: {resolved}"
        )

    return target_temp


def clean_shader_cache(
    beamng_user_path: Path,
    dry_run: bool = False,
) -> CacheCleanResult:
    """Safely purge compiled shaders and vehicle caches from BeamNG temp directory.

    Args:
        beamng_user_path: Path to BeamNG user directory or direct temp/ cache folder.
        dry_run: If True, calculates deletions without modifying the filesystem.

    Returns:
        CacheCleanResult with statistics on deleted files and freed bytes.

    Raises:
        CacheCleanError: If the target path fails safety validation.
    """
    target_temp_dir = _resolve_temp_directory(beamng_user_path)

    if not target_temp_dir.exists():
        logger.info("Cache directory %s does not exist; nothing to clean.", target_temp_dir)
        return CacheCleanResult(
            files_deleted=0,
            bytes_freed=0,
            directories_cleaned=[],
            skipped_files=[],
            success=True,
            error_message=None,
        )

    files_to_delete: List[Path] = []
    bytes_freed: int = 0
    directories_cleaned: List[Path] = []
    skipped_files: List[Path] = []

    # Walk all files within target temp directory
    for root, _dirs, files in os.walk(target_temp_dir):
        root_path = Path(root)
        for filename in files:
            file_path = root_path / filename

            # Absolute protection: Never delete vehicle configurations (.pc) or files in protected paths
            if file_path.suffix.lower() == ".pc" or any(
                part.lower() in ("mods", "settings", "screenshots", "replays", "saves")
                for part in file_path.parts
            ):
                skipped_files.append(file_path)
                continue

            try:
                st = file_path.stat()
                file_size = st.st_size
            except OSError:
                file_size = 0

            if dry_run:
                files_to_delete.append(file_path)
                bytes_freed += file_size
            else:
                try:
                    file_path.unlink()
                    files_to_delete.append(file_path)
                    bytes_freed += file_size
                except (PermissionError, OSError) as err:
                    logger.warning("Could not delete %s (locked or permission denied): %s", file_path, err)
                    skipped_files.append(file_path)

    # Clean empty directories
    for root, _dirs, _files in os.walk(target_temp_dir, topdown=False):
        root_path = Path(root)
        if root_path != target_temp_dir:
            if dry_run:
                directories_cleaned.append(root_path)
            else:
                try:
                    # Only remove if truly empty
                    if not any(root_path.iterdir()):
                        root_path.rmdir()
                        directories_cleaned.append(root_path)
                except OSError:
                    pass

    logger.info(
        "Cleaned cache in %s: %d files (%d bytes freed), %d directories cleared (dry_run=%s)",
        target_temp_dir,
        len(files_to_delete),
        bytes_freed,
        len(directories_cleaned),
        dry_run,
    )

    return CacheCleanResult(
        files_deleted=len(files_to_delete),
        bytes_freed=bytes_freed,
        directories_cleaned=directories_cleaned,
        skipped_files=skipped_files,
        success=True,
        error_message=None,
    )
