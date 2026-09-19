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
RE_OBSOLETE_SOUND_PATH = re.compile(
    r'(?i)([\"\'\`]?(?:sampleName|soundFile|soundEvent|audioProfile)[\"\'\`]?\s*:\s*[\"\'`])'
    r'(?:/*art/sound/[^\"\'`]+|[^\"\'`]+\.(?:wav|ogg))([\"\'`])'
)

# Obsolete event:>art> paths
RE_OBSOLETE_EVENT_ART = re.compile(
    r'(?i)([\"\'\`]?(?:sampleName|soundFile|soundEvent)[\"\'\`]?\s*:\s*[\"\'`])'
    r'event:>art>[^\"\'`]+([\"\'`])'
)

# Out of range soundVolume or soundPitch
RE_SOUND_VOLUME = re.compile(
    r'(?i)([\"\'\`]?soundVolume[\"\'\`]?\s*:\s*)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?|[5-9]\d*(?:\.\d+)?)(?![.\d])'
)
RE_SOUND_PITCH = re.compile(
    r'(?i)([\"\'\`]?soundPitch[\"\'\`]?\s*:\s*)(-[0-9]+(?:\.[0-9]+)?|0(?:\.0+)?|[4-9]\d*(?:\.\d+)?)(?![.\d])'
)


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

    has_sound = any(k in content_lower for k in ("sound", "samplename", "audioprofile", "soundevent", "soundconfig"))
    if not has_sound:
        return content, 0, diagnostics

    fix_count = 0

    # 1. Obsolete sound file/path references (art/sound/* -> event:>Engine>default)
    if "art/sound/" in content_lower or ".wav" in content_lower or ".ogg" in content_lower:
        def _replace_sound(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Modernized legacy sound path to modern BeamNG FMOD event 'event:>Engine>default'",
                    file_path=filename,
                    rule="sound_path_modernized",
                )
            )
            return f"{m.group(1)}{MODERN_ENGINE_EVENT}{m.group(2)}"

        text = RE_OBSOLETE_SOUND_PATH.sub(_replace_sound, text)

    # 2. Obsolete event:>art> references
    if "event:>art>" in content_lower:
        def _replace_event_art(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Replaced obsolete event:>art> reference with modern BeamNG FMOD event",
                    file_path=filename,
                    rule="sound_event_art_modernized",
                )
            )
            return f"{m.group(1)}{MODERN_ENGINE_EVENT}{m.group(2)}"

        text = RE_OBSOLETE_EVENT_ART.sub(_replace_event_art, text)

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
