## 2026-09-18T14:50:10Z

You are Worker 3 (teamwork_preview_worker) for Milestone 3: Graphics Optimizer & Safe Cache Cleaner.
Your working directory: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\worker_m3\
Original Request path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\ORIGINAL_REQUEST.md
PROJECT.md path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\orchestrator_1\PROJECT.md
TEST_READY.md path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\TEST_READY.md
Explorer 1 & 2 Reports path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\explorer_survey_1\survey_report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

WRITE OWNERSHIP:
You exclusively own:
- C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\src\beamng_mod_fixer\core\graphics_optimizer.py
- C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\src\beamng_mod_fixer\core\cache_cleaner.py

TASK:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and Explorer reports.
2. Implement `src/beamng_mod_fixer/core/graphics_optimizer.py`:
   - `optimize_settings(settings_path: Path, preset: str = "balanced", backup: bool = True, dry_run: bool = False) -> OptimizationResult`:
     * Automatically creates timestamped backup `settings.json.backup_YYYYMMDD_HHMMSS` (and/or `.bak`) before modifying.
     * Applies balanced optimization preset:
       - `GraphicDynReflectionFacesPerupdate`: 2 (reduces CPU draw-calls on reflections)
       - `GraphicDynReflectionTexsize`: 512 (crisp reflections without VRAM penalty)
       - `GraphicShadowsQuality`: "High" / balanced filtering
       - `GraphicDynMirrorsDetail`: 0.75
       - Balanced decal and particle settings
     * Preserves all other user keys, controls, audio, steering bindings.
     * Safely handles JSON formatting and atomic file write.
   - `restore_settings_backup(settings_path: Path, backup_path: Optional[Path] = None) -> bool`:
     * Restores the most recent backup if needed.
3. Implement `src/beamng_mod_fixer/core/cache_cleaner.py`:
   - `clean_shader_cache(beamng_user_path: Path, dry_run: bool = False) -> CacheCleanResult`:
     * Strict safety guard: validates that target path contains `temp` or is a verified BeamNG user directory.
     * Strictly refuses to delete anything outside `temp/`.
     * Purges `temp/shaders/` (`.d3dcsx`, `.cani`, shader cache databases) and `temp/vehicles/` (stale collision/mesh caches).
     * Never deletes `settings/`, `mods/`, or user vehicle configurations (`vehicles/*.pc`).
     * Returns structured `CacheCleanResult(files_deleted=..., bytes_freed=..., directories_cleared=...)`.
4. Run verification tests:
   `python -m pytest tests/tier1_feature/test_graphics_optimizer.py tests/tier1_feature/test_cache_cleaner.py -v`
   Ensure 100% passing tests!
5. Write your handoff report to:
   C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\worker_m3\handoff.md
6. Send a message to parent (ID: 6ea9e2a6-86af-4093-9e1b-3a0131e19d2f) with summary and path to your handoff.
