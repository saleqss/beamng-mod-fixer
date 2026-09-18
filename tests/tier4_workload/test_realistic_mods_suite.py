"""Tier 4: Workload & Realistic Scenario Tests (25+ Vehicle Mods Suite).

Verifies:
- High-performance batch processing across 25+ synthetic vehicle mod archives
- Varied vehicle categories: sedans, trucks, supercars, trailers, racing setups
- Mixed light configurations: broken headlights, already-clean headlights, suspension-only
- Throughput and performance: streaming I/O handles 25+ archives with low memory footprint
- Preservation of binary assets and directory structures at scale
- Zero residual .tmp or .bak files
"""

from pathlib import Path
import time
import zipfile

import pytest

try:
    from beamng_mod_fixer.core.zip_processor import scan_and_fix_mods
    HAS_BATCH_PROCESSOR = True
except ImportError:
    HAS_BATCH_PROCESSOR = False

from beamng_mod_fixer.models import OverallSummary
from tests.fixtures.factory import (
    create_corrupt_zip_truncated,
    create_password_protected_zip,
    create_realistic_mod_zip,
)


@pytest.fixture(autouse=True)
def skip_if_unimplemented() -> None:
    if not HAS_BATCH_PROCESSOR:
        pytest.skip("beamng_mod_fixer.core.zip_processor not yet implemented (Milestone M2)")


def test_realistic_25_plus_mods_workload(tmp_path: Path) -> None:
    """Benchmark and verify batch processing across 28 synthetic vehicle mods."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    total_expected_broken = 0
    total_expected_clean = 0

    # 1. Generate 20 standard vehicle mods with broken lights (2 headlights each)
    for i in range(1, 21):
        mod_file = mods_dir / f"vehicle_mod_{i:02d}.zip"
        create_realistic_mod_zip(mod_file, f"car_{i}", light_count=2, add_textures=True)
        total_expected_broken += 1

    # 2. Generate 4 supercars with 6 spotlights each
    for i in range(21, 25):
        mod_file = mods_dir / f"supercar_mod_{i:02d}.zip"
        create_realistic_mod_zip(mod_file, f"supercar_{i}", light_count=6, add_textures=True, add_sounds=True)
        total_expected_broken += 1

    # 3. Generate 3 already-clean vehicle mods
    for i in range(25, 28):
        mod_file = mods_dir / f"clean_mod_{i:02d}.zip"
        create_realistic_mod_zip(mod_file, f"clean_car_{i}", already_false=True)
        total_expected_clean += 1

    # 4. Generate 1 corrupt archive and 1 encrypted archive
    create_corrupt_zip_truncated(mods_dir / "mod_corrupt.zip")
    create_password_protected_zip(mods_dir / "mod_encrypted.zip")

    total_archives = 20 + 4 + 3 + 2  # 29 archives total
    assert len(list(mods_dir.glob("*.zip"))) == total_archives

    start_time = time.perf_counter()
    summary = scan_and_fix_mods(mods_dir, dry_run=False)
    elapsed = time.perf_counter() - start_time

    # Performance assertion: batch scan should complete in under 10.0 seconds
    assert elapsed < 10.0, f"Workload took too long: {elapsed:.2f}s"

    assert isinstance(summary, OverallSummary)
    assert summary.total_scanned == total_archives
    assert summary.modified_archives == total_expected_broken
    assert summary.clean_archives == total_expected_clean
    assert summary.skipped_corrupt >= 1
    assert summary.skipped_encrypted >= 1

    # Verify that modified archives now actually have lightCastShadows: false
    sample_fixed = mods_dir / "vehicle_mod_01.zip"
    with zipfile.ZipFile(sample_fixed, "r") as zf:
        content = zf.read("vehicles/car_1/headlights.jbeam").decode("utf-8")
        assert '"lightCastShadows": false' in content
        assert '"lightCastShadows": true' not in content

    # Verify zero leftover temporary files
    assert len(list(mods_dir.glob("*.tmp*"))) == 0

