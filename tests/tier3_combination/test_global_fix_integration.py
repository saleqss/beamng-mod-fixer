"""Tier 3 Combination Tests: 1-Click Global Multi-Domain Mod Fix.

Verifies:
- Simultaneous detection and repair of all mod breakages in a single archive:
  * Headlight self-shadow occlusion (lightCastShadows: true -> false)
  * materials.cs converted to modern main.materials.json 1.5 PBR
  * Broken texture paths and backslashes in materials.json
  * Differential freeze & explosion (gearRatio: 0, viscousCoupling: 50000)
  * Tire pressure blowout (pressurePSI: 0 -> 30.0)
  * Obsolete pre-FMOD audio (art/sound/* -> event:>Engine>default)
  * Dangerous vehicle Lua scripts guarded against nil dereference
  * Removal of OS/editor junk files (Thumbs.db)
  * Byte-for-byte passthrough integrity of non-modified binary assets (.dds)
"""

import hashlib
import json
from pathlib import Path
import zipfile

from beamng_mod_fixer.core.zip_processor import process_mod_archive, scan_and_fix_mods
from beamng_mod_fixer.models import ModStatus
from tests.fixtures.factory import DUMMY_DDS_BYTES


def create_multi_issue_mod_zip(zip_path: Path, vehicle_name: str = "broken_ride") -> Path:
    """Create a mod zip archive afflicted with all major BeamNG update breakages."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Headlights with self-shadow bug
        headlights_jbeam = """{
            "ride_headlights": {
                "spotlights": [
                    ["headlight_L", "b1", "b2", "b3", {"lightRange": 60, "lightCastShadows": true, "flareName": "vehicleHeadLightFlare"}]
                ]
            }
        }"""
        zf.writestr(f"vehicles/{vehicle_name}/headlights.jbeam", headlights_jbeam)

        # 2. Differential with gearRatio: 0 and dangerous viscous coupling
        diff_jbeam = """{
            "ride_differential": {
                "gearRatio": 0,
                "viscousCoupling": 50000,
                "diffTorqueSplit": 0.0
            }
        }"""
        zf.writestr(f"vehicles/{vehicle_name}/differential.jbeam", diff_jbeam)

        # 3. Wheels with flat tire pressure
        wheels_jbeam = """{
            "ride_wheels": {
                "pressurePSI": 0,
                "frictionCoef": 9.0
            }
        }"""
        zf.writestr(f"vehicles/{vehicle_name}/wheels.jbeam", wheels_jbeam)

        # 4. Engine with obsolete audio path
        engine_jbeam = """{
            "ride_engine": {
                "sampleName": "art/sound/old_engine.wav",
                "soundVolume": 0
            }
        }"""
        zf.writestr(f"vehicles/{vehicle_name}/engine.jbeam", engine_jbeam)

        # 5. Legacy materials.cs
        materials_cs = """
        singleton Material(ride_body)
        {
            mapTo = "ride_body";
            diffuseMap[0] = "vehicles/broken_ride/body_d.dds";
            normalMap[0] = "vehicles\\broken_ride\\body_n.dds";
            translucent = false;
        };
        """
        zf.writestr(f"vehicles/{vehicle_name}/materials.cs", materials_cs)

        # 6. Legacy materials.json with backslashes
        materials_json = json.dumps({
            "ride_interior": {
                "name": "ride_interior",
                "mapTo": "ride_interior",
                "class": "Material",
                "Stages": [
                    {
                        "colorMap": "vehicles\\broken_ride\\interior_d.dds"
                    }
                ],
                "version": 1
            }
        })
        zf.writestr(f"vehicles/{vehicle_name}/interior.materials.json", materials_json)

        # 7. Corrupted Lua script with toxic preamble and broken wrapper
        lua_code = """-- [GBEAM FIX] Guard against uninitialized vehicle globals
local v = v or { data = {} }
local M = {}
function M.init()
    local rpm = v.data.rpm
    (obj.queueGameEngineLua and obj:queueGameEngineLua or function(...) end)("print(1)")
end
return M
"""
        zf.writestr(f"vehicles/{vehicle_name}/lua/dash.lua", lua_code)

        # 8. Junk file
        zf.writestr(f"vehicles/{vehicle_name}/Thumbs.db", b"\x00\x01\x02\x03junk")

        # 9. Binary DDS texture
        zf.writestr(f"vehicles/{vehicle_name}/textures/paint.dds", DUMMY_DDS_BYTES)

    return zip_path


def test_1click_global_fix_all_breakages(tmp_path: Path) -> None:
    """Test that 1-Click Global Fix repairs all breakages while preserving binary assets."""
    mod_path = tmp_path / "broken_mod.zip"
    create_multi_issue_mod_zip(mod_path, "super_car")

    # Hash binary asset before repair
    with zipfile.ZipFile(mod_path, "r") as zf:
        orig_dds_hash = hashlib.sha256(zf.read("vehicles/super_car/textures/paint.dds")).hexdigest()
        assert "vehicles/super_car/Thumbs.db" in zf.namelist()

    # Process archive
    report = process_mod_archive(mod_path, dry_run=False)

    assert report.status == ModStatus.FIXED.value
    assert report.shadows_fixed >= 1
    assert report.materials_converted >= 1
    assert report.materials_fixed >= 1
    assert report.drivetrains_fixed >= 2
    assert report.sounds_fixed >= 2
    assert report.lua_fixed >= 2
    assert report.junk_cleaned >= 1

    # Verify contents of rewritten archive
    with zipfile.ZipFile(mod_path, "r") as zf:
        namelist = zf.namelist()

        # 1. Thumbs.db should be purged
        assert "vehicles/super_car/Thumbs.db" not in namelist

        # 2. main.materials.json should exist and be valid JSON 1.5
        assert "vehicles/super_car/main.materials.json" in namelist
        mats_data = json.loads(zf.read("vehicles/super_car/main.materials.json").decode("utf-8"))
        assert mats_data["ride_body"]["version"] == 1.5
        assert "\\" not in mats_data["ride_body"]["Stages"][0]["normalMap"]

        # 3. Headlights jbeam should have lightCastShadows: false
        hl_text = zf.read("vehicles/super_car/headlights.jbeam").decode("utf-8")
        assert "false" in hl_text
        assert "true" not in hl_text

        # 4. Differential should have gearRatio: 3.73 and clamped viscous coupling
        diff_text = zf.read("vehicles/super_car/differential.jbeam").decode("utf-8")
        assert "3.73" in diff_text
        assert "250" in diff_text

        # 5. Wheels should have pressurePSI: 30.0
        wheels_text = zf.read("vehicles/super_car/wheels.jbeam").decode("utf-8")
        assert "30.0" in wheels_text
        assert "1.0" in wheels_text

        # 6. Sound should use event:>Engine>default
        engine_text = zf.read("vehicles/super_car/engine.jbeam").decode("utf-8")
        assert "event:>Engine>default" in engine_text

        # 7. Lua should have toxic preambles stripped and native engine queue restored
        lua_text = zf.read("vehicles/super_car/lua/dash.lua").decode("utf-8")
        assert "local v = v or" not in lua_text
        assert "obj:queueGameEngineLua" in lua_text

        # 8. Binary DDS texture must be byte-for-byte identical
        new_dds_hash = hashlib.sha256(zf.read("vehicles/super_car/textures/paint.dds")).hexdigest()
        assert new_dds_hash == orig_dds_hash


def test_scan_and_fix_mods_aggregates_all_domains(tmp_path: Path) -> None:
    """Test scan_and_fix_mods batch runner accurately sums all multi-domain metrics."""
    mods_dir = tmp_path / "mods"
    create_multi_issue_mod_zip(mods_dir / "mod1.zip", "car1")
    create_multi_issue_mod_zip(mods_dir / "mod2.zip", "car2")

    summary = scan_and_fix_mods(mods_dir, dry_run=False)

    assert summary.total_scanned == 2
    assert summary.modified_archives == 2
    assert summary.shadows_fixed >= 2
    assert summary.materials_converted >= 2
    assert summary.materials_fixed >= 2
    assert summary.drivetrains_fixed >= 4
    assert summary.sounds_fixed >= 4
    assert summary.lua_fixed >= 4
    assert summary.junk_cleaned >= 2


def test_materials_cs_and_json_merge_in_archive(tmp_path: Path) -> None:
    """Test that when an archive contains both main.materials.json and materials.cs, neither is lost."""
    zip_path = tmp_path / "merge_test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("vehicles/car/main.materials.json", json.dumps({"existing_mat": {"version": 1.5, "Stages": [{}]}}))
        zf.writestr("vehicles/car/materials.cs", 'singleton Material("cs_mat") { mapTo = "cs_mat"; diffuseMap[0] = "car.png"; };')

    rep = process_mod_archive(zip_path, fix_materials=True)
    assert rep.status == ModStatus.FIXED.value

    with zipfile.ZipFile(zip_path, "r") as zf:
        data = json.loads(zf.read("vehicles/car/main.materials.json"))
        assert "existing_mat" in data
        assert "cs_mat" in data, f"Converted cs_mat must be merged into main.materials.json! Got: {list(data.keys())}"

