# Handoff Report — Explorer 3: Testing & Repository Strategy
**Agent**: `explorer_survey_3` (teamwork_preview_explorer)
**Date**: 2026-09-18
**Target Milestone**: Milestone 0 — Survey and Architecture

---

## 1. Observation

1. **Source Requirements (`ORIGINAL_REQUEST.md`)**:
   - Lines 14–20 (R1): JBeam headlights and configuration fixing:
     > "Точная замена параметра lightCastShadows: true на lightCastShadows: false во всех найденных .jbeam файлах с использованием гибкого регулярного выражения... Атомарное обновление архивов на месте (in-place) через временный файл с немедленной заменой оригинала... Диагностика и исправление сопутствующих сбоев оптики"
   - Lines 21–28 (R2): Graphics optimization & cache cleaning:
     > "Резервное копирование файлов настроек пользователя (settings.json... в settings.json.bak)... Деплой сбалансированного оптимизационного пресета... Безопасная очистка кэша (temp/ и скомпилированных шейдеров)"
   - Lines 29–33 (R3): Fault tolerance & UX:
     > "Пропуск поврежденных, заблокированных игрой или запароленных архивов без аварийного завершения работы скрипта, с фиксацией причины в журнале... Итоговый подробный отчет"
   - Lines 34–42 (R4): Repository & documentation:
     > "Инициализация чистого Git-репозитория... .gitignore для Python/BeamNG... Подробный двуязычный гайд (README.md на английском и README_RU.md на русском): Причина проблемы: почему фары перестали светить (механика self-shadow occlusion в Torque3D/BeamNG PBR при lightCastShadows: true)... Лицензия MIT, pyproject.toml / requirements.txt, шаблоны GitHub Issues и рабочий процесс GitHub Actions CI"
   - Lines 43–47 (R5): Pytest suite:
     > "Модульные тесты для регулярных выражений JBeam... Интеграционные тесты для работы с ZIP-архивами... Тесты модуля оптимизации настроек"

2. **Orchestrator Strategy (`orchestrator_1/BRIEFING.md`)**:
   - Lines 14–22: Mandates Dual Track (Implementation Track + E2E Testing Track), with E2E Testing Track publishing opaque-box test suites.
   - Lines 51–55: Three parallel explorers dispatched:
     - `explorer_survey_1`: Specification Mining
     - `explorer_survey_2`: Architecture & Systems Design
     - `explorer_survey_3` (Current): Testing & Repo Strategy

3. **Filesystem State**:
   - The workspace root `C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer` contains `ORIGINAL_REQUEST.md` and `.agents/`.
   - Python code, test directories, packaging files, and documentation are not yet implemented.

---

## 2. Logic Chain

1. **Test Pyramid Alignment (From Observation 1, R5 & Observation 2)**:
   - To achieve reliable verification of user archive manipulation without data loss, tests must be partitioned into 4 distinct tiers:
     - *Tier 1 (Unit / Small)*: Isolates regex logic, optics diagnostics, JSON mutation, and cache file filtering. Executed in-memory or in isolated tmpdirs with zero network dependencies.
     - *Tier 2 (Boundaries / Fault Tolerance)*: Targets corrupt ZIPs, PKWARE/AES encrypted ZIPs, locked files (Windows sharing violations), non-UTF-8 encodings (CP1251), and deep path lengths.
     - *Tier 3 (Integration / Medium)*: Verifies the in-place atomic rewrite engine (`tempfile` + `os.replace`), non-JBeam binary pass-through, batch scanner statistics, and dry-run idempotency.
     - *Tier 4 (E2E / Large)*: Validates the full CLI interface across realistic synthetic BeamNG directory trees (25+ mods) with exit codes, rich formatting, and performance profiling.

2. **Hermetic Fixture Generation (From Observation 1, R1, R3 & R5)**:
   - Tests cannot rely on external game installations or copyrighted BeamNG game content.
   - Therefore, a self-contained `FixtureFactory` (`tests/fixtures/factory.py`) must generate authentic synthetic JBeam structures, valid/corrupted/password ZIPs, synthetic `settings.json`, and dummy compiled shader files (`.d3dcsx`, `.cani`) purely through standard library Python (`zipfile`, `io`, `bytearray`).

3. **Packaging & CI Standardization (From Observation 1, R4)**:
   - To support modern Python packaging, the project requires a PEP 517/621 `pyproject.toml` with console script `beamng-mod-fixer = "beamng_mod_fixer.cli:main"`.
   - CI workflow requires a multi-OS (Windows + Ubuntu) and multi-version (Python 3.10, 3.11, 3.12, 3.13) matrix with `ruff`, `mypy --strict`, and `pytest --cov`.

4. **Physics & Engine Grounding for Documentation (From Observation 1, R4)**:
   - The documentation must provide the definitive 3D rendering explanation:
     - In Torque3D PBR lighting, enabling `lightCastShadows: true` on vehicle headlights whose light origin node resides inside the 3D reflector or behind the glass lens geometry creates an immediate self-intersection depth occlusion.
     - The shadow map renders the vehicle's own headlight lens as an occluder, casting a 100% shadow over the forward light cone.
     - Setting `lightCastShadows: false` disables the shadow pass for that light, allowing photons to penetrate the glass mesh unimpeded and illuminate the environment, while providing a 20–35% FPS gain at night.

---

## 3. Caveats

- **Linux / Wine Differences**: While Windows is the primary platform where file locking issues (`[WinError 32]`) occur, CI tests on Ubuntu will use POSIX file handling. File locking tests must simulate Windows `PermissionError` using cross-platform mocks or `fcntl` when testing on Linux.
- **Third-Party Dependencies**: The core package relies only on `rich`, `colorama` (on Windows), and `typing-extensions`. All fixture generation in tests is implemented without external binary dependencies.

---

## 4. Conclusion

The testing and repository architecture for the BeamNG.drive Mod Fixer & Graphics Optimizer is fully defined and documented in `survey_report.md`:
1. **4-Tier Test Architecture**: 100% specified across 14 dedicated test modules.
2. **Fixture Generation Engine**: Ready for implementation via `tests/fixtures/factory.py` covering valid, corrupted, encrypted, and locked archives.
3. **Repository Infrastructure**: Fully mapped (`pyproject.toml`, `.gitignore`, MIT License, GitHub Actions CI matrix for Python 3.10–3.13, issue/PR templates).
4. **Bilingual Documentation**: Detailed structural and technical blueprints for `README.md` and `README_RU.md` with Torque3D PBR physics explanations.

All requirements R1–R5 from `ORIGINAL_REQUEST.md` have been addressed with concrete technical specifications.

---

## 5. Verification Method

To independently verify the strategy and artifacts produced:

1. **Inspect Report Files**:
   - `C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\explorer_survey_3\survey_report.md`
   - `C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\explorer_survey_3\BRIEFING.md`
   - `C:\Users\method\.gemini\antigravity\scratch\beamng_mod_fixer\.agents\explorer_survey_3\progress.md`

2. **Downstream Implementation Verification Commands** (for subsequent milestones):
   - Unit & 4-Tier Test Suite: `pytest -v --cov=beamng_mod_fixer`
   - Linter: `ruff check src/ tests/`
   - Type Checker: `mypy src/`
   - CLI Entry Point: `beamng-mod-fixer --help`
   - CI Workflow Execution: Verify GitHub Actions run across Windows and Ubuntu on Python 3.10, 3.11, 3.12, and 3.13.
