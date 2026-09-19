"""Sound & Audio Modernizer Engine for BeamNG.drive mods.

Provides:
- Modernization of legacy pre-FMOD audio paths (art/sound/*, AudioProfile references)
  to modern BeamNG FMOD sound events.
- Repair of dead sound event references that trigger vehicle audio lua script crashes
  and silent engines.
- Audio volume and pitch factor stabilization.
"""

import logging
import re
from typing import List, Optional, Tuple

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

# Modern BeamNG official FMOD fallback audio events
MODERN_ENGINE_EVENT = "event:>Engine>default"
MODERN_TRANSMISSION_EVENT = "event:>Vehicles>Transmission>transmission_manual_01"
MODERN_HORN_EVENT = "event:>Vehicles>Horn>horn_01"

# Obsolete pre-FMOD sound paths (art/sound/... or .wav/.ogg direct file references)
RE_OBSOLETE_SOUND_PROPERTY = re.compile(
    r'(?i)([\"\'\`]?(?P<key>sampleName|soundFile|soundEvent|audioProfile|soundProfile|hornSound|bovSound|blowoffSound|turboSound|transmissionSound|engineSound|exhaustSound)[\"\'\`]?\s*:\s*[\"\'`])'
    r'(?:/*art/sound/[^\"\'`]+|[^\"\'`]+\.(?:wav|ogg|sfx)|event:>art>[^\"\'`]+)([\"\'`])'
)

# Out of range soundVolume or soundPitch
RE_SOUND_VOLUME = re.compile(
    r'(?i)([\"\'\`]?soundVolume[\"\'\`]?\s*:\s*)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?|[5-9]\d*(?:\.\d+)?)(?![.\d])'
)
RE_SOUND_PITCH = re.compile(
    r'(?i)([\"\'\`]?soundPitch[\"\'\`]?\s*:\s*)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?|[4-9]\d*(?:\.\d+)?)(?![.\d])'
)


def _select_modern_event(key_name: str) -> str:
    """Select appropriate modern BeamNG FMOD event based on property context."""
    k = key_name.lower()
    if "horn" in k:
        return MODERN_HORN_EVENT
    elif "transmission" in k or "gearbox" in k:
        return MODERN_TRANSMISSION_EVENT
    elif any(t in k for t in ("turbo", "bov", "blowoff", "wastegate")):
        return "event:>Vehicles>Turbo>turbo_01"
    return MODERN_ENGINE_EVENT


def fix_sound_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Inspect and modernize sound events and volume parameters in JBeam text.

    Args:
        content: Raw JBeam text content.
        filename: Optional filename for diagnostics.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Modernized JBeam content.
            - fix_count: Number of sound definitions repaired.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    content_lower = content.lower()

    has_sound = any(k in content_lower for k in ("sound", "samplename", "audioprofile", "soundevent", "soundconfig", "hornsound", "soundprofile"))
    if not has_sound:
        return content, 0, diagnostics

    fix_count = 0

    # 1. Obsolete sound file/path references modernized to context-specific FMOD event
    if any(tok in content_lower for tok in ("art/sound/", ".wav", ".ogg", ".sfx", "event:>art>")):
        def _replace_sound(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            prop_key = m.group("key")
            modern_event = _select_modern_event(prop_key)
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message=f"Modernized legacy sound path in '{prop_key}' to modern BeamNG FMOD event '{modern_event}'",
                    file_path=filename,
                    rule="sound_path_modernized",
                )
            )
            return f"{m.group(1)}{modern_event}{m.group(3)}"

        text = RE_OBSOLETE_SOUND_PROPERTY.sub(_replace_sound, text)

    # 3. Sound volume normalization
    if "soundvolume" in content_lower:
        def _fix_volume(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Normalized non-positive or extreme soundVolume to 1.0",
                    file_path=filename,
                    rule="sound_volume_normalized",
                )
            )
            return f"{m.group(1)}1.0"

        text = RE_SOUND_VOLUME.sub(_fix_volume, text)

    # 4. Sound pitch normalization
    if "soundpitch" in content_lower:
        def _fix_pitch(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Normalized non-positive or extreme soundPitch to 1.0",
                    file_path=filename,
                    rule="sound_pitch_normalized",
                )
            )
            return f"{m.group(1)}1.0"

        text = RE_SOUND_PITCH.sub(_fix_pitch, text)

    if fix_count == 0 or text == content:
        return content, 0, diagnostics

    return text, fix_count, diagnostics
