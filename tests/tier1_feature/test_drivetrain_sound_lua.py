"""Tier 1 Feature Tests: Drivetrain, Sound, and Lua Fixers.

Verifies:
- Differential gearRatio zero/negative repair.
- Differential torque split normalization.
- Viscous coupling extreme stiffness clamp.
- Tire pressure (pressurePSI <= 0 -> 30.0) repair.
- Tire friction coefficient normalization.
- Clutch torque zero repair.
- Obsolete sound path modernization to BeamNG FMOD events.
- Guarding of deprecated vehicle Lua scripts against nil dereference.
"""

from beamng_mod_fixer.core.drivetrain_fixer import fix_drivetrain_content
from beamng_mod_fixer.core.lua_fixer import fix_lua_content
from beamng_mod_fixer.core.sound_fixer import fix_sound_content


def test_drivetrain_differential_gearratio_repair() -> None:
    """Test that zero or negative gearRatio is repaired to standard 3.73."""
    jbeam = """{
        "differential_R": {
            "gearRatio": 0,
            "diffTorqueSplit": 0.0,
            "viscousCoupling": 50000
        }
    }"""
    fixed, count, diags = fix_drivetrain_content(jbeam)
    assert count >= 2
    assert "3.73" in fixed
    assert "0.5" in fixed
    assert "250" in fixed


def test_drivetrain_tire_pressure_and_friction_repair() -> None:
    """Test that tire pressure <= 0 and extreme friction coefficients are repaired."""
    jbeam = """{
        "wheels": [
            ["name", "radius", "width"],
            ["wheel_FR", 0.32, 0.22, {
                "pressurePSI": 0,
                "frictionCoef": 9.5,
                "wheelInertia": 0
            }]
        ],
        "clutch": {
            "clutchTorque": 0
        }
    }"""
    fixed, count, diags = fix_drivetrain_content(jbeam)
    assert count >= 4
    assert '"pressurePSI": 30.0' in fixed or 'pressurePSI": 30.0' in fixed
    assert '"frictionCoef": 1.0' in fixed or 'frictionCoef": 1.0' in fixed
    assert '"wheelInertia": 0.85' in fixed or 'wheelInertia": 0.85' in fixed
    assert '"clutchTorque": 350' in fixed or 'clutchTorque": 350' in fixed


def test_sound_obsolete_paths_modernized() -> None:
    """Test that legacy art/sound/* paths are modernized to official FMOD events."""
    jbeam = """{
        "mainEngine": {
            "soundConfig": "soundConfig",
            "sampleName": "art/sound/engine_v8_cross.wav",
            "soundVolume": 0,
            "soundPitch": -1.0
        }
    }"""
    fixed, count, diags = fix_sound_content(jbeam)
    assert count >= 3
    assert "event:>Engine>default" in fixed
    assert '"soundVolume": 1.0' in fixed or 'soundVolume": 1.0' in fixed
    assert '"soundPitch": 1.0' in fixed or 'soundPitch": 1.0' in fixed


def test_lua_vdata_and_queue_guarded() -> None:
    """Test that unguarded v.data and deprecated obj:queueGameEngineLua are guarded."""
    lua_code = """
local M = {}
function M.init()
    local val = v.data.engineSpeed
    obj:queueGameEngineLua("guihooks.trigger('test')")
    guihooks.trigger('gaugeUpdate', 100)
end
return M
"""
    fixed, count, diags = fix_lua_content(lua_code)
    assert count >= 2
    assert "local v = v or" in fixed
    assert "obj.queueGameEngineLua" in fixed
    assert "guihooks and guihooks.trigger" in fixed


def test_drivetrain_quoted_and_low_psi() -> None:
    """Test drivetrain repairs with quoted numbers and dangerously low tire PSI."""
    jbeam = """
    "differential_R": {
        "gearRatio": "0",
        "diffTorqueSplit": 0.0
    },
    "wheel_RR": {
        "pressurePSI": 2.0,
        "clutchTorque": "0"
    }
    """
    fixed, count, diags = fix_drivetrain_content(jbeam)
    assert count >= 3
    assert '3.73' in fixed
    assert '30.0' in fixed
    assert '350' in fixed


def test_sound_horn_and_context_mapping() -> None:
    """Test context-aware sound modernization for horn and transmission."""
    jbeam = """
    "horn": {
        "hornSound": "art/sound/horn.wav"
    },
    "engine": {
        "soundProfile": "art/sound/v8.wav"
    }
    """
    fixed, count, diags = fix_sound_content(jbeam)
    assert count == 2
    assert "event:>Vehicles>Horn>" in fixed
    assert "event:>Engine>" in fixed


def test_lua_electrics_table_guard() -> None:
    """Test that electrics table is guarded in Lua scripts."""
    lua = """
    local function update(dt)
        local val = electrics.values.headlight
    end
    """
    fixed, count, diags = fix_lua_content(lua)
    assert count > 0
    assert "electrics" in fixed

