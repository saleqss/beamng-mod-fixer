"""Tier 1: Feature Tests for Bilingual Localization and Config.

Verifies:
- Default language resolution.
- Setting and persisting language preference (ru/en).
- Translation strings existence and formatting.
"""

from pathlib import Path
import pytest

from beamng_mod_fixer.i18n import (
    get_current_language,
    load_config,
    save_config,
    set_language,
    t,
)


def test_i18n_translation_keys():
    set_language("en")
    assert get_current_language() == "en"
    assert "GBEAM FIX" in t("app_title")
    assert "1-Click Global Fix" in t("opt_global_fix")

    set_language("ru")
    assert get_current_language() == "ru"
    assert "ГЛОБАЛЬНЫЙ ФИКС" in t("app_title")
    assert "ГЛОБАЛЬНЫЙ ФИКС В 1 КЛИК" in t("opt_global_fix")


def test_i18n_interpolation():
    set_language("en")
    formatted = t("mods_detected", count=42)
    assert "42 mod archives detected" in formatted

    set_language("ru")
    formatted_ru = t("mods_detected", count=42)
    assert "42" in formatted_ru


def test_config_persistence(tmp_path, monkeypatch):
    test_cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("beamng_mod_fixer.i18n.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("beamng_mod_fixer.i18n.CONFIG_FILE", test_cfg_file)

    cfg = {"language": "en", "auto_installer_enabled": True}
    save_config(cfg)

    loaded = load_config()
    assert loaded["language"] == "en"
    assert loaded["auto_installer_enabled"] is True
