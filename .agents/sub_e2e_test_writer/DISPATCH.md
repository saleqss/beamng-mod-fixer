## 2026-09-18T14:27:31Z
You are the E2E Test Writer (teamwork_preview_test_writer) for the BeamNG.drive Mod Fixer & Graphics Optimizer project.
Your working directory: C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\sub_e2e_test_writer\\
Original Request path: C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\ORIGINAL_REQUEST.md
PROJECT.md path: C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\orchestrator_1\\PROJECT.md
TEST_INFRA.md path: C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\orchestrator_1\\TEST_INFRA.md
Explorer 3 Report path: C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\explorer_survey_3\\survey_report.md

WRITE OWNERSHIP:
You exclusively own all files in C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\tests\\ and the file C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\TEST_READY.md.
Do NOT modify any files in src/.

TASK:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, TEST_INFRA.md, and Explorer 3\'s survey report.
2. Implement the complete hermetic synthetic fixture factory in tests/fixtures/factory.py:
   - Functions to create realistic BeamNG vehicle mod zip archives (containing vehicles/<model>/... .jbeam files, textures, sound files).
   - Functions to generate corrupted zip archives (truncated header, bad CRC, empty).
   - Functions to generate password-protected zip archives.
   - Functions to generate JBeam files with various lightCastShadows representations (spacing, tabs, quotes, comments, already-false, case variations).
   - Functions to generate synthetic settings.json / game-settings.json structures.
   - Functions to generate synthetic temp/ cache structures (temp/shaders/, temp/vehicles/, dummy .d3dcsx/.cani files).
3. Create tests/conftest.py with reusable fixtures.
4. Implement the 4 tiers of comprehensive tests:
   - Tier 1: tests/tier1_feature/test_jbeam_regex.py, test_optics_diagnostics.py, test_graphics_optimizer.py, test_cache_cleaner.py. (>=5 tests per feature).
   - Tier 2: tests/tier2_boundary/test_corrupt_zip.py, test_encrypted_zip.py, test_file_locks.py, test_encoding_bom.py. (>=5 tests per feature).
   - Tier 3: tests/tier3_combination/test_atomic_rewrite.py, test_binary_passthrough.py, test_batch_scanner.py.
   - Tier 4: tests/tier4_workload/test_cli_e2e.py, test_realistic_mods_suite.py (subprocess execution on synthetic 25+ mods).
5. When all test files and fixtures are written, publish TEST_READY.md at project root C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\TEST_READY.md using the exact template from the project instructions (Test runner command, coverage summary table across all 4 tiers, feature checklist).
6. Write your handoff report to:
   C:\\Users\\method\\.gemini\\antigravity\\scratch\\beamng_mod_fixer\\.agents\\sub_e2e_test_writer\\handoff.md
7. Send a message to parent (ID: 6ea9e2a6-86af-4093-9e1b-3a0131e19d2f) with summary and path to your handoff.
