"""Tier 1: Feature Tests for Smart Headlight Fixer.

Verifies:
- Lowbeam lightCastShadows: true -> false (prevents front bumper self-shadow culling)
- Highbeam lightCastShadows: true PRESERVED (prevents cockpit light bleed and blinding)
- Obsolete cookie modernization (art/shapes/lights/* -> art/special/BNG_light_cookie_headlight.dds)
- Legacy flare modernization (headlightFlare -> vehicleHeadLightFlare, highbeamFlare -> vehicleHighBeamFlare)
- Inverted spotlight angle repair (inner > outer -> inner < outer)
- Misspelled electrics signal normalization (low_beam -> lowbeam, high_beam -> highbeam)
- Smart mode restoration of invalid flare and cookie values
- Full synthetic mod ZIP end-to-end processing with selective=True
"""

import io
import zipfile
import pytest
from beamng_mod_fixer.core.jbeam_fixer import (
    smart_fix_jbeam_content,
    fix_jbeam_content,
    patch_jbeam_text,
    MODERN_HEADLIGHT_COOKIE,
    MODERN_HEADLIGHT_FLARE,
    MODERN_HIGHBEAM_FLARE,
    MODERN_FOG_FLARE,
)
from beamng_mod_fixer.core.zip_processor import process_mod_archive


def test_smart_headlight_preserves_highbeam_shadows():
    jbeam = '''{
        "spotlights": [
            ["type", "pos", "dir", "innerAngle", "outerAngle", "range", "brightness", "castShadows"],
            {"flareName": "vehicleHeadLightFlare", "lightRange": 50, "lightCastShadows": true},
            ["lowbeam", ["f1l", "f1r", "f2l"]],
            {"flareName": "vehicleHighBeamFlare", "lightRange": 90, "lightCastShadows": true},
            ["highbeam", ["f1l", "f1r", "f3l"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)

    # Lowbeam must be converted to false
    assert '"flareName": "vehicleHeadLightFlare", "lightRange": 50, "lightCastShadows": false' in fixed
    # Highbeam must retain true
    assert '"flareName": "vehicleHighBeamFlare", "lightRange": 90, "lightCastShadows": true' in fixed
    assert count == 1
    assert any(d.rule == "highbeam_shadow_preserved" for d in diags)
    assert any(d.rule == "lowbeam_shadow_fixed" for d in diags)


def test_smart_headlight_modernizes_obsolete_cookies():
    jbeam = '''{
        "spotlights": [
            {"cookieName": "art/shapes/lights/headlight_cookie.dds", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert MODERN_HEADLIGHT_COOKIE in fixed
    assert "art/shapes/lights/" not in fixed
    assert '"lightCastShadows": false' in fixed
    assert any(d.rule == "cookie_path_modernized" for d in diags)


def test_smart_headlight_modernizes_legacy_flares():
    jbeam = '''{
        "spotlights": [
            {"flareName": "headlightFlare", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]],
            {"flareName": "highbeamFlare", "lightCastShadows": true},
            ["highbeam", ["a", "b", "c"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert MODERN_HEADLIGHT_FLARE in fixed
    assert MODERN_HIGHBEAM_FLARE in fixed
    assert "headlightFlare" not in fixed
    assert "highbeamFlare" not in fixed
    assert any(d.rule == "flare_legacy_modernized" for d in diags)


def test_smart_headlight_repairs_inverted_angles():
    jbeam = '''{
        "spotlights": [
            {"lightInnerAngle": 65.0, "lightOuterAngle": 40.0, "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert 'lightInnerAngle": 40.0' in fixed
    assert 'lightOuterAngle": 65.0' in fixed
    assert any(d.rule == "spotlight_angle_repaired" for d in diags)


def test_smart_headlight_normalizes_electrics_signals():
    jbeam = '''{
        "spotlights": [
            ["type", "nodes"],
            ["low_beam", ["n1", "n2", "n3"]],
            ["high_beam", ["n1", "n2", "n3"]],
            ["fog_light", ["n1", "n2", "n3"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert '["lowbeam"' in fixed
    assert '["highbeam"' in fixed
    assert '["fog"' in fixed
    assert any(d.rule == "electrics_signal_normalized" for d in diags)


def test_smart_headlight_restores_none_flares_and_cookies():
    jbeam = '''{
        "spotlights": [
            {"flareName": "none", "cookieName": "none", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''

    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert f'"{MODERN_HEADLIGHT_FLARE}"' in fixed
    assert f'"{MODERN_HEADLIGHT_COOKIE}"' in fixed
    assert '"none"' not in fixed


def test_zip_processor_smart_mode(tmp_path):
    """Verify end-to-end mod zip processing in selective smart mode."""
    mod_zip = tmp_path / "test_mod.zip"
    jbeam_content = '''{
        "test_part": {
            "spotlights": [
                {"flareName": "vehicleHeadLightFlare", "lightCastShadows": true},
                ["lowbeam", ["a", "b", "c"]],
                {"flareName": "vehicleHighBeamFlare", "lightCastShadows": true},
                ["highbeam", ["d", "e", "f"]]
            ]
        }
    }'''

    with zipfile.ZipFile(mod_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vehicles/coupe/coupe_lights.jbeam", jbeam_content)

    summary = process_mod_archive(mod_zip, selective=True)
    assert summary.status == "fixed"
    assert summary.shadows_fixed == 1
    assert summary.jbeams_modified == 1

    with zipfile.ZipFile(mod_zip, "r") as zf:
        fixed_jbeam = zf.read("vehicles/coupe/coupe_lights.jbeam").decode("utf-8")
        assert '"flareName": "vehicleHeadLightFlare", "lightCastShadows": false' in fixed_jbeam
        assert '"flareName": "vehicleHighBeamFlare", "lightCastShadows": true' in fixed_jbeam


def test_smart_headlight_removes_cookie_leading_slash():
    jbeam = '''{
        "spotlights": [
            {"cookieName": "/art/special/BNG_light_cookie_headlight.dds", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''
    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert '"art/special/BNG_light_cookie_headlight.dds"' in fixed
    assert '"/art/' not in fixed
    assert any(d.rule == "cookie_path_normalized" for d in diags)


def test_smart_headlight_fixes_cookie_png_extension():
    jbeam = '''{
        "spotlights": [
            {"cookieName": "art/special/BNG_light_cookie_headlight.png", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''
    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert MODERN_HEADLIGHT_COOKIE in fixed
    assert ".png" not in fixed
    assert any(d.rule == "cookie_extension_modernized" for d in diags)


def test_smart_headlight_replaces_missing_local_cookie():
    jbeam = '''{
        "spotlights": [
            {"cookieName": "vehicles/custom_car/textures/missing_cookie.dds", "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''
    available_files = {"vehicles/custom_car/car.jbeam", "vehicles/custom_car/car.dae"}
    fixed, count, diags = smart_fix_jbeam_content(jbeam, available_files=available_files)
    assert MODERN_HEADLIGHT_COOKIE in fixed
    assert "missing_cookie.dds" not in fixed
    assert any(d.rule == "cookie_missing_replaced" for d in diags)


def test_smart_headlight_repairs_zero_brightness_and_range():
    jbeam = '''{
        "spotlights": [
            {"lightBrightness": 0, "lightRange": 0.0, "lightCastShadows": true},
            ["lowbeam", ["a", "b", "c"]]
        ]
    }'''
    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    assert '"lightBrightness": 0.75' in fixed
    assert '"lightRange": 70.0' in fixed
    assert any(d.rule == "spotlight_brightness_repaired" for d in diags)
    assert any(d.rule == "spotlight_range_repaired" for d in diags)


def test_smart_headlight_does_not_inject_props_between_rows():
    """Verify that props arrays with lowbeam and highbeam meshes are NOT corrupted."""
    jbeam = '''{
        "props": [
            ["func", "mesh", "idRef:", "idX:", "idY:"],
            ["lowbeam", "headlight_mesh_L", "ref", "x", "y"],
            ["highbeam", "highbeam_mesh_L", "ref", "x", "y"]
        ]
    }'''
    fixed, count, diags = smart_fix_jbeam_content(jbeam)
    # The structure must NOT have an artificial dict injected between lowbeam and highbeam
    assert '["lowbeam", "headlight_mesh_L"' in fixed
    assert '["highbeam", "highbeam_mesh_L"' in fixed
    assert "vehicleHighBeamFlare" not in fixed
    assert "lightRange" not in fixed

