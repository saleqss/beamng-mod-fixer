# TEST_READY.md: Comprehensive Test Suite Specification & Verification

## 1. Overview & Verification Status
The hermetic E2E and unit test suite for the **BeamNG.drive Mod Fixer & Graphics Optimizer** has been authored and verified.
The suite adheres strictly to the Opaque-box / Black-box testing methodology (Category-Partition, Boundary Value Analysis, Pairwise, and Workload Testing) as defined in `TEST_INFRA.md`.

- **Total Test Items Collected**: 190 tests
- **Active Tests Status (Milestone 1)**: 100% passing (132 passed, 53 skipped for pending milestones, 5 xfailed)
- **Zero External Dependencies**: 100% synthetic, pure-Python fixtures generated in-memory or in local temporary workspaces.
- **Progressive Testability**: Tests for pending milestones (M2 `zip_processor`, M3 `graphics_optimizer` / `cache_cleaner`, M4 `cli`) gracefully skip via clean decoupling hooks and will automatically activate as subsequent milestones are implemented.

---

## 2. Test Execution Commands

### Standard Test Run
```powershell
python -m pytest tests/
```

### Verbose Execution with Progress
```powershell
python -m pytest -v tests/
```

### Execution by Specific Test Tier
```powershell
# Tier 1: Feature Isolation
python -m pytest -v tests/tier1_feature/

# Tier 2: Boundary & Edge Cases
python -m pytest -v tests/tier2_boundary/

# Tier 3: Combination & Pipeline Tests
python -m pytest -v tests/tier3_combination/

# Tier 4: Workload & CLI End-to-End Scenarios
python -m pytest -v tests/tier4_workload/

# Tier 5: Adversarial & Property Stress Testing
python -m pytest -v tests/tier5_adversarial/
```

---

## 3. Test Tier Breakdown & Test Counts

| Test Tier | Directory | Test Files | Total Tests | Active Status | Description |
|-----------|-----------|:----------:|:-----------:|:-------------:|-------------|
| **Tier 1: Feature Isolation** | `tests/tier1_feature/` | 4 | 35 | 22 Pass / 13 Pending M3 | Tests isolated feature units: JBeam regex replacement, optics diagnostics, graphics optimizer preset application, and shader cache cleaning. |
| **Tier 2: Boundary & Edge Cases** | `tests/tier2_boundary/` | 4 | 22 | 6 Pass / 16 Pending M2 | Validates robustness against corrupt ZIP headers, bad CRCs, password-protected/encrypted archives, Windows locked files (WinError 32), and multi-byte / BOM character encodings (UTF-8, UTF-8-BOM, CP1251, CP1252). |
| **Tier 3: Combination & Integration** | `tests/tier3_combination/` | 3 | 14 | 14 Pending M2 | Tests cross-feature interactions: atomic in-place file replacement (`.tmp` → swap), binary asset passthrough integrity (DDS, DAE, WAV, PC), and batch scanning directory rollups with error resilience. |
| **Tier 4: Workload & E2E Scenarios** | `tests/tier4_workload/` | 2 | 10 | 10 Pending M2/M4 | Real-world application scenarios: CLI subprocess execution (`--help`, `--fix-mods`, `--dry-run`, `--json`, exit codes), and a realistic multi-mod workload suite benchmarking 29 synthetic vehicle mods. |
| **Tier 5: Adversarial Hardening** | `tests/tier5_adversarial/` | 2 | 109 | 104 Pass / 5 Xfail | Property-based fuzzing, white-box branch coverage, and malicious/adversarial input resilience. |
| **Total Suite** | `tests/` | **15 files** | **190 tests** | **Ready & Verified** | **Comprehensive hermetic verification suite.** |

---

## 4. Requirements & Feature Coverage Matrix

| Requirement | Feature Description | Tier 1 Coverage | Tier 2 Coverage | Tier 3 Coverage | Tier 4 Coverage |
|-------------|---------------------|:---------------:|:---------------:|:---------------:|:---------------:|
| **R1.1** | Windows BeamNG directory discovery | — | — | — | `test_cli_e2e.py` |
| **R1.2** | Regex replacement of `lightCastShadows` boolean literals | `test_jbeam_regex.py` (12 tests) | `test_encoding_bom.py` (6 tests) | `test_atomic_rewrite.py` | `test_realistic_mods_suite.py` |
| **R1.3** | JBeam optics diagnostics & normalization | `test_optics_diagnostics.py` (10 tests) | — | — | `test_realistic_mods_suite.py` |
| **R1.4** | In-place streaming ZIP archive modification | — | `test_corrupt_zip.py` (6 tests) | `test_atomic_rewrite.py` (5 tests) | `test_realistic_mods_suite.py` |
| **R1.5** | Binary asset integrity passthrough (DDS, DAE, WAV, PC) | — | — | `test_binary_passthrough.py` (5 tests) | `test_realistic_mods_suite.py` |
| **R2.1** | Graphics settings detection & automatic backup (`.backup_YYYYMMDD_HHMMSS`) | `test_graphics_optimizer.py` (7 tests) | — | — | `test_cli_e2e.py` |
| **R2.2** | Safe graphics optimization preset deployment | `test_graphics_optimizer.py` (7 tests) | — | — | `test_cli_e2e.py` |
| **R2.3** | Safe shader cache cleaning (temp purge, preserving user presets) | `test_cache_cleaner.py` (6 tests) | — | — | `test_cli_e2e.py` |
| **R3.1** | Graceful error handling (locked files, corrupt zips, encrypted zips) | — | `test_corrupt_zip.py`<br>`test_encrypted_zip.py`<br>`test_file_locks.py` | `test_batch_scanner.py` (4 tests) | `test_cli_e2e.py` |
| **R3.2** | Dry-run mode (`--dry-run`) with zero disk side-effects | — | — | `test_batch_scanner.py` | `test_cli_e2e.py` |
| **R3.3** | Machine-readable JSON summary report (`--json`) | — | — | — | `test_cli_e2e.py` |
| **R4.1** | Rich CLI entrypoint & interactive commands | — | — | — | `test_cli_e2e.py` (9 tests) |

---

## 5. Synthetic Fixture Architecture (`tests/fixtures/factory.py`)

All tests run completely hermetically without requiring BeamNG.drive or proprietary game assets.
The fixture infrastructure in `tests/fixtures/factory.py` provides 51 reusable exports:

1. **JBeam Syntax Generators & Variations**:
   - `SAMPLE_JBEAM_COMPACT`, `SAMPLE_JBEAM_SPACED`, `SAMPLE_JBEAM_QUOTED_BOOL`
   - `SAMPLE_JBEAM_ALREADY_FIXED`, `SAMPLE_JBEAM_OUTDATED_OPTICS`, `SAMPLE_JBEAM_WITH_COMMENTS`
   - Multi-encoding fixtures: `SAMPLE_JBEAM_CP1251`, `SAMPLE_JBEAM_CP1252`, `SAMPLE_JBEAM_UTF8_BOM`
2. **Binary Asset Generators**:
   - `create_dummy_dds(width, height)`: Valid DirectX DDS header + DXT1 magic bytes.
   - `create_dummy_dae(mesh_name)`: Valid XML COLLADA 1.4.1 schema mesh.
   - `create_dummy_wav(duration_ms)`: Valid RIFF/WAVE PCM audio header and samples.
   - `create_dummy_pc(part_config)`: JSON part configuration structure.
3. **Mod Archive & ZIP Builders**:
   - `ModArchiveBuilder`: Fluent builder to assemble complex zip archives containing JBeam files, nested directories (`vehicles/`, `levels/`), and binary assets.
   - `create_corrupt_zip_truncated()`: Truncated byte stream missing Central Directory.
   - `create_corrupt_zip_bad_crc()`: Synthesized ZIP with intentionally mismatched CRC-32 checksums.
   - `create_encrypted_zip()`: Password-protected ZIP archive (PKWARE traditional encryption).
4. **System Directory Synthesizers**:
   - `create_mock_settings_dir()`: Realistic `settings/` tree containing `settings.json`, `game-settings.ini`, and custom input bindings.
   - `create_mock_cache_dir()`: Realistic `temp/` and shader cache hierarchies (`shaders/`, `materials/`, `vehicles/`).
   - `create_mock_beamng_structure()`: Complete BeamNG user directory simulation with `mods/`, `settings/`, and `temp/` trees.

---

## 6. Pytest Shared Fixtures (`tests/conftest.py`)

The test suite exports 9 central pytest fixtures accessible to all tests:
- `temp_beamng_dir`: Fresh temporary BeamNG root directory with mock structure.
- `sample_mod_zip`: Mod ZIP containing outdated `lightCastShadows: true` JBeam files needing repair.
- `clean_mod_zip`: Already fixed mod ZIP containing `lightCastShadows: 1`.
- `corrupt_mod_zip`: Corrupt / truncated archive for fault-tolerance testing.
- `bad_crc_mod_zip`: Archive with invalid CRC-32 checksums.
- `encrypted_mod_zip`: Password-encrypted ZIP archive.
- `settings_dir`: Mock BeamNG settings folder with sample `settings.json`.
- `cache_dir`: Mock shader cache folder populated with temporary shader files.
- `mixed_mods_dir`: Realistic mod folder containing valid, clean, corrupted, encrypted, and locked mod archives.

---

## 7. Discovered Implementation Behaviors & Escalations
1. **Character Encoding Fallback Order in `jbeam_fixer.py`**:
   - In `src/beamng_mod_fixer/core/jbeam_fixer.py`, `decode_jbeam_bytes()` attempts `cp1251` prior to `cp1252`. Because `cp1251` maps every single byte in the `0x80-0xFF` range without raising `UnicodeDecodeError`, Western European accented characters (CP1252) are decoded into Cyrillic equivalents rather than falling through to CP1252.
   - *Impact*: Safe (no crashes, `lightCastShadows` is still successfully fixed), but characters in mod names or comments may be mojibaked.
   - *Recommendation*: Prioritize CP1252 before CP1251 or use language heuristics / chardet if accurate non-English comment preservation is required.

---

## 8. Verification & Handoff
All tests in `tests/` compile and pass without unexpected errors:
```powershell
python -m pytest tests/
# Output: 132 passed, 53 skipped, 5 xfailed in 2.47s (Exit code 0)
```
The test suite is fully decoupled, hermetic, and ready for integration across all remaining milestones.
