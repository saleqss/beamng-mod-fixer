"""Core JBeam and Optics Engine for BeamNG Mod Fixer.

Provides robust, comment-preserving regular expression replacement of
`lightCastShadows: true` with `false`, optics validation and normalization
(flareName, cookieName, spotlight geometries), and multi-encoding decoding.
"""

import codecs
import re
from typing import List, Optional, Set, Tuple

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

# General cookieName value extractor
RE_COOKIE_VALUE = re.compile(
    r'(?i)[\"\'\`]?\bcookieName\b[\"\'\`]?\s*:\s*[\"\'`]([^\"\'`]+)[\"\'`]'
)

# Spotlight angles
RE_INNER_ANGLE = re.compile(
    r'(?i)[\"\'\`]?\blightInnerAngle\b[\"\'\`]?\s*:\s*(-?\d+(?:\.\d+)?)'
)
RE_OUTER_ANGLE = re.compile(
    r'(?i)[\"\'\`]?\blightOuterAngle\b[\"\'\`]?\s*:\s*(-?\d+(?:\.\d+)?)'
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
            cookie_val = match.group(1).strip()
            # Ignore Lua expressions (starting with $)
            if cookie_val.startswith("$"):
                continue
            # Ignore base game official cookies
            if cookie_val.lower().startswith("art/special/") or cookie_val.lower().startswith("art/"):
                continue
            # Check local vehicle cookie paths
            cookie_norm = cookie_val.lower().replace("\\", "/")
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
    normalize_optics: bool = True
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Fix broken headlight self-shadow occlusion and normalize optics in JBeam text.

    Replaces `lightCastShadows: true` with `false` using a robust, comment-preserving
    regular expression that retains exact quotation, indentation, spacing, inline
    comments, and trailing commas.

    Also runs optics diagnostics and normalizes invalid `flareName` and `cookieName`.

    Args:
        content: Raw JBeam text content.
        filename: Optional filename for diagnostic reporting.
        available_files: Optional set of filenames in the mod archive to check texture links.
        normalize_optics: If True, normalizes invalid flareName/cookieName ('none' -> '').

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

    if not has_shadows and not has_optics:
        return content, 0, diagnostics

    # 1. Replace lightCastShadows: true -> false
    fix_count = 0
    if has_shadows:
        matches = list(RE_LIGHT_CAST_SHADOWS.finditer(text))
        if matches:
            pieces: List[str] = []
            last_idx = 0
            for m in matches:
                if _is_inside_string_literal(text, m.start()):
                    continue
                pieces.append(text[last_idx:m.start()])
                pieces.append(m.group(1))
                pieces.append("false")
                last_idx = m.end()
                fix_count += 1
            if fix_count > 0:
                pieces.append(text[last_idx:])
                text = "".join(pieces)

    # 2. Normalize optics if requested
    if normalize_optics and has_optics:
        # Normalize invalid flareName ('none', 'null', 'undefined' -> "")
        def _replace_flare(m: re.Match) -> str:
            val = m.group(0).split(":")[-1].strip().strip("\"'`")
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message=f'Normalized invalid flareName "{val}" to empty string ""',
                    file_path=filename,
                    rule="flare_name_normalized",
                )
            )
            return f'{m.group(1)}""'

        text = RE_INVALID_FLARE.sub(_replace_flare, text)

        # Normalize invalid cookieName ('none', 'null', 'undefined' -> "")
        def _replace_cookie(m: re.Match) -> str:
            val = m.group(0).split(":")[-1].strip().strip("\"'`")
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f'Normalized invalid cookieName "{val}" to empty string ""',
                    file_path=filename,
                    rule="cookie_name_normalized",
                )
            )
            return f'{m.group(1)}""'

        text = RE_INVALID_COOKIE.sub(_replace_cookie, text)

    # 3. Collect non-destructive optics diagnostics
    if has_optics:
        additional_diag = audit_spotlights(
            text,
            filename=filename,
            available_files=available_files
        )
        # Avoid duplicate diagnostics if already recorded during normalization
        existing_rules = {d.rule for d in diagnostics}
        for d in additional_diag:
            if d.rule == "flare_name_invalid" and "flare_name_normalized" in existing_rules:
                continue
            if d.rule == "cookie_name_invalid" and "cookie_name_normalized" in existing_rules:
                continue
            diagnostics.append(d)

    # If no modifications were made, return original content object and fix_count=0
    if fix_count == 0 and text == content:
        return content, 0, diagnostics

    return text, fix_count, diagnostics


def patch_jbeam_text(content: str) -> Tuple[str, int]:
    """Convenience helper to patch lightCastShadows in JBeam text without diagnostics.

    Returns:
        Tuple[str, int]: (patched_text, fix_count)
    """
    fixed_text, fix_count, _ = fix_jbeam_content(content, normalize_optics=False)
    return fixed_text, fix_count
