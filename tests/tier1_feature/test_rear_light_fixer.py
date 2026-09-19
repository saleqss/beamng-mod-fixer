"""Tier 1: Feature Tests for Rear Light Ground Illumination Fixer.

Verifies:
- Detection of rear light files and content
- Repair of missing comma after cookieName attribute
- Repair of missing commas between JBeam array rows
- Removal of directional headlight cutoff cookies from rear lamps
- Elimination of the white rear light bug (explicit lightColor injection to stop template inheritance)
- Calibration of reverse lights to realistic 0.75 brightness and 13.0m range
- Calibration of brake lights to realistic 0.35 brightness and 9.0m range (no nuclear red discs)
- Calibration of taillights to realistic 0.12 brightness and 6.0m range
- Injection of quadratic lightAttenuation (x:0, y:1, z:2) for smooth photographic road wash
- Disabling self-shadow casting (lightCastShadows: false) on rear lights
- Cadillac Escalade taillight sample verification
"""

import pytest
from beamng_mod_fixer.core.rear_light_fixer import (
    enhance_rear_light_content,
    is_rear_light_file,
)


def test_is_rear_light_file():
    assert is_rear_light_file("vehicles/car/car_taillights.jbeam") is True
    assert is_rear_light_file("vehicles/car/car_rearlights.jbeam") is True
    assert is_rear_light_file("vehicles/car/car_tail_light.jbeam") is True
    assert is_rear_light_file("vehicles/car/car_headlights.jbeam") is False
    assert is_rear_light_file("vehicles/car/car_body.jbeam") is False
    # Content detection
    assert is_rear_light_file("car.jbeam", '["reverse", "SPOTLIGHT", ...]') is True
    assert is_rear_light_file("car.jbeam", '{"flareName": "vehicleReverseLightFlare"}') is True


def test_rear_light_missing_cookie_comma_repair():
    jbeam = """{
        "props": [
            {
                "cookieName": "art/special/BNG_light_cookie_headlight.dds"
                "texSize": 512,
            }
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")
    assert '"cookieName": "",' in fixed or '"cookieName": "art/special/BNG_light_cookie_headlight.dds",' in fixed
    assert any(d.rule == "jbeam_syntax_comma_repaired" for d in diags)


def test_rear_light_missing_row_comma_repair():
    jbeam = """{
        "beams": [
            ["tl4r", "q7r"]
            ["tl3r", "q3r"],
            {"deformGroup": ""}
            ["tl1r", "q2r"]
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")
    assert '["tl4r", "q7r"],\n            ["tl3r", "q3r"]' in fixed
    assert '{"deformGroup": ""},\n            ["tl1r", "q2r"]' in fixed
    assert any(d.rule == "jbeam_row_comma_repaired" for d in diags)


def test_rear_light_clears_headlight_cookie():
    jbeam = """{
        "props": [
            {
                "cookieName": "art/special/BNG_light_cookie_headlight.dds",
                "texSize": 512
            }
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")
    assert '"cookieName": ""' in fixed
    assert any(d.rule == "rear_cookie_cutoff_removed" for d in diags)


def test_rear_light_boosts_reverse_and_brake_lights():
    jbeam = """{
        "props": [
            {
                "lightRange": 5,
                "lightCastShadows": true
            },
            ["reverse", "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-30}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"lightBrightness": 0.06, "lightCastShadows": true}],
            ["brake", "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-40}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"lightBrightness": 0.07, "lightCastShadows": true}],
            ["lowhighbeam", "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-40}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"lightBrightness": 0.02, "lightRange": 4}]
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")

    # Template range calibrated
    assert '"lightRange": 10.0' in fixed

    # Reverse calibrated to 0.75, range 13.0m, warm white color, shadows disabled
    assert '"lightBrightness": 0.75' in fixed
    assert '"lightRange": 13.0' in fixed
    assert '"lightCastShadows": false' in fixed
    assert '"lightColor": {"r": 255, "g": 250, "b": 220, "a": 255}' in fixed

    # Brake calibrated to 0.35, range 9.0m, vivid red color, shadows disabled
    assert '"lightBrightness": 0.35' in fixed
    assert '"lightRange": 9.0' in fixed
    assert '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}' in fixed

    # Lowhighbeam / taillight calibrated to 0.12, range 6.0m, vivid red color
    assert '"lightBrightness": 0.12' in fixed
    assert '"lightRange": 6.0' in fixed

    # Quadratic attenuation injected
    assert '"lightAttenuation": {"x": 0, "y": 1, "z": 2}' in fixed

    assert any(d.rule == "rear_brightness_boosted" for d in diags)
    assert any(d.rule == "rear_color_inheritance_prevented" for d in diags)
    assert any(d.rule == "rear_attenuation_softened" for d in diags)
    assert any(d.rule == "rear_shadow_occlusion_disabled" for d in diags)


def test_cadillac_escalade_sample_fix():
    cadillac_sample = """{
"AR23esv_taillight_R": {
    "props": [
        ["func", "mesh", "idRef:", "idX:", "idY:", "baseRotation", "rotation", "translation", "min", "max", "offset", "multiplier"],
        {
            "lightInnerAngle":40.0,
            "lightOuterAngle":120.0,
            "lightRange":8,
            "lightColor":{"r":255, "g":255, "b":160, "a":255},
            "lightAttenuation":{"x":0, "y":1, "z":1},
            "lightCastShadows":false,
            "flareName":"vehicleReverseLightFlare",
            "cookieName":"art/special/BNG_light_cookie_headlight.dds"
            "texSize":512,
            "shadowSoftness":0.5,
        },
        ["reverse" , "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-30}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"baseTranslation":{"x":0.40, "y":0.1, "z":-0.015},"flareScale":0.0,"lightBrightness":0.06,"deformGroup":"taillight_R_break"}],
        {
            "lightInnerAngle":40.0,
            "lightOuterAngle":120.0,
            "lightRange":8,
            "lightColor":{"r":255, "g":50, "b":0, "a":255},
            "lightCastShadows":false,
            "flareName":"vehicleBrakeLightFlare",
        },
        ["brake" , "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-40}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"baseTranslation":{"x":0.40, "y":0.4, "z":-0.015},"flareScale":0.0,"lightBrightness":0.07,"deformGroup":"taillight_R_break"}],
        ["signal_R" , "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-40}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"baseTranslation":{"x":0.40, "y":0.6, "z":-0.015},"flareScale":0.0,"lightBrightness":0.04,"deformGroup":"taillight_R_break"}],
        ["lowhighbeam" , "SPOTLIGHT", "tl2r", "tl4r", "tl1r", {"x":0, "y":-30, "z":-40}, {"x":0, "y":0, "z":0}, {"x":0, "y":0, "z":0}, 0, 0, 0, 1, {"baseTranslation":{"x":0.40, "y":0.6, "z":-0.015},"flareScale":0.0,"lightBrightness":0.02,"lightRange":8,"deformGroup":"taillight_R_break"}],
     ]
}
}"""
    fixed, count, diags = enhance_rear_light_content(cadillac_sample, "AR23esv_taillights.jbeam")
    assert '"cookieName":""' in fixed.replace(" ", "")
    assert '"lightBrightness": 0.75' in fixed
    assert '"lightBrightness": 0.35' in fixed
    assert '"lightBrightness": 0.4' in fixed
    assert '"lightBrightness": 0.12' in fixed
    # Verify lowhighbeam has explicit red color to eliminate white headlight bug
    assert '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}' in fixed


def test_eliminate_white_headlight_rear_bug():
    """Verify that when a reverse light template precedes a taillight, white light is prevented."""
    jbeam = """{
        "props": [
            {
                "lightColor": {"r": 255, "g": 255, "b": 255, "a": 255},
                "flareName": "vehicleReverseLightFlare"
            },
            ["reverse", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.5}],
            ["lowhighbeam", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.5}]
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")
    # Lowhighbeam must have explicit red color, NOT inheriting white!
    assert '"lightColor": {"r": 255, "g": 20, "b": 20, "a": 255}' in fixed
    assert any(d.rule == "rear_color_inheritance_prevented" for d in diags)


def test_overbright_rear_spotlights_calibrated_down():
    """Verify that nuclear-bright rear spotlights (e.g. 0.85 on tail, 1.5 on reverse) are calibrated down."""
    jbeam = """{
        "props": [
            ["brake", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 1.2, "lightRange": 25.0}],
            ["lowhighbeam", "SPOTLIGHT", "a", "b", "c", {}, {}, {}, 0, 0, 0, 1, {"lightBrightness": 0.85, "lightRange": 18.0}]
        ]
    }"""
    fixed, count, diags = enhance_rear_light_content(jbeam, "car_taillights.jbeam")
    assert '"lightBrightness": 0.35' in fixed
    assert '"lightBrightness": 0.12' in fixed
    assert '"lightRange": 9.0' in fixed
    assert '"lightRange": 6.0' in fixed
    assert any(d.rule == "rear_brightness_calibrated" for d in diags)
    assert any(d.rule == "rear_range_calibrated" for d in diags)
