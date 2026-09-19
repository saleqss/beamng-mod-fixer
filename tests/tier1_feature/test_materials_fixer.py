"""Tier 1 Feature Tests: Materials & Texture Doctor.

Verifies:
- Parsing of legacy TorqueScript materials.cs blocks.
- Conversion of materials.cs to modern BeamNG main.materials.json (v1.5 PBR).
- Upgrading obsolete version fields in materials.json to 1.5.
- Normalization of Windows backslashes '\\' to forward slashes '/' in texture paths.
- Texture reconciliation (.png <-> .dds and archive inventory lookup).
- Emissive glow restoration on vehicle lights and gauges.
"""

import json
from pathlib import Path

import pytest

from beamng_mod_fixer.core.materials_fixer import (
    convert_materials_cs_to_json,
    fix_materials_json_content,
    parse_materials_cs,
)


SAMPLE_MATERIALS_CS = """
// Vehicle Body Material
singleton Material(car_body)
{
    mapTo = "car_body";
    diffuseMap[0] = "vehicles/car/car_body_d.dds";
    normalMap[0] = "vehicles\\car\\car_body_n.dds";
    specularMap[0] = "vehicles/car/car_body_s.dds";
    specularPower[0] = 64;
    translucent = false;
    doubleSided = false;
};

/* Headlight glass material */
singleton Material(car_headlight)
{
    mapTo = "car_headlight";
    diffuseMap[0] = "vehicles/car/lights_d.dds";
    glow[0] = true;
    translucent = true;
};
"""


def test_parse_materials_cs_properties() -> None:
    """Test parsing of TorqueScript material properties."""
    parsed = parse_materials_cs(SAMPLE_MATERIALS_CS)
    assert "car_body" in parsed
    assert "car_headlight" in parsed

    body = parsed["car_body"]
    assert body["mapTo"] == "car_body"
    assert body["stages"][0]["colorMap"] == "vehicles/car/car_body_d.dds"
    assert body["stages"][0]["normalMap"] == "vehicles/car/car_body_n.dds"
    assert body["translucent"] is False

    headlight = parsed["car_headlight"]
    assert headlight["translucent"] is True
    assert "emissiveFactor" in headlight["stages"][0]


def test_convert_materials_cs_to_json() -> None:
    """Test converting materials.cs to modern 1.5 JSON."""
    json_str, count, diags = convert_materials_cs_to_json(SAMPLE_MATERIALS_CS)
    assert count == 2
    assert len(diags) >= 2

    data = json.loads(json_str)
    assert "car_body" in data
    assert data["car_body"]["version"] == 1.5
    assert data["car_body"]["Stages"][0]["colorMap"] == "vehicles/car/car_body_d.dds"
    assert data["car_body"]["Stages"][0]["normalMap"] == "vehicles/car/car_body_n.dds"
    assert "emissiveFactor" in data["car_headlight"]["Stages"][0]


def test_materials_json_backslashes_and_version_repair() -> None:
    """Test that backslashes in texture paths are replaced and version is upgraded to 1.5."""
    raw_json = json.dumps({
        "my_skin": {
            "name": "my_skin",
            "mapTo": "my_skin",
            "class": "Material",
            "Stages": [
                {
                    "colorMap": "vehicles\\mycar\\textures\\skin.png",
                    "normalMap": "vehicles\\mycar\\textures\\skin_n.png"
                }
            ],
            "version": 1
        }
    })

    # Available files has .dds instead of .png
    archive_files = {
        "vehicles/mycar/textures/skin.dds",
        "vehicles/mycar/textures/skin_n.dds",
    }

    fixed_json_str, fix_count, diags = fix_materials_json_content(
        raw_json,
        filename="main.materials.json",
        available_files=archive_files
    )
    assert fix_count > 0
    data = json.loads(fixed_json_str)

    assert data["my_skin"]["version"] == 1.5
    assert data["my_skin"]["Stages"][0]["colorMap"] == "vehicles/mycar/textures/skin.dds"
    assert data["my_skin"]["Stages"][0]["normalMap"] == "vehicles/mycar/textures/skin_n.dds"


def test_materials_json_emissive_restoration() -> None:
    """Test that lighting materials receive emissive glow factor."""
    raw_json = json.dumps({
        "vehicle_taillight_glass": {
            "name": "vehicle_taillight_glass",
            "mapTo": "vehicle_taillight_glass",
            "class": "Material",
            "Stages": [
                {
                    "colorMap": "vehicles/car/taillight.dds"
                }
            ],
            "version": 1.5
        }
    })

    fixed_json_str, fix_count, diags = fix_materials_json_content(
        raw_json,
        filename="main.materials.json"
    )
    assert fix_count >= 1
    data = json.loads(fixed_json_str)
    assert data["vehicle_taillight_glass"]["Stages"][0]["emissiveFactor"] == [1.0, 1.0, 1.0]
