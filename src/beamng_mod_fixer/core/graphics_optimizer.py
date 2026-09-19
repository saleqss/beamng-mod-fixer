"""Graphics optimizer and settings configuration engine for BeamNG.drive.

Provides:
- Creation of timestamped backups (.backup_YYYYMMDD_HHMMSS and .bak) before modifying settings
- Application of balanced graphics optimization presets:
  * GraphicDynReflectionFacesPerupdate: 2 (reduces CPU draw calls)
  * GraphicDynReflectionTexsize: 512 (crisp reflections without VRAM penalty)
  * GraphicDynReflectionDistance: 300
  * GraphicDynMirrorsDetail: 0.75
  * GraphicShadowsQuality: "High" / balanced filtering
  * Balanced decal, particle, and texture settings
- Synchronization of low-level Torque3D engine preferences ($pref in game-settings.json)
- Preservation of user preferences (audio volume, display resolution, custom input bindings)
- Safe restoration of settings from backups
- Atomic file writing to avoid configuration corruption
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple
import uuid

from beamng_mod_fixer.exceptions import (
    SettingsCorruptedError,
    SettingsError,
    SettingsNotFoundError,
)
from beamng_mod_fixer.models import OptimizationResult

logger = logging.getLogger(__name__)

# ==============================================================================
# Graphics Presets
# ==============================================================================

OPTIMIZATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "ultra-max-fps": {
        "settings": {
            "GraphicOverallQuality": "Ultra",
            "GraphicLightingQuality": "Ultra",
            "GraphicClusteredQuality": "Ultra",
            "GraphicMeshQuality": "Ultra",
            "GraphicShadowQuality": "Ultra",
            "GraphicShadowsQuality": "Ultra",
            "GraphicTerrainQuality": "Ultra",
            "GraphicCloudsQuality": "Ultra",
            "GraphicTextureQuality": "High",
            "GraphicAnisotropic": 16,
            "GraphicAntialias": 4,
            "GraphicAntialiasType": "smaa",
            "GraphicGrassDensity": 1.0,
            "GraphicMaxDecalCount": 8000,
            "GraphicDisableShadows": "0",
            "GraphicDynReflection": True,
            "GraphicDynReflectionEnabled": True,
            "GraphicDynReflectionTexsize": 3,
            "GraphicDynReflectionDistance": 500,
            "GraphicDynReflectionDetail": 1.0,
            "GraphicDynReflectionFacesPerupdate": 3,
            "GraphicDynMirrorsEnabled": True,
            "GraphicDynMirrorsTexsize": 2,
            "GraphicDynMirrorsDetail": 1.0,
            "GraphicDynMirrorsDistance": 400,
            "PostFXSSAOGeneralEnabled": True,
            "PostFXScreenSpaceShadowsEnabled": True,
            "PostFXLightRaysEnabled": True,
            "PostFXDOFGeneralEnabled": True,
            "PostFXMotionBlurEnabled": False,
        },
        "game_settings": {
            "BeamNGVehicle": {
                "dynamicReflection": {
                    "enabled": True,
                    "facesPerUpdate": 3,
                    "textureSize": 1024,
                    "detail": 1.0,
                    "distance": 500,
                    "debugEnabled": False,
                },
                "dynamicMirrors": {
                    "enabled": True,
                    "textureSize": 1024,
                    "detail": 1.0,
                    "distance": 400,
                },
            },
            "Shadows": {
                "textureScalar": 4,
                "filterMode": 1,
                "disable": 0,
            },
            "Terrain": {
                "lodScale": 1.0,
                "detailScale": 2.0,
            },
            "GroundCover": {
                "densityScale": 1.0,
            },
            "Reflect": {
                "maxLights": 8,
                "deferredLighting": True,
                "depthPrepass": True,
                "frameLimitMS": 0,
                "refractTexScale": 1,
            },
            "TS": {
                "maxDecalCount": 8000,
                "detailAdjust": 2,
                "skipRenderDLs": 0,
            },
            "Decals": {
                "enabled": True,
            },
        },
    },
    "cinematic-fast": {
        "settings": {
            "GraphicDynReflection": True,
            "GraphicDynReflectionEnabled": True,
            "GraphicDynReflectionFacesPerupdate": 2,
            "GraphicDynReflectionTexsize": 2,
            "GraphicDynReflectionDistance": 350,
            "GraphicDynReflectionDetail": 0.85,
            "GraphicDynMirrorsEnabled": True,
            "GraphicDynMirrorsTexsize": 2,
            "GraphicDynMirrorsDetail": 0.85,
            "GraphicDynMirrorsDistance": 350,
            "GraphicShadowsQuality": "High",
            "GraphicShadowQuality": "High",
            "GraphicDisableShadows": "0",
            "GraphicLightingQuality": "High",
            "GraphicClusteredQuality": "High",
            "GraphicMaxDecalCount": 8000,
            "GraphicMeshQuality": "High",
            "GraphicTextureQuality": "High",
            "GraphicTerrainQuality": "High",
            "GraphicGrassDensity": 0.85,
            "GraphicAnisotropic": 16,
            "GraphicAntialias": 4,
            "GraphicAntialiasType": "smaa",
            "GraphicCloudsQuality": "High",
            "PostFXSSAOGeneralEnabled": True,
            "PostFXScreenSpaceShadowsEnabled": True,
            "PostFXDOFGeneralEnabled": False,
            "PostFXMotionBlurEnabled": False,
            "PostFXLightRaysEnabled": True,
        },
        "game_settings": {
            "BeamNGVehicle": {
                "dynamicReflection": {
                    "enabled": True,
                    "facesPerUpdate": 2,
                    "textureSize": 512,
                    "detail": 0.85,
                    "distance": 350,
                    "debugEnabled": False,
                },
                "dynamicMirrors": {
                    "enabled": True,
                    "textureSize": 512,
                    "detail": 0.85,
                    "distance": 350,
                },
            },
            "Shadows": {
                "textureScalar": 2,
                "filterMode": 1,
                "disable": 0,
            },
            "TS": {
                "maxDecalCount": 8000,
                "detailAdjust": 2,
                "skipRenderDLs": 0,
            },
            "Decals": {
                "enabled": True,
            },
            "Reflect": {
                "maxLights": 96,
                "deferredLighting": True,
                "depthPrepass": True,
            },
        },
    },
    "balanced": {
        "settings": {
            "GraphicDynReflection": True,
            "GraphicDynReflectionEnabled": True,
            "GraphicDynReflectionFacesPerupdate": 2,
            "GraphicDynReflectionTexsize": 2,
            "GraphicDynReflectionDistance": 300,
            "GraphicDynReflectionDetail": 0.75,
            "GraphicDynMirrorsEnabled": True,
            "GraphicDynMirrorsTexsize": 2,
            "GraphicDynMirrorsDetail": 0.75,
            "GraphicDynMirrorsDistance": 300,
            "GraphicShadowsQuality": "High",
            "GraphicShadowQuality": "High",
            "GraphicDisableShadows": "0",
            "GraphicLightingQuality": "High",
            "GraphicClusteredQuality": "High",
            "GraphicMaxDecalCount": 6000,
            "GraphicMeshQuality": "High",
            "GraphicTextureQuality": "Normal",
            "GraphicTerrainQuality": "High",
            "GraphicGrassDensity": 0.75,
            "GraphicAnisotropic": 16,
            "GraphicAntialias": 4,
            "GraphicAntialiasType": "smaa",
            "GraphicCloudsQuality": "High",
            "PostFXSSAOGeneralEnabled": True,
            "PostFXScreenSpaceShadowsEnabled": True,
            "PostFXDOFGeneralEnabled": False,
            "PostFXMotionBlurEnabled": False,
            "PostFXLightRaysEnabled": True,
        },
        "game_settings": {
            "BeamNGVehicle": {
                "dynamicReflection": {
                    "enabled": True,
                    "facesPerUpdate": 2,
                    "textureSize": 512,
                    "detail": 0.75,
                    "distance": 300,
                    "debugEnabled": False,
                },
                "dynamicMirrors": {
                    "enabled": True,
                    "textureSize": 512,
                    "detail": 0.75,
                    "distance": 300,
                },
            },
            "Shadows": {
                "textureScalar": 2,
                "filterMode": 1,
                "disable": 0,
            },
            "TS": {
                "maxDecalCount": 6000,
                "detailAdjust": 2,
                "skipRenderDLs": 0,
            },
            "Decals": {
                "enabled": True,
            },
            "Reflect": {
                "maxLights": 64,
                "deferredLighting": True,
                "depthPrepass": True,
            },
        },
    },
    "performance": {
        "settings": {
            "GraphicDynReflection": False,
            "GraphicDynReflectionEnabled": False,
            "GraphicDynReflectionFacesPerupdate": 1,
            "GraphicDynReflectionTexsize": 1,
            "GraphicDynReflectionDistance": 150,
            "GraphicDynReflectionDetail": 0.5,
            "GraphicDynMirrorsEnabled": True,
            "GraphicDynMirrorsTexsize": 1,
            "GraphicDynMirrorsDetail": 0.5,
            "GraphicDynMirrorsDistance": 150,
            "GraphicShadowsQuality": "Normal",
            "GraphicShadowQuality": "Normal",
            "GraphicDisableShadows": "0",
            "GraphicLightingQuality": "Normal",
            "GraphicMaxDecalCount": 3000,
            "GraphicMeshQuality": "Normal",
            "GraphicTextureQuality": "Normal",
            "GraphicTerrainQuality": "Normal",
            "GraphicGrassDensity": 0.5,
            "GraphicAnisotropic": 8,
            "GraphicAntialias": 2,
            "GraphicAntialiasType": "fxaa",
        },
        "game_settings": {
            "BeamNGVehicle": {
                "dynamicReflection": {
                    "enabled": False,
                    "facesPerUpdate": 1,
                    "textureSize": 256,
                    "detail": 0.5,
                    "distance": 150,
                },
                "dynamicMirrors": {
                    "enabled": True,
                    "textureSize": 256,
                    "detail": 0.5,
                    "distance": 150,
                },
            },
            "Shadows": {
                "textureScalar": 1,
                "filterMode": 0,
                "disable": 0,
            },
            "TS": {
                "maxDecalCount": 3000,
                "detailAdjust": 1,
                "skipRenderDLs": 0,
            },
            "Reflect": {
                "maxLights": 32,
                "deferredLighting": True,
                "depthPrepass": True,
            },
        },
    },
    "ultra": {
        "settings": {
            "GraphicDynReflection": True,
            "GraphicDynReflectionEnabled": True,
            "GraphicDynReflectionFacesPerupdate": 6,
            "GraphicDynReflectionTexsize": 3,
            "GraphicDynReflectionDistance": 500,
            "GraphicDynReflectionDetail": 1.0,
            "GraphicDynMirrorsEnabled": True,
            "GraphicDynMirrorsTexsize": 3,
            "GraphicDynMirrorsDetail": 1.0,
            "GraphicDynMirrorsDistance": 500,
            "GraphicShadowsQuality": "Ultra",
            "GraphicShadowQuality": "Ultra",
            "GraphicLightingQuality": "High",
            "GraphicMaxDecalCount": 10000,
            "GraphicMeshQuality": "High",
            "GraphicTextureQuality": "High",
            "GraphicTerrainQuality": "High",
            "GraphicGrassDensity": 1.0,
            "GraphicAnisotropic": 16,
            "GraphicAntialias": 8,
            "GraphicAntialiasType": "smaa",
        },
        "game_settings": {
            "BeamNGVehicle": {
                "dynamicReflection": {
                    "enabled": True,
                    "facesPerUpdate": 6,
                    "textureSize": 1024,
                    "detail": 1.0,
                    "distance": 500,
                },
                "dynamicMirrors": {
                    "enabled": True,
                    "textureSize": 1024,
                    "detail": 1.0,
                    "distance": 500,
                },
            },
            "Shadows": {
                "textureScalar": 3,
                "filterMode": 2,
                "disable": 0,
            },
            "TS": {
                "maxDecalCount": 10000,
                "detailAdjust": 3,
                "skipRenderDLs": 0,
            },
            "Reflect": {
                "maxLights": 128,
                "deferredLighting": True,
                "depthPrepass": True,
            },
        },
    },
}


# ==============================================================================
# Helper Functions
# ==============================================================================

def _deep_update(target: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """Recursively update nested dictionaries preserving existing keys."""
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _resolve_paths(target: Path) -> Tuple[Path, Optional[Path], Path]:
    """Resolve settings.json, game-settings.json, and the directory path.

    Returns:
        (settings_file, game_settings_file, settings_directory)
    """
    if target.is_dir():
        settings_dir = target
        settings_file = settings_dir / "settings.json"
        game_settings_file = settings_dir / "game-settings.json"
    else:
        settings_file = target
        settings_dir = target.parent
        game_settings_file = settings_dir / "game-settings.json"

    if not settings_file.exists():
        raise SettingsNotFoundError(
            f"BeamNG settings file not found: {settings_file}",
            details=f"Target path checked: {target}",
        )

    gs_file = game_settings_file if game_settings_file.exists() else None
    return settings_file, gs_file, settings_dir


def _atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomically write JSON data to file using a temporary replacement."""
    parent_dir = file_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    temp_file = parent_dir / f".{file_path.name}.tmp_{uuid.uuid4().hex}"

    try:
        content = json.dumps(data, indent=4) + "\n"
        temp_file.write_text(content, encoding="utf-8")
        os.replace(temp_file, file_path)
    except Exception as err:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise SettingsError(
            f"Failed to atomically write settings to {file_path}: {err}",
            details=str(err),
        ) from err


# ==============================================================================
# Public API
# ==============================================================================

def backup_settings_file(
    file_path: Path,
    timestamp: Optional[str] = None,
) -> Path:
    """Create a backup of a settings file before modification.

    Creates both a timestamped backup (`settings.json.backup_YYYYMMDD_HHMMSS`)
    and a `.bak` copy for convenient rollback.

    Args:
        file_path: Absolute path to the settings file to back up.
        timestamp: Optional formatted timestamp string. Defaults to current UTC time.

    Returns:
        Path to the primary timestamped backup file.
    """
    if not file_path.exists():
        raise SettingsNotFoundError(
            f"Cannot backup non-existent settings file: {file_path}",
            details=str(file_path),
        )

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Primary timestamped backup file
    backup_path = file_path.with_name(f"{file_path.name}.backup_{timestamp}")
    shutil.copy2(file_path, backup_path)

    # Standard .bak copy
    bak_path = file_path.with_name(f"{file_path.name}.bak")
    try:
        shutil.copy2(file_path, bak_path)
    except Exception as err:
        logger.warning("Could not create secondary .bak copy: %s", err)

    logger.info("Created settings backup: %s", backup_path)
    return backup_path


def restore_settings_backup(
    settings_path: Path,
    backup_path: Optional[Path] = None,
) -> bool:
    """Restore a settings file from backup.

    If backup_path is specified, restores directly from that file.
    Otherwise, automatically locates the most recent backup in the directory.

    Args:
        settings_path: Path to the settings file or settings directory.
        backup_path: Optional explicit path to the backup file to restore.

    Returns:
        True if restoration succeeded, False otherwise.
    """
    if settings_path.is_dir():
        settings_dir = settings_path
        settings_file = settings_dir / "settings.json"
    else:
        settings_file = settings_path
        settings_dir = settings_path.parent

    target_backup: Optional[Path] = None

    if backup_path is not None:
        if not backup_path.exists():
            logger.error("Specified backup file does not exist: %s", backup_path)
            return False
        target_backup = backup_path
    else:
        # Search for available backups
        candidates: List[Path] = []
        for pattern in (
            f"{settings_file.name}.backup_*",
            f"{settings_file.name}.bak*",
            "*.bak*",
        ):
            candidates.extend(settings_dir.glob(pattern))

        candidates = [p for p in candidates if p.is_file() and p != settings_file]
        if not candidates:
            logger.warning("No settings backup files found in %s", settings_dir)
            return False

        # Sort by modification time descending
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        target_backup = candidates[0]

    try:
        shutil.copy2(target_backup, settings_file)
        logger.info("Successfully restored settings from %s to %s", target_backup, settings_file)

        # If matching game-settings backup exists, restore it as well
        gs_file = settings_dir / "game-settings.json"
        if "backup_" in target_backup.name:
            ts = target_backup.name.split("backup_")[-1]
            gs_backup = settings_dir / f"game-settings.json.backup_{ts}"
            if gs_backup.exists():
                shutil.copy2(gs_backup, gs_file)
                logger.info("Restored matching game-settings backup: %s", gs_backup)
        elif (settings_dir / "game-settings.json.bak").exists():
            shutil.copy2(settings_dir / "game-settings.json.bak", gs_file)

        return True
    except Exception as err:
        logger.error("Failed to restore settings backup: %s", err)
        return False


def optimize_settings(
    settings_path: Path,
    preset: str = "ultra-max-fps",
    backup: bool = True,
    dry_run: bool = False,
) -> OptimizationResult:
    """Deploy balanced graphics optimization presets to BeamNG.drive settings.

    Args:
        settings_path: Path to settings.json or the BeamNG settings/ directory.
        preset: Optimization preset name ('balanced', 'performance', 'ultra').
        backup: If True, creates a timestamped backup before modifying files.
        dry_run: If True, calculates changes without modifying files on disk.

    Returns:
        OptimizationResult indicating backup status and applied keys.

    Raises:
        SettingsNotFoundError: If settings.json cannot be found.
        SettingsCorruptedError: If settings.json contains invalid JSON.
        ValueError: If an unknown preset is requested.
    """
    preset_lower = preset.lower()
    if preset_lower not in OPTIMIZATION_PRESETS:
        raise ValueError(
            f"Unknown optimization preset: '{preset}'. "
            f"Available presets: {list(OPTIMIZATION_PRESETS.keys())}"
        )

    preset_config = OPTIMIZATION_PRESETS[preset_lower]
    settings_preset = preset_config["settings"]
    game_settings_preset = preset_config.get("game_settings", {})

    settings_file, gs_file, settings_dir = _resolve_paths(settings_path)

    # Parse settings.json
    try:
        raw_text = settings_file.read_text(encoding="utf-8")
        settings_data: Dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as err:
        raise SettingsCorruptedError(
            f"Corrupted or invalid JSON in settings file: {settings_file}",
            details=str(err),
        ) from err
    except Exception as err:
        raise SettingsError(
            f"Failed to read settings file {settings_file}: {err}",
            details=str(err),
        ) from err

    # Parse game-settings.json if present
    gs_data: Optional[Dict[str, Any]] = None
    if gs_file is not None:
        try:
            gs_text = gs_file.read_text(encoding="utf-8")
            gs_data = json.loads(gs_text)
        except Exception as err:
            logger.warning("Could not read game-settings.json: %s", err)
            gs_data = None

    # Handle backup creation
    backup_created = False
    backup_file_path: Optional[Path] = None
    if backup and not dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file_path = backup_settings_file(settings_file, timestamp=ts)
        backup_created = True

        if gs_file is not None and gs_file.exists():
            try:
                backup_settings_file(gs_file, timestamp=ts)
            except Exception as err:
                logger.warning("Could not backup game-settings.json: %s", err)

    # Apply preset values while strictly preserving all other user preferences
    applied_keys: Dict[str, Any] = {}
    for key, val in settings_preset.items():
        settings_data[key] = val
        applied_keys[key] = val

    if gs_data is not None and game_settings_preset:
        if "$pref" not in gs_data:
            gs_data["$pref"] = {}
        _deep_update(gs_data["$pref"], game_settings_preset)

    # Write changes if not in dry-run mode
    if not dry_run:
        _atomic_write_json(settings_file, settings_data)
        if gs_file is not None and gs_data is not None:
            _atomic_write_json(gs_file, gs_data)
        logger.info("Successfully applied '%s' graphics preset to %s", preset_lower, settings_file)

    return OptimizationResult(
        backup_created=backup_created,
        backup_path=backup_file_path,
        applied_keys=applied_keys,
        preset_name=preset_lower,
        success=True,
        error_message=None,
    )
