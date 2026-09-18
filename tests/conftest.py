"""Reusable pytest fixtures for BeamNG Mod Fixer & Graphics Optimizer test suite."""

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure src/ is in sys.path for test execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tests.fixtures.factory import (
    create_corrupt_zip_bad_crc,
    create_corrupt_zip_truncated,
    create_corrupt_zip_zero_byte,
    create_password_protected_zip,
    create_realistic_mod_zip,
    create_synthetic_beamng_user_dir,
    create_synthetic_cache_structure,
    create_synthetic_settings_files,
)


@pytest.fixture
def temp_beamng_dir(tmp_path: Path) -> Dict[str, Any]:
    """Provides a complete synthetic BeamNG user directory hierarchy."""
    user_dir = tmp_path / "beamng_user"
    return create_synthetic_beamng_user_dir(user_dir, mod_count=5)


@pytest.fixture
def sample_mod_zip(tmp_path: Path) -> Path:
    """Provides a realistic BeamNG mod zip archive with headlights needing fix."""
    mod_path = tmp_path / "mod_headlight_test.zip"
    return create_realistic_mod_zip(mod_path, "headlight_test_car", light_count=2)


@pytest.fixture
def clean_mod_zip(tmp_path: Path) -> Path:
    """Provides a realistic BeamNG mod zip archive with already-false headlights."""
    mod_path = tmp_path / "mod_clean.zip"
    return create_realistic_mod_zip(mod_path, "clean_car", light_count=2, already_false=True)


@pytest.fixture
def corrupt_mod_zip(tmp_path: Path) -> Path:
    """Provides a truncated corrupt zip archive."""
    mod_path = tmp_path / "mod_corrupt.zip"
    return create_corrupt_zip_truncated(mod_path)


@pytest.fixture
def bad_crc_mod_zip(tmp_path: Path) -> Path:
    """Provides a zip archive with invalid CRC-32 checksum."""
    mod_path = tmp_path / "mod_bad_crc.zip"
    return create_corrupt_zip_bad_crc(mod_path)


@pytest.fixture
def encrypted_mod_zip(tmp_path: Path) -> Path:
    """Provides an encrypted / password-protected zip archive."""
    mod_path = tmp_path / "mod_encrypted.zip"
    return create_password_protected_zip(mod_path)


@pytest.fixture
def settings_dir(tmp_path: Path) -> Path:
    """Provides a settings directory with settings.json and game-settings.json."""
    s_dir = tmp_path / "settings"
    create_synthetic_settings_files(s_dir)
    return s_dir


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Provides a temporary cache directory with shaders and vehicle caches."""
    t_dir = tmp_path / "temp"
    create_synthetic_cache_structure(t_dir)
    return t_dir


@pytest.fixture
def mixed_mods_dir(tmp_path: Path) -> Path:
    """Provides a mods directory containing a mixture of valid, clean, corrupt, and non-zip files."""
    m_dir = tmp_path / "mods"
    m_dir.mkdir(parents=True, exist_ok=True)

    # 3 fixable mods
    create_realistic_mod_zip(m_dir / "mod_broken_1.zip", "car1", light_count=2)
    create_realistic_mod_zip(m_dir / "mod_broken_2.zip", "car2", light_count=4)
    create_realistic_mod_zip(m_dir / "mod_broken_3.zip", "car3", light_count=2)

    # 2 already clean mods
    create_realistic_mod_zip(m_dir / "mod_clean_1.zip", "clean1", already_false=True)
    create_realistic_mod_zip(m_dir / "mod_clean_2.zip", "clean2", already_false=True)

    # 1 corrupt mod
    create_corrupt_zip_truncated(m_dir / "mod_corrupt.zip")

    # 1 zero-byte mod
    create_corrupt_zip_zero_byte(m_dir / "mod_empty.zip")

    # 1 encrypted mod
    create_password_protected_zip(m_dir / "mod_encrypted.zip")

    # 1 non-zip file
    (m_dir / "readme.txt").write_text("Not a mod archive", encoding="utf-8")

    return m_dir

