# E2E Test Infra: BeamNG.drive Mod Fixer & Graphics Optimizer

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.
- 100% Hermetic: Pure-Python synthetic fixture generation via `tests/fixtures/factory.py` with zero dependency on proprietary game files.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | BeamNG Windows Directory Discovery | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | JBeam Headlight Regex Replacement Engine | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | JBeam Optics Diagnostics & Normalization | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | High-Performance Streaming ZIP In-Place Rewriter | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Fault-Tolerant Archive Handling | ORIGINAL_REQUEST §R1, §R3 | 5 | 5 | ✓ |
| 6 | Settings Backup Engine | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 7 | Graphics Optimization Preset Deployer | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 8 | Safe Shader Cache Cleaner | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 9 | Rich Interactive CLI & Terminal UI | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 10 | Structured Error Logging & Summary Reporting | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 11 | Git Repository & CI Setup | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 12 | Packaging & CLI Entrypoint | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 13 | Comprehensive Bilingual Documentation | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest` with `pytest-cov`
- Location: `tests/`
- Structure:
  - `tests/fixtures/factory.py`: Synthetic ZIP generator, corrupt archives, password archives, JBeam syntax variations, settings.json trees, shader cache trees.
  - `tests/tier1_feature/`: Isolated feature coverage (regex replacement, optics diagnostics, graphics optimizer, cache cleaner).
  - `tests/tier2_boundary/`: Boundary and error conditions (corrupt ZIPs, locked files WinError 32, encrypted archives, UTF-8/CP1251 BOM, deep nested paths).
  - `tests/tier3_combination/`: Cross-feature interactions (atomic rewrite with binary assets, batch scanner statistics, dry-run idempotency).
  - `tests/tier4_workload/`: Real-world application scenarios (CLI subprocess execution on 25+ synthetic vehicle mods, exit codes, performance throughput).
  - `tests/tier5_adversarial/`: White-box coverage hardening and edge-case stress testing.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Mod Directory Scan & Repair | F1, F2, F3, F4, F5, F9, F10 | High |
| 2 | Corrupted & Locked Archive Resilient Run | F4, F5, F9, F10 | Medium |
| 3 | Graphics Preset Optimization with Backup | F6, F7, F9, F10 | Medium |
| 4 | Safe Shader Cache Purge | F8, F9, F10 | Medium |
| 5 | Full Interactive Wizard End-to-End | F1-F10 | High |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature
- Tier 2: ≥5 test cases per feature (boundary and failure cases)
- Tier 3: pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
- Target: 100% test pass rate with high line and branch coverage
