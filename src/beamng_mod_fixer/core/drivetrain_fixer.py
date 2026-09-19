"""Drivetrain & Physics Repair Engine for BeamNG.drive mods.

Provides:
- Fix for frozen vehicles and physics explosions caused by obsolete differential definitions.
- Normalization of gear ratios, differential torque splits, and viscous coupling limits.
- Tire pressure and friction table repairs (pressurePSI <= 0, broken friction coefficients).
- Clutch and gearbox torque parameter stabilization to restore vehicle driveability.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

# Regular expressions for JBeam drivetrain & physics patching

# Differential gear ratio: gearRatio: 0, negative, or quoted "0" (never match valid 0.xxx)
RE_DIFF_GEAR_RATIO = re.compile(
    r'(?i)([\"\'\`]?gearRatio[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?)(?![.\d])([\"\'`]?)'
)

# Differential torque split: diffTorqueSplit <= 0 or >= 1.0 or negative (never match valid 0.xxx)
RE_DIFF_TORQUE_SPLIT = re.compile(
    r'(?i)([\"\'\`]?diffTorqueSplit[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?|[1-9]\d*(?:\.\d+)?)(?![.\d])([\"\'`]?)'
)

# Viscous coupling stiffness explosion (values > 10000 cause infinite velocity in BeamNG physics)
RE_VISCOUS_STIFFNESS = re.compile(
    r'(?i)([\"\'\`]?viscousCoupling[\"\'\`]?\s*:\s*[\"\'`]?)([1-9]\d{4,}(?:\.\d+)?)(?![.\d])([\"\'`]?)'
)

# Tire pressure: pressurePSI < 10.0, 0, or negative (never match lookup arrays like "pressurePSI":[ )
RE_TIRE_PRESSURE = re.compile(
    r'(?i)([\"\'\`]?pressurePSI[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|[0-9](?:\.[0-9]+)?)(?![.\d\[])([\"\'`]?)'
)

# Wheel inertia: wheelInertia: 0 or negative
RE_WHEEL_INERTIA = re.compile(
    r'(?i)([\"\'\`]?wheelInertia[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?)(?![.\d])([\"\'`]?)'
)

# Clutch torque: clutchTorque: 0 or negative
RE_CLUTCH_TORQUE = re.compile(
    r'(?i)([\"\'\`]?clutchTorque[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?)(?![.\d])([\"\'`]?)'
)

# Abnormal tire friction coefficients (<= 0.05 or > 5.0, never match valid 1.0 or 0.8)
RE_TIRE_FRICTION = re.compile(
    r'(?i)([\"\'\`]?frictionCoef[\"\'\`]?\s*:\s*[\"\'`]?)(0(?:\.0[0-4]*)?|[5-9]\d*(?:\.\d+)?)(?![.\d])([\"\'`]?)'
)

# Extreme or negative brake torque
RE_BRAKE_TORQUE = re.compile(
    r'(?i)([\"\'\`]?(?:brakeTorque|brakingTorque)[\"\'\`]?\s*:\s*[\"\'`]?)(-[0-9]+(?:\.[0-9]+)?|[5-9]\d{4,}(?:\.\d+)?)(?![.\d])([\"\'`]?)'
)


def fix_drivetrain_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Fix broken differential, wheel, tire, and clutch definitions in JBeam text.

    Args:
        content: Raw JBeam text content.
        filename: Optional filename for diagnostic reporting.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Altered JBeam content (or original string if no changes needed).
            - fix_count: Number of physics/drivetrain repairs applied.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    content_lower = content.lower()

    # Fast check: does text contain any drivetrain or wheel tokens?
    has_diff = any(k in content_lower for k in ("gearratio", "difftorquesplit", "viscouscoupling", "differential"))
    has_wheels = any(k in content_lower for k in ("pressurepsi", "wheelinertia", "frictioncoef", "pressurewheels"))
    has_clutch = any(k in content_lower for k in ("clutchtorque", "clutchengage"))

    if not has_diff and not has_wheels and not has_clutch:
        return content, 0, diagnostics

    fix_count = 0

    # 1. Fix zero or negative differential gear ratio (gearRatio: 0 -> 3.73)
    if "gearratio" in content_lower:
        def _fix_ratio(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message="Repaired non-positive differential gearRatio to standard 3.73 (prevents physics freeze)",
                    file_path=filename,
                    rule="diff_gearratio_fixed",
                )
            )
            return f"{m.group(1)}3.73{m.group(3)}"

        text = RE_DIFF_GEAR_RATIO.sub(_fix_ratio, text)

    # 2. Fix invalid differential torque split (<= 0 or >= 1.0)
    if "difftorquesplit" in content_lower:
        def _fix_split(m: re.Match) -> str:
            val = float(m.group(2))
            if val <= 0.0 or val >= 1.0:
                nonlocal fix_count
                fix_count += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="info",
                        message=f"Normalized out-of-range diffTorqueSplit ({val}) to balanced 0.5",
                        file_path=filename,
                        rule="diff_torquesplit_normalized",
                    )
                )
                return f"{m.group(1)}0.5{m.group(3)}"
            return m.group(0)

        text = RE_DIFF_TORQUE_SPLIT.sub(_fix_split, text)

    # 3. Clamp extreme viscous coupling stiffness to prevent explosion
    if "viscouscoupling" in content_lower:
        def _fix_viscous(m: re.Match) -> str:
            val = float(m.group(2))
            if val > 10000:
                nonlocal fix_count
                fix_count += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f"Clamped dangerous viscousCoupling stiffness ({val} -> 250) to prevent physics explosion",
                        file_path=filename,
                        rule="viscous_stiffness_clamped",
                    )
                )
                return f"{m.group(1)}250{m.group(3)}"
            return m.group(0)

        text = RE_VISCOUS_STIFFNESS.sub(_fix_viscous, text)

    # 4. Fix tire pressure (pressurePSI < 10.0 -> 30.0)
    if "pressurepsi" in content_lower:
        def _fix_psi(m: re.Match) -> str:
            val = float(m.group(2))
            if val < 10.0:
                nonlocal fix_count
                fix_count += 1
                diagnostics.append(
                    DiagnosticNotice(
                        severity="warning",
                        message=f"Repaired unstable tire pressurePSI ({val} -> 30.0 PSI) to prevent tire collapse / simulation pause",
                        file_path=filename,
                        rule="tire_pressure_fixed",
                    )
                )
                return f"{m.group(1)}30.0{m.group(3)}"
            return m.group(0)

        text = RE_TIRE_PRESSURE.sub(_fix_psi, text)

    # 5. Fix wheel inertia (wheelInertia <= 0 -> 0.85)
    if "wheelinertia" in content_lower:
        def _fix_inertia(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Repaired non-positive wheelInertia to standard 0.85 kg*m²",
                    file_path=filename,
                    rule="wheel_inertia_fixed",
                )
            )
            return f"{m.group(1)}0.85{m.group(3)}"

        text = RE_WHEEL_INERTIA.sub(_fix_inertia, text)

    # 6. Fix abnormal tire friction coefficients
    if "frictioncoef" in content_lower:
        def _fix_friction(m: re.Match) -> str:
            val = float(m.group(2))
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Normalized abnormal tire frictionCoef ({val} -> 1.0)",
                    file_path=filename,
                    rule="tire_friction_normalized",
                )
            )
            return f"{m.group(1)}1.0{m.group(3)}"

        text = RE_TIRE_FRICTION.sub(_fix_friction, text)

    # 7. Fix zero clutch torque (prevents permanent free-revving stall)
    if "clutchtorque" in content_lower:
        def _fix_clutch(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message="Repaired zero/negative clutchTorque to standard 350 N*m",
                    file_path=filename,
                    rule="clutch_torque_fixed",
                )
            )
            return f"{m.group(1)}350{m.group(3)}"

        text = RE_CLUTCH_TORQUE.sub(_fix_clutch, text)

    # 8. Fix extreme or negative brake torque
    if "braketorque" in content_lower or "brakingtorque" in content_lower:
        def _fix_brake(m: re.Match) -> str:
            val = float(m.group(2))
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message=f"Normalized extreme/negative brakeTorque ({val} -> 3500 N*m)",
                    file_path=filename,
                    rule="brake_torque_normalized",
                )
            )
            return f"{m.group(1)}3500{m.group(3)}"

        text = RE_BRAKE_TORQUE.sub(_fix_brake, text)

    if fix_count == 0 or text == content:
        return content, 0, diagnostics

    return text, fix_count, diagnostics
