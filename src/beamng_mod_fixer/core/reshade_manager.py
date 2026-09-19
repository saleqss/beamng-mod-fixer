"""ReShade preset generator and manager for BeamNG.drive.

Provides:
- Generation and deployment of tailored ReShade preset configurations (.ini):
  * 'medium-optimal': The most beautiful yet optimized preset (Tonemap, Curves, CAS, Colourfulness, AmbientLight).
  * 'low-fast': Zero-lag enhancement for entry-level / weak PCs.
  * 'potato-boost': Minimalist sharpening and level-balancing for iGPUs.
  * 'ultra-photoreal': Full cinematic fidelity for high-end systems.
- Detection of existing ReShade installations in BeamNG user or game directories.
- Automatic synchronization with ReShade.ini (updating CurrentPresetPath).
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ==============================================================================
# ReShade Preset Configurations
# ==============================================================================

RESHADE_PRESETS: Dict[str, Dict[str, Any]] = {
    "medium-optimal": {
        "filename": "BeamNG_Medium_Optimal.ini",
        "description": "Самая красивая и оптимальная (Balanced 60 FPS, Tonemap + CAS + Curves + AmbientLight)",
        "content": """PreprocessorDefinitions=
Techniques=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx,Colourfulness@Colourfulness.fx,AmbientLight@AmbientLight.fx
TechniqueSorting=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx,Colourfulness@Colourfulness.fx,AmbientLight@AmbientLight.fx

[CAS.fx]
Contrast=0.000000
Sharpening=0.450000

[Curves.fx]
Formula=0
Mode=0
NumberOfFormulaControlPoints=2
NumberOfSplineControlPoints=5
SplitMethod=0
Curve=0.150000

[Tonemap.fx]
Bleach=0.000000
Defog=0.015000
Exposure=0.050000
Gamma=1.000000
Saturation=0.080000

[Colourfulness.fx]
colourfulness=0.150000
lim_luma=0.700000

[AmbientLight.fx]
alInt=1.200000
alThreshold=15.000000
alAdapt=0.700000
""",
    },
    "low-fast": {
        "filename": "BeamNG_Low_Fast.ini",
        "description": "Оптимизированный для слабых ПК (Fast Tonemap + Sharpness, 0 FPS cost)",
        "content": """PreprocessorDefinitions=
Techniques=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx
TechniqueSorting=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx

[CAS.fx]
Contrast=0.000000
Sharpening=0.550000

[Curves.fx]
Formula=0
Mode=0
NumberOfFormulaControlPoints=2
NumberOfSplineControlPoints=5
SplitMethod=0
Curve=0.120000

[Tonemap.fx]
Bleach=0.000000
Defog=0.020000
Exposure=0.040000
Gamma=1.000000
Saturation=0.050000
""",
    },
    "potato-boost": {
        "filename": "BeamNG_Potato_Boost.ini",
        "description": "Ультра-слабый / Картошка (CAS Sharpening, устраняет мыло без потери FPS)",
        "content": """PreprocessorDefinitions=
Techniques=CAS@CAS.fx
TechniqueSorting=CAS@CAS.fx

[CAS.fx]
Contrast=0.000000
Sharpening=0.600000
""",
    },
    "ultra-photoreal": {
        "filename": "BeamNG_Ultra_Photoreal.ini",
        "description": "Максимальный ультра-фотореализм (Full PostFX + Ambient Light + Filmic Tonemap)",
        "content": """PreprocessorDefinitions=
Techniques=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx,Colourfulness@Colourfulness.fx,AmbientLight@AmbientLight.fx,EyeAdaptation@EyeAdaptation.fx
TechniqueSorting=CAS@CAS.fx,Curves@Curves.fx,Tonemap@Tonemap.fx,Colourfulness@Colourfulness.fx,AmbientLight@AmbientLight.fx,EyeAdaptation@EyeAdaptation.fx

[CAS.fx]
Contrast=0.000000
Sharpening=0.400000

[Curves.fx]
Formula=0
Mode=0
NumberOfFormulaControlPoints=2
NumberOfSplineControlPoints=5
SplitMethod=0
Curve=0.180000

[Tonemap.fx]
Bleach=0.000000
Defog=0.010000
Exposure=0.060000
Gamma=1.020000
Saturation=0.100000

[Colourfulness.fx]
colourfulness=0.200000
lim_luma=0.750000

[AmbientLight.fx]
alInt=1.500000
alThreshold=12.000000
alAdapt=0.800000

[EyeAdaptation.fx]
fAdp_Speed=1.500000
fAdp_Brighten=1.000000
fAdp_Darken=1.200000
""",
    },
}

# Aliases
RESHADE_PRESETS["medium"] = RESHADE_PRESETS["medium-optimal"]
RESHADE_PRESETS["low"] = RESHADE_PRESETS["low-fast"]
RESHADE_PRESETS["potato"] = RESHADE_PRESETS["potato-boost"]
RESHADE_PRESETS["ultra"] = RESHADE_PRESETS["ultra-photoreal"]


def detect_reshade_installation(search_dirs: List[Path]) -> Optional[Path]:
    """Detect if ReShade is installed in any of the candidate directories."""
    markers = ("ReShade.ini", "dxgi.dll", "ReShade64.dll", "opengl32.dll", "d3d11.dll", "reshade-shaders")
    for d in search_dirs:
        if not d.exists() or not d.is_dir():
            continue
        for m in markers:
            target = d / m
            if target.exists():
                return target.parent
    return None


def deploy_reshade_preset(
    target_dir: Path,
    preset_name: str = "medium-optimal",
    dry_run: bool = False,
) -> Tuple[bool, str, Optional[Path]]:
    """Deploy the selected ReShade preset .ini file into target_dir.

    Args:
        target_dir: Directory where presets or game files reside.
        preset_name: Key in RESHADE_PRESETS ('medium-optimal', 'low-fast', 'potato-boost', 'ultra-photoreal').
        dry_run: Simulate without writing.

    Returns:
        (success, message, preset_path)
    """
    preset = RESHADE_PRESETS.get(preset_name.lower())
    if not preset:
        valid_keys = [k for k in RESHADE_PRESETS.keys() if "-" in k]
        return False, f"Unknown ReShade preset '{preset_name}'. Valid: {', '.join(valid_keys)}", None

    out_file = target_dir / preset["filename"]

    if dry_run:
        return True, f"[Dry-Run] Would deploy ReShade preset '{preset_name}' to {out_file}", out_file

    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Atomic write
        tmp_file = out_file.with_suffix(".tmp")
        tmp_file.write_text(preset["content"], encoding="utf-8")
        tmp_file.replace(out_file)

        # Also update ReShade.ini if present in target_dir or parent
        _update_reshade_ini_current_preset(target_dir, out_file)

        return True, f"ReShade preset '{preset['filename']}' ({preset['description']}) successfully deployed.", out_file
    except Exception as e:
        logger.warning("Failed deploying ReShade preset %s: %s", out_file, e)
        return False, f"Failed deploying ReShade preset: {e}", None


def deploy_all_reshade_presets(
    target_dir: Path,
    dry_run: bool = False,
) -> List[Path]:
    """Deploy all 4 ReShade preset files into target_dir."""
    deployed: List[Path] = []
    keys = ("medium-optimal", "low-fast", "potato-boost", "ultra-photoreal")
    for k in keys:
        ok, _, p = deploy_reshade_preset(target_dir, preset_name=k, dry_run=dry_run)
        if ok and p:
            deployed.append(p)
    return deployed


def _update_reshade_ini_current_preset(search_dir: Path, preset_path: Path) -> None:
    """Update CurrentPresetPath in ReShade.ini if it exists."""
    candidates = (
        search_dir / "ReShade.ini",
        search_dir.parent / "ReShade.ini",
    )
    for cfg in candidates:
        if cfg.exists() and cfg.is_file():
            try:
                lines = cfg.read_text(encoding="utf-8", errors="ignore").splitlines()
                updated = False
                new_lines = []
                for line in lines:
                    if line.strip().lower().startswith("currentpresetpath="):
                        new_lines.append(f"CurrentPresetPath={preset_path.resolve()}")
                        updated = True
                    else:
                        new_lines.append(line)
                if not updated:
                    new_lines.append(f"CurrentPresetPath={preset_path.resolve()}")
                cfg.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception:
                pass
