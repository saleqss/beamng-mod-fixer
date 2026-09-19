"""Materials & Texture Doctor for BeamNG.drive mods.

Provides:
- Conversion of legacy TorqueScript `materials.cs` to modern `main.materials.json` (v1.5 PBR).
- Detection and repair of orange "NO TEXTURE" issues caused by broken VFS paths or legacy formatting.
- Path normalization: Windows backslashes `\\` -> `/`, leading slash removal for VFS compatibility.
- Texture reconciliation: automatic .png <-> .dds correction and local texture path resolution.
- Emissive glow and lighting material repair for modern PBR clustered forward renderer.
"""

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

# Regular expressions for TorqueScript materials.cs parsing
RE_CS_COMMENT_SINGLE = re.compile(r'//[^\n]*')
RE_CS_COMMENT_MULTI = re.compile(r'/\*[\s\S]*?\*/')

RE_CS_MATERIAL_BLOCK = re.compile(
    r'(?i)(?:singleton|new)\s+Material\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\{([^}]+)\};'
)

RE_CS_PROPERTY = re.compile(
    r'^\s*([a-zA-Z0-9_]+)(?:\[(\d+)\])?\s*=\s*(.*?)\s*;',
    re.MULTILINE
)

# Emissive and lighting material keywords
LIGHT_MATERIAL_KEYWORDS = (
    "headlight", "highbeam", "lowbeam", "taillight", "brakelight", "brake_light",
    "signal", "turnsignal", "foglight", "fog_light", "reverse", "reverselight",
    "glow", "gauge", "gauges", "cluster", "interior_light", "lightbar", "siren"
)


def _strip_cs_quotes(val: str) -> str:
    """Strip surrounding quotes from a TorqueScript property value."""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    return val


def parse_materials_cs(cs_content: str) -> Dict[str, Dict[str, Any]]:
    """Parse TorqueScript materials.cs content into structured material definitions.

    Args:
        cs_content: Raw text content of a materials.cs file.

    Returns:
        Dict mapping material names to their parsed properties.
    """
    # Remove comments while preserving string structure
    clean_text = RE_CS_COMMENT_MULTI.sub('', cs_content)
    clean_text = RE_CS_COMMENT_SINGLE.sub('', clean_text)

    materials: Dict[str, Dict[str, Any]] = {}

    for match in RE_CS_MATERIAL_BLOCK.finditer(clean_text):
        mat_name = match.group(1).strip()
        body = match.group(2)

        props: Dict[str, Any] = {
            "stages": [{}, {}, {}, {}],
            "translucent": False,
            "doubleSided": False,
            "alphaTest": False,
            "alphaRef": 0,
        }

        for prop_match in RE_CS_PROPERTY.finditer(body):
            key = prop_match.group(1).strip()
            idx_str = prop_match.group(2)
            val_raw = _strip_cs_quotes(prop_match.group(3).strip())

            stage_idx = int(idx_str) if idx_str is not None else 0
            if stage_idx < 0 or stage_idx > 3:
                continue

            stage = props["stages"][stage_idx]

            key_lower = key.lower()
            if key_lower == "mapto":
                props["mapTo"] = val_raw
            elif key_lower in ("diffusemap", "colormap"):
                stage["colorMap"] = val_raw.replace("\\", "/").lstrip("/")
            elif key_lower == "normalmap":
                stage["normalMap"] = val_raw.replace("\\", "/").lstrip("/")
            elif key_lower in ("specularmap", "roughnessmap"):
                stage["roughnessMap"] = val_raw.replace("\\", "/").lstrip("/")
                stage["metallicMap"] = val_raw.replace("\\", "/").lstrip("/")
            elif key_lower == "specularpower":
                try:
                    pwr = float(val_raw)
                    stage["roughnessFactor"] = max(0.05, min(1.0, round(1.0 - (pwr / 128.0), 2)))
                except ValueError:
                    stage["roughnessFactor"] = 0.5
            elif key_lower == "translucent":
                props["translucent"] = val_raw.lower() in ("true", "1")
            elif key_lower == "doublesided":
                props["doubleSided"] = val_raw.lower() in ("true", "1")
            elif key_lower == "alphatest":
                props["alphaTest"] = val_raw.lower() in ("true", "1")
            elif key_lower in ("glow", "emissive"):
                is_glow = val_raw.lower() in ("true", "1")
                if is_glow:
                    stage["emissiveFactor"] = [1.0, 1.0, 1.0]

        if "mapTo" not in props:
            props["mapTo"] = mat_name

        materials[mat_name] = props

    return materials


def convert_materials_cs_to_json(
    cs_content: str,
    vehicle_folder: str = "",
    filename: str = ""
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Convert legacy TorqueScript materials.cs into modern BeamNG main.materials.json (v1.5).

    Args:
        cs_content: Raw text content of materials.cs.
        vehicle_folder: Optional base folder name for fallback paths (e.g. 'vehicles/mycar/').
        filename: Optional filename for diagnostics.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - json_content: Formatted JSON string ready to save as main.materials.json.
            - converted_count: Number of material blocks converted.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    parsed_mats = parse_materials_cs(cs_content)
    if not parsed_mats:
        return "{}", 0, diagnostics

    modern_materials: Dict[str, Any] = {}
    converted_count = 0

    for mat_name, props in parsed_mats.items():
        converted_count += 1
        stages: List[Dict[str, Any]] = []

        for st in props.get("stages", []):
            if not st:
                stages.append({})
                continue

            stage_dict: Dict[str, Any] = {}
            if "colorMap" in st:
                stage_dict["colorMap"] = st["colorMap"]
            if "normalMap" in st:
                stage_dict["normalMap"] = st["normalMap"]
            if "roughnessMap" in st:
                stage_dict["roughnessMap"] = st["roughnessMap"]
            if "metallicMap" in st:
                stage_dict["metallicMap"] = st["metallicMap"]

            stage_dict["roughnessFactor"] = st.get("roughnessFactor", 0.5)
            stage_dict["metallicFactor"] = st.get("metallicFactor", 0.0)

            # Detect emissive light requirement
            is_light = any(kw in mat_name.lower() or kw in props.get("mapTo", "").lower() for kw in LIGHT_MATERIAL_KEYWORDS)
            if is_light or "emissiveFactor" in st:
                stage_dict["emissiveFactor"] = st.get("emissiveFactor", [1.0, 1.0, 1.0])
                stage_dict["useColorPalette"] = False

            stages.append(stage_dict)

        # Pad stages to exactly 4 as required by Torque3D PBR specification
        while len(stages) < 4:
            stages.append({})

        modern_materials[mat_name] = {
            "name": mat_name,
            "mapTo": props.get("mapTo", mat_name),
            "class": "Material",
            "Stages": stages,
            "translucent": props.get("translucent", False),
            "doubleSided": props.get("doubleSided", False),
            "alphaTest": props.get("alphaTest", False),
            "version": 1.5,
        }

        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message=f"Converted legacy materials.cs definition '{mat_name}' to modern PBR 1.5 material",
                file_path=filename,
                rule="material_cs_converted",
            )
        )

    json_str = json.dumps(modern_materials, indent=2, ensure_ascii=False)
    return json_str, converted_count, diagnostics


def _reconcile_texture_path(
    path_str: str,
    available_files: Optional[Set[str]] = None
) -> Tuple[str, bool]:
    """Normalize and reconcile texture paths against mod archive files.

    - Converts backslashes to forward slashes.
    - Strips leading slashes (/vehicles/... -> vehicles/...).
    - Checks for .png vs .dds existence in available_files.
    - If relative path is broken, searches available_files for matching basename.

    Returns:
        Tuple[str, bool]: (reconciled_path, changed)
    """
    if not path_str or not isinstance(path_str, str):
        return path_str, False

    # Skip engine procedural textures
    if path_str.startswith("#") or path_str.startswith("$"):
        return path_str, False

    orig = path_str
    # 1. Normalize slashes
    norm = path_str.replace("\\", "/").lstrip("/")
    # Clean multiple consecutive slashes
    norm = re.sub(r'/+', '/', norm)

    changed = (norm != orig)

    if available_files is None:
        return norm, changed

    norm_lower = norm.lower()
    available_lower = {f.lower().replace("\\", "/"): f for f in available_files}

    # If file exists directly
    if norm_lower in available_lower:
        matched_actual = available_lower[norm_lower]
        return matched_actual, (matched_actual != orig)

    # 2. Try PNG <-> DDS swap
    if norm_lower.endswith(".png"):
        dds_cand = norm_lower[:-4] + ".dds"
        if dds_cand in available_lower:
            return available_lower[dds_cand], True
    elif norm_lower.endswith(".dds"):
        png_cand = norm_lower[:-4] + ".png"
        if png_cand in available_lower:
            return available_lower[png_cand], True

    # 3. Basename lookup: if full VFS path has wrong folder prefix, find by filename in archive
    file_name = norm_lower.split("/")[-1]
    candidate_matches = [
        actual for low, actual in available_lower.items()
        if low.endswith("/" + file_name) or low == file_name
    ]
    if len(candidate_matches) == 1:
        # Unambiguous match found in archive!
        return candidate_matches[0], True

    return norm, changed


def fix_materials_json_content(
    content: str,
    filename: str = "",
    available_files: Optional[Set[str]] = None,
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Inspect and fix modern BeamNG main.materials.json.

    Repairs:
    - Obsolete or missing `version` (updates to 1.5).
    - Windows backslashes `\\` in texture paths.
    - Broken leading slashes.
    - Reconciles missing texture links (.png vs .dds, misplaced folder paths).
    - Emissive factor for light meshes to restore proper glow.

    Args:
        content: Raw JSON text content.
        filename: Optional filename for diagnostics.
        available_files: Optional set of archive file paths to reconcile against.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Patched JSON text.
            - fix_count: Number of material blocks fixed or modernized.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    if not content.strip():
        return content, 0, diagnostics

    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        # Fallback: line-by-line regex path repair if JSON has non-standard syntax
        repaired_content = content.replace("\\\\", "/").replace("\\", "/")
        if repaired_content != content:
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message=f"Repaired backslashes in non-standard JSON: {err}",
                    file_path=filename,
                    rule="materials_json_backslashes_repaired",
                )
            )
            return repaired_content, 1, diagnostics
        return content, 0, diagnostics

    if not isinstance(data, dict):
        return content, 0, diagnostics

    fix_count = 0
    modified = False

    for mat_name, mat_data in data.items():
        if not isinstance(mat_data, dict):
            continue

        mat_modified = False

        # 1. Update version to 1.5
        curr_ver = mat_data.get("version")
        if curr_ver is None or curr_ver < 1.5:
            mat_data["version"] = 1.5
            mat_modified = True
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Upgraded material '{mat_name}' version to modern BeamNG PBR 1.5",
                    file_path=filename,
                    rule="material_version_upgraded",
                )
            )

        # 2. Check and repair Stages
        stages = mat_data.get("Stages")
        if isinstance(stages, list):
            for stage_idx, stage in enumerate(stages):
                if not isinstance(stage, dict):
                    continue

                for map_key in ("colorMap", "normalMap", "roughnessMap", "metallicMap", "ambientOcclusionMap", "opacityMap"):
                    if map_key in stage and isinstance(stage[map_key], str):
                        raw_val = stage[map_key]
                        reconciled, changed = _reconcile_texture_path(raw_val, available_files)
                        if changed:
                            stage[map_key] = reconciled
                            mat_modified = True
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Reconciled {map_key} '{raw_val}' -> '{reconciled}' in material '{mat_name}'",
                                    file_path=filename,
                                    rule="material_texture_reconciled",
                                )
                            )

                # Check light emissive glow
                is_light = any(kw in mat_name.lower() or kw in mat_data.get("mapTo", "").lower() for kw in LIGHT_MATERIAL_KEYWORDS)
                if is_light:
                    if "emissiveFactor" not in stage or stage.get("emissiveFactor") in ([0, 0, 0], [0.0, 0.0, 0.0]):
                        stage["emissiveFactor"] = [1.0, 1.0, 1.0]
                        mat_modified = True
                        diagnostics.append(
                            DiagnosticNotice(
                                severity="info",
                                message=f"Restored emissive glow factor [1, 1, 1] on lighting material '{mat_name}'",
                                file_path=filename,
                                rule="material_emissive_restored",
                            )
                        )

        if mat_modified:
            fix_count += 1
            modified = True

    if not modified:
        return content, 0, diagnostics

    new_content = json.dumps(data, indent=2, ensure_ascii=False)
    return new_content, fix_count, diagnostics
