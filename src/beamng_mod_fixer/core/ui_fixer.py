"""UI error detection, rogue UI neutralization, and JSON repair engine for BeamNG.drive.

Resolves:
- 'UI error while loading. Try launching the game in Safe Mode (mods disabled)'
- Obsolete core UI script overrides (e.g. ancient AngularJS ui/modules/loading/loading.js in vehicle mods)
- Unauthorized overrides of core CEF entrypoints (ui/entrypoints/*, ui/index.html)
- Corrupt info.json, mod_info.json, and model_info.json files (trailing commas, unquoted keys, comments)
- Nested container ZIP archives containing inner mod ZIPs (e.g. *_UNZIP.zip packs)
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import zipfile

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

# List of critical core UI file paths that mods should NEVER override.
# Overriding these causes the BeamNG CEF bootloader to crash or time out.
ROGUE_CORE_UI_PATTERNS = [
    # The notorious culprit: overrides game loading screen with obsolete 2016 Angular 1.x script
    re.compile(r"^ui/modules/loading/loading\.js$", re.IGNORECASE),
    # Core bootloader and entrypoints
    re.compile(r"^ui/entrypoints/.*", re.IGNORECASE),
    re.compile(r"^ui/index\.html$", re.IGNORECASE),
    re.compile(r"^ui/ui-vue/.*", re.IGNORECASE),
    re.compile(r"^ui/common/.*", re.IGNORECASE),
]


def is_rogue_ui_entry(entry_name: str) -> bool:
    """Check if an archive entry path represents a conflicting core game UI file.

    Allowed UI files in mods:
    - Custom vehicle dashboard screens (e.g. vehicles/car/RadarScreen/radar.html)
    - Custom UI app modules inside their own subfolder (ui/modules/apps/<app_name>/*)
    - Loading screen wallpaper photos (ui/modules/loading/drive/*.jpg)

    Disallowed UI files (rogue overrides):
    - ui/modules/loading/loading.js (destroys modern 0.30+ Vue loading readiness)
    - ui/entrypoints/*
    - ui/index.html
    - ui/ui-vue/*
    """
    normalized = entry_name.replace("\\", "/").strip().lstrip("/")
    normalized_lower = normalized.lower()

    # Fast-path check: does not start with ui/
    if not normalized_lower.startswith("ui/"):
        return False

    # Safe exceptions: loading background images
    if normalized_lower.startswith("ui/modules/loading/drive/") and normalized_lower.endswith((".jpg", ".png", ".dds", ".jpeg")):
        return False

    # Check against rogue core patterns
    for pat in ROGUE_CORE_UI_PATTERNS:
        if pat.match(normalized):
            return True

    return False


def strip_json_comments(text: str) -> str:
    """Safely strip single-line (//) and multi-line (/* */) comments from JSON strings.

    Preserves strings that contain comment delimiters (e.g. "http://...").
    """
    result = []
    i = 0
    length = len(text)
    in_string = False
    string_char = ""
    escape = False

    while i < length:
        char = text[i]

        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == string_char:
                in_string = False
            i += 1
            continue

        if char in ('"', "'"):
            in_string = True
            string_char = char
            result.append(char)
            i += 1
            continue

        # Check for single-line comment //
        if char == "/" and i + 1 < length and text[i + 1] == "/":
            i += 2
            while i < length and text[i] not in ("\r", "\n"):
                i += 1
            continue

        # Check for multi-line comment /* */
        if char == "/" and i + 1 < length and text[i + 1] == "*":
            i += 2
            while i + 1 < length and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2  # skip closing */
            continue

        result.append(char)
        i += 1

    return "".join(result)


def fix_info_json_content(
    content: str,
    filename: str = "info.json"
) -> Tuple[str, bool, List[DiagnosticNotice]]:
    """Sanitize and repair malformed info.json, mod_info.json, or model_info.json files.

    Fixes:
    - BOM (Byte Order Mark) markers
    - JS/C++ style comments (// and /* */)
    - Trailing commas in arrays and objects (, } or , ])
    - Unquoted or single-quoted object keys ({ key: "val" } -> { "key": "val" })
    - Invalid control characters (ASCII 0-31) inside strings
    - Missing commas between key-value pairs
    - Trailing garbage after the closing brace

    Returns:
        Tuple[str, bool, List[DiagnosticNotice]]:
            (repaired_json, was_modified, diagnostics)
    """
    diagnostics: List[DiagnosticNotice] = []

    # Strip BOM
    clean_text = content.lstrip("\ufeff")
    was_modified = clean_text != content

    # Check if already strictly valid JSON
    try:
        json.loads(clean_text)
        if not was_modified:
            return content, False, []
    except Exception:
        pass

    fixed = clean_text

    # 1. Strip comments
    text_no_comments = strip_json_comments(fixed)
    if text_no_comments != fixed:
        fixed = text_no_comments
        was_modified = True

    # 2. Strip unescaped ASCII control characters (0x00-0x1F except \t, \n, \r)
    sanitized_chars = []
    for c in fixed:
        if ord(c) < 32 and c not in ("\t", "\n", "\r"):
            was_modified = True
            continue
        sanitized_chars.append(c)
    fixed = "".join(sanitized_chars)

    # 3. Replace single quotes around keys and string values
    # Match single-quoted strings: 'something' -> "something"
    def _replace_single_quotes(m: re.Match) -> str:
        inner = m.group(1).replace('"', '\\"')
        return f'"{inner}"'

    fixed_quotes = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", _replace_single_quotes, fixed)
    if fixed_quotes != fixed:
        fixed = fixed_quotes
        was_modified = True

    # 4. Quote unquoted keys: { key: "val" } or , key: "val"
    # Matches alphanumeric or underscore identifier followed by colon
    unquoted_key_pattern = re.compile(
        r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_\-\.]*)\s*:'
    )
    fixed_keys = unquoted_key_pattern.sub(r'\1"\2":', fixed)
    if fixed_keys != fixed:
        fixed = fixed_keys
        was_modified = True

    # 5. Fix trailing commas before } or ]
    trailing_comma_pattern = re.compile(r',\s*([\]}])')
    fixed_commas = trailing_comma_pattern.sub(r'\1', fixed)
    if fixed_commas != fixed:
        fixed = fixed_commas
        was_modified = True

    # 6. Fix missing commas between properties (e.g. "prop1": "val" \n "prop2": "val")
    missing_comma_pattern = re.compile(
        r'("(?:[^"\\]|\\.)*"\s*:\s*(?:"(?:[^"\\]|\\.)*"|[-0-9\.]+|true|false|null|[\]\}]))\s*\n(\s*"[a-zA-Z0-9_\-\.]+"\s*:)'
    )
    fixed_missing = missing_comma_pattern.sub(r'\1,\n\2', fixed)
    if fixed_missing != fixed:
        fixed = fixed_missing
        was_modified = True

    # 7. Strip trailing garbage after the last closing brace/bracket
    last_brace = fixed.rfind("}")
    last_bracket = fixed.rfind("]")
    cut_point = max(last_brace, last_bracket)
    if cut_point != -1 and cut_point < len(fixed) - 1:
        trailing = fixed[cut_point + 1 :].strip()
        if trailing:
            fixed = fixed[: cut_point + 1]
            was_modified = True

    # Validate output with json.loads
    try:
        parsed = json.loads(fixed)
        # Re-encode as formatted JSON to ensure 100% CEF compliance
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message=f"Repaired malformed JSON syntax in '{filename}'",
                file_path=filename,
            )
        )
        return formatted, True, diagnostics
    except Exception as err:
        logger.debug("Could not fully re-parse '%s' after JSON repairs: %s", filename, err)
        # If still failing, return fixed draft with warning notice
        if was_modified:
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message=f"Partially sanitized JSON in '{filename}': {err}",
                    file_path=filename,
                )
            )
            return fixed, True, diagnostics
        return content, False, []


def unpack_container_mod_archives(
    mods_dir: Path,
    dry_run: bool = False
) -> List[Tuple[Path, List[str]]]:
    """Scan mods_dir for container ZIP files containing other ZIP files and unpack them.

    For example, packs named 'Nissan_Silvia_S15_v1.7_UNZIP.zip' or mod bundles that
    contain inner .zip archives. BeamNG cannot mount archives-within-archives.

    Args:
        mods_dir: Path to the BeamNG mods directory.
        dry_run: If True, only identifies container archives without modifying files.

    Returns:
        List of tuples: (container_path, list_of_extracted_mod_names)
    """
    results: List[Tuple[Path, List[str]]] = []

    if not mods_dir.exists() or not mods_dir.is_dir():
        return results

    for zip_path in mods_dir.glob("*.zip"):
        # Skip empty / truncated files
        try:
            if zip_path.stat().st_size < 64:
                continue
        except OSError:
            continue

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                inner_zips = [
                    name for name in zf.namelist()
                    if name.lower().endswith(".zip") and not name.startswith("__MACOSX")
                ]

                # Check if this archive is a container (contains at least one .zip and no direct vehicles/levels)
                has_direct_game_assets = any(
                    name.lower().startswith(("vehicles/", "levels/", "art/"))
                    for name in zf.namelist()
                )

                # If it has inner zips and (has UNZIP in name OR no direct game assets):
                is_container = bool(inner_zips) and (
                    "unzip" in zip_path.name.lower() or not has_direct_game_assets
                )

                if not is_container:
                    continue

                extracted_names: List[str] = []
                for inner_zip_name in inner_zips:
                    # Clean filename (flatten folders inside container)
                    target_name = Path(inner_zip_name).name
                    target_path = mods_dir / target_name

                    if not dry_run:
                        data = zf.read(inner_zip_name)
                        target_path.write_bytes(data)
                    extracted_names.append(target_name)

            # Outside with block: file handle is closed, safe to rename on Windows
            if extracted_names:
                results.append((zip_path, extracted_names))
                if not dry_run:
                    # Rename the container so BeamNG doesn't try to load it as an invalid mod
                    disabled_path = zip_path.with_suffix(".zip.extracted")
                    try:
                        if disabled_path.exists():
                            disabled_path.unlink()
                        zip_path.rename(disabled_path)
                    except OSError as e:
                        logger.warning("Could not rename container %s: %s", zip_path, e)

        except Exception as err:
            logger.debug("Error checking container status of %s: %s", zip_path, err)

    return results
