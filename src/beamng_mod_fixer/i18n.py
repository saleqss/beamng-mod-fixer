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
        "app_title": "GBEAM FIX - BeamNG.drive Mod & Graphics Fixer",
        "app_subtitle": "Utility for BeamNG.drive 0.30 - 0.34+",
        "system_env": "System & Game Environment",
        "user_dir": "BeamNG Folder",
        "mods_folder": "Mods Folder",
        "settings_folder": "Settings Folder",
        "cache_folder": "Cache / Temp Folder",
        "mods_detected": "{count} mod archives detected",
        "persistent_cache": "Persistent Path Cache",
        "cache_active": "Active",
        "cache_inactive": "Not cached",
        "engine_active": "Engine Status",
        "auto_installer_status": "Auto-Installer",
        "auto_installer_on": "ON (monitoring Downloads)",
        "auto_installer_off": "OFF",

        # Main Menu
        "main_menu_title": "MAIN MENU",
        "opt_global_fix": "1. 🚀 1-Click Global Fix (Headlights + Textures + UI Errors + Physics + Sound + Graphics + Cache)",
        "opt_optics": "2. 💡 Headlights & Lighting (Low/high beam balance, rear light road wash)",
        "opt_materials": "3. 🎨 Textures & Materials (Fix 'NO TEXTURE', convert materials.cs, VFS paths)",
        "opt_drivetrain": "4. ⚙️ Drivetrain & Physics (Unfreeze vehicles, differential & tire pressure fixes)",
        "opt_sound_lua": "5. 🔊 Sound & Lua Scripts (FMOD audio events, vehicle Lua crash prevention)",
        "opt_graphics": "6. 🎮 Graphics & ReShade Presets (Ultra-Max-FPS, 60 FPS Optimal, Low, Potato)",
        "opt_cache": "7. 🧹 Cache Purge (DirectX/Vulkan shaders, temporary binaries)",
        "opt_ui_fixer": "8. 🖥️ UI & Loading Error Fix (Fix 'UI error while loading', clean CEF cache)",
        "opt_audit": "9. 📋 Mod Health Check (Safe non-modifying scan with report)",
        "opt_paths": "P. 📁 BeamNG Directories & Paths (Auto-detection & path validator)",
        "opt_watcher": "W. 📥 Mod Auto-Installer & Downloads Watcher",
        "opt_language": "L. 🌐 Switch Language / Сменить язык (English / Русский)",
        "opt_exit": "0. 🚪 Exit",
        "prompt_choice": "Select an option (default: 1): ",

        # Global Fix Pipeline
        "global_fix_header": "EXECUTING 1-CLICK GLOBAL FIX",
        "global_fix_desc": "Running comprehensive repair and optimization pipeline...",
        "stage_optics": "1. Headlights & Front Lighting",
        "stage_optics_desc": "Selective lowbeam shadow fix, angle alignment, highbeam penetration boost",
        "stage_rear": "2. Rear Lights Calibration",
        "stage_rear_desc": "Eliminates white rear light bug and nuclear red discs with soft road wash",
        "stage_materials": "3. Materials & Texture Repair",
        "stage_materials_desc": "materials.cs to 1.5 JSON, resolves orange NO TEXTURE, reconciles DDS/PNG",
        "stage_drivetrain": "4. Drivetrain & Physics Repair",
        "stage_drivetrain_desc": "Unfreezes differentials, clamps tire pressures, stabilizes suspension",
        "stage_sound": "5. Sound Modernization",
        "stage_sound_desc": "Pre-FMOD audio paths to official BeamNG FMOD sound events",
        "stage_lua": "6. Lua Crash Prevention",
        "stage_lua_desc": "Guards deprecated vehicle Lua calls against runtime crashes",
        "stage_ui": "7. UI Error Fix & info.json Repair",
        "stage_ui_desc": "Neutralizes rogue loading.js overrides, fixes malformed info.json syntax",
        "stage_graphics": "Applying Ultra graphics with high FPS balance...",
        "stage_cache": "Purging compiled DirectX/Vulkan shader binaries and CEF cache in temp/...",
        "pipeline_complete": "All repair and optimization stages completed successfully.",

        # Post-Fix Studio
        "post_fix_title": "1-CLICK GLOBAL FIX RESULTS",
        "post_fix_actions": "POST-FIX ACTIONS:",
        "post_return_main": "1. 🏠 Return to Main Menu (Default)",
        "post_view_diags": "2. 📋 View File Diagnostic Notices",
        "post_launch_graphics": "3. 🎮 Open Graphics & ReShade Studio",
        "post_purge_cache": "4. 🧹 Purge Compiled Shader & CEF Caches",
        "post_exit": "0. 🚪 Exit GBEAM FIX",
        "press_enter_return": "Press Enter to return to Main Menu...",

        # Summary Report Keys
        "rep_scanned": "Mod archives scanned",
        "rep_fixed": "Fixed archives",
        "rep_clean": "Already clean archives",
        "rep_shadows": "Headlight shadows fixed",
        "rep_rear": "Rear lights calibrated",
        "rep_materials_cs": "materials.cs converted",
        "rep_materials_json": "materials.json textures fixed",
        "rep_drivetrain": "Drivetrain & physics repaired",
        "rep_sound": "FMOD audio events modernized",
        "rep_lua": "Vehicle Lua scripts guarded",
        "rep_ui_conflicts": "Rogue UI overrides neutralized",
        "rep_info_json": "Malformed info.json files repaired",
        "rep_graphics": "Graphics & FPS optimization",
        "rep_cache": "Cache purged",
        "rep_junk": "Archive junk files removed",
        "rep_locked": "Skipped (locked / in-use)",
        "rep_corrupt": "Skipped (corrupt)",
        "rep_encrypted": "Skipped (encrypted)",
        "rep_errors": "Errors encountered",
        "rep_elapsed": "Elapsed processing time",

        # UI Fixer Submenu
        "ui_fixer_title": "UI & LOADING ERROR REPAIR",
        "ui_fixer_desc": "Resolves 'UI error while loading. Try launching the game in Safe Mode'. Neutralizes rogue loading.js overrides, fixes corrupt info.json files, unpacks container packs, and purges CEF browser cache.",
        "ui_fix_all": "1. Run Full UI Repair (Neutralize loading.js + fix info.json + unpack containers + clean CEF cache)",
        "ui_fix_rogue": "2. Neutralize Rogue Core UI Overrides (Removes conflicting loading.js from mods)",
        "ui_fix_json": "3. Repair Malformed info.json Files (Fix syntax errors, trailing commas, comments)",
        "ui_unpack_containers": "4. Unpack Container ZIP Archives (Extract nested *.zip mod packs in mods folder)",
        "ui_clean_cef": "5. Purge CEF Browser & UI Caches (temp/ui, temp/cef, temp/cef_cache)",
        "opt_back": "0. Return to Main Menu",

        # Auto-Installer Submenu
        "watcher_title": "MOD AUTO-INSTALLER (DOWNLOADS WATCHER)",
        "watcher_desc": "Monitors your Downloads folder. When you download a BeamNG mod, it automatically unwraps nested folders, moves the archive to your mods directory, and applies all repairs.",
        "watcher_downloads_dir": "Downloads Directory",
        "watcher_toggle_on": "1. 🟢 Start Background Auto-Installer",
        "watcher_toggle_off": "2. 🔴 Stop Background Auto-Installer",
        "watcher_scan_now": "3. ⚡ Scan Downloads Folder Now (One-time import & fix)",
        "watcher_recent": "4. 📜 View Recently Installed Mods Log",
        "watcher_back": "0. ↩️ Return to Main Menu",

        # Graphics Presets
        "gfx_title": "GRAPHICS & RESHADE OPTIMIZER",
        "gfx_preset_1": "1. Deploy 'Ultra-Max-FPS' (Max Ultra visuals, 1024px cubemaps, 4x shadows + ReShade Ultra Photoreal)",
        "gfx_preset_2": "2. Deploy 'Medium-60FPS' (Best visual balance: 60 FPS sweet spot + ReShade Medium Optimal)",
        "gfx_preset_3": "3. Deploy 'Low-Weak' (Entry-level GPUs: reduced particles + ReShade Low Fast)",
        "gfx_preset_4": "4. Deploy 'Potato-Ultra-Weak' (High performance for iGPUs / weak laptops + ReShade Potato Boost)",
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
        "app_subtitle": "Инструмент для BeamNG.drive 0.30 - 0.34+",
        "system_env": "Система и игровое окружение",
        "user_dir": "Папка BeamNG",
        "mods_folder": "Папка модов",
        "settings_folder": "Папка настроек",
        "cache_folder": "Папка кэша / Temp",
        "mods_detected": "Обнаружено архивов модов: {count}",
        "persistent_cache": "Постоянный кэш путей",
        "cache_active": "Активен",
        "cache_inactive": "Не кэширован",
        "engine_active": "Статус движка",
        "auto_installer_status": "Автоустановщик модов",
        "auto_installer_on": "ВКЛЮЧЕН (следит за Загрузками)",
        "auto_installer_off": "ВЫКЛЮЧЕН",

        # Main Menu
        "main_menu_title": "ГЛАВНОЕ МЕНЮ",
        "opt_global_fix": "1. 🚀 ГЛОБАЛЬНЫЙ ФИКС В 1 КЛИК (Фары + Задний свет + Текстуры + Ошибки UI + Физика + Звук + Графика + Кэш)",
        "opt_optics": "2. 💡 Фары и освещение (Ближний, дальний свет, калибровка задних фонарей)",
        "opt_materials": "3. 🎨 Текстуры и материалы (Устранение 'NO TEXTURE', конвертация materials.cs, пути VFS)",
        "opt_drivetrain": "4. ⚙️ Трансмиссия и физика (Разморозка авто, дифференциалы, давление в шинах)",
        "opt_sound_lua": "5. 🔊 Звук и скрипты Lua (FMOD звуки моторов, предотвращение сбоев Lua)",
        "opt_graphics": "6. 🎮 Настройка графики и ReShade (Ultra-Max-FPS, 60FPS-Balanced, Low, Картошка)",
        "opt_cache": "7. 🧹 Очистка кэша (Шейдеры DirectX/Vulkan, временные файлы)",
        "opt_ui_fixer": "8. 🖥️ Исправление ошибок UI и загрузки (Фикс 'UI error while loading', кэш CEF)",
        "opt_audit": "9. 📋 Проверка модов (Безопасное сканирование без изменений)",
        "opt_paths": "P. 📁 Папки и пути BeamNG (Автопоиск по дискам и ручной выбор)",
        "opt_watcher": "W. 📥 Автоустановщик модов из Загрузок",
        "opt_language": "L. 🌐 Сменить язык / Switch Language (Русский / English)",
        "opt_exit": "0. 🚪 Выход",
        "prompt_choice": "Выберите пункт (по умолчанию 1): ",

        # Global Fix Pipeline
        "global_fix_header": "ЗАПУСК ГЛОБАЛЬНОГО ФИКСА В 1 КЛИК",
        "global_fix_desc": "Выполнение комплексной проверки, исправления и оптимизации...",
        "stage_optics": "1. Передняя оптика и фары",
        "stage_optics_desc": "Выборочный фикс ближнего света, углы лучей, пробивающий дальний свет",
        "stage_rear": "2. Калибровка задних фонарей",
        "stage_rear_desc": "Устранение белого света сзади при включении фар и ядовито-красных пятен на асфальте",
        "stage_materials": "3. Материалы и текстуры",
        "stage_materials_desc": "Конвертация materials.cs в 1.5 JSON, устранение оранжевого NO TEXTURE, сверка DDS/PNG",
        "stage_drivetrain": "4. Ремонт трансмиссии и физики",
        "stage_drivetrain_desc": "Разморозка дифференциалов, калибровка давления шин, стабилизация подвески",
        "stage_sound": "5. Модернизация звука",
        "stage_sound_desc": "Перевод устаревших путей звука на звуковые события FMOD BeamNG",
        "stage_lua": "6. Защита скриптов Lua",
        "stage_lua_desc": "Защита устаревших функций Lua от сбоев при появлении машины",
        "stage_ui": "7. Исправление ошибок UI и файлов info.json",
        "stage_ui_desc": "Обезвреживание подмены loading.js, исправление синтаксиса info.json",
        "stage_graphics": "Применение пресета Ultra-Max-FPS (максимальная графика с высоким FPS)...",
        "stage_cache": "Очистка кэша шейдеров DirectX/Vulkan и браузера CEF в temp/...",
        "pipeline_complete": "Все этапы проверки, исправления и оптимизации успешно завершены.",

        # Post-Fix Studio
        "post_fix_title": "РЕЗУЛЬТАТЫ ГЛОБАЛЬНОГО ФИКСА",
        "post_fix_actions": "ДЕЙСТВИЯ ПОСЛЕ ФИКСА:",
        "post_return_main": "1. 🏠 Вернуться в главное меню (По умолчанию)",
        "post_view_diags": "2. 📋 Просмотреть подробный журнал изменений",
        "post_launch_graphics": "3. 🎮 Открыть меню настройки графики и ReShade",
        "post_purge_cache": "4. 🧹 Очистить кэш шейдеров и браузера CEF",
        "post_exit": "0. 🚪 Выйти из GBEAM FIX",
        "press_enter_return": "Нажмите Enter для возврата в главное меню...",

        # Summary Report Keys
        "rep_scanned": "Всего просканировано архивов модов",
        "rep_fixed": "Исправлено архивов",
        "rep_clean": "Уже чистых (без ошибок) архивов",
        "rep_shadows": "Исправлено теней фар (lightCastShadows)",
        "rep_rear": "Откалибровано освещение задних фонарей",
        "rep_materials_cs": "Сконвертировано materials.cs в JSON 1.5",
        "rep_materials_json": "Исправлено текстур в materials.json",
        "rep_drivetrain": "Исправлено узлов трансмиссии и физики",
        "rep_sound": "Модернизировано звуков на FMOD события",
        "rep_lua": "Защищено от вылетов скриптов Lua",
        "rep_ui_conflicts": "Устранено конфликтов файлов UI (loading.js)",
        "rep_info_json": "Исправлено синтаксических ошибок в info.json",
        "rep_graphics": "Оптимизация графики и FPS",
        "rep_cache": "Очистка кэша шейдеров и CEF",
        "rep_junk": "Удалено мусорных файлов из архивов",
        "rep_locked": "Пропущено (заблокировано игрой)",
        "rep_corrupt": "Пропущено (поврежденный архив)",
        "rep_encrypted": "Пропущено (с паролем)",
        "rep_errors": "Ошибок при обработке",
        "rep_elapsed": "Время выполнения операции",

        # UI Fixer Submenu
        "ui_fixer_title": "ИСПРАВЛЕНИЕ ОШИБОК UI И ЭКРАНА ЗАГРУЗКИ",
        "ui_fixer_desc": "Устраняет ошибку 'UI error while loading. Try launching the game in Safe Mode'. Обезвреживает конфликтующие loading.js в модах, исправляет синтаксис info.json, распаковывает вложенные ZIP-контейнеры и очищает кэш браузера CEF.",
        "ui_fix_all": "1. Запустить полный фикс UI (Обезвредить loading.js + починить info.json + распаковать контейнеры + очистить кэш CEF)",
        "ui_fix_rogue": "2. Обезвредить системные файлы UI (Удалить конфликтующие loading.js из модов)",
        "ui_fix_json": "3. Исправить синтаксис info.json (Устранить висячие запятые, пропущенные кавычки, комментарии)",
        "ui_unpack_containers": "4. Распаковать архивы-контейнеры (Извлечь вложенные *.zip из модов-паков)",
        "ui_clean_cef": "5. Очистить кэш браузера CEF и UI (temp/ui, temp/cef, temp/cef_cache)",
        "opt_back": "0. Вернуться в главное меню",

        # Auto-Installer Submenu
        "watcher_title": "АВТОУСТАНОВЩИК МОДОВ И ЗАГРУЗКИ",
        "watcher_desc": "Следит за папкой Загрузки. При скачивании любого мода для BeamNG скрипт распакует вложенные папки, переместит архив в папку модов и применит все исправления.",
        "watcher_downloads_dir": "Папка загрузок",
        "watcher_toggle_on": "1. 🟢 Включить фоновый автоустановщик",
        "watcher_toggle_off": "2. 🔴 Выключить фоновый автоустановщик",
        "watcher_scan_now": "3. ⚡ Проверить Загрузки прямо сейчас (разовый импорт и фикс)",
        "watcher_recent": "4. 📜 Журнал недавно установленных модов",
        "watcher_back": "0. ↩️ Вернуться в главное меню",

        # Graphics Presets
        "gfx_title": "ОПТИМИЗАТОР ГРАФИКИ И RESHADE",
        "gfx_preset_1": "1. Применить 'Ultra-Max-FPS' (Максимальная графика: 1024px кубмапы, 4x тени + ReShade Ultra Photoreal)",
        "gfx_preset_2": "2. Применить 'Medium-60FPS' (Оптимальный баланс: 60 FPS без фризов + ReShade Medium Optimal)",
        "gfx_preset_3": "3. Применить 'Low-Weak' (Для слабых ПК: оптимизация частиц и теней + ReShade Low Fast)",
        "gfx_preset_4": "4. Применить 'Potato-Ultra-Weak' (Для слабых ноутбуков и встроенных видеокарт + ReShade Potato Boost)",
        "gfx_reshade_deploy": "5. 🎨 Установить пресеты ReShade (.ini файлы)",
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
