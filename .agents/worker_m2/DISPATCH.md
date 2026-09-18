## 2026-09-18T14:50:10Z
You are Worker 2 (teamwork_preview_worker) for Milestone 2: Atomic Streaming ZIP Rewriter & File Safety.
Your working directory: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\worker_m2\
Original Request path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\ORIGINAL_REQUEST.md
PROJECT.md path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\orchestrator_1\PROJECT.md
TEST_READY.md path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\TEST_READY.md
Explorer 2 Report path: C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\explorer_survey_2\survey_report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

WRITE OWNERSHIP:
You exclusively own:
- C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\src\beamng_mod_fixer\core\file_utils.py
- C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\src\beamng_mod_fixer\core\zip_processor.py

TASK:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and Explorer 2's survey report.
2. Implement `src/beamng_mod_fixer/core/file_utils.py`:
   - `atomic_replace(temp_path: Path, target_path: Path, max_retries: int = 5, retry_delay: float = 0.05) -> None`:
     Uses `os.replace` on the same drive volume. Catches Windows file lock sharing violations (`PermissionError` / `WinError 32`) with exponential backoff.
   - `create_temp_target(target_path: Path) -> Path`:
     Creates temporary hidden file on the same volume: `target_path.with_name(f".{target_path.name}.tmp_{uuid.uuid4().hex[:8]}")`.
   - `is_archive_locked(path: Path) -> bool`:
     Checks for active file sharing locks.
3. Implement `src/beamng_mod_fixer/core/zip_processor.py`:
   - `process_mod_archive(zip_path: Path, dry_run: bool = False, backup_dir: Optional[Path] = None) -> ModArchiveReport`:
     * Inspects zip entries for JBeam files.
     * Catches and reports `PasswordProtectedArchiveError` (`zinfo.flag_bits & 0x1`).
     * Catches and reports `CorruptArchiveError` (`BadZipFile`, CRC errors).
     * Catches and reports `ArchiveLockedError` (`PermissionError`).
     * If no JBeam files need fixing and no diagnostics require rewrite, skip write entirely (`ModStatus.UNTOUCHED`).
     * In-place atomic rewrite:
       - Uses `shutil.copyfileobj(src, dst, length=256*1024)` to stream non-JBeam binary files (DDS, DAE, WAV, PC) without memory blowup, preserving `ZipInfo` (timestamps, permissions, compress_type).
       - For modified `.jbeam` files, writes fixed bytes via `target_zip.writestr(zinfo, fixed_bytes)`.
       - Replaces original atomically via `file_utils.atomic_replace`.
       - Guarantees `finally: temp_path.unlink(missing_ok=True)` so zero `.tmp` files are left behind.
   - `scan_and_process_directory(mods_dir: Path, dry_run: bool = False, progress_callback: Optional[Callable] = None) -> OverallSummary`:
     * Iterates all `.zip` mod archives in `mods_dir`.
     * Gracefully records errors without terminating batch execution.
     * Returns structured `OverallSummary`.
4. Run verification tests:
   `python -m pytest tests/tier2_boundary/ tests/tier3_combination/ -v`
   Ensure 100% passing tests!
5. Write your handoff report to:
   C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\worker_m2\handoff.md
6. Send a message to parent (ID: 6ea9e2a6-86af-4093-9e1b-3a0131e19d2f) with summary and path to your handoff.
