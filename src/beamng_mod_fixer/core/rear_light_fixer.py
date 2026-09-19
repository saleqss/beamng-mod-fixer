"""Rear lighting repair, license plate floodlight elimination, and photographic ground illumination engine for BeamNG.drive.

Provides:
- Detection of rear lighting fixtures (reverse, brake, taillight, running, signal, fog, license plate).
- Repair of JBeam syntax defects in rear light blocks:
  * Missing commas after cookieName before texSize.
  * Missing commas between beam definition rows ('] \n [') and dicts ('} \n [').
- Elimination of Rogue License Plate Floodlights:
  * Fixes modder copy-paste bug where high-power headlights / reverse spotlights
    (e.g., lightRange: 16-28m, lightBrightness: 1.2-1.6, outerAngle: 170°) are attached to license plates.
  * Clamps license plate spotlights to authentic, subtle levels:
    - lightBrightness: 0.04 (subtle plate glow only, eliminating road illumination).
    - lightRange: 1.5m (illuminates only the license plate, zero beam on asphalt).
    - lightOuterAngle: max 75.0° (narrow localized illumination).
    - lightColor: soft warm white {"r": 255, "g": 240, "b": 200, "a": 255}.
    - quadratic lightAttenuation ({"x": 0, "y": 1, "z": 2}).
    - lightCastShadows: false.
- Elimination of the "Blinding White Rear Light" bug:
  * In JBeam props, rows inherit unspecified properties from preceding templates.
  * If a reverse light template sets lightColor: white, subsequent taillight / lowhighbeam
    rows inherit white if lightColor is omitted!
  * This engine injects explicit, calibrated lightColor into every rear spotlight row:
    - Pure vivid red for brake, taillight, running, and rear fog.
    - Warm white for reverse lights.
    - Crisp amber for turn signals.
- Elimination of the "Nuclear-Bright Red Ground Discs" bug:
  * Calibrates lightBrightness and lightRange to realistic, subtle photographic levels:
    - Taillights / Running: brightness 0.12, range 6.0m (soft diffuse ambient road wash).
    - Brake lights: brightness 0.35, range 9.0m (clear braking bloom without road laser discs).
    - Reverse lights: brightness 0.75, range 13.0m (clean white reversing visibility).
    - Turn signals: brightness 0.40, range 8.0m.
    - Rear fog lights: brightness 0.45, range 10.0m.
  * Enforces quadratic lightAttenuation ({"x": 0, "y": 1, "z": 2}) for smooth, natural falloff.
- Removal of inappropriate directional headlight cookie textures from rear lamps.
- Disabling self-shadow casting (lightCastShadows: false) to prevent rear bumper occlusion.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

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
    "licenseplate",
    "license_plate",
    "plate_light",
    "numberplate",
    "trunklight",
    "trunk_light",
    "tailcone",
    "tailgate",
    "trunk",
    "chmsl",
    "thirdbrakelight",
    "centerbrakelight",
    "reverse",
    "reverselight",
    "backuplight",
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


def _is_license_plate_context(filename: str, text_context: str = "") -> bool:
    """Determine if a file or block context corresponds to vehicle license plate lighting."""
    fname_lower = filename.lower().replace("\\", "/")
    if any(k in fname_lower for k in ("licenseplate", "license_plate", "numberplate", "plate_light")) or bool(
        re.search(r'\bplate\b|[_\-]plate[_\-.]', fname_lower)
    ):
        return True
    ctx_lower = text_context.lower()
    return any(k in ctx_lower for k in ("licenseplate", "license_plate", "plate_light", "licenselight"))


def is_rear_light_file(filename: str, content: str = "") -> bool:
    """Determine if a file or its contents correspond to rear vehicle lighting or license plate fixtures."""
    fname_lower = filename.lower().replace("\\", "/")
    if any(k in fname_lower for k in REAR_LIGHT_KEYWORDS) or bool(
        re.search(r'\bplate\b|[_\-]plate[_\-.]', fname_lower)
    ):
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
            "licenseplate",
            "license_plate",
            "numberplate",
            "trunklight",
            "chmsl",
        )
    ) or ("spotlight" in content_lower and any(k in content_lower for k in ("reverse", "brake", "tail", "plate"))):
        return True

    return False


def _find_properties_dict(line: str) -> Optional[Tuple[int, int, str]]:
    """Find the span and body of the lighting properties dict in a spotlight row.

    In JBeam SPOTLIGHT rows, earlier dictionaries are coordinate/rotational offsets
    (e.g., {"x": -85, "y": 0, "z": 10}). The properties dictionary (lightRange,
    lightBrightness, flares, colors) is either the trailing dictionary or one
    containing property keys.
    """
    matches = list(re.finditer(r'\{([^{}]+)\}', line))
    if not matches:
        return None

    # Search in reverse order for a dict containing lighting/property keys
    for m in reversed(matches):
        body_lower = m.group(1).lower()
        if any(
            k in body_lower
            for k in (
                "light", "flare", "cookie", "shadow", "attenuation", "deformgroup", "texsize", "color"
            )
        ):
            return (m.start(1), m.end(1), m.group(1))

    # If all dicts only contain coordinate keys (x, y, z), do not treat as property dict
    last_m = matches[-1]
    body = last_m.group(1)
    body_clean = re.sub(r'[\s"\']', '', body.lower())
    keys = re.findall(r'([a-z0-9_]+):', body_clean)
    if keys and set(keys).issubset({"x", "y", "z"}):
        return None

    return (last_m.start(1), last_m.end(1), last_m.group(1))


def enhance_rear_light_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Audit and calibrate rear lighting for photographic, realistic ground illumination.

    Eliminates:
    1. Rogue white/yellow floodlights from license plates shining backwards onto the ground.
    2. White light on rear lights when headlights are turned on (template inheritance bug).
    3. Blinding, nuclear-bright red ground discs (calibrates brightness & adds quadratic attenuation).
    4. Bumper shadow occlusion (lightCastShadows: false).

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
    content_lower = content.lower()
    is_rear = is_rear_light_file(filename, content)
    is_plate_file = _is_license_plate_context(filename, content)

    # Fast pre-check: if neither rear keywords nor spotlights exist, return unchanged
    if not is_rear and not is_plate_file and "spotlight" not in content_lower and "taillight" not in content_lower and "reverselight" not in content_lower:
        return content, 0, diagnostics

    fixes = 0

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

    # 4. Calibrate templates in rear/license plate files
    if is_plate_file:
        RE_PLATE_TEMPLATE_BRIGHTNESS = re.compile(r'(?i)(["\']lightBrightness["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)')
        RE_PLATE_TEMPLATE_ANGLE = re.compile(r'(?i)(["\']lightOuterAngle["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)')
        RE_PLATE_TEMPLATE_COLOR = re.compile(r'(?i)(["\']lightColor["\']\s*:\s*\{[^{}]+\})')

        def _calibrate_plate_template_line(tm: re.Match) -> str:
            nonlocal fixes
            tline = tm.group(1)

            # Range
            m_r = RE_TEMPLATE_LIGHT_RANGE.search(tline)
            if m_r and float(m_r.group(2)) > 1.5:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Calibrated excessive license plate template lightRange from {m_r.group(2)}m down to 1.5m to eliminate rear floodlight",
                        file_path=filename,
                        rule="rear_plate_floodlight_clamped",
                    )
                )
                tline = tline[:m_r.start()] + f"{m_r.group(1)}1.5" + tline[m_r.end():]

            # Brightness
            m_b = RE_PLATE_TEMPLATE_BRIGHTNESS.search(tline)
            if m_b and float(m_b.group(2)) > 0.05:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Calibrated excessive license plate template lightBrightness from {m_b.group(2)} down to 0.04 to eliminate rear floodlight",
                        file_path=filename,
                        rule="rear_plate_floodlight_clamped",
                    )
                )
                tline = tline[:m_b.start()] + f"{m_b.group(1)}0.04" + tline[m_b.end():]

            # OuterAngle
            m_a = RE_PLATE_TEMPLATE_ANGLE.search(tline)
            if m_a and float(m_a.group(2)) > 85.0:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Clamped wide license plate template lightOuterAngle from {m_a.group(2)}° down to 75.0°",
                        file_path=filename,
                        rule="rear_plate_angle_clamped",
                    )
                )
                tline = tline[:m_a.start()] + f"{m_a.group(1)}75.0" + tline[m_a.end():]

            # Color
            m_c = RE_PLATE_TEMPLATE_COLOR.search(tline)
            if m_c and '{"r": 255, "g": 240, "b": 200, "a": 255}' not in m_c.group(1).replace(" ", ""):
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message="Calibrated license plate template lightColor to soft warm white",
                        file_path=filename,
                        rule="rear_plate_color_calibrated",
                    )
                )
                tline = tline[:m_c.start()] + '"lightColor": {"r": 255, "g": 240, "b": 200, "a": 255}' + tline[m_c.end():]

            return tline

        RE_PLATE_TEMPLATE_LINE = re.compile(
            r'(?im)^(?![^\n]*\bSPOTLIGHT\b)([^\n]*?\b(?:lightRange|lightBrightness|lightOuterAngle|lightColor)\b[^\n]*)$'
        )
        text = RE_PLATE_TEMPLATE_LINE.sub(_calibrate_plate_template_line, text)

    elif is_rear:
        def _calibrate_rear_template_range(m: re.Match) -> str:
            nonlocal fixes
            val = float(m.group(2))
            if val < 8.0:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Calibrated rear light template lightRange from {val}m to 10.0m",
                        file_path=filename,
                        rule="rear_template_range_boosted",
                    )
                )
                return f"{m.group(1)}10.0"
            elif val > 15.0:
                fixes += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Calibrated excessive rear template lightRange from {val}m down to 12.0m",
                        file_path=filename,
                        rule="rear_template_range_calibrated",
                    )
                )
                return f"{m.group(1)}12.0"
            return m.group(0)

        RE_TEMPLATE_RANGE_LINE = re.compile(
            r'(?im)^(?![^\n]*\bSPOTLIGHT\b)([^\n]*?\blightRange\b[^\n]*)$'
        )

        def _process_template_line(tm: re.Match) -> str:
            return RE_TEMPLATE_LIGHT_RANGE.sub(_calibrate_rear_template_range, tm.group(1))

        text = RE_TEMPLATE_RANGE_LINE.sub(_process_template_line, text)

    # 5. Process SPOTLIGHT rows: calibrate brightness, range, attenuation, angle, and color
    def _process_spotlight_line(lm: re.Match) -> str:
        nonlocal fixes
        line = lm.group(1)
        line_lower = line.lower()

        target_brightness: Optional[float] = None
        target_range: Optional[float] = None
        category: Optional[str] = None
        target_color_str: Optional[str] = None
        target_attenuation_str: Optional[str] = None
        max_angle: Optional[float] = None

        # Determine light category
        if is_plate_file or _is_license_plate_context(filename, line_lower):
            target_brightness = 0.04
            target_range = 1.5
            category = "license plate light"
            target_color_str = '"lightColor": {"r": 255, "g": 240, "b": 200, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 2}'
            max_angle = 75.0
        elif "reverse" in line_lower:
            target_brightness = 0.75
            target_range = 13.0
            category = "reverse light"
            target_color_str = '"lightColor": {"r": 255, "g": 250, "b": 220, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 1.5}'
        elif any(k in line_lower for k in ("brake", "brakelights", "brakelight", "chmsl")):
            target_brightness = 0.35
            target_range = 9.0
            category = "brake light"
            target_color_str = '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 2}'
        elif any(k in line_lower for k in ("signal_l", "signal_r", "turnsignal")):
            target_brightness = 0.40
            target_range = 8.0
            category = "turn signal"
            target_color_str = '"lightColor": {"r": 255, "g": 140, "b": 15, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 2}'
        elif any(k in line_lower for k in ("fog", "rearfog")) and (is_rear or "rear" in line_lower):
            target_brightness = 0.45
            target_range = 10.0
            category = "rear fog light"
            target_color_str = '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 2}'
        elif any(k in line_lower for k in ("lowhighbeam", "running", "taillight", "taillights", "parking")) and (
            is_rear or any(k in line_lower for k in ("rear", "tail", "trunk", "back"))
        ):
            target_brightness = 0.12
            target_range = 6.0
            category = "taillight / running light"
            target_color_str = '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}'
            target_attenuation_str = '"lightAttenuation": {"x": 0, "y": 1, "z": 2}'

        if target_brightness is not None:
            prop_res = _find_properties_dict(line)
            if prop_res is not None:
                start_idx, end_idx, dict_body = prop_res
                modified_dict = dict_body

                # 5a. Explicit lightColor Injection / Correction:
                m_col = re.search(r'(?i)(["\']lightColor["\']\s*:\s*\{[^{}]+\})', modified_dict)
                if not m_col:
                    modified_dict = f"{target_color_str}, {modified_dict}"
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Injected explicit {category} lightColor to prevent inheriting white reverse light template",
                            file_path=filename,
                            rule="rear_color_inheritance_prevented",
                        )
                    )
                else:
                    col_str = m_col.group(1).lower()
                    if category == "license plate light":
                        if '{"r": 255, "g": 240, "b": 200, "a": 255}' not in col_str.replace(" ", ""):
                            modified_dict = modified_dict[:m_col.start()] + target_color_str + modified_dict[m_col.end():]
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message="Calibrated license plate lightColor to soft warm white",
                                    file_path=filename,
                                    rule="rear_plate_color_calibrated",
                                )
                            )
                    elif category in ("brake light", "taillight / running light", "rear fog light"):
                        m_rgb = re.search(
                            r'["\']r["\']\s*:\s*(\d+).*?["\']g["\']\s*:\s*(\d+).*?["\']b["\']\s*:\s*(\d+)',
                            col_str,
                        )
                        if m_rgb:
                            r_val, g_val, b_val = int(m_rgb.group(1)), int(m_rgb.group(2)), int(m_rgb.group(3))
                            if g_val > 120 and b_val > 120 and r_val > 180:
                                modified_dict = modified_dict[:m_col.start()] + target_color_str + modified_dict[m_col.end():]
                                fixes += 1
                                diagnostics.append(
                                    DiagnosticNotice(
                                        severity="info",
                                        message=f"Repaired erroneous white lightColor in {category} to proper red",
                                        file_path=filename,
                                        rule="rear_white_light_fixed",
                                    )
                                )

                # 5b. Explicit lightAttenuation Injection (smooth photographic falloff)
                if "lightattenuation" not in modified_dict.lower():
                    modified_dict = f"{target_attenuation_str}, {modified_dict}"
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Injected quadratic lightAttenuation to {category} for soft natural road wash without hard circular discs",
                            file_path=filename,
                            rule="rear_attenuation_softened",
                        )
                    )

                # 5c. Calibrate lightBrightness
                m_b = re.search(r'(["\']lightBrightness["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)', modified_dict)
                if m_b:
                    cur_b = float(m_b.group(2))
                    if category == "license plate light":
                        if cur_b > 0.05:
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Calibrated excessive {category} lightBrightness from {cur_b} down to {target_brightness} to eliminate rear road floodlight",
                                    file_path=filename,
                                    rule="rear_plate_floodlight_clamped",
                                )
                            )
                            modified_dict = modified_dict[:m_b.start()] + f'{m_b.group(1)}{target_brightness}' + modified_dict[m_b.end():]
                        elif cur_b < 0.02:
                            fixes += 1
                            modified_dict = modified_dict[:m_b.start()] + f'{m_b.group(1)}{target_brightness}' + modified_dict[m_b.end():]
                    else:
                        if cur_b < (target_brightness * 0.7):
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Boosted dim {category} lightBrightness from {cur_b} to {target_brightness}",
                                    file_path=filename,
                                    rule="rear_brightness_boosted",
                                )
                            )
                            modified_dict = modified_dict[:m_b.start()] + f'{m_b.group(1)}{target_brightness}' + modified_dict[m_b.end():]
                        elif cur_b > (target_brightness * 1.6):
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Calibrated over-bright {category} lightBrightness from {cur_b} down to {target_brightness} to eliminate blinding glare",
                                    file_path=filename,
                                    rule="rear_brightness_calibrated",
                                )
                            )
                            modified_dict = modified_dict[:m_b.start()] + f'{m_b.group(1)}{target_brightness}' + modified_dict[m_b.end():]
                else:
                    modified_dict = f'"lightBrightness": {target_brightness}, {modified_dict}'
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Added calibrated lightBrightness: {target_brightness} to {category}",
                            file_path=filename,
                            rule="rear_brightness_boosted",
                        )
                    )

                # 5d. Calibrate lightRange
                m_r = re.search(r'(["\']lightRange["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)', modified_dict)
                if m_r:
                    cur_r = float(m_r.group(2))
                    if category == "license plate light":
                        if cur_r > 1.8:
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Calibrated excessive {category} lightRange from {cur_r}m down to {target_range}m to eliminate rear road floodlight",
                                    file_path=filename,
                                    rule="rear_plate_floodlight_clamped",
                                )
                            )
                            modified_dict = modified_dict[:m_r.start()] + f'{m_r.group(1)}{target_range}' + modified_dict[m_r.end():]
                        elif cur_r < 0.8:
                            fixes += 1
                            modified_dict = modified_dict[:m_r.start()] + f'{m_r.group(1)}{target_range}' + modified_dict[m_r.end():]
                    else:
                        if cur_r < (target_range * 0.7):
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Extended short {category} lightRange from {cur_r}m to {target_range}m",
                                    file_path=filename,
                                    rule="rear_range_extended",
                                )
                            )
                            modified_dict = modified_dict[:m_r.start()] + f'{m_r.group(1)}{target_range}' + modified_dict[m_r.end():]
                        elif cur_r > (target_range * 1.25):
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Calibrated excessive {category} lightRange from {cur_r}m down to {target_range}m",
                                    file_path=filename,
                                    rule="rear_range_calibrated",
                                )
                            )
                            modified_dict = modified_dict[:m_r.start()] + f'{m_r.group(1)}{target_range}' + modified_dict[m_r.end():]
                else:
                    modified_dict = f'"lightRange": {target_range}, {modified_dict}'
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Added explicit lightRange: {target_range}m to {category}",
                            file_path=filename,
                            rule="rear_range_extended",
                        )
                    )

                # 5e. Clamp excessive beam angle for license plates
                if max_angle is not None:
                    m_a = re.search(r'(["\']lightOuterAngle["\']\s*:\s*)([0-9]+(?:\.[0-9]+)?)', modified_dict)
                    if m_a:
                        cur_a = float(m_a.group(2))
                        if cur_a > (max_angle + 10.0):
                            fixes += 1
                            diagnostics.append(
                                DiagnosticNotice(
                                    severity="info",
                                    message=f"Clamped wide {category} lightOuterAngle from {cur_a}° down to {max_angle}° to eliminate rear road floodlight",
                                    file_path=filename,
                                    rule="rear_plate_angle_clamped",
                                )
                            )
                            modified_dict = modified_dict[:m_a.start()] + f'{m_a.group(1)}{max_angle}' + modified_dict[m_a.end():]

                # 5f. Ensure lightCastShadows is false for all rear lights
                if '"lightcastshadows":true' in modified_dict.lower().replace(" ", ""):
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Disabled self-shadow casting on {category} to prevent rear bumper occlusion",
                            file_path=filename,
                            rule="rear_shadow_occlusion_disabled",
                        )
                    )
                    modified_dict = re.sub(
                        r'(["\']lightCastShadows["\']\s*:\s*)true\b',
                        r'\g<1>false',
                        modified_dict,
                        flags=re.IGNORECASE,
                    )
                elif "lightcastshadows" not in modified_dict.lower():
                    modified_dict = f'"lightCastShadows": false, {modified_dict}'
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Added explicit lightCastShadows: false to {category}",
                            file_path=filename,
                            rule="rear_shadow_occlusion_disabled",
                        )
                    )

                if modified_dict != dict_body:
                    line = line[:start_idx] + modified_dict + line[end_idx:]

            else:
                # No property dict exists on row: append new properties dictionary before closing bracket
                close_bracket = line.rfind("]")
                if close_bracket != -1:
                    new_props = (
                        f', {{"lightRange": {target_range}, "lightBrightness": {target_brightness}, '
                        f'{target_color_str}, {target_attenuation_str}, "lightCastShadows": false}}'
                    )
                    line = line[:close_bracket] + new_props + line[close_bracket:]
                    fixes += 1
                    diagnostics.append(
                        DiagnosticNotice(
                            severity="info",
                            message=f"Injected calibrated lighting properties dictionary to {category}",
                            file_path=filename,
                            rule="rear_range_extended",
                        )
                    )

        return line

    RE_SPOTLIGHT_LINE = re.compile(r'(?im)^([^\n]*\bSPOTLIGHT\b[^\n]*)$')
    fixed_text = RE_SPOTLIGHT_LINE.sub(_process_spotlight_line, text)

    if fixes == 0 and fixed_text == content:
        return content, 0, diagnostics

    return fixed_text, fixes, diagnostics
