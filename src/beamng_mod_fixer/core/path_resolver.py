"""BeamNG.drive user path and directory topology resolver."""

import logging
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def find_candidate_user_dirs() -> List[Path]:
    """Discover potential BeamNG.drive user data directories across Windows and Linux.

    Returns:
        List[Path]: List of candidate directories, prioritized by newest/most specific.
    """
    candidates: List[Path] = []

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        user_profile = os.environ.get("USERPROFILE")

        if local_app_data:
            lad = Path(local_app_data)
            # 1. New BeamNG launcher location: %LOCALAPPDATA%/BeamNG/BeamNG.drive/current
            current_path = lad / "BeamNG" / "BeamNG.drive" / "current"
            if current_path.exists():
                candidates.append(current_path)

            # 2. Versioned folders under %LOCALAPPDATA%/BeamNG/BeamNG.drive/
            bng_parent = lad / "BeamNG" / "BeamNG.drive"
            if bng_parent.exists():
                for sub in sorted(bng_parent.iterdir(), reverse=True):
                    if sub.is_dir() and sub.name != "current":
                        candidates.append(sub)

            # 3. Older %LOCALAPPDATA%/BeamNG.drive/current and versioned
            bng_old = lad / "BeamNG.drive"
            if bng_old.exists():
                if (bng_old / "current").exists():
                    candidates.append(bng_old / "current")
                for sub in sorted(bng_old.iterdir(), reverse=True):
                    if sub.is_dir() and sub.name != "current":
                        candidates.append(sub)

        # 4. Legacy Documents folder: %USERPROFILE%/Documents/BeamNG.drive
        if user_profile:
            docs = Path(user_profile) / "Documents" / "BeamNG.drive"
            if docs.exists():
                candidates.append(docs)
                for sub in sorted(docs.iterdir(), reverse=True):
                    if sub.is_dir():
                        candidates.append(sub)

    else:
        # Linux Proton / Wine / Steam deck paths
        home = Path.home()
        steam_compat = home / ".local/share/Steam/steamapps/compatdata/284160/pfx/drive_c/users/steamuser/AppData/Local/BeamNG.drive"
        if steam_compat.exists():
            candidates.append(steam_compat / "current")
            for sub in sorted(steam_compat.iterdir(), reverse=True):
                if sub.is_dir():
                    candidates.append(sub)

    return candidates


def detect_beamng_user_dir() -> Optional[Path]:
    """Detect the most active or newest BeamNG.drive user data directory.

    Returns:
        Optional[Path]: The best match user directory, or None if not found.
    """
    candidates = find_candidate_user_dirs()
    for c in candidates:
        # A valid BeamNG user dir typically has 'mods', 'settings', or 'temp'
        if (c / "mods").exists() or (c / "settings").exists() or (c / "temp").exists():
            return c
    return candidates[0] if candidates else None


def resolve_beamng_paths(
    user_dir: Optional[Path | str] = None,
    mods_dir: Optional[Path | str] = None,
    settings_dir: Optional[Path | str] = None,
    cache_dir: Optional[Path | str] = None,
) -> Dict[str, Path]:
    """Resolve all active working directories (mods, settings, temp cache).

    Args:
        user_dir: Explicit root user directory (e.g. %LOCALAPPDATA%/BeamNG/BeamNG.drive/current).
        mods_dir: Explicit override for mods folder.
        settings_dir: Explicit override for settings folder.
        cache_dir: Explicit override for cache/temp folder.

    Returns:
        Dict[str, Path]: Resolved paths for 'user_dir', 'mods_dir', 'settings_dir', 'cache_dir'.
    """
    root = Path(user_dir) if user_dir else detect_beamng_user_dir()

    resolved_mods = (
        Path(mods_dir)
        if mods_dir
        else (root / "mods" if root else Path("mods"))
    )
    resolved_settings = (
        Path(settings_dir)
        if settings_dir
        else (root / "settings" if root else Path("settings"))
    )
    resolved_cache = (
        Path(cache_dir)
        if cache_dir
        else (root / "temp" if root else Path("temp"))
    )

    return {
        "user_dir": root if root else Path.cwd(),
        "mods_dir": resolved_mods,
        "settings_dir": resolved_settings,
        "cache_dir": resolved_cache,
    }
