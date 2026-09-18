# Project: BeamNG.drive Mod Fixer & Graphics Optimizer

## Architecture
The application is structured as a high-performance, modular Python package `beamng_mod_fixer` designed for CLI execution and library usage on Windows (with cross-platform CI support on Ubuntu/Linux).

```
User / CLI Interface (`beamng_mod_fixer.cli`)
  │
  ├── Mod Scanner & In-Place Rewriter (`beamng_mod_fixer.core.zip_processor`)
  │     ├── Archive Discovery (`beamng_mod_fixer.core.discovery`)
  │     ├── In-Place Atomic Streamer (`beamng_mod_fixer.core.file_utils`)
  │     └── JBeam Regex & Optics Engine (`beamng_mod_fixer.core.jbeam_fixer`)
  │
  ├── Graphics Optimizer & Preset Deployer (`beamng_mod_fixer.core.graphics_optimizer`)
  │     └── Settings File Backup & Atomic Modifier
  │
  ├── Safe Shader Cache Cleaner (`beamng_mod_fixer.core.cache_cleaner`)
  │     └── Verified `temp/shaders` and `temp/vehicles` Purging Guard
  │
  └── Rich UX & Metrics Reporter (`beamng_mod_fixer.ui.reporter`)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | BeamNG Windows Directory Discovery | Auto-detect `%LOCALAPPDATA%/BeamNG/BeamNG.drive/current` and versioned paths; interactive confirmation or `--mods-dir` CLI flag | M4 | R1 |
| 2 | JBeam Headlight Regex Replacement Engine | Robust regex replacing `"lightCastShadows": true` with `false` across all `.jbeam` files in vehicle archives, preserving format, quotes, comments, indentation | M1 | R1 |
| 3 | JBeam Optics Diagnostics & Normalization | Identify and repair corrupted spotlights blocks, invalid flareName ("none") and missing cookie textures | M1 | R1 |
| 4 | High-Performance Streaming ZIP In-Place Rewriter | Stream unmodified binary entries in 256KB chunks, re-pack modified `.jbeam` entries, preserve `ZipInfo` (time, mode, compression, crc), atomic replace | M2 | R1 |
| 5 | Fault-Tolerant Archive Handling | Graceful skip and error logging for locked archives (`WinError 32`), corrupt archives (`BadZipFile`), and password-protected archives | M2 | R1, R3 |
| 6 | Settings Backup Engine | Automatic backup of `settings.json` and `game-settings.json` to `.bak` timestamped copies in `settings/` | M3 | R2 |
| 7 | Graphics Optimization Preset Deployer | Apply balanced presets: `GraphicDynReflectionFacesPerupdate: 2`, `GraphicDynReflectionTexsize: 512`, balanced shadows, mirrors, decals, particles | M3 | R2 |
| 8 | Safe Shader Cache Cleaner | Purge `temp/shaders/` and `temp/vehicles/` without deleting user configs, mods, or controls | M3 | R2 |
| 9 | Rich Interactive CLI & Terminal UI | Colorized status, live progress bars, summary tables, interactive mode wizard, `--dry-run`, `--verbose` flags | M4 | R3 |
| 10 | Structured Error Logging & Summary Reporting | Complete statistics: mods scanned, archives updated, jbeam files fixed, optimizations deployed, warnings/errors | M4 | R3 |
| 11 | Git Repository & CI Setup | Initialize Git repo, `.gitignore` for Python/BeamNG, MIT License, GitHub Actions CI workflow (matrix Python 3.10-3.13 on Windows/Ubuntu), Issue templates | M5 | R4 |
| 12 | Packaging & CLI Entrypoint | PEP 517/621 `pyproject.toml` and `requirements.txt` with console script `beamng-mod-fixer` | M5 | R4 |
| 13 | Comprehensive Bilingual Documentation | Full `README.md` (EN) and `README_RU.md` (RU) detailing Torque3D PBR self-shadow physics bug, CLI guide, graphics preset rationale, modder manual guide | M5 | R4 |
| 14 | 4-Tier Test Architecture & Fixture Engine | Comprehensive `pytest` suite (Tier 1-4) with hermetic `FixtureFactory` achieving 100% pass rate | E2E Track | R5 |
| 15 | Adversarial Coverage Hardening | Tier 5 adversarial stress testing and coverage validation | M6 (Final) | R5 |

## Milestones
| # | Name | Scope | Dependencies | Status | Key Outputs |
|---|------|-------|-------------|--------|-------------|
| E2E | E2E Testing Track | Requirement-driven test suite, `FixtureFactory`, Tiers 1-4, `TEST_INFRA.md`, publish `TEST_READY.md` | none | DONE | `tests/fixtures/factory.py`, `tests/conftest.py`, 15 test files, `TEST_READY.md` |
| M1 | Core JBeam & Optics Fixer Engine | JBeam regex replacement, spotlight diagnostics, encoding handler, unit tests | none | DONE | `src/beamng_mod_fixer/exceptions.py`, `models.py`, `core/jbeam_fixer.py` |
| M2 | Atomic Streaming ZIP Rewriter & File Safety | In-place atomic rewrite, streaming chunk copy, locked/corrupt/password archive fault tolerance | M1 | PLANNED | - |
| M3 | Graphics Optimizer & Safe Cache Cleaner | Settings backup, graphics JSON preset modifier, safe cache cleaner guard | none | PLANNED | - |
| M4 | CLI, Rich UI & Reporting System | Auto-discovery, interactive wizard, CLI options, Rich progress/tables, logging | M1, M2, M3 | PLANNED | - |
| M5 | Packaging, Repo Infrastructure & Bilingual Docs | `pyproject.toml`, `.gitignore`, MIT License, GitHub Actions CI, `README.md`, `README_RU.md` | M4 | PLANNED | - |
| M6 | Final Milestone (100% E2E Pass & Adversarial Hardening) | Run full E2E test suite (Tiers 1-4), fix any regressions, Tier 5 adversarial coverage hardening | M1, M2, M3, M4, M5, E2E | PLANNED | - |

## Interface Contracts

### `beamng_mod_fixer.core.jbeam_fixer` ↔ `beamng_mod_fixer.core.zip_processor`
- `fix_jbeam_content(content: str, filename: str = "", available_files: Optional[Set[str]] = None) -> Tuple[str, int, List[DiagnosticNotice]]`
  - Takes raw JBeam text string.
  - Returns `(fixed_content, fix_count, diagnostics)`. If no fix needed, `fix_count == 0` and `fixed_content is content` (or equal).
  - Preserves exact formatting, quotes, comments, indentation.
- `detect_light_cast_shadows(content: str) -> bool`
  - Quick check if content contains `"lightCastShadows": true` before running full regex pass.
- `decode_jbeam_bytes(data: bytes) -> Tuple[str, str]`
  - Robust multi-encoding byte decoder (UTF-8 with BOM, UTF-8, heuristic CP1252 vs CP1251, Latin-1 fallback).
- `encode_jbeam_str(text: str, encoding: str, with_bom: bool = False) -> bytes`
  - Symmetric encoder preserving original encoding.

### `beamng_mod_fixer.core.file_utils` ↔ `beamng_mod_fixer.core.zip_processor`
- `atomic_replace(temp_path: Path, target_path: Path, max_retries: int = 5, retry_delay: float = 0.05) -> None`
  - Uses `os.replace` on the same filesystem volume.
  - Catches transient Windows file locks with exponential backoff.
- `create_temp_target(target_path: Path) -> Path`
  - Creates a hidden temporary file `.target_path.tmp_<uuid>` in the same directory as `target_path`.

### `beamng_mod_fixer.core.graphics_optimizer` ↔ `beamng_mod_fixer.cli`
- `optimize_settings(settings_path: Path, preset: str = "balanced", backup: bool = True) -> OptimizationResult`
  - Creates timestamped `.bak` backup file.
  - Updates `GraphicDynReflectionFacesPerupdate: 2`, `GraphicDynReflectionTexsize: 512`, shadows, mirrors, decals.
  - Returns structured `OptimizationResult(backup_created=True, backup_path=..., applied_keys={...})`.

### `beamng_mod_fixer.core.cache_cleaner` ↔ `beamng_mod_fixer.cli`
- `clean_shader_cache(beamng_user_path: Path, dry_run: bool = False) -> CacheCleanResult`
  - Strictly validates that target path contains `temp/shaders` or `temp/vehicles`.
  - Removes compiled shaders (`.d3dcsx`, `.cani`) and temporary vehicle cache.
  - Refuses to delete anything outside `temp/`.
  - Returns `CacheCleanResult(files_deleted=..., bytes_freed=...)`.

## Code Layout
```
beamng_mod_fixer/
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── src/
│   └── beamng_mod_fixer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── exceptions.py
│       ├── models.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── cache_cleaner.py
│       │   ├── discovery.py
│       │   ├── file_utils.py
│       │   ├── graphics_optimizer.py
│       │   ├── jbeam_fixer.py
│       │   └── zip_processor.py
│       └── ui/
│           ├── __init__.py
│           └── reporter.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── factory.py
│   ├── tier1_feature/
│   │   ├── test_jbeam_regex.py
│   │   ├── test_optics_diagnostics.py
│   │   ├── test_graphics_optimizer.py
│   │   └── test_cache_cleaner.py
│   ├── tier2_boundary/
│   │   ├── test_corrupt_zip.py
│   │   ├── test_encrypted_zip.py
│   │   ├── test_file_locks.py
│   │   └── test_encoding_bom.py
│   ├── tier3_combination/
│   │   ├── test_atomic_rewrite.py
│   │   ├── test_binary_passthrough.py
│   │   └── test_batch_scanner.py
│   ├── tier4_workload/
│   │   ├── test_cli_e2e.py
│   │   └── test_realistic_mods_suite.py
│   └── tier5_adversarial/
│       └── test_adversarial_hardening.py
├── .gitignore
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── README.md
└── README_RU.md
```
