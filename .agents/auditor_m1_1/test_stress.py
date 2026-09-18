import sys
sys.path.insert(0, "src")

from beamng_mod_fixer.core.jbeam_fixer import (
    detect_light_cast_shadows,
    fix_jbeam_content,
    audit_spotlights,
    decode_jbeam_bytes,
    encode_jbeam_str,
)
from beamng_mod_fixer.models import (
    DiagnosticNotice,
    JBeamFixResult,
    ModArchiveReport,
    ModStatus,
    OptimizationResult,
    CacheCleanResult,
    OverallSummary
)
from beamng_mod_fixer.exceptions import (
    BeamNGModFixerError,
    CorruptArchiveError,
    ArchiveLockedError,
    PasswordProtectedArchiveError,
    ArchivePermissionError,
    JBeamError,
    JBeamSyntaxError,
    JBeamSyntaxWarning,
    SettingsError,
    SettingsNotFoundError,
    SettingsCorruptedError,
    BeamNGPathNotFoundError,
    CacheCleanError,
    GameRunningWarning
)

passed = 0
failed = 0

def check(cond, msg):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAILED: {msg}")

# 1. CP1251 Raw Bytes Decoding
raw_cp1251 = b'{"desc": "\xcf\xf0\xe8\xe2\xe5\xf2"}' # "Привет" in CP1251
text, enc = decode_jbeam_bytes(raw_cp1251)
check(enc == "cp1251", f"Expected cp1251, got {enc}")
check(text == '{"desc": "Привет"}', f"Expected Привет, got {text}")
check(encode_jbeam_str(text, enc) == raw_cp1251, "CP1251 roundtrip failed")

# 2. UTF-8 with BOM
raw_bom = b'\xef\xbb\xbf{"key": "value"}'
text, enc = decode_jbeam_bytes(raw_bom)
check(enc == "utf-8-sig", "BOM encoding check")
check(text == '{"key": "value"}', "BOM stripped check")
check(encode_jbeam_str(text, enc) == raw_bom, "BOM roundtrip")

# 3. Standard UTF-8 with multibyte characters
raw_utf8 = '{"desc": "Фары и свет 🚗"}'.encode("utf-8")
text, enc = decode_jbeam_bytes(raw_utf8)
check(enc == "utf-8", "UTF-8 multibyte detected")
check("Фары и свет 🚗" in text, "UTF-8 multibyte text")
check(encode_jbeam_str(text, enc) == raw_utf8, "UTF-8 roundtrip")

# 4. Fallback encoding (invalid utf-8, invalid cp1251 -> latin-1)
# Note: CP1251 maps all bytes 0x00-0xFF except 0x98 (which fails in cp1251 strict in python)
# Byte 0x98 in CP1251 raises UnicodeDecodeError
raw_unassigned = b'{"data": "\x98"}'
text, enc = decode_jbeam_bytes(raw_unassigned)
check(enc == "cp1252", f"Expected cp1252, got {enc}") # 0x98 in cp1252 is mapped or falls to latin-1

# 5. Regex Stress Testing
sample_complex = """
// Vehicle headlight definition
{
    "headlight_L": {
        "information": {
            "name": "Left Headlight"
        },
        /* Core beam configuration */
        "lightCastShadows": true, // Main headlight shadow
        "flareName": "none",
        "cookieName": "art/shapes/lights/old_cookie.dds",
        "lightInnerAngle": 45.0,
        "lightOuterAngle": 40.0
    },
    "headlight_R": {
        'lightCastShadows' : /* inline */ true ,
        "flareName": "vehicle_headlight_flare",
        "cookieName": "vehicles/mycar/cookie.dds"
    },
    "tail_light": {
        "lightCastShadows": false,
        "flareName": ""
    }
}
"""
fixed, count, diags = fix_jbeam_content(sample_complex, filename="headlights.jbeam")
check(count == 2, f"Count expected 2, got {count}")
check('"lightCastShadows": false, // Main headlight shadow' in fixed, "Preserved trailing line comment")
check("'lightCastShadows' : /* inline */ false ," in fixed, "Preserved single quotes and inline comments")
check('"flareName": ""' in fixed, "flareName 'none' normalized")
check('"flareName": "vehicle_headlight_flare"' in fixed, "Valid flareName untouched")
check('"lightCastShadows": false,\n        "flareName": ""' in fixed, "Already false untouched")

rules = [d.rule for d in diags]
check("flare_name_normalized" in rules, "flare_name_normalized diagnostic emitted")
check("cookie_path_obsolete" in rules, "cookie_path_obsolete diagnostic emitted")
check("spotlight_angle_inverted" in rules, "spotlight_angle_inverted diagnostic emitted")

print(f"STRESS SUITE COMPLETE: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
