"""Core JBeam and Optics Engine for BeamNG Mod Fixer.

Provides robust, comment-preserving regular expression replacement of
`lightCastShadows: true` with `false`, optics validation and normalization
(flareName, cookieName, spotlight geometries), and multi-encoding decoding.
"""

import codecs
import re
from typing import List, Optional, Set, Tuple

from beamng_mod_fixer.core.rear_light_fixer import enhance_rear_light_content
from beamng_mod_fixer.models import DiagnosticNotice, JBeamFixResult


# ==============================================================================
# Regular Expressions for JBeam Parsing & Patching
# ==============================================================================

# Fast substring pre-check token
FAST_SHADOW_CHECK = "lightcastshadows"

# Robust regex matching lightCastShadows: true
# Capturing Group 1 captures:
# - key 'lightCastShadows' with matching quote pair (", ', `, or unquoted)
# - colon and any surrounding whitespace/tabs/newlines and inline/single-line comments
# Followed by truthy values: true (word-bounded), "true", 'true', `true`, or numeric 1
RE_LIGHT_CAST_SHADOWS = re.compile(
    r'(?i)(?<![-$\w])'
    r'((?P<q>[\"\'\`]?)\blightCastShadows\b(?P=q)'
    r'(?:\s|/\*[\s\S]*?\*/|//[^\n]*\n)*:'
    r'(?:\s|/\*[\s\S]*?\*/|//[^\n]*\n)*)'
    r'(?:["\'`](?:true|1)["\'`]|true\b|1\b)'
)

# Invalid flareName strings that cause Torque3D warnings ("none", "null", "undefined")
RE_INVALID_FLARE = re.compile(
    r'(?i)([\"\'\`]?\bflareName\b[\"\'\`]?\s*:\s*)(?:[\"\'`](?:none|null|undefined)[\"\'`]|(?:none|null|undefined)\b)'
)

# Invalid cookieName strings ("none", "null", "undefined")
RE_INVALID_COOKIE = re.compile(
    r'(?i)([\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*)(?:[\"\'`](?:none|null|undefined)[\"\'`]|(?:none|null|undefined)\b)'
)

# Obsolete cookie paths (e.g. art/shapes/lights/... from pre-PBR Torque3D)
RE_OBSOLETE_COOKIE = re.compile(
    r'(?i)[\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*[\"\'`](art/shapes/lights/[^\"\'`]+)[\"\'`]'
)

# General cookieName value extractor (preserving exact quotes)
RE_COOKIE_VALUE = re.compile(
    r'(?i)([\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*)([\"\'`])([^\"\'`]+)([\"\'`])'
)

# Spotlight angles
RE_INNER_ANGLE = re.compile(
    r'(?i)[\"\'\`]?\blightInnerAngle\b[\"\'\`]?\s*:\s*(-?\d+(?:\.\d+)?)'
)
RE_OUTER_ANGLE = re.compile(
    r'(?i)[\"\'\`]?\blightOuterAngle\b[\"\'\`]?\s*:\s*(-?\d+(?:\.\d+)?)'
)

# Modern official BeamNG headlight assets (Torque3D PBR Clustered Forward+)
MODERN_HEADLIGHT_COOKIE = "art/special/BNG_light_cookie_headlight.dds"
MODERN_HEADLIGHT_FLARE = "vehicleHeadLightFlare"
MODERN_HIGHBEAM_FLARE = "vehicleHighBeamFlare"
MODERN_FOG_FLARE = "vehicleFogLightFlare"

# Obsolete cookie path replacement (pre-PBR art/shapes/lights/* -> art/special/*)
RE_OBSOLETE_COOKIE_REPLACE = re.compile(
    r'(?i)([\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*[\"\'`])/*art/shapes/lights/[^\"\'`]+([\"\'`])'
)

# Cookie leading slash normalization: strip any leading slash from VFS cookies ("/path/..." -> "path/...")
RE_COOKIE_LEADING_SLASH = re.compile(
    r'(?i)([\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*[\"\'`])/+([^\"\'`]+)([\"\'`])'
)

# Obsolete .png extension for official headlight cookie
RE_COOKIE_PNG_HEADLIGHT = re.compile(
    r'(?i)([\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*[\"\'`])/*art[/\\]special[/\\]bng_light_cookie_headlight\.png([\"\'`])'
)

# Spotlight zero or non-positive brightness and range
RE_ZERO_BRIGHTNESS = re.compile(
    r'(?i)([\"\'\`]?\blightBrightness\b[\"\'\`]?\s*:\s*)(-\d+(?:\.\d+)?|0(?:\.0+)?)(?![.\d])'
)
RE_ZERO_RANGE = re.compile(
    r'(?i)([\"\'\`]?\blightRange\b[\"\'\`]?\s*:\s*)(-\d+(?:\.\d+)?|0(?:\.0+)?)(?![.\d])'
)

# Legacy flare names replacement
RE_LEGACY_FLARES = re.compile(
    r'(?i)([\"\'\`]?\bflareName\b[\"\'\`]?\s*:\s*[\"\'`])(headlightFlare|highbeamFlare|fogFlare)([\"\'`])'
)

# Misspelled or non-standard electrics signal names in spotlight table rows (preserving valid headlight/lights signals)
RE_ELECTRICS_ROW = re.compile(
    r'(?i)(\[\s*[\"\'`])(low_beam|lowBeam|low_beams|high_beam|highBeam|high_beams|fog_light|foglight|fog_lights|reverse_light|reverselight)([\"\'`]\s*,)'
)


# ==============================================================================
# Encoding Handler Functions
# ==============================================================================

def decode_jbeam_bytes(data: bytes) -> Tuple[str, str]:
    """Safely decode raw bytes of a .jbeam file to a Python string.

    Supports:
    - UTF-8 with BOM (utf-8-sig)
    - Standard UTF-8
    - CP1252 (Western European Latin) and CP1251 (Cyrillic CIS mods) via smart heuristic
    - Latin-1 with surrogateescape fallback

    Returns:
        Tuple[str, str]: (decoded_content, detected_encoding)
    """
    if not data:
        return "", "utf-8"

    # 1. Check for UTF-8 BOM
    if data.startswith(codecs.BOM_UTF8):
        try:
            return data.decode("utf-8-sig"), "utf-8-sig"
        except UnicodeDecodeError:
            pass

    # 2. Try standard UTF-8 (strict)
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    # 3. Decode non-UTF8 single-byte content (CP1252 vs CP1251 vs Latin-1)
    text_1252: Optional[str] = None
    try:
        text_1252 = data.decode("cp1252")
    except UnicodeDecodeError:
        pass

    text_1251: Optional[str] = None
    try:
        text_1251 = data.decode("cp1251")
    except UnicodeDecodeError:
        pass

    if text_1252 is not None and text_1251 is None:
        return text_1252, "cp1252"
    if text_1251 is not None and text_1252 is None:
        return text_1251, "cp1251"

    if text_1251 is not None and text_1252 is not None:
        # Both succeed on single-byte stream. Distinguish Cyrillic vs Western European.
        # Check if text_1251 has valid Cyrillic words (sequences of 2+ Cyrillic letters)
        # and does not form unnatural Latin-Cyrillic hybrid words (e.g. "Spйcial").
        mixed_word_count = len(re.findall(r'[a-zA-Z][\u0400-\u04FF]|[\u0400-\u04FF][a-zA-Z]', text_1251))
        cyrillic_word_count = len(re.findall(r'[\u0400-\u04FF]{2,}', text_1251))

        if cyrillic_word_count > 0 and mixed_word_count == 0:
            return text_1251, "cp1251"
        if mixed_word_count > 0 and cyrillic_word_count == 0:
            return text_1252, "cp1252"
        if cyrillic_word_count > mixed_word_count:
            return text_1251, "cp1251"
        return text_1252, "cp1252"

    # 4. Guaranteed fallback: Latin-1 with surrogateescape
    return data.decode("latin-1", errors="surrogateescape"), "latin-1"


def encode_jbeam_str(
    text: str,
    encoding: str = "utf-8",
    with_bom: bool = False
) -> bytes:
    """Encode a JBeam string back to bytes preserving encoding and BOM if needed.

    Args:
        text: Decoded JBeam content string.
        encoding: Target encoding name (e.g. 'utf-8', 'utf-8-sig', 'cp1251').
        with_bom: If True or if encoding is 'utf-8-sig', output includes UTF-8 BOM.

    Returns:
        bytes: Encoded byte stream.
    """
    enc_lower = encoding.lower().replace("-", "").replace("_", "")
    if enc_lower == "utf8sig" or with_bom:
        return text.encode("utf-8-sig")

    try:
        return text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return text.encode("utf-8")


# ==============================================================================
# Detection and Optics Diagnostics
# ==============================================================================

def _is_inside_string_literal(text: str, pos: int) -> bool:
    """Check if character index `pos` is inside an active string literal on its line."""
    line_start = text.rfind("\n", 0, pos) + 1
    prefix = text[line_start:pos]

    in_quote: Optional[str] = None
    in_block_comment = False
    i = 0
    n = len(prefix)

    while i < n:
        c = prefix[i]
        if in_quote is not None:
            if c == "\\":
                i += 2  # skip escaped character
                continue
            elif c == in_quote:
                in_quote = None
        elif in_block_comment:
            if c == "*" and i + 1 < n and prefix[i + 1] == "/":
                in_block_comment = False
                i += 2
                continue
        else:
            if c in ('"', "'", "`"):
                in_quote = c
            elif c == "/" and i + 1 < n:
                if prefix[i + 1] == "/":
                    # Single-line comment: rest of the line is a comment
                    break
                elif prefix[i + 1] == "*":
                    in_block_comment = True
                    i += 2
                    continue
        i += 1

    return in_quote is not None


def detect_light_cast_shadows(content: str) -> bool:
    """Quickly check if JBeam content contains `lightCastShadows: true` (or truthy variant).

    Uses a fast substring pre-filter before executing the compiled regular expression.

    Args:
        content: Raw JBeam file text content.

    Returns:
        bool: True if at least one un-fixed lightCastShadows property is found.
    """
    if FAST_SHADOW_CHECK not in content.lower():
        return False
    for m in RE_LIGHT_CAST_SHADOWS.finditer(content):
        if not _is_inside_string_literal(content, m.start()):
            return True
    return False


def _is_highbeam_context(text: str, pos: int) -> bool:
    """Determine whether a lightCastShadows property instance belongs to a highbeam light.

    In modern BeamNG (0.28+ / 0.30+ Clustered Forward+ PBR), highbeams MUST retain
    lightCastShadows: true to avoid severe light bleeding through the dashboard/interior
    into the driver cockpit and to maintain environmental dynamic shadows.
    """
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    if line_end == -1:
        line_end = len(text)
    line_content = text[line_start:line_end].lower()

    if any(tok in line_content for tok in ("highbeam", "high_beam", "high_beams")):
        return True

    dict_start = text.rfind("{", 0, pos)
    if dict_start != -1:
        depth = 0
        dict_end = len(text)
        for idx in range(dict_start, min(len(text), dict_start + 1500)):
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
                if depth == 0:
                    dict_end = idx + 1
                    break
        dict_body = text[dict_start:dict_end].lower()
        if "highbeam" in dict_body or "high_beam" in dict_body or "vehiclehighbeamflare" in dict_body:
            return True

        prefix_block = text[max(0, dict_start - 250):dict_start].lower()
        last_bracket = prefix_block.rfind("[")
        if last_bracket != -1:
            row_prefix = prefix_block[last_bracket:]
            if any(tok in row_prefix for tok in ("highbeam", "high_beam", "high_beams")):
                return True

        after_dict = text[dict_end:min(len(text), dict_end + 1000)]
        next_brace = after_dict.find("{")
        valid_after = after_dict[:next_brace] if next_brace != -1 else after_dict
        valid_after_lower = valid_after.lower()

        has_hb = any(tok in valid_after_lower for tok in ("\"highbeam", "'highbeam", "`highbeam", "highbeam_"))
        has_lb = any(tok in valid_after_lower for tok in ("\"lowbeam", "'lowbeam", "`lowbeam", "lowbeam_", "headlight"))
        if has_hb and not has_lb:
            return True

    return False


def repair_spotlight_angles(content: str) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Detect and repair inverted, zero, or negative spotlight angles.

    In Torque3D spotlight math, when innerAngle >= outerAngle or angles are non-positive,
    the cosine falloff division results in zero or negative light intensity, extinguishing the spotlight.
    """
    diags: List[DiagnosticNotice] = []
    fixed_text = content
    repairs = 0

    re_angle_pair = re.compile(
        r'(?i)([\"\'\`]?lightInnerAngle[\"\'\`]?\s*:\s*)(-?\d+(?:\.\d+)?)([\s\S]{1,300}?)([\"\'\`]?lightOuterAngle[\"\'\`]?\s*:\s*)(-?\d+(?:\.\d+)?)'
    )
    re_reverse_pair = re.compile(
        r'(?i)([\"\'\`]?lightOuterAngle[\"\'\`]?\s*:\s*)(-?\d+(?:\.\d+)?)([\s\S]{1,300}?)([\"\'\`]?lightInnerAngle[\"\'\`]?\s*:\s*)(-?\d+(?:\.\d+)?)'
    )

    def _compute_valid_angles(inner_val: float, outer_val: float) -> Tuple[float, float, bool]:
        if inner_val <= 0 and outer_val <= 0:
            return 40.0, 65.0, True
        elif inner_val <= 0 and outer_val > 0:
            new_outer = outer_val
            new_inner = min(40.0, round(outer_val * 0.6, 1))
            return new_inner, new_outer, True
        elif inner_val > 0 and outer_val <= 0:
            new_inner = inner_val
            new_outer = max(65.0, round(inner_val * 1.5, 1))
            return new_inner, new_outer, True
        elif inner_val >= outer_val:
            new_inner = min(inner_val, outer_val)
            new_outer = max(inner_val, outer_val)
            if new_inner == new_outer:
                new_inner = round(new_outer * 0.6, 1)
            return new_inner, new_outer, True
        return inner_val, outer_val, False

    def _fix_pair(m: re.Match) -> str:
        nonlocal repairs
        inner_val = float(m.group(2))
        outer_val = float(m.group(5))
        new_inner, new_outer, changed = _compute_valid_angles(inner_val, outer_val)
        if changed:
            repairs += 1
            diags.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Repaired invalid spotlight angles from inner={inner_val}, outer={outer_val} to inner={new_inner}, outer={new_outer}",
                    rule="spotlight_angle_repaired",
                )
            )
            return f"{m.group(1)}{new_inner}{m.group(3)}{m.group(4)}{new_outer}"
        return m.group(0)

    fixed_text = re_angle_pair.sub(_fix_pair, fixed_text)

    def _fix_rev_pair(m: re.Match) -> str:
        nonlocal repairs
        outer_val = float(m.group(2))
        inner_val = float(m.group(5))
        new_inner, new_outer, changed = _compute_valid_angles(inner_val, outer_val)
        if changed:
            repairs += 1
            diags.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Repaired invalid spotlight angles from inner={inner_val}, outer={outer_val} to inner={new_inner}, outer={new_outer}",
                    rule="spotlight_angle_repaired",
                )
            )
            return f"{m.group(1)}{new_outer}{m.group(3)}{m.group(4)}{new_inner}"
        return m.group(0)

    fixed_text = re_reverse_pair.sub(_fix_rev_pair, fixed_text)
    return fixed_text, repairs, diags


def normalize_electrics_signals(content: str) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Normalize misspelled or non-standard electrics signal names in spotlight table rows."""
    diags: List[DiagnosticNotice] = []
    count = 0

    def _replace_electrics(m: re.Match) -> str:
        nonlocal count
        prefix = m.group(1)
        raw_name = m.group(2)
        name_lower = raw_name.lower()
        suffix = m.group(3)

        if name_lower in ("low_beam", "lowbeam", "low_beams"):
            target = "lowbeam"
        elif name_lower in ("high_beam", "highbeam", "high_beams"):
            target = "highbeam"
        elif name_lower in ("fog_light", "foglight", "fog_lights"):
            target = "fog"
        elif name_lower in ("reverse_light", "reverselight"):
            target = "reverse"
        else:
            return m.group(0)

        if raw_name != target:
            count += 1
            diags.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Normalized electrics signal '{raw_name}' to '{target}' in spotlight row",
                    rule="electrics_signal_normalized",
                )
            )
            return f"{prefix}{target}{suffix}"
        return m.group(0)

    fixed_text = RE_ELECTRICS_ROW.sub(_replace_electrics, content)
    return fixed_text, count, diags


def repair_spotlight_brightness_and_range(content: str) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Detect and repair zero or non-positive spotlight brightness and range."""
    diags: List[DiagnosticNotice] = []
    fixed_text = content
    repairs = 0

    def _fix_brightness(m: re.Match) -> str:
        nonlocal repairs
        repairs += 1
        diags.append(
            DiagnosticNotice(
                severity="info",
                message="Repaired non-positive lightBrightness to standard 0.75",
                rule="spotlight_brightness_repaired",
            )
        )
        return f"{m.group(1)}0.75"

    fixed_text = RE_ZERO_BRIGHTNESS.sub(_fix_brightness, fixed_text)

    def _fix_range(m: re.Match) -> str:
        nonlocal repairs
        repairs += 1
        diags.append(
            DiagnosticNotice(
                severity="info",
                message="Repaired non-positive lightRange to standard 70.0",
                rule="spotlight_range_repaired",
            )
        )
        return f"{m.group(1)}70.0"

    fixed_text = RE_ZERO_RANGE.sub(_fix_range, fixed_text)
    return fixed_text, repairs, diags


def audit_spotlights(
    content: str,
    filename: str = "",
    available_files: Optional[Set[str]] = None
) -> List[DiagnosticNotice]:
    """Audit JBeam content for broken or malformed optics and spotlight definitions.

    Checks for:
    - Invalid flareName (e.g. 'none', 'null')
    - Obsolete cookie texture paths ('art/shapes/lights/...')
    - Broken local cookie texture references not in the archive
    - Inverted spotlight angles (innerAngle > outerAngle or negative angles)
    - Malformed spotlight array definition rows

    Args:
        content: Raw JBeam text content.
        filename: Optional path or name of the file being audited for diagnostics.
        available_files: Optional set of all file paths inside the containing archive.

    Returns:
        List[DiagnosticNotice]: List of diagnostic notices found.
    """
    diagnostics: List[DiagnosticNotice] = []

    # 1. Check for invalid flareName
    for match in RE_INVALID_FLARE.finditer(content):
        val_str = match.group(0).split(":")[-1].strip().strip("\"'`")
        diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"Invalid flareName '{val_str}' detected; Torque3D requires valid flare asset or empty string.",
                file_path=filename,
                rule="flare_name_invalid",
            )
        )

    # 2. Check for obsolete cookie paths (Torque3D pre-PBR)
    for match in RE_OBSOLETE_COOKIE.finditer(content):
        cookie_path = match.group(1)
        diagnostics.append(
            DiagnosticNotice(
                severity="warning",
                message=f"Obsolete cookie path '{cookie_path}' detected. Modern BeamNG cookies are in 'art/special/'.",
                file_path=filename,
                rule="cookie_path_obsolete",
            )
        )

    # 3. Check for missing local cookie textures if archive contents provided
    if available_files is not None:
        normalized_archive_files = {
            f.lower().replace("\\", "/") for f in available_files
        }
        for match in RE_COOKIE_VALUE.finditer(content):
            cookie_val = match.group(3).strip()
            # Ignore Lua expressions (starting with $)
            if cookie_val.startswith("$"):
                continue
            cookie_norm = cookie_val.lower().replace("\\", "/").lstrip("/")
            # Ignore base game official cookies
            if cookie_norm.startswith("art/special/") or cookie_norm.startswith("art/"):
                continue
            # Check local vehicle cookie paths
            if cookie_norm and cookie_norm not in normalized_archive_files:
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f"Cookie texture '{cookie_val}' referenced in JBeam not found in mod archive.",
                        file_path=filename,
                        rule="cookie_file_missing",
                    )
                )

    # 4. Check for inverted or invalid spotlight angles
    inner_matches = list(RE_INNER_ANGLE.finditer(content))
    outer_matches = list(RE_OUTER_ANGLE.finditer(content))
    for im, om in zip(inner_matches, outer_matches):
        try:
            inner_val = float(im.group(1))
            outer_val = float(om.group(1))
            if inner_val < 0 or outer_val < 0:
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f"Negative spotlight angle detected: inner={inner_val}, outer={outer_val}.",
                        file_path=filename,
                        rule="spotlight_angle_invalid",
                    )
                )
            elif inner_val > outer_val:
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f"Inverted spotlight angles: innerAngle ({inner_val}) > outerAngle ({outer_val}).",
                        file_path=filename,
                        rule="spotlight_angle_inverted",
                    )
                )
        except ValueError:
            pass

    # 5. Check for malformed spotlight definition rows (fewer than 4 elements)
    # Scan spotlights array blocks
    spotlights_block_match = re.search(r'(?i)[\"\'\`]?spotlights[\"\'\`]?\s*:\s*\[', content)
    if spotlights_block_match:
        block_start = spotlights_block_match.end()
        # Find closing bracket of the spotlights array
        depth = 1
        i = block_start
        while i < len(content) and depth > 0:
            if content[i] == "[":
                depth += 1
            elif content[i] == "]":
                depth -= 1
            i += 1
        spotlights_block = content[block_start : i - 1]

        # Scan for rows like ["type", "node1"]
        row_matches = re.finditer(r'\[([^\[\]]+)\]', spotlights_block)
        for rm in row_matches:
            row_text = rm.group(1).strip()
            # Split items taking care of simple commas
            items = [item.strip() for item in row_text.split(",") if item.strip()]
            if items:
                # If first item looks like a string (identifier) and is not header row
                first_item_lower = items[0].lower().strip("\"'`")
                if first_item_lower in ("type", "name"):
                    continue
                # Spotlight rows need at least 4 items: [type/name, node1, node2, node3]
                if len(items) < 4 and not any("{" in it for it in items):
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="warning",
                            message=f"Malformed spotlight row with fewer than 4 elements: [{row_text}]",
                            file_path=filename,
                            rule="spotlight_row_malformed",
                        )
                    )

    return diagnostics


# ==============================================================================
# JBeam Content Fixer Engine
# ==============================================================================

def fix_jbeam_content(
    content: str,
    filename: str = "",
    available_files: Optional[Set[str]] = None,
    normalize_optics: bool = True,
    selective: bool = False,
    modernize_cookies: bool = True,
    modernize_flares: bool = True,
    normalize_electrics: bool = True,
    repair_angles: bool = True,
    fix_rear_lights: bool = False,
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Fix broken headlight self-shadow occlusion and normalize optics in JBeam text.

    Replaces `lightCastShadows: true` with `false` (with highbeam preservation when
    `selective=True`) using a robust, comment-preserving regular expression that
    retains exact quotation, indentation, spacing, inline comments, and trailing commas.

    Also modernizes obsolete cookie paths, legacy flares, corrects electrics signals,
    repairs inverted spotlight angles, and normalizes invalid optics assets.

    Args:
        content: Raw JBeam text content.
        filename: Optional filename for diagnostic reporting.
        available_files: Optional set of filenames in the mod archive to check texture links.
        normalize_optics: If True, normalizes invalid flareName/cookieName.
        selective: If True, selectively fixes lowbeams and fog lights while preserving
                   highbeam shadow casting (lightCastShadows: true) to prevent cockpit bleed.
        modernize_cookies: If True, updates pre-PBR art/shapes/lights/* to modern cookies.
        modernize_flares: If True, updates legacy flare names to modern vehicle flares.
        normalize_electrics: If True, corrects non-standard electrics signal names.
        repair_angles: If True, fixes inverted or negative spotlight angles.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Altered JBeam content (or original string if no fixes needed).
            - fix_count: Number of `lightCastShadows` instances converted.
            - diagnostics: List of diagnostic notices and normalization records.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    content_lower = content.lower()

    # Fast bypass if no relevant tokens exist in the text
    has_shadows = FAST_SHADOW_CHECK in content_lower
    has_optics = any(tok in content_lower for tok in ("flarename", "cookiename", "spotlights"))
    has_electrics = any(tok in content_lower for tok in ("low_beam", "high_beam", "fog_light", "headlight"))
    has_angles = "lightinnerangle" in content_lower and "lightouterangle" in content_lower
    has_brightness = "lightbrightness" in content_lower or "lightrange" in content_lower

    if not has_shadows and not has_optics and not has_electrics and not has_angles and not has_brightness:
        return content, 0, diagnostics

    fix_count = 0

    # 1. Normalize electrics signals in spotlight rows if requested
    if normalize_electrics and (selective or has_electrics):
        text, el_count, el_diags = normalize_electrics_signals(text)
        diagnostics.extend(el_diags)

    # 2. Repair inverted spotlight angles if requested
    if repair_angles and (selective or has_angles):
        text, ang_count, ang_diags = repair_spotlight_angles(text)
        diagnostics.extend(ang_diags)

    # 3. Repair non-positive brightness and range if requested
    if repair_angles:
        text, br_count, br_diags = repair_spotlight_brightness_and_range(text)
        diagnostics.extend(br_diags)

    # 4. Modernize and repair cookie paths
    if modernize_cookies and (has_optics or "art/" in text.lower() or "cookie" in text.lower()):
        # 4a. Obsolete cookie paths (art/shapes/lights/* -> art/special/BNG_light_cookie_headlight.dds)
        if "art/shapes/lights/" in text.lower():
            def _replace_obsolete_cookie(m: re.Match) -> str:
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message="Modernized obsolete cookie path to modern Torque3D PBR asset 'art/special/BNG_light_cookie_headlight.dds'",
                        file_path=filename,
                        rule="cookie_path_modernized",
                    )
                )
                return f'{m.group(1)}{MODERN_HEADLIGHT_COOKIE}{m.group(2)}'

            text = RE_OBSOLETE_COOKIE_REPLACE.sub(_replace_obsolete_cookie, text)

        # 4b. Remove leading slash from VFS cookies ("/art/..." or "/vehicles/..." -> "art/..." or "vehicles/...")
        def _strip_cookie_slash(m: re.Match) -> str:
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Removed leading slash from cookie path for Torque3D VFS compatibility",
                    file_path=filename,
                    rule="cookie_path_normalized",
                )
            )
            return f'{m.group(1)}{m.group(2)}{m.group(3)}'

        text = RE_COOKIE_LEADING_SLASH.sub(_strip_cookie_slash, text)

        # 4c. Fix non-existent .png headlight cookie to official .dds
        if "bng_light_cookie_headlight.png" in text.lower():
            text = RE_COOKIE_PNG_HEADLIGHT.sub(f'\\g<1>{MODERN_HEADLIGHT_COOKIE}\\g<2>', text)
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Updated cookie texture extension from .png to official .dds 'art/special/BNG_light_cookie_headlight.dds'",
                    file_path=filename,
                    rule="cookie_extension_modernized",
                )
            )

        # 4d. Fallback missing local vehicle cookies to modern official cookie if archive file set is provided
        if available_files is not None:
            normalized_archive = {f.lower().replace("\\", "/") for f in available_files}
            def _fix_missing_cookie(m: re.Match) -> str:
                cval = m.group(3).strip()
                cval_norm = cval.lower().replace("\\", "/").lstrip("/")
                if cval.startswith("$") or cval_norm.startswith("art/special/") or cval_norm.startswith("art/"):
                    return m.group(0)
                if cval_norm and cval_norm not in normalized_archive:
                    # If mod authored with .png but only .dds exists in archive, update extension
                    if cval_norm.endswith(".png"):
                        dds_cand = cval_norm[:-4] + ".dds"
                        if dds_cand in normalized_archive:
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Converted cookie path '{cval}' from .png to existing archive .dds '{dds_cand}'",
                                    file_path=filename,
                                    rule="cookie_extension_modernized",
                                )
                            )
                            new_path = cval[:-4] + ".dds"
                            return f'{m.group(1)}{m.group(2)}{new_path}{m.group(4)}'

                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Replaced missing local cookie texture '{cval}' with standard '{MODERN_HEADLIGHT_COOKIE}'",
                            file_path=filename,
                            rule="cookie_missing_replaced",
                        )
                    )
                    return f'{m.group(1)}{m.group(2)}{MODERN_HEADLIGHT_COOKIE}{m.group(4)}'
                return m.group(0)

            text = RE_COOKIE_VALUE.sub(_fix_missing_cookie, text)

    # 5. Modernize legacy flare names (headlightFlare -> vehicleHeadLightFlare, etc.)
    if modernize_flares and any(tok in text.lower() for tok in ("headlightflare", "highbeamflare", "fogflare")):
        def _replace_legacy_flare(m: re.Match) -> str:
            legacy = m.group(2).lower()
            if "high" in legacy:
                new_flare = MODERN_HIGHBEAM_FLARE
            elif "fog" in legacy:
                new_flare = MODERN_FOG_FLARE
            else:
                new_flare = MODERN_HEADLIGHT_FLARE

            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Modernized legacy flare '{m.group(2)}' to '{new_flare}'",
                    file_path=filename,
                    rule="flare_legacy_modernized",
                )
            )
            return f'{m.group(1)}{new_flare}{m.group(3)}'

        text = RE_LEGACY_FLARES.sub(_replace_legacy_flare, text)

    # 6. Fix lightCastShadows: true -> false (with selective highbeam protection when selective=True)
    if has_shadows:
        matches = list(RE_LIGHT_CAST_SHADOWS.finditer(text))
        if matches:
            pieces: List[str] = []
            last_idx = 0
            for m in matches:
                if _is_inside_string_literal(text, m.start()):
                    continue

                if selective and _is_highbeam_context(text, m.start()):
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message="Preserved highbeam lightCastShadows: true to maintain environmental shadows and prevent cockpit bleed",
                            file_path=filename,
                            rule="highbeam_shadow_preserved",
                        )
                    )
                    continue

                pieces.append(text[last_idx:m.start()])
                pieces.append(m.group(1))
                pieces.append("false")
                last_idx = m.end()
                fix_count += 1
                if selective:
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message="Fixed lowbeam self-shadow occlusion (lightCastShadows: false)",
                            file_path=filename,
                            rule="lowbeam_shadow_fixed",
                        )
                    )

            if fix_count > 0:
                pieces.append(text[last_idx:])
                text = "".join(pieces)

    # 6. Normalize optics if requested
    if normalize_optics and has_optics:
        # Normalize invalid flareName ('none', 'null', 'undefined')
        def _replace_flare(m: re.Match) -> str:
            val = m.group(0).split(":")[-1].strip().strip("\"'`")
            if selective:
                replacement = f'"{MODERN_HEADLIGHT_FLARE}"'
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f'Restored valid headlight flare "{MODERN_HEADLIGHT_FLARE}" in place of invalid flareName "{val}"',
                        file_path=filename,
                        rule="flare_name_restored",
                    )
                )
            else:
                replacement = '""'
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f'Normalized invalid flareName "{val}" to empty string ""',
                        file_path=filename,
                        rule="flare_name_normalized",
                    )
                )
            return f'{m.group(1)}{replacement}'

        text = RE_INVALID_FLARE.sub(_replace_flare, text)

        # Normalize invalid cookieName ('none', 'null', 'undefined')
        def _replace_cookie(m: re.Match) -> str:
            val = m.group(0).split(":")[-1].strip().strip("\"'`")
            if selective:
                replacement = f'"{MODERN_HEADLIGHT_COOKIE}"'
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f'Restored valid headlight cookie "{MODERN_HEADLIGHT_COOKIE}" in place of invalid cookieName "{val}"',
                        file_path=filename,
                        rule="cookie_name_restored",
                    )
                )
            else:
                replacement = '""'
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f'Normalized invalid cookieName "{val}" to empty string ""',
                        file_path=filename,
                        rule="cookie_name_normalized",
                    )
                )
            return f'{m.group(1)}{replacement}'

        text = RE_INVALID_COOKIE.sub(_replace_cookie, text)

    # 7. Collect non-destructive optics diagnostics
    if has_optics:
        additional_diag = audit_spotlights(
            text,
            filename=filename,
            available_files=available_files
        )
        existing_rules = {d.rule for d in diagnostics}
        for d in additional_diag:
            if d.rule == "flare_name_invalid" and ("flare_name_normalized" in existing_rules or "flare_name_restored" in existing_rules):
                continue
            if d.rule == "cookie_name_invalid" and ("cookie_name_normalized" in existing_rules or "cookie_name_restored" in existing_rules):
                continue
            if d.rule == "cookie_path_obsolete" and "cookie_path_modernized" in existing_rules:
                continue
            if d.rule == "spotlight_angle_inverted" and "spotlight_angle_repaired" in existing_rules:
                continue
            diagnostics.append(d)

    # 7. Rear Lighting Enhancement & Ground Illumination
    if fix_rear_lights:
        text, rear_count, rear_diags = enhance_rear_light_content(text, filename=filename)
        fix_count += rear_count
        diagnostics.extend(rear_diags)

    # If no modifications were made, return original content object and fix_count=0
    if fix_count == 0 and text == content:
        return content, 0, diagnostics

    return text, fix_count, diagnostics


def smart_fix_jbeam_content(
    content: str,
    filename: str = "",
    available_files: Optional[Set[str]] = None,
    fix_rear_lights: bool = True,
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Intelligently fix BeamNG JBeam vehicle optics with 100% precision.

    - Selectively fixes lowbeam self-shadow occlusion (lightCastShadows: false).
    - Preserves highbeam shadow casting (lightCastShadows: true) to prevent cockpit bleed.
    - Modernizes obsolete cookie paths (art/shapes/lights/* -> art/special/BNG_light_cookie_headlight.dds).
    - Modernizes legacy flares (headlightFlare -> vehicleHeadLightFlare).
    - Corrects misspelled electrics signals in spotlight rows (low_beam -> lowbeam).
    - Repairs inverted spotlight cone angles (innerAngle > outerAngle).
    - Enhances rear lighting (reverse, brake, taillights) for realistic ground illumination.
    """
    return fix_jbeam_content(
        content=content,
        filename=filename,
        available_files=available_files,
        normalize_optics=True,
        selective=True,
        modernize_cookies=True,
        modernize_flares=True,
        normalize_electrics=True,
        repair_angles=True,
        fix_rear_lights=fix_rear_lights,
    )


def patch_jbeam_text(content: str, selective: bool = False) -> Tuple[str, int]:
    """Convenience helper to patch lightCastShadows in JBeam text without diagnostics.

    Args:
        content: Raw JBeam text content.
        selective: If True, selectively preserves highbeam shadows. Defaults to False.

    Returns:
        Tuple[str, int]: (patched_text, fix_count)
    """
    fixed_text, fix_count, _ = fix_jbeam_content(content, normalize_optics=False, selective=selective)
    return fixed_text, fix_count
