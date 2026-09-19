"""Rear lighting repair and ground illumination engine for BeamNG.drive.

Provides:
- Detection of rear lighting fixtures (reverse, brake, taillight, running, signal, fog).
- Repair of JBeam syntax defects in rear light blocks:
  * Missing commas after cookieName before texSize.
  * Missing commas between beam definition rows ('] \n [') and dicts ('} \n [').
- Removal of inappropriate directional headlight cookie textures from rear lamps.
- Ground illumination boost for dim spotlights:
  * Reverse lights: brightness boosted to 1.2, range expanded to 16.0m (bright white ground wash).
  * Brake lights: brightness boosted to 0.85, range expanded to 14.0m (vivid red road wash).
  * Taillights / Running / Low beam rear: brightness boosted to 0.35, range expanded to 12.0m.
  * Turn signals: brightness boosted to 0.6, range expanded to 12.0m.
  * Fog lights: brightness boosted to 0.75, range expanded to 14.0m.
- Disabling self-shadow casting (lightCastShadows: false) to prevent bumper self-occlusion.
"""

import re
from typing import List, Optional, Tuple

from beamng_mod_fixer.models import DiagnosticNotice


REAR_LIGHT_KEYWORDS = {
    "taillight",
    "tail_light",
    "taillights",
    "tail_lights",
    "rear_light",
    "rearlights",
    "rear_lights",
    "rearlight",
    "bumper_r",
    "bumperlight_r",
    "bumperlight_l",
    "fascia_r",
}

# Regex matching missing comma after cookieName
RE_MISSING_COOKIE_COMMA = re.compile(
    r'(?i)(["\']cookieName["\']\s*:\s*["\'][^"\']*["\'])(\s*\n\s*["\']texSize["\'])'
)

# Regex matching missing commas between row arrays in JBeam
RE_ROW_MISSING_COMMA = re.compile(
    r'(\])(\s*\n\s*\[)'
)

# Regex matching missing commas between dict block and row array
RE_DICT_ROW_MISSING_COMMA = re.compile(
    r'(\})(\s*\n\s*\[)'
)

# Regex matching headlight cookie in rear context
RE_HEADLIGHT_COOKIE_IN_REAR = re.compile(
    r'(?i)(["\']cookieName["\']\s*:\s*)(["\'][^"\']*bng_light_cookie_headlight[^"\']*["\'])(,?)'
)

# Regex matching lightRange in template dictionaries
RE_TEMPLATE_LIGHT_RANGE = re.compile(
    r'(?i)(["\']lightRange["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)'
)


def is_rear_light_file(filename: str, content: str = "") -> bool:
    """Determine if a file or its contents correspond to rear vehicle lighting."""
    fname_lower = filename.lower().replace("\\", "/")
    if any(k in fname_lower for k in REAR_LIGHT_KEYWORDS):
        return True

    content_lower = content.lower()
    if any(
        k in content_lower
        for k in (
            "taillight",
            "reverselight",
            "brakelight",
            "vehiclebrakelightflare",
            "vehiclereverselightflare",
            "vehicletaillightflare",
        )
    ) or ("spotlight" in content_lower and any(k in content_lower for k in ("reverse", "brake"))):
        return True

    return False


def enhance_rear_light_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Audit and enhance rear lighting to provide realistic ground and environmental illumination.

    Args:
        content: Raw JBeam text content.
        filename: Optional path or name of the file being processed.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Patched JBeam string.
            - fix_count: Number of enhancements applied.
            - diagnostics: List of diagnostic notices describing changes made.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    fixes = 0
    is_rear = is_rear_light_file(filename, content)

    # 1. Syntax Fix: Missing comma after cookieName
    def _fix_cookie_comma(m: re.Match) -> str:
        nonlocal fixes
        fixes += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Repaired missing comma after cookieName attribute before texSize",
                file_path=filename,
                rule="jbeam_syntax_comma_repaired",
            )
        )
        return f"{m.group(1)},{m.group(2)}"

    text = RE_MISSING_COOKIE_COMMA.sub(_fix_cookie_comma, text)

    # 2. Syntax Fix: Missing commas between array rows
    def _fix_row_comma(m: re.Match) -> str:
        nonlocal fixes
        fixes += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Repaired missing comma between JBeam array rows",
                file_path=filename,
                rule="jbeam_row_comma_repaired",
            )
        )
        return f"{m.group(1)},{m.group(2)}"

    text = RE_ROW_MISSING_COMMA.sub(_fix_row_comma, text)
    text = RE_DICT_ROW_MISSING_COMMA.sub(_fix_row_comma, text)

    # 3. Clean up improper headlight cookies in rear lights
    if is_rear and "bng_light_cookie_headlight" in text.lower():
        def _clear_cookie(m: re.Match) -> str:
            nonlocal fixes
            fixes += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Removed directional headlight cutoff cookie from rear light fixture for smooth diffuse ground illumination",
                    file_path=filename,
                    rule="rear_cookie_cutoff_removed",
                )
            )
            return f'{m.group(1)}""{m.group(3)}'

        text = RE_HEADLIGHT_COOKIE_IN_REAR.sub(_clear_cookie, text)

    # 4. Boost template lightRange in rear files if < 10.0m
    if is_rear:
        def _boost_template_range(m: re.Match) -> str:
            nonlocal fixes
            val = float(m.group(2))
            if val < 10.0:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Boosted rear light template lightRange from {val}m to 14.0m for realistic road throw",
                        file_path=filename,
                        rule="rear_template_range_boosted",
                    )
                )
                return f"{m.group(1)}14.0"
            return m.group(0)

        text = RE_TEMPLATE_LIGHT_RANGE.sub(_boost_template_range, text)

    # 5. Process SPOTLIGHT rows: boost brightness and range per function
    lines = text.splitlines(keepends=True)
    new_lines = []

    for line in lines:
        if "SPOTLIGHT" in line:
            line_lower = line.lower()
            target_brightness: Optional[float] = None
            target_range: Optional[float] = None
            category: Optional[str] = None

            if "reverse" in line_lower:
                target_brightness = 1.2
                target_range = 16.0
                category = "reverse light"
            elif any(k in line_lower for k in ("brake", "brakelights", "brakelight")):
                target_brightness = 0.85
                target_range = 14.0
                category = "brake light"
            elif any(k in line_lower for k in ("signal_l", "signal_r", "turnsignal")):
                target_brightness = 0.6
                target_range = 12.0
                category = "turn signal"
            elif any(k in line_lower for k in ("fog", "rearfog")) and (is_rear or "rear" in line_lower):
                target_brightness = 0.75
                target_range = 14.0
                category = "rear fog light"
            elif any(k in line_lower for k in ("lowhighbeam", "running", "taillight", "taillights")) and (is_rear or "rear" in line_lower):
                target_brightness = 0.35
                target_range = 12.0
                category = "taillight / running light"

            if target_brightness is not None:
                # Check current lightBrightness
                m_b = re.search(r'(["\']lightBrightness["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)', line)
                if m_b:
                    cur_b = float(m_b.group(2))
                    if cur_b < (target_brightness * 0.7):
                        fixes += 1
                        diagnostics.append(
                            DiagnosticNotice(
                                severity="info",
                                message=f"Boosted {category} lightBrightness from {cur_b} to {target_brightness} for ground illumination",
                                file_path=filename,
                                rule="rear_brightness_boosted",
                            )
                        )
                        line = line[:m_b.start()] + f'{m_b.group(1)}{target_brightness}' + line[m_b.end():]

                # Check current lightRange
                m_r = re.search(r'(["\']lightRange["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)', line)
                if m_r:
                    cur_r = float(m_r.group(2))
                    if cur_r < target_range:
                        fixes += 1
                        diagnostics.append(
                            DiagnosticNotice(
                                severity="info",
                                message=f"Extended {category} lightRange from {cur_r}m to {target_range}m",
                                file_path=filename,
                                rule="rear_range_extended",
                            )
                        )
                        line = line[:m_r.start()] + f'{m_r.group(1)}{target_range}' + line[m_r.end():]
                elif m_b and category == "reverse light":
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Added explicit lightRange: {target_range}m to {category}",
                            file_path=filename,
                            rule="rear_range_extended",
                        )
                    )
                    line = line[:m_b.start()] + f'"lightRange": {target_range}, ' + line[m_b.start():]

                # Ensure lightCastShadows is false for rear lights
                if '"lightcastshadows":true' in line.lower().replace(" ", ""):
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Disabled self-shadow casting on {category} to prevent rear bumper occlusion",
                            file_path=filename,
                            rule="rear_shadow_occlusion_disabled",
                        )
                    )
                    line = re.sub(
                        r'(["\']lightCastShadows["\']\s*:\s*)true\b',
                        r'\g<1>false',
                        line,
                        flags=re.IGNORECASE,
                    )

        new_lines.append(line)

    fixed_text = "".join(new_lines)
    if fixes == 0 and fixed_text == content:
        return content, 0, diagnostics

    return fixed_text, fixes, diagnostics
