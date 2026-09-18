"""Synthetic Fixture Factory for BeamNG Mod Fixer & Graphics Optimizer.

Provides hermetic, pure-Python synthetic generation of:
- Realistic BeamNG vehicle mod zip archives (vehicles/<model>/... .jbeam, textures, models, sounds)
- Corrupted zip archives (0-byte, truncated header, bad CRC, bad central directory, non-zip data)
- Password-protected / encrypted zip archives
- JBeam files with various lightCastShadows representations (formatting, comments, booleans)
- Optics diagnostics samples (flareName, cookieName, inverted angles, malformed rows)
- Synthetic settings.json and game-settings.json structures
- Synthetic temp/ cache structures (shaders, vehicles, .d3dcsx, .cani, .db)
- Full BeamNG user directory topologies
"""

import codecs
import io
import json
import os
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ==============================================================================
# 1. JBeam Sample Templates
# ==============================================================================

SAMPLE_JBEAM_STANDARD_HEADLIGHT = """{
    "pickup_headlight_L": {
        "information": {
            "authors": "BeamNG Modder Team",
            "name": "Left Headlight",
            "value": 120
        },
        "slotType": "pickup_headlight_L",
        "slots": [
            ["type", "default", "description"],
            ["pickup_headlight_L_cover", "", "Headlight Cover"]
        ],
        "props": [
            ["type", "default", "description"],
            ["headlight_L", "b1", "b2", "b3", {"lightRange": 50, "lightFov": 65, "lightCastShadows": true, "flareName": "vehicleHeadLightFlare"}]
        ],
        "spotlights": [
            ["type", "start", "stop", "step"],
            ["headlight_L", "b1", "b2", "b3", {"lightRange": 50, "lightFov": 65, "lightCastShadows": true, "flareName": "vehicleHeadLightFlare"}],
            ["highbeam_L", "b1", "b4", "b5", {"lightRange": 85, "lightFov": 45, "lightCastShadows": true, "flareName": "vehicleHighBeamFlare"}],
            ["fog_L", "b2", "b6", "b7", {"lightRange": 30, "lightFov": 90, "lightCastShadows": false, "flareName": "vehicleFogLightFlare"}]
        ]
    }
}
"""

SAMPLE_JBEAM_UNQUOTED = """
sedan_headlight_R: {
    information: {
        authors: "Community Author",
        name: "Right Headlight"
    },
    slotType: "sedan_headlight_R",
    spotlights: [
        ["type", "start", "stop", "step"],
        ["headlight_R", "b10", "b11", "b12", {lightRange: 50, lightFov: 65, lightCastShadows: true, flareName: "vehicleHeadLightFlare"}],
    ],
}
"""

SAMPLE_JBEAM_SINGLE_QUOTES = """{
    'sports_car_lights': {
        'information': {'name': 'Projector Headlights'},
        'spotlights': [
            ['main', 'n1', 'n2', 'n3', {'lightCastShadows': true, 'flareName': 'vehicleHeadLightFlare'}]
        ]
    }
}
"""

SAMPLE_JBEAM_SPACING_VARIANTS = """{
    "spacing_test": {
        "spotlights": [
            ["l1", "a", "b", "c", {"lightCastShadows":true}],
            ["l2", "a", "b", "c", {"lightCastShadows" : true}],
            ["l3", "a", "b", "c", {\t"lightCastShadows"\t:\ttrue\t}],
            ["l4", "a", "b", "c", {"lightCastShadows"  :   true  }]
        ]
    }
}
"""

SAMPLE_JBEAM_BOOLEAN_VARIANTS = """{
    "bool_variants": {
        "spotlights": [
            ["v1", "a", "b", "c", {"lightCastShadows": True}],
            ["v2", "a", "b", "c", {"lightCastShadows": TRUE}],
            ["v3", "a", "b", "c", {"lightCastShadows": 1}],
            ["v4", "a", "b", "c", {"lightCastShadows": "true"}]
        ]
    }
}
"""

SAMPLE_JBEAM_WITH_COMMENTS = """{
    "commented_mod": {
        // Top level comment explaining headlight setup
        "spotlights": [
            // Headlight row with trailing comment
            ["headlight_L", "b1", "b2", "b3", {
                "lightRange": 60,
                /* inline comment before key */ "lightCastShadows": /* inline before value */ true, // comment after value
                "flareName": "vehicleHeadLightFlare"
            }]
        ]
    }
}
"""

SAMPLE_JBEAM_ALREADY_FALSE = """{
    "clean_mod": {
        "spotlights": [
            ["headlight_L", "b1", "b2", "b3", {"lightRange": 50, "lightCastShadows": false, "flareName": "vehicleHeadLightFlare"}],
            ["headlight_R", "b4", "b5", "b6", {"lightRange": 50, "lightCastShadows": false, "flareName": "vehicleHeadLightFlare"}]
        ]
    }
}
"""

SAMPLE_JBEAM_NO_LIGHTS = """{
    "racing_suspension": {
        "information": {
            "name": "Independent Double Wishbone",
            "authors": "Suspension Tuner"
        },
        "nodes": [
            ["id", "posX", "posY", "posZ"],
            ["susp1", 0.65, -1.2, 0.35],
            ["susp2", -0.65, -1.2, 0.35]
        ],
        "beams": [
            ["id1:", "id2:"],
            ["susp1", "susp2", {"beamSpring": 85000, "beamDamp": 4500}]
        ]
    }
}
"""

SAMPLE_JBEAM_MULTIPLE_LIGHTS = """{
    "supercar_fascia": {
        "spotlights": [
            ["low_L", "n1", "n2", "n3", {"lightRange": 45, "lightCastShadows": true, "flareName": "vehicleHeadLightFlare"}],
            ["low_R", "n4", "n5", "n6", {"lightRange": 45, "lightCastShadows": true, "flareName": "vehicleHeadLightFlare"}],
            ["high_L", "n1", "n7", "n8", {"lightRange": 95, "lightCastShadows": true, "flareName": "vehicleHighBeamFlare"}],
            ["high_R", "n4", "n9", "n10", {"lightRange": 95, "lightCastShadows": true, "flareName": "vehicleHighBeamFlare"}],
            ["fog_L", "n11", "n12", "n13", {"lightRange": 25, "lightCastShadows": true, "flareName": "vehicleFogLightFlare"}],
            ["fog_R", "n14", "n15", "n16", {"lightRange": 25, "lightCastShadows": true, "flareName": "vehicleFogLightFlare"}]
        ]
    }
}
"""

SAMPLE_JBEAM_OPTICS_ISSUES = """{
    "optics_trouble": {
        "spotlights": [
            ["hl_invalid_flare", "a", "b", "c", {
                "lightInnerAngle": 40,
                "lightOuterAngle": 60,
                "flareName": "none",
                "cookieName": "art/shapes/lights/old_cookie.dds",
                "lightCastShadows": true
            }],
            ["hl_inverted_angles", "d", "e", "f", {
                "lightInnerAngle": 75,
                "lightOuterAngle": 45,
                "flareName": "null",
                "cookieName": "vehicles/optics_trouble/missing_lamp.png",
                "lightCastShadows": true
            }],
            ["hl_malformed_row", "g"]
        ]
    }
}
"""

# ==============================================================================
# 2. Binary Asset Fixtures
# ==============================================================================

def make_dummy_dds(width: int = 16, height: int = 16) -> bytes:
    """Generates a valid 128-byte DirectDraw Surface header + raw test pixel payload."""
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)          # dwSize
    struct.pack_into("<I", header, 8, 0x1007)       # dwFlags (CAPS|HEIGHT|WIDTH|PIXELFORMAT)
    struct.pack_into("<I", header, 12, height)      # dwHeight
    struct.pack_into("<I", header, 16, width)       # dwWidth
    struct.pack_into("<I", header, 20, width * 4)   # dwPitchOrLinearSize
    struct.pack_into("<I", header, 76, 32)          # ddspf.dwSize
    struct.pack_into("<I", header, 80, 0x41)        # ddspf.dwFlags (RGBA)
    struct.pack_into("<I", header, 88, 32)          # ddspf.dwRGBBitCount
    struct.pack_into("<I", header, 92, 0x00FF0000)  # RMask
    struct.pack_into("<I", header, 96, 0x0000FF00)  # GMask
    struct.pack_into("<I", header, 100, 0x000000FF) # BMask
    struct.pack_into("<I", header, 104, 0xFF000000) # AMask
    pixels = b"\xFF\x00\x00\xFF" * (width * height)
    return bytes(header) + pixels

DUMMY_DDS_BYTES = make_dummy_dds(16, 16)

DUMMY_DAE_BYTES = b"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><created>2026-09-18T12:00:00Z</created></asset>
  <library_geometries><geometry id="body_mesh"><mesh></mesh></geometry></library_geometries>
</COLLADA>
"""

def make_dummy_wav(duration_ms: int = 50) -> bytes:
    """Generates a valid 44-byte RIFF WAVE header + PCM silence."""
    sample_rate = 22050
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    data_size = num_samples * 2
    file_size = 36 + data_size
    header = bytearray(44)
    header[0:4] = b"RIFF"
    struct.pack_into("<I", header, 4, file_size)
    header[8:12] = b"WAVE"
    header[12:16] = b"fmt "
    struct.pack_into("<I", header, 16, 16)
    struct.pack_into("<H", header, 20, 1)
    struct.pack_into("<H", header, 22, 1)
    struct.pack_into("<I", header, 24, sample_rate)
    struct.pack_into("<I", header, 28, sample_rate * 2)
    struct.pack_into("<H", header, 32, 2)
    struct.pack_into("<H", header, 34, 16)
    header[36:40] = b"data"
    struct.pack_into("<I", header, 40, data_size)
    return bytes(header) + (b"\x00" * data_size)

DUMMY_WAV_BYTES = make_dummy_wav(50)

DUMMY_PC_CONTENT = """{
  "format": 2,
  "mainPartName": "test_car",
  "parts": {
    "test_car_body": "test_car_body",
    "test_car_headlight_L": "test_car_headlight_L",
    "test_car_headlight_R": "test_car_headlight_R"
  }
}
"""

# ==============================================================================
# 3. ModArchiveBuilder
# ==============================================================================

class ModArchiveBuilder:
    """Fluent builder for generating synthetic BeamNG mod archives."""

    def __init__(self, archive_name: str = "custom_mod.zip", vehicle_name: str = "custom_car"):
        self.archive_name = archive_name
        self.vehicle_name = vehicle_name
        self.entries: Dict[str, bytes] = {}

    def add_file(self, internal_path: str, data: Union[bytes, str], encoding: str = "utf-8") -> "ModArchiveBuilder":
        if isinstance(data, str):
            self.entries[internal_path] = data.encode(encoding)
        else:
            self.entries[internal_path] = data
        return self

    def add_jbeam(
        self,
        relative_path: str,
        content: str,
        encoding: str = "utf-8",
        with_bom: bool = False
    ) -> "ModArchiveBuilder":
        full_path = f"vehicles/{self.vehicle_name}/{relative_path}"
        if with_bom or encoding.lower().replace("-", "") in ("utf8sig", "utf8bom"):
            encoded = codecs.BOM_UTF8 + content.encode("utf-8")
        else:
            encoded = content.encode(encoding)
        self.entries[full_path] = encoded
        return self

    def add_binary(self, relative_path: str, data: bytes) -> "ModArchiveBuilder":
        full_path = f"vehicles/{self.vehicle_name}/{relative_path}"
        self.entries[full_path] = data
        return self

    def add_default_assets(self) -> "ModArchiveBuilder":
        """Adds standard textures, 3D model, sound, and .pc config."""
        self.add_binary("textures/body_color.dds", DUMMY_DDS_BYTES)
        self.add_binary("textures/glass_spec.dds", DUMMY_DDS_BYTES)
        self.add_binary("models/vehicle_mesh.dae", DUMMY_DAE_BYTES)
        self.add_binary("sounds/horn.wav", DUMMY_WAV_BYTES)
        self.add_file(f"vehicles/{self.vehicle_name}/default.pc", DUMMY_PC_CONTENT)
        return self

    def build(self, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        archive_path = target_dir / self.archive_name
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for internal_path, data in sorted(self.entries.items()):
                zf.writestr(internal_path, data)
        return archive_path


# ==============================================================================
# 4. Realistic and Edge-Case Mod Zip Generators
# ==============================================================================

def create_realistic_mod_zip(
    target_path: Path,
    vehicle_name: str = "test_vehicle",
    light_count: int = 2,
    already_false: bool = False,
    add_textures: bool = True,
    add_sounds: bool = True,
    encoding: str = "utf-8",
    with_bom: bool = False
) -> Path:
    """Generates a realistic BeamNG mod zip archive with headlights and assets."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    builder = ModArchiveBuilder(target_path.name, vehicle_name)

    if already_false:
        jbeam_code = SAMPLE_JBEAM_ALREADY_FALSE
    elif light_count >= 4:
        jbeam_code = SAMPLE_JBEAM_MULTIPLE_LIGHTS
    else:
        jbeam_code = SAMPLE_JBEAM_STANDARD_HEADLIGHT

    builder.add_jbeam("headlights.jbeam", jbeam_code, encoding=encoding, with_bom=with_bom)
    builder.add_jbeam("suspension.jbeam", SAMPLE_JBEAM_NO_LIGHTS, encoding="utf-8")

    if add_textures:
        builder.add_binary("textures/skin_paint.dds", DUMMY_DDS_BYTES)
        builder.add_binary("models/body.dae", DUMMY_DAE_BYTES)
    if add_sounds:
        builder.add_binary("sounds/engine_idle.wav", DUMMY_WAV_BYTES)

    return builder.build(target_path.parent)


def create_empty_zip(target_path: Path) -> Path:
    """Creates a 22-byte valid empty zip archive containing zero entries."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target_path, "w") as zf:
        pass
    return target_path


def create_corrupt_zip_zero_byte(target_path: Path) -> Path:
    """Creates an empty 0-byte file with a .zip extension."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(b"")
    return target_path


def create_corrupt_zip_truncated(target_path: Path) -> Path:
    """Creates a zip archive truncated halfway through local file entry header."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"PK\x03\x04\x14\x00\x00\x00\x08\x00\x50\x7a\x42\x59truncated_data_without_central_directory"
    target_path.write_bytes(payload)
    return target_path


def create_corrupt_zip_bad_crc(target_path: Path) -> Path:
    """Creates a zip archive with intentionally corrupted CRC32 checksum."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vehicles/broken/headlights.jbeam", b"lightCastShadows: true")
    raw = bytearray(buf.getvalue())
    if len(raw) > 20:
        raw[14] ^= 0xAA
        raw[15] ^= 0x55
    target_path.write_bytes(raw)
    return target_path


def create_corrupt_zip_bad_central_dir(target_path: Path) -> Path:
    """Creates a zip archive with damaged end-of-central-directory (EOCD)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.jbeam", b"content")
    raw = bytearray(buf.getvalue())
    eocd_idx = raw.find(b"PK\x05\x06")
    if eocd_idx != -1:
        raw[eocd_idx + 2] = 0xFF
        raw[eocd_idx + 3] = 0xFF
    target_path.write_bytes(raw)
    return target_path


def create_corrupt_zip_non_zip(target_path: Path) -> Path:
    """Creates a text file masquerading as a .zip file."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("This is an ordinary text file, not a PKZIP archive!\n", encoding="utf-8")
    return target_path


def create_password_protected_zip(target_path: Path, password: str = "modpass123") -> Path:
    """Creates a zip archive marked as password-protected / encrypted.
    
    Sets the general purpose bit flag 0 (0x0001) in both the local file header
    and the central directory header, triggering standard ZIP encryption detection.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vehicles/secure_car/lights.jbeam", b"lightCastShadows: true\npassword protected")
    raw = bytearray(buf.getvalue())

    if raw.startswith(b"PK\x03\x04"):
        raw[6] |= 0x01

    cd_pos = raw.find(b"PK\x01\x02")
    if cd_pos != -1:
        raw[cd_pos + 8] |= 0x01

    target_path.write_bytes(raw)
    return target_path


# ==============================================================================
# 5. Settings and Cache Structure Generators
# ==============================================================================

DEFAULT_SETTINGS_JSON = {
    "GraphicDynReflection": True,
    "GraphicDynReflectionFacesPerupdate": 6,
    "GraphicDynReflectionTexsize": 1024,
    "GraphicDynReflectionDistance": 300,
    "GraphicDynReflectionDetail": 1.0,
    "GraphicShadowQuality": "Ultra",
    "GraphicDisableShadows": "0",
    "GraphicLightingQuality": "High",
    "GraphicMaxDecalCount": 10000,
    "GraphicAntialiasType": "SMAA",
    "GraphicAntialias": 4,
    "AudioMasterVol": 0.85,
    "WindowMode": "Borderless",
    "GraphicResolution": "2560 1440"
}

DEFAULT_GAME_SETTINGS_JSON = {
    "$pref": {
        "BeamNGVehicle": {
            "dynamicReflection": {
                "enabled": True,
                "facesPerUpdate": 6,
                "textureSize": 1024,
                "detail": 1.0,
                "distance": 300
            },
            "dynamicMirrors": {
                "enabled": True,
                "textureSize": 1024,
                "detail": 1.0,
                "distance": 300
            }
        },
        "Shadows": {
            "textureScalar": 3,
            "filterMode": 2,
            "disable": 0
        },
        "TS": {
            "maxDecalCount": 10000,
            "detailAdjust": 3,
            "skipRenderDLs": 0
        }
    }
}


def create_synthetic_settings_files(
    settings_dir: Path,
    custom_settings: Optional[Dict[str, Any]] = None,
    custom_game_settings: Optional[Dict[str, Any]] = None
) -> Tuple[Path, Path]:
    """Generates synthetic settings.json and game-settings.json files."""
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_p = settings_dir / "settings.json"
    game_settings_p = settings_dir / "game-settings.json"

    s_data = dict(DEFAULT_SETTINGS_JSON)
    if custom_settings:
        s_data.update(custom_settings)
    settings_p.write_text(json.dumps(s_data, indent=4), encoding="utf-8")

    gs_data = dict(DEFAULT_GAME_SETTINGS_JSON)
    if custom_game_settings:
        gs_data.update(custom_game_settings)
    game_settings_p.write_text(json.dumps(gs_data, indent=4), encoding="utf-8")

    return settings_p, game_settings_p


def create_synthetic_cache_structure(
    temp_dir: Path,
    file_count: int = 10
) -> Dict[str, List[Path]]:
    """Creates a realistic temp/ cache directory structure with compiled shaders and caches."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    shader_d3d11 = temp_dir / "shaders" / "d3d11"
    shader_d3d12 = temp_dir / "shaders" / "d3d12"
    vehicles_dir = temp_dir / "vehicles"
    art_dir = temp_dir / "art"

    for d in (shader_d3d11, shader_d3d12, vehicles_dir, art_dir):
        d.mkdir(parents=True, exist_ok=True)

    created_shaders: List[Path] = []
    created_vehicles: List[Path] = []
    created_others: List[Path] = []

    for i in range(1, max(3, file_count // 2)):
        p1 = shader_d3d11 / f"pbr_material_pass_{i}.d3dcsx"
        p1.write_bytes(b"\x00\x01\x02\x03" * 256)
        created_shaders.append(p1)

        p2 = shader_d3d12 / f"pipeline_state_{i}.d3dcsx"
        p2.write_bytes(b"\x04\x05\x06\x07" * 256)
        created_shaders.append(p2)

    db_path = temp_dir / "shaders" / "shaders.db"
    db_path.write_bytes(b"SQLite format 3\x00" + b"\x00" * 1000)
    created_shaders.append(db_path)

    for i in range(1, max(2, file_count // 3)):
        cani = vehicles_dir / f"vehicle_anim_{i}.cani"
        cani.write_bytes(b"CANI" + b"\x00" * 512)
        created_vehicles.append(cani)

    bin_file = temp_dir / "ui-cache-rt-sfc.bin"
    bin_file.write_bytes(b"UICACHE" + b"\x00" * 128)
    created_others.append(bin_file)

    return {
        "shaders": created_shaders,
        "vehicles": created_vehicles,
        "others": created_others,
        "all": created_shaders + created_vehicles + created_others,
    }


def create_synthetic_beamng_user_dir(
    root_dir: Path,
    mod_count: int = 5,
    include_corrupt: bool = False,
    include_locked: bool = False,
    include_encrypted: bool = False
) -> Dict[str, Any]:
    """Generates a complete synthetic BeamNG user folder hierarchy."""
    mods_dir = root_dir / "mods"
    settings_dir = root_dir / "settings"
    temp_dir = root_dir / "temp"

    mods_dir.mkdir(parents=True, exist_ok=True)
    settings_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    settings_p, game_settings_p = create_synthetic_settings_files(settings_dir)
    cache_info = create_synthetic_cache_structure(temp_dir)

    mod_paths: List[Path] = []
    for i in range(1, mod_count + 1):
        p = mods_dir / f"mod_car_{i}.zip"
        create_realistic_mod_zip(p, f"car_{i}", light_count=2, add_textures=True)
        mod_paths.append(p)

    corrupt_paths: List[Path] = []
    if include_corrupt:
        p_trunc = mods_dir / "mod_corrupt_truncated.zip"
        create_corrupt_zip_truncated(p_trunc)
        corrupt_paths.append(p_trunc)

        p_crc = mods_dir / "mod_corrupt_crc.zip"
        create_corrupt_zip_bad_crc(p_crc)
        corrupt_paths.append(p_crc)

    encrypted_paths: List[Path] = []
    if include_encrypted:
        p_enc = mods_dir / "mod_encrypted.zip"
        create_password_protected_zip(p_enc)
        encrypted_paths.append(p_enc)

    return {
        "root": root_dir,
        "mods_dir": mods_dir,
        "settings_dir": settings_dir,
        "temp_dir": temp_dir,
        "settings_file": settings_p,
        "game_settings_file": game_settings_p,
        "mod_paths": mod_paths,
        "corrupt_paths": corrupt_paths,
        "encrypted_paths": encrypted_paths,
        "cache_info": cache_info,
    }

