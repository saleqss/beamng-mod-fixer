"""Bilingual Internationalization (i18n) and Configuration Manager for GBEAM FIX.

Supports:
- English (en) and Russian (ru).
- Persistent user configuration in ~/.beamng_mod_fixer/config.json.
- Automatic system locale detection on first run.
- Clean, bracket-free typography without spam.
"""

import json
import locale
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".beamng_mod_fixer"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "ru",
    "auto_installer_enabled": False,
    "graphics_preset": "ultra-max-fps",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App & Header
        "app_title": "GBEAM FIX - ULTIMATE GLOBAL MOD FIXER & GRAPHICS OPTIMIZER",
        "app_subtitle": "BeamNG.drive 0.30 - 0.34+ Adaptive Community Standard",
        "system_env": "System & Game Environment",
        "user_dir": "BeamNG Directory",
        "mods_folder": "Mods Folder",
        "settings_folder": "Settings Folder",
        "cache_folder": "Cache / Temp Folder",
        "mods_detected": "{count} mod archives detected",
        "persistent_cache": "Persistent Cache",
        "cache_active": "Active (instant)",
        "cache_inactive": "Not cached",
        "engine_active": "Adaptive Multi-Domain Recovery Active",
        "auto_installer_status": "Auto-Installer",
        "auto_installer_on": "ON (monitoring Downloads)",
        "auto_installer_off": "OFF",

        # Main Menu
        "main_menu_title": "MAIN CONTROL MENU",
        "opt_global_fix": "1. 🚀 1-Click Global Fix (Optics + Textures + Physics + Audio + Lua + Graphics + Cache)",
        "opt_optics": "2. 💡 Headlights & Optics Studio (Low/high beam balance, angle repair, cookie modernizer)",
        "opt_materials": "3. 🎨 Materials & Texture Doctor (Fix NO TEXTURE, materials.cs -> 1.5 JSON, VFS paths)",
        "opt_drivetrain": "4. ⚙️ Drivetrain & Physics Repair (Fix frozen cars, differential explosion, tire PSI)",
        "opt_sound_lua": "5. 🔊 Sound & Lua Crash Guard (Modernize FMOD audio, guard deprecated lua APIs)",
        "opt_graphics": "6. 🚀 Graphics & FPS Optimizer (Ultra-Max-FPS, 60FPS-Balanced, Low, Potato presets)",
        "opt_cache": "7. 🧹 Cache & Diagnostics Purge (DirectX/Vulkan shaders, vehicle binaries, temp files)",
        "opt_audit": "8. 📋 Deep Mod Health Audit (Safe non-modifying dry-run scan with report)",
        "opt_paths": "9. 📁 BeamNG Directory & Paths (Auto-detection & path validator across drives)",
        "opt_watcher": "W. ⚡ Mod Auto-Installer & Downloads Watcher",
        "opt_language": "L. 🌐 Change Language / Сменить язык (English / Русский)",
        "opt_exit": "0. 🚪 Exit",
        "prompt_choice": "Select an option (default: 1): ",

        # Global Fix Pipeline
        "global_fix_header": "EXECUTING 1-CLICK GLOBAL FIX",
        "global_fix_desc": "Starting Unified 7-Stage Repair & Optimization Pipeline...",
        "stage_optics": "1. Headlights & Front Optics",
        "stage_optics_desc": "Selective lowbeams, cookie modernizer, angle repair, highbeam penetration",
        "stage_rear": "2. Rear Lights Calibration",
        "stage_rear_desc": "Eliminates white rear light bug & nuclear red discs with soft ambient wash",
        "stage_materials": "3. Materials & Texture Doctor",
        "stage_materials_desc": "materials.cs -> 1.5 JSON, resolves orange NO TEXTURE, reconciles DDS/PNG",
        "stage_drivetrain": "4. Drivetrain & Physics Repair",
        "stage_drivetrain_desc": "Unfreezes differentials, clamps tire pressures, stabilizes suspension",
        "stage_sound": "5. Sound Modernizer",
        "stage_sound_desc": "Pre-FMOD audio paths -> BeamNG FMOD sound events",
        "stage_lua": "6. Lua Safety Guard",
        "stage_lua_desc": "Guards deprecated vehicle Lua calls from crashes",
        "stage_graphics": "Deploying Maximum Ultra Visuals & Smart FPS Optimization...",
        "stage_cache": "Purging compiled DirectX/Vulkan shader binaries in temp/...",
        "pipeline_complete": "All 7 Pipeline Stages Completed Successfully!",

        # Post-Fix Studio
        "post_fix_title": "1-CLICK GLOBAL FIX RESULTS",
        "post_fix_actions": "POST-FIX ACTIONS & NAVIGATION:",
        "post_return_main": "1. 🏠 Return to Main Control Menu (Default)",
        "post_view_diags": "2. 📋 View Detailed File-by-File Diagnostic Notices & Logs",
        "post_launch_graphics": "3. 🚀 Launch Graphics & FPS Optimizer Studio",
        "post_purge_cache": "4. 🧹 Purge Compiled Shader Caches (.d3dcsx, .db)",
        "post_exit": "0. 🚪 Exit GBEAM FIX",
        "press_enter_return": "Press Enter to return to Main Menu...",

        # Summary Report Keys
        "rep_scanned": "Total mod archives scanned",
        "rep_fixed": "Modified (fixed) archives",
        "rep_clean": "Already clean archives",
        "rep_shadows": "Headlight shadows fixed",
        "rep_rear": "Rear lights ground wash fixed",
        "rep_materials_cs": "materials.cs converted",
        "rep_materials_json": "materials.json textures fixed",
        "rep_drivetrain": "Drivetrain & physics repaired",
        "rep_sound": "FMOD audio events modernized",
        "rep_lua": "Vehicle Lua scripts guarded",
        "rep_graphics": "Graphics & FPS optimization",
        "rep_cache": "DirectX/Vulkan cache purge",
        "rep_junk": "Archive junk files removed",
        "rep_locked": "Skipped (locked / in-use)",
        "rep_corrupt": "Skipped (corrupt)",
        "rep_encrypted": "Skipped (encrypted)",
        "rep_errors": "Errors encountered",
        "rep_elapsed": "Elapsed processing time",

        # Auto-Installer Submenu
        "watcher_title": "MOD AUTO-INSTALLER & DOWNLOADS WATCHER",
        "watcher_desc": "Automatically monitors your Downloads folder. When you download any BeamNG mod, it unwraps nested folders, moves it to the mods folder, and applies the complete 7-stage auto-fix on the fly.",
        "watcher_downloads_dir": "Downloads Directory",
        "watcher_toggle_on": "1. 🟢 Start Background Auto-Installer (Runs in background)",
        "watcher_toggle_off": "2. 🔴 Stop Background Auto-Installer",
        "watcher_scan_now": "3. ⚡ Scan Downloads Folder Now (Manual 1-time import & fix)",
        "watcher_recent": "4. 📜 View Recent Auto-Installed Mods Log",
        "watcher_back": "0. ↩️ Return to Main Menu",

        # Graphics Presets
        "gfx_title": "GRAPHICS & RESHADE OPTIMIZER",
        "gfx_preset_1": "1. Deploy 'Ultra-Max-FPS' (Max Ultra visuals, 1024px cubemaps, 4x shadows + ReShade Ultra Photoreal)",
        "gfx_preset_2": "2. Deploy 'Medium-60FPS' (Most beautiful yet optimal 60 FPS sweet spot + ReShade Medium Optimal)",
        "gfx_preset_3": "3. Deploy 'Low-Weak' (Entry-level GPUs: reduced particles + ReShade Low Fast)",
        "gfx_preset_4": "4. Deploy 'Potato-Ultra-Weak' (Extreme performance for iGPUs / weak laptops + ReShade Potato Boost)",
        "gfx_reshade_deploy": "5. 🎨 Deploy All ReShade Presets (.ini files for ReShade)",
        "gfx_restore": "6. ↩️ Restore Graphics Settings from Previous Backup",

        # Messages
        "thanks": "Thank you for using GBEAM FIX. Happy driving!",
        "cancelled": "Operation cancelled by user.",
        "invalid_opt": "Invalid option. Please enter a valid number.",
    },
    "ru": {
        # App & Header
        "app_title": "GBEAM FIX - ГЛОБАЛЬНЫЙ ФИКС МОДОВ И ОПТИМИЗАТОР ГРАФИКИ",
        "app_subtitle": "Стандарт сообщества для BeamNG.drive 0.30 - 0.34+",
        "system_env": "Система и игровое окружение",
        "user_dir": "Папка BeamNG",
        "mods_folder": "Папка модов",
        "settings_folder": "Папка настроек",
        "cache_folder": "Папка кэша / Temp",
        "mods_detected": "Обнаружено архивов модов: {count}",
        "persistent_cache": "Постоянный кэш путей",
        "cache_active": "Активен (мгновенно)",
        "cache_inactive": "Не кэширован",
        "engine_active": "Адаптивное мультидоменное восстановление активно",
        "auto_installer_status": "Автоустановщик модов",
        "auto_installer_on": "ВКЛЮЧЕН (следит за Загрузками)",
        "auto_installer_off": "ВЫКЛЮЧЕН",

        # Main Menu
        "main_menu_title": "ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ",
        "opt_global_fix": "1. 🚀 ГЛОБАЛЬНЫЙ ФИКС В 1 КЛИК (Оптика + Текстуры + Физика + Звук + Lua + Графика + Кэш)",
        "opt_optics": "2. 💡 Студия оптики и фар (Баланс дальний/ближний, углы лучей, современные текстуры)",
        "opt_materials": "3. 🎨 Доктор материалов и текстур (Устранение NO TEXTURE, materials.cs -> 1.5 JSON, пути VFS)",
        "opt_drivetrain": "4. ⚙️ Ремонт трансмиссии и физики (Разморозка дифференциалов, давление в шинах, сцепление)",
        "opt_sound_lua": "5. 🔊 Защита звука и Lua (Перевод на FMOD BeamNG, защита от вылетов Lua)",
        "opt_graphics": "6. 🚀 Оптимизатор графики и FPS (Пресеты Ultra-Max-FPS, 60FPS-Balanced, Low, Картошка)",
        "opt_cache": "7. 🧹 Полная очистка кэша (Шейдеры DirectX/Vulkan, кэш физики авто, временные файлы)",
        "opt_audit": "8. 📋 Глубокий аудит модов (Безопасное сканирование без изменений с отчетом)",
        "opt_paths": "9. 📁 Управление путями BeamNG (Автопоиск по всем дискам и ручной выбор)",
        "opt_watcher": "W. ⚡ Фоновый автоустановщик модов из Загрузок",
        "opt_language": "L. 🌐 Сменить язык / Change Language (Русский / English)",
        "opt_exit": "0. 🚪 Выход",
        "prompt_choice": "Выберите пункт (по умолчанию 1): ",

        # Global Fix Pipeline
        "global_fix_header": "ЗАПУСК ГЛОБАЛЬНОГО ФИКСА В 1 КЛИК",
        "global_fix_desc": "Запуск единого 7-этапного комплекса восстановления и оптимизации...",
        "stage_optics": "1. Передняя оптика и фары",
        "stage_optics_desc": "Выборочный ближний свет, современные текстуры flare/cookie, пробивающий дальний свет",
        "stage_rear": "2. Калибровка задних фонарей",
        "stage_rear_desc": "Устранение белого света фар сзади и ядовито-красных пятен, мягкий реалистичный свет",
        "stage_materials": "3. Доктор материалов и текстур",
        "stage_materials_desc": "Конвертация materials.cs в 1.5 JSON, устранение оранжевого NO TEXTURE, сверка DDS/PNG",
        "stage_drivetrain": "4. Ремонт трансмиссии и физики",
        "stage_drivetrain_desc": "Разморозка дифференциалов, калибровка давления шин, стабилизация подвески",
        "stage_sound": "5. Модернизация звука",
        "stage_sound_desc": "Перевод устаревших путей звука на звуковые события FMOD BeamNG",
        "stage_lua": "6. Защита скриптов Lua",
        "stage_lua_desc": "Защита устаревших функций Lua от краша при спавне авто",
        "stage_graphics": "Применение пресета Ultra-Max-FPS (максимальный ультра-графон с бустом FPS)...",
        "stage_cache": "Очистка скомпилированных шейдеров DirectX/Vulkan в temp/...",
        "pipeline_complete": "Все 7 этапов успешно выполнены на 100%!",

        # Post-Fix Studio
        "post_fix_title": "РЕЗУЛЬТАТЫ ГЛОБАЛЬНОГО ФИКСА",
        "post_fix_actions": "ДЕЙСТВИЯ ПОСЛЕ ФИКСА И НАВИГАЦИЯ:",
        "post_return_main": "1. 🏠 Вернуться в главное меню (По умолчанию)",
        "post_view_diags": "2. 📋 Просмотреть подробный журнал изменений по файлам",
        "post_launch_graphics": "3. 🚀 Открыть меню настройки графики и FPS",
        "post_purge_cache": "4. 🧹 Очистить кэш шейдеров (.d3dcsx, .db)",
        "post_exit": "0. 🚪 Выйти из GBEAM FIX",
        "press_enter_return": "Нажмите Enter для возврата в главное меню...",

        # Summary Report Keys
        "rep_scanned": "Всего просканировано архивов модов",
        "rep_fixed": "Исправлено (модифицировано) архивов",
        "rep_clean": "Уже чистых (без ошибок) архивов",
        "rep_shadows": "Исправлено теней фар (lightCastShadows)",
        "rep_rear": "Откалибровано освещение задних фонарей",
        "rep_materials_cs": "Сконвертировано materials.cs в JSON 1.5",
        "rep_materials_json": "Исправлено текстур в materials.json",
        "rep_drivetrain": "Исправлено узлов трансмиссии и физики",
        "rep_sound": "Модернизировано звуков на FMOD события",
        "rep_lua": "Защищено от вылетов скриптов Lua",
        "rep_graphics": "Оптимизация графики и FPS",
        "rep_cache": "Очистка кэша шейдеров DirectX/Vulkan",
        "rep_junk": "Удалено мусорных файлов из архивов",
        "rep_locked": "Пропущено (заблокировано игрой)",
        "rep_corrupt": "Пропущено (поврежденный архив)",
        "rep_encrypted": "Пропущено (с паролем)",
        "rep_errors": "Ошибок при обработке",
        "rep_elapsed": "Время выполнения операции",

        # Auto-Installer Submenu
        "watcher_title": "АВТОУСТАНОВЩИК МОДОВ И МОНИТОРИНГ ЗАГРУЗОК",
        "watcher_desc": "Автоматически следит за папкой Загрузки. При скачивании любого мода для BeamNG скрипт распакует вложенные папки, переместит мод в папку игры и на лету применит полный комплекс фиксов.",
        "watcher_downloads_dir": "Папка загрузок",
        "watcher_toggle_on": "1. 🟢 Включить фоновый автоустановщик (работает в фоне)",
        "watcher_toggle_off": "2. 🔴 Выключить фоновый автоустановщик",
        "watcher_scan_now": "3. ⚡ Проверить Загрузки прямо сейчас (разовый импорт и фикс)",
        "watcher_recent": "4. 📜 Журнал недавно установленных модов",
        "watcher_back": "0. ↩️ Вернуться в главное меню",

        # Graphics Presets
        "gfx_title": "ОПТИМИЗАТОР ГРАФИКИ И РЕШЕЙДА",
        "gfx_preset_1": "1. Применить 'Ultra-Max-FPS' (Максимальный ультра-графон: 1024px кубмапы, 4x тени + Решейд Ultra Photoreal)",
        "gfx_preset_2": "2. Применить 'Medium-60FPS' (Самая красивая и оптимальная: 60 FPS без фризов + Решейд Medium Optimal)",
        "gfx_preset_3": "3. Применить 'Low-Weak' (Для слабых ПК: оптимизация частиц и теней + Решейд Low Fast)",
        "gfx_preset_4": "4. Применить 'Potato-Ultra-Weak' (Для ультра-слабых / встроек / картошка + Решейд Potato Boost)",
        "gfx_reshade_deploy": "5. 🎨 Установить пресеты Решейда (.ini файлы для ReShade)",
        "gfx_restore": "6. ↩️ Восстановить настройки графики из резервной копии",

        # Messages
        "thanks": "Спасибо за использование GBEAM FIX. Приятной игры!",
        "cancelled": "Операция отменена пользователем.",
        "invalid_opt": "Неверный выбор. Пожалуйста, введите корректный номер.",
    },
}

_CURRENT_LANG = "ru"


def load_config() -> Dict[str, Any]:
    """Load configuration from ~/.beamng_mod_fixer/config.json."""
    if not CONFIG_FILE.exists():
        # Detect system locale if no config exists
        lang = "ru"
        try:
            loc = locale.getdefaultlocale()[0]
            if loc and not loc.lower().startswith("ru"):
                lang = "en"
        except Exception:
            pass

        cfg = dict(DEFAULT_CONFIG)
        cfg["language"] = lang
        save_config(cfg)
        return cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
    except Exception as e:
        logger.debug("Failed reading config: %s", e)
        return dict(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    """Save configuration to ~/.beamng_mod_fixer/config.json atomically."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = CONFIG_FILE.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        tmp_file.replace(CONFIG_FILE)
    except Exception as e:
        logger.debug("Failed saving config: %s", e)


def get_current_language() -> str:
    """Get the active language code ('ru' or 'en')."""
    global _CURRENT_LANG
    return _CURRENT_LANG


def set_language(lang: str) -> None:
    """Set the active language code and persist to config."""
    global _CURRENT_LANG
    norm_lang = "ru" if lang.lower().startswith("ru") else "en"
    _CURRENT_LANG = norm_lang
    cfg = load_config()
    cfg["language"] = norm_lang
    save_config(cfg)


def t(key: str, **kwargs: Any) -> str:
    """Translate a message key into the active language with optional formatting."""
    lang = get_current_language()
    dict_lang = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = dict_lang.get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


# Initialize language from config on module load
try:
    _cfg = load_config()
    _CURRENT_LANG = _cfg.get("language", "ru")
except Exception:
    _CURRENT_LANG = "ru"
