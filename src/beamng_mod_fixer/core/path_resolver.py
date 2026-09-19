"""BeamNG.drive user path and directory topology resolver.

Provides:
- High-performance multi-drive and multi-source BeamNG path discovery:
  * AppData version subdirectories (current, latest, 0.34, 0.33, 0.32, 0.31, 0.30...)
  * Windows Registry Steam library discovery (HKCU/HKLM -> libraryfolders.vdf -> startup.ini)
  * Common drive roots (C:, D:, E:, F:... BeamNG.drive / Games)
  * Linux Proton / Wine / Steam Deck compatibility paths
- Intelligent candidate scoring (prioritizing directories with active mods and newest mtime)
- 0ms instant retrieval via persistent local cache (%LOCALAPPDATA%/BeamNGModFixer/config.json)
- Robust path validation and normalization (handling ~ and %ENV% vars, quotes, mods subdirs)
"""

import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing winreg on Windows platforms
if sys.platform == "win32":
    try:
        import winreg  # type: ignore
    except ImportError:
        winreg = None
else:
    winreg = None

CONFIG_DIR_NAME = "BeamNGModFixer"
CONFIG_FILE_NAME = "config.json"
BEAMNG_STEAM_APP_ID = "284160"


# ==============================================================================
# 1. Persistent Local Cache (0ms instant retrieval)
# ==============================================================================
def get_cache_config_path() -> Path:
    """Determine the path to the persistent cache configuration file."""
    if sys.platform == "win32":
        lad = os.environ.get("LOCALAPPDATA")
        if lad:
            return Path(lad) / CONFIG_DIR_NAME / CONFIG_FILE_NAME
    return Path.home() / ".beamng_fixer_paths.json"


def load_cached_paths() -> Optional[Dict[str, Path]]:
    """Load previously discovered and validated BeamNG paths from cache.

    Returns:
        Optional[Dict[str, Path]]: Dict of paths if cache exists and directories still exist,
                                   otherwise None.
    """
    cache_file = get_cache_config_path()
    if not cache_file.exists():
        fallback = Path.home() / ".beamng_fixer_paths.json"
        if fallback.exists():
            cache_file = fallback
        else:
            return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        user_dir_str = data.get("user_dir")
        mods_dir_str = data.get("mods_dir")
        settings_dir_str = data.get("settings_dir")
        cache_dir_str = data.get("cache_dir")

        if not user_dir_str or not mods_dir_str:
            return None

        user_dir = Path(user_dir_str)
        mods_dir = Path(mods_dir_str)
        settings_dir = Path(settings_dir_str) if settings_dir_str else user_dir / "settings"
        cache_dir = Path(cache_dir_str) if cache_dir_str else user_dir / "temp"

        # Check if either user_dir or mods_dir exists on disk
        if not user_dir.exists() and not mods_dir.exists():
            return None

        # Guard against lingering test directories when reading default global system config
        lad = os.environ.get("LOCALAPPDATA")
        default_cfg = (Path(lad) / CONFIG_DIR_NAME / CONFIG_FILE_NAME) if lad else None
        if default_cfg and cache_file.resolve() == default_cfg.resolve():
            if "pytest" in str(user_dir).lower() or "test_cli" in str(user_dir).lower():
                return None

        return {
            "user_dir": user_dir,
            "mods_dir": mods_dir,
            "settings_dir": settings_dir,
            "cache_dir": cache_dir,
        }
    except Exception as e:
        logger.debug("Failed loading persistent path cache: %s", e)
        return None


def save_cached_paths(paths: Dict[str, Path], force: bool = False) -> bool:
    """Save validated BeamNG paths to persistent cache for instant 0ms retrieval."""
    cache_file = get_cache_config_path()

    # Safety check: avoid caching temporary test directories unless explicitly forced
    if not force:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        user_str = str(paths.get("user_dir", "")).lower()
        if "pytest" in user_str or "temp" in user_str or "tmp" in user_str:
            return False
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "user_dir": str(paths["user_dir"].resolve()),
            "mods_dir": str(paths["mods_dir"].resolve()),
            "settings_dir": str(paths["settings_dir"].resolve()),
            "cache_dir": str(paths["cache_dir"].resolve()),
            "timestamp": time.time(),
        }
        tmp_file = cache_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_file, cache_file)
        return True
    except Exception as e:
        logger.debug("Failed saving persistent path cache: %s", e)
        return False


def clear_cached_paths() -> bool:
    """Clear persistent path cache."""
    cleared = False
    for p in [get_cache_config_path(), Path.home() / ".beamng_fixer_paths.json"]:
        try:
            if p.exists():
                p.unlink()
                cleared = True
        except Exception:
            pass
    return cleared


# ==============================================================================
# 2. Steam Registry & Library Discovery
# ==============================================================================
def get_steam_install_paths() -> List[Path]:
    """Retrieve Steam installation root directories from the Windows Registry or Linux defaults."""
    paths: List[Path] = []
    if sys.platform == "win32" and winreg is not None:
        registry_keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ]
        for root_key, subkey, val_name in registry_keys:
            try:
                with winreg.OpenKey(root_key, subkey) as key:
                    val, _ = winreg.QueryValueEx(key, val_name)
                    if val:
                        p = Path(str(val))
                        if p.exists() and p not in paths:
                            paths.append(p)
            except OSError:
                pass
    else:
        home = Path.home()
        for loc in [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        ]:
            if loc.exists() and loc not in paths:
                paths.append(loc)
    return paths


def parse_steam_library_folders(vdf_path: Path) -> List[Path]:
    """Parse Steam libraryfolders.vdf to find all Steam library paths across all drives."""
    if not vdf_path.exists() or not vdf_path.is_file():
        return []

    libraries: List[Path] = []
    try:
        content = vdf_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    # Matches modern format: "path"\s+"([^"]+)"
    for m in re.finditer(r'"path"\s+"([^"]+)"', content, re.IGNORECASE):
        raw = m.group(1).replace(r"\\", "\\")
        p = Path(raw)
        if p.exists() and p not in libraries:
            libraries.append(p)

    # Legacy VDF format: "1"\t\t"D:\\SteamLibrary" (ensure value contains path separators)
    for m in re.finditer(r'"\d+"\s+"([^"]+)"', content):
        raw = m.group(1).replace(r"\\", "\\")
        if (":" in raw or "/" in raw or "\\" in raw):
            p = Path(raw)
            if p.exists() and p not in libraries:
                libraries.append(p)

    return libraries


def parse_startup_ini_userpath(ini_path: Path, game_dir: Path) -> Optional[Path]:
    """Parse UserPath directive from BeamNG startup.ini if configured."""
    try:
        content = ini_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(";") or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                if key.strip().lower() == "userpath":
                    val = val.strip().strip('"').strip("'")
                    if val:
                        val = os.path.expandvars(os.path.expanduser(val))
                        if val in (".\\", "./", "."):
                            return game_dir.resolve()
                        p = Path(val)
                        if not p.is_absolute():
                            p = (game_dir / p).resolve()
                        return p.resolve()
    except Exception:
        pass
    return None


def find_steam_beamng_dirs() -> List[Path]:
    """Discover BeamNG game installation and user data directories from Steam.

    Checks Steam App ID 284160, appmanifest_284160.acf, libraryfolders.vdf,
    and startup.ini userPath directives.
    """
    discovered: List[Path] = []
    steam_roots = get_steam_install_paths()
    all_libs: List[Path] = list(steam_roots)

    for s_root in steam_roots:
        vdf = s_root / "steamapps" / "libraryfolders.vdf"
        for lib in parse_steam_library_folders(vdf):
            if lib not in all_libs:
                all_libs.append(lib)

    for lib in all_libs:
        # Check for BeamNG Steam manifest: appmanifest_284160.acf
        manifest = lib / "steamapps" / f"appmanifest_{BEAMNG_STEAM_APP_ID}.acf"
        installdir = "BeamNG.drive"
        if manifest.exists():
            try:
                m_content = manifest.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'"installdir"\s+"([^"]+)"', m_content, re.IGNORECASE)
                if m:
                    installdir = m.group(1).strip()
            except OSError:
                pass

        game_dir = lib / "steamapps" / "common" / installdir
        if game_dir.exists() and game_dir.is_dir():
            startup_ini = game_dir / "startup.ini"
            if startup_ini.exists():
                up = parse_startup_ini_userpath(startup_ini, game_dir)
                if up and up.exists() and up not in discovered:
                    discovered.append(up)

            # Check if game directory itself contains mods or content
            if (game_dir / "mods").exists() and game_dir not in discovered:
                discovered.append(game_dir)
            elif (game_dir / "content" / "mods").exists() and game_dir not in discovered:
                discovered.append(game_dir)
            elif game_dir not in discovered:
                discovered.append(game_dir)

    return discovered


# ==============================================================================
# 3. Common Drive Roots Discovery
# ==============================================================================
def get_available_drives() -> List[str]:
    """Get list of accessible drive roots on Windows (C:, D:, E:, etc.).

    Uses Windows GetLogicalDrives bitmask and GetDriveType for instant 0ms,
    hang-free logical drive enumeration, filtering out CD-ROM / optical drives.
    """
    if sys.platform != "win32":
        return []

    drives: List[str] = []
    try:
        import ctypes
        # Suppress critical error dialogs (e.g. empty optical drive or disconnected volume)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x8000)
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            if bitmask & (1 << i):
                root = f"{letter}:\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(root)
                # Exclude CD-ROM / optical drives (5)
                if dtype != 5:
                    drives.append(root)
        if drives:
            return drives
    except Exception:
        pass

    # Fallback enumeration
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = Path(f"{letter}:\\")
        try:
            if drive_path.exists():
                drives.append(f"{letter}:\\")
        except OSError:
            pass
    return drives


def find_drive_root_candidates() -> List[Path]:
    """Discover BeamNG directories located in root or Games folders across multiple drives."""
    candidates: List[Path] = []
    drives = get_available_drives()
    common_subdirs = [
        "BeamNG.drive",
        "BeamNG/BeamNG.drive",
        "Games/BeamNG.drive",
        "Games/BeamNG/BeamNG.drive",
        "Games/BeamNG-drive",
        "Steam/steamapps/common/BeamNG.drive",
        "Games/Steam/steamapps/common/BeamNG.drive",
        "SteamLibrary/steamapps/common/BeamNG.drive",
        "Games/SteamLibrary/steamapps/common/BeamNG.drive",
        "Program Files/BeamNG.drive",
        "Program Files (x86)/BeamNG.drive",
        "Program Files/Steam/steamapps/common/BeamNG.drive",
        "Program Files (x86)/Steam/steamapps/common/BeamNG.drive",
    ]
    for d in drives:
        drive_path = Path(d)
        for sub in common_subdirs:
            target = drive_path / sub
            try:
                if target.exists() and target.is_dir():
                    ini = target / "startup.ini"
                    if ini.exists():
                        up = parse_startup_ini_userpath(ini, target)
                        if up and up.exists() and up not in candidates:
                            candidates.append(up)
                    if (target / "mods").exists() or (target / "settings").exists() or (target / "temp").exists():
                        if target not in candidates:
                            candidates.append(target)
            except OSError:
                pass
    return candidates


# ==============================================================================
# 4. Intelligent Candidate Scoring & Topology Discovery
# ==============================================================================
def score_candidate_user_dir(candidate: Path) -> float:
    """Calculate an activity score for a candidate BeamNG user directory.

    Prioritizes directories with active mod archives, valid settings, recent modification,
    and modern version topologies (current, latest, 0.34...).
    """
    if not candidate.exists() or not candidate.is_dir():
        return -1.0

    score = 0.0

    # 1. Mod archives presence (highest priority)
    mods_dir = candidate / "mods"
    if mods_dir.exists() and mods_dir.is_dir():
        score += 200.0
        try:
            mod_zips = [p for p in mods_dir.iterdir() if p.is_file() and p.suffix.lower() == ".zip"]
            mod_count = len(mod_zips)
            score += min(mod_count * 50.0, 5000.0)  # Up to 5000 points for active mods!
            if (mods_dir / "unpacked").exists() or (mods_dir / "repo").exists():
                score += 150.0
        except OSError:
            pass

    # 2. Settings directory presence
    settings_dir = candidate / "settings"
    if settings_dir.exists() and settings_dir.is_dir():
        score += 150.0
        if (settings_dir / "settings.json").exists() or (settings_dir / "game-settings.json").exists():
            score += 200.0

    # 3. Cache / temp directory presence
    temp_dir = candidate / "temp"
    if temp_dir.exists() and temp_dir.is_dir():
        score += 50.0

    # 4. Version and naming bonuses (current > latest > 0.34 > 0.33 > 0.30)
    name_lower = candidate.name.lower()
    if name_lower == "current":
        score += 100.0
    elif name_lower == "latest":
        score += 80.0
    else:
        # Numeric version parsing (e.g. "0.34", "0.33", "0.30")
        ver_match = re.match(r"^0\.(\d+)", name_lower)
        if ver_match:
            try:
                minor_ver = int(ver_match.group(1))
                score += minor_ver * 2.0  # Newer versions score higher
            except ValueError:
                pass

    # 5. Modification recency & active game launch logs (tie breaker)
    try:
        mtimes: List[float] = [candidate.stat().st_mtime]
        if mods_dir.exists():
            mtimes.append(mods_dir.stat().st_mtime)
        if settings_dir.exists():
            mtimes.append(settings_dir.stat().st_mtime)
        # Check active log files created on game execution
        for log_name in ("beamng.log", "beamng-launcher.log"):
            log_file = candidate / log_name
            if log_file.exists():
                mtimes.append(log_file.stat().st_mtime)
                score += 50.0

        newest_mtime = max(mtimes)
        # Recency window scoring
        now = time.time()
        age_days = max(0.0, (now - newest_mtime) / 86400.0)
        if age_days < 7.0:
            score += 300.0
        elif age_days < 30.0:
            score += 150.0
        elif age_days < 90.0:
            score += 50.0

        score += (newest_mtime / 1e9)  # Fine-grained fraction for tie-breaking
    except OSError:
        pass

    return score


def find_candidate_user_dirs() -> List[Path]:
    """Discover potential BeamNG.drive user data directories across Windows and Linux.

    Scans:
    1. %LOCALAPPDATA%/BeamNG/BeamNG.drive/ (all version folders: current, latest, 0.34, 0.33...)
    2. %LOCALAPPDATA%/BeamNG.drive/ (current, 0.34...)
    3. %USERPROFILE%/Documents/BeamNG.drive/
    4. Steam library locations & startup.ini
    5. Multi-drive root and Games locations (C:, D:, E:, F:...)
    6. Linux Steam Proton / Wine compatdata paths

    Returns:
        List[Path]: Ranked list of candidate directories, prioritized by active mods and recency.
    """
    raw_candidates: List[Path] = []

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        user_profile = os.environ.get("USERPROFILE")

        if local_app_data:
            lad = Path(local_app_data)

            # 1. New BeamNG launcher location: %LOCALAPPDATA%/BeamNG/BeamNG.drive/
            bng_parent = lad / "BeamNG" / "BeamNG.drive"
            if bng_parent.exists() and bng_parent.is_dir():
                try:
                    for sub in bng_parent.iterdir():
                        if sub.is_dir():
                            raw_candidates.append(sub)
                except OSError:
                    pass

            # 2. Older %LOCALAPPDATA%/BeamNG.drive/
            bng_old = lad / "BeamNG.drive"
            if bng_old.exists() and bng_old.is_dir():
                try:
                    for sub in bng_old.iterdir():
                        if sub.is_dir():
                            raw_candidates.append(sub)
                except OSError:
                    pass

        # 3. Legacy Documents folder: %USERPROFILE%/Documents/BeamNG.drive
        if user_profile:
            docs = Path(user_profile) / "Documents" / "BeamNG.drive"
            if docs.exists() and docs.is_dir():
                raw_candidates.append(docs)
                try:
                    for sub in docs.iterdir():
                        if sub.is_dir():
                            raw_candidates.append(sub)
                except OSError:
                    pass

        # 4. Steam installation and library discovery
        for steam_dir in find_steam_beamng_dirs():
            if steam_dir not in raw_candidates:
                raw_candidates.append(steam_dir)

        # 5. Multi-drive search
        for drive_dir in find_drive_root_candidates():
            if drive_dir not in raw_candidates:
                raw_candidates.append(drive_dir)

    else:
        # Linux Proton / Wine / Steam deck paths
        home = Path.home()
        steam_compat = (
            home
            / ".local/share/Steam/steamapps/compatdata/284160/pfx/drive_c/users/steamuser/AppData/Local/BeamNG.drive"
        )
        if steam_compat.exists() and steam_compat.is_dir():
            if (steam_compat / "current").exists():
                raw_candidates.append(steam_compat / "current")
            try:
                for sub in steam_compat.iterdir():
                    if sub.is_dir():
                        raw_candidates.append(sub)
            except OSError:
                pass

        # Also check native Linux Steam discovery
        for steam_dir in find_steam_beamng_dirs():
            if steam_dir not in raw_candidates:
                raw_candidates.append(steam_dir)

    # Deduplicate while preserving order
    unique_candidates: List[Path] = []
    seen = set()
    for c in raw_candidates:
        resolved = c.resolve() if c.exists() else c
        if resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(c)

    # Sort candidates by intelligent activity score descending
    unique_candidates.sort(key=score_candidate_user_dir, reverse=True)

    return unique_candidates


def detect_beamng_user_dir(use_cache: bool = True) -> Optional[Path]:
    """Detect the most active or newest BeamNG.drive user data directory.

    Checks persistent cache first (0ms), then scans all sources.

    Args:
        use_cache: If True, check persistent cache before running discovery.

    Returns:
        Optional[Path]: The best match user directory, or None if not found.
    """
    if use_cache:
        cached = load_cached_paths()
        if cached and cached["user_dir"].exists():
            return cached["user_dir"]

    candidates = find_candidate_user_dirs()
    for c in candidates:
        if (c / "mods").exists() or (c / "settings").exists() or (c / "temp").exists():
            return c
    return candidates[0] if candidates else None


# ==============================================================================
# 5. Validation and Path Resolution
# ==============================================================================
def validate_beamng_dir(input_path: Path | str, is_mods_dir: bool = False) -> Tuple[bool, str, Dict[str, Path]]:
    """Validate and normalize a user-provided BeamNG directory.

    Accepts:
    - User data directory (e.g. %LOCALAPPDATA%/BeamNG/BeamNG.drive/current)
    - Direct mods directory (e.g. D:/Mods or .../BeamNG.drive/current/mods)
    - Paths with environment variables (%LOCALAPPDATA%, ~) or enclosing quotes.

    Args:
        input_path: Path string or Path object.
        is_mods_dir: If True, treats input_path directly as the mods directory.

    Returns:
        Tuple[bool, str, Dict[str, Path]]: (is_valid, description_or_error, resolved_paths)
    """
    s = str(input_path).strip().strip('"').strip("'")
    if not s:
        return False, "Path is empty.", {}

    s = os.path.expandvars(os.path.expanduser(s))
    path = Path(s).resolve()

    if not path.exists():
        return False, f"Directory does not exist: {path}", {}

    if not path.is_dir():
        return False, f"Specified path is a file, not a directory: {path}", {}

    if is_mods_dir or path.name.lower() == "mods":
        resolved_mods = path
        parent = path.parent
        resolved_user = parent if (parent / "settings").exists() or (parent / "temp").exists() else path
        resolved_settings = resolved_user / "settings"
        resolved_cache = resolved_user / "temp"
    elif (path / "mods").exists() and (path / "mods").is_dir():
        # User pointed to user directory containing 'mods'
        resolved_user = path
        resolved_mods = path / "mods"
        resolved_settings = path / "settings"
        resolved_cache = path / "temp"
    elif (path / "content" / "mods").exists() and (path / "content" / "mods").is_dir():
        # Game installation folder with content/mods
        resolved_user = path
        resolved_mods = path / "content" / "mods"
        resolved_settings = path / "settings"
        resolved_cache = path / "temp"
    else:
        # Check if this folder itself contains .zip mod files
        zip_count = 0
        try:
            zip_count = len([p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".zip"])
        except OSError:
            pass
        if zip_count > 0:
            resolved_mods = path
            resolved_user = path.parent
            resolved_settings = resolved_user / "settings"
            resolved_cache = resolved_user / "temp"
        else:
            # Fallback: assume user root
            resolved_user = path
            resolved_mods = path / "mods"
            resolved_settings = path / "settings"
            resolved_cache = path / "temp"

    mod_count = 0
    if resolved_mods.exists() and resolved_mods.is_dir():
        try:
            mod_count = len([p for p in resolved_mods.iterdir() if p.is_file() and p.suffix.lower() == ".zip"])
        except OSError:
            pass

    msg = f"Verified BeamNG directory: {resolved_user} ({mod_count} mod archives detected in {resolved_mods.name}/)."

    return True, msg, {
        "user_dir": resolved_user,
        "mods_dir": resolved_mods,
        "settings_dir": resolved_settings,
        "cache_dir": resolved_cache,
    }


def resolve_beamng_paths(
    user_dir: Optional[Path | str] = None,
    mods_dir: Optional[Path | str] = None,
    settings_dir: Optional[Path | str] = None,
    cache_dir: Optional[Path | str] = None,
    use_cache: bool = True,
    save_cache: bool = True,
) -> Dict[str, Path]:
    """Resolve all active working directories (mods, settings, temp cache).

    Order of priority:
    1. Explicit arguments (user_dir, mods_dir, etc.)
    2. Persistent local cache (0ms instant retrieval)
    3. Multi-source automatic discovery (AppData, Steam, multi-drive)

    Args:
        user_dir: Explicit root user directory.
        mods_dir: Explicit override for mods folder.
        settings_dir: Explicit override for settings folder.
        cache_dir: Explicit override for cache/temp folder.
        use_cache: If True, check persistent cache when arguments are omitted.
        save_cache: If True, save resolved valid paths to persistent cache.

    Returns:
        Dict[str, Path]: Resolved paths for 'user_dir', 'mods_dir', 'settings_dir', 'cache_dir'.
    """
    has_explicit = bool(user_dir or mods_dir or settings_dir or cache_dir)

    # If no explicit arguments provided, check cache first
    if not has_explicit and use_cache:
        cached = load_cached_paths()
        if cached:
            return cached

    # Resolve root user directory
    root: Optional[Path] = None
    if user_dir:
        root = Path(os.path.expandvars(os.path.expanduser(str(user_dir))))
    else:
        root = detect_beamng_user_dir(use_cache=use_cache)

    resolved_mods = (
        Path(os.path.expandvars(os.path.expanduser(str(mods_dir))))
        if mods_dir
        else (root / "mods" if root else Path("mods"))
    )
    resolved_settings = (
        Path(os.path.expandvars(os.path.expanduser(str(settings_dir))))
        if settings_dir
        else (root / "settings" if root else Path("settings"))
    )
    resolved_cache = (
        Path(os.path.expandvars(os.path.expanduser(str(cache_dir))))
        if cache_dir
        else (root / "temp" if root else Path("temp"))
    )

    result = {
        "user_dir": root if root else Path.cwd(),
        "mods_dir": resolved_mods,
        "settings_dir": resolved_settings,
        "cache_dir": resolved_cache,
    }

    # Save to persistent cache if appropriate and valid
    if save_cache and not has_explicit and root and root.exists():
        save_cached_paths(result)

    return result
