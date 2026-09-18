"""Tier 5 Adversarial & Stress Test Suite for Milestone 1: Core JBeam & Optics Engine.

Verifies:
1. Multi-encoding handling (UTF-8 BOM, standard UTF-8, CP1251 Russian Cyrillic, Latin-1 fallback, roundtrips)
2. flareName variations ("none", "null", "None", empty strings, valid flares, prefix/suffix edge cases)
3. Cookie texture audit (missing local files, path normalization, obsolete Torque3D paths, base-game exclusions)
4. Malformed spotlight structures (syntax errors, empty arrays, unclosed brackets, inverted angles, truncated rows)
5. Exception hierarchy correctness (inheritance, polymorphism, string formatting, aliases)
"""

import codecs
import pytest
from pathlib import Path
from typing import Set

import beamng_mod_fixer as bmf
from beamng_mod_fixer.core.jbeam_fixer import (
    FAST_SHADOW_CHECK,
    audit_spotlights,
    decode_jbeam_bytes,
    detect_light_cast_shadows,
    encode_jbeam_str,
    fix_jbeam_content,
    patch_jbeam_text,
)
from beamng_mod_fixer.exceptions import (
    ArchiveCorruptedError,
    ArchiveEncryptedError,
    ArchiveLockedError,
    ArchivePermissionError,
    BeamNGModFixerError,
    BeamNGPathNotFoundError,
    CacheCleanError,
    CorruptArchiveError,
    EncryptedArchiveWarning,
    GameRunningWarning,
    JBeamError,
    JBeamSyntaxError,
    JBeamSyntaxWarning,
    ModArchiveError,
    PasswordProtectedArchiveError,
    SettingsCorruptedError,
    SettingsError,
    SettingsNotFoundError,
)
from beamng_mod_fixer.models import (
    DiagnosticNotice,
    JBeamFixResult,
    ModArchiveReport,
    ModStatus,
    OptimizationResult,
    OverallSummary,
)


# ==============================================================================
# 1. Multi-Encoding Adversarial Tests
# ==============================================================================

class TestMultiEncodingAdversarial:
    """Stress-test byte decoding, encoding, and roundtrips across international character sets."""

    def test_utf8_with_bom_decoding_and_roundtrip(self):
        """Verify UTF-8 with BOM (utf-8-sig) is correctly stripped and roundtripped."""
        raw_jbeam = '{\n  "name": "Тестовая Машина",\n  "lightCastShadows": true\n}'
        encoded = codecs.BOM_UTF8 + raw_jbeam.encode("utf-8")

        # Decode
        decoded_text, detected_enc = decode_jbeam_bytes(encoded)
        assert detected_enc == "utf-8-sig"
        assert not decoded_text.startswith("\ufeff"), "BOM must be stripped from decoded text"
        assert "Тестовая Машина" in decoded_text

        # Fix content
        fixed_text, count, _ = fix_jbeam_content(decoded_text)
        assert count == 1
        assert '"lightCastShadows": false' in fixed_text

        # Re-encode with detected encoding
        re_encoded = encode_jbeam_str(fixed_text, detected_enc)
        assert re_encoded.startswith(codecs.BOM_UTF8), "Re-encoded byte stream must retain UTF-8 BOM"
        assert b'"lightCastShadows": false' in re_encoded

        # Re-encode with with_bom=True explicitly
        re_encoded_explicit = encode_jbeam_str(fixed_text, "utf-8", with_bom=True)
        assert re_encoded_explicit.startswith(codecs.BOM_UTF8)

    def test_standard_utf8_multilingual(self):
        """Verify standard UTF-8 handles Cyrillic, CJK, German umlauts, and emojis."""
        text = (
            '// Комментарий на русском: Основные фары\n'
            '// 日本語コメント: ヘッドライト\n'
            '// Äpfel, Öl, Überholen 🚗💡\n'
            '{\n  "lightCastShadows": true\n}'
        )
        data = text.encode("utf-8")
        decoded, enc = decode_jbeam_bytes(data)
        assert enc == "utf-8"
        assert decoded == text

        fixed, cnt, _ = fix_jbeam_content(decoded)
        assert cnt == 1
        assert "🚗💡" in fixed
        assert "日本語コメント" in fixed
        assert "Основные фары" in fixed

    def test_cp1251_russian_cyrillic_mod_support(self):
        """Verify CP1251 (Windows-1251) decoding commonly used in CIS community mods."""
        # Cyrillic text in Windows-1251 containing bytes invalid in strict UTF-8
        cyrillic_comment = "// Фары ВАЗ-2107 передние (свет и тени)"
        jbeam_body = f'{cyrillic_comment}\n{{"name": "vaz2107", "lightCastShadows": true}}'
        data = jbeam_body.encode("cp1251")

        # Ensure these raw bytes fail strict UTF-8 decode
        with pytest.raises(UnicodeDecodeError):
            data.decode("utf-8")

        # Decoder must automatically detect and decode cp1251
        decoded, enc = decode_jbeam_bytes(data)
        assert enc == "cp1251"
        assert cyrillic_comment in decoded
        assert '"lightCastShadows": true' in decoded

        # Patching must succeed without corrupting Cyrillic characters
        fixed, count, _ = fix_jbeam_content(decoded)
        assert count == 1
        assert '"lightCastShadows": false' in fixed

        # Encode back to cp1251
        re_encoded = encode_jbeam_str(fixed, enc)
        assert re_encoded.decode("cp1251") == fixed

    def test_latin1_and_cp1252_fallback(self):
        """Verify byte combinations invalid in both UTF-8 and CP1251 gracefully fall back."""
        # 0x98 is undefined in CP1251; 0x81 is undefined in CP1252. Together they trigger Latin-1.
        adversarial_bytes = b'{"name": "test\x98\x81", "lightCastShadows": true}'
        decoded, enc = decode_jbeam_bytes(adversarial_bytes)
        assert enc in ("cp1252", "latin-1")
        assert "lightCastShadows" in decoded

        fixed, cnt, _ = fix_jbeam_content(decoded)
        assert cnt == 1
        assert '"lightCastShadows": false' in fixed

    def test_empty_and_null_bytes(self):
        """Verify decoder handles empty bytes and null bytes safely."""
        empty_text, enc = decode_jbeam_bytes(b"")
        assert empty_text == ""
        assert enc == "utf-8"

        null_text, enc = decode_jbeam_bytes(b"\x00\x00")
        assert null_text == "\x00\x00"

    def test_encode_jbeam_str_unsupported_encoding_fallback(self):
        """Verify encode_jbeam_str falls back to utf-8 when given invalid or incompatible encoding."""
        text = "Hello 🚗"
        # Emoji cannot be encoded in cp1251 or ascii
        res = encode_jbeam_str(text, encoding="cp1251")
        assert res == text.encode("utf-8")

        # Non-existent codec
        res_bogus = encode_jbeam_str(text, encoding="non_existent_codec_xyz")
        assert res_bogus == text.encode("utf-8")


# ==============================================================================
# 2. flareName Adversarial Tests
# ==============================================================================

class TestFlareNameAdversarial:
    """Adversarial testing of flareName detection, normalization, and false-positive resistance."""

    @pytest.mark.parametrize("bad_val", [
        '"none"',
        '"None"',
        '"NONE"',
        '"null"',
        '"Null"',
        '"NULL"',
        'null',
        'none',
        '"undefined"',
        'undefined',
    ])
    def test_invalid_flare_names_normalized(self, bad_val):
        """All variations of 'none', 'null', and 'undefined' must normalize to empty string."""
        raw = f'{{"flareName": {bad_val}, "lightCastShadows": false}}'
        fixed, count, diags = fix_jbeam_content(raw, normalize_optics=True)
        assert '"flareName": ""' in fixed
        assert any(d.rule == "flare_name_normalized" for d in diags)

    @pytest.mark.parametrize("valid_flare", [
        '""',
        '"headlight_flare"',
        '"spotlight_headlight_01"',
        '"lens_flare_clean"',
        '"none_flare"',       # Starts with 'none' but is a valid identifier
        '"null_pointer_flare"',# Starts with 'null' but is a valid identifier
        '"my_flare_none"',    # Ends with 'none'
        '"my_flare_null"',    # Ends with 'null'
    ])
    def test_valid_flare_names_unmodified(self, valid_flare):
        """Valid flare names and already-empty strings must NEVER be touched."""
        raw = f'{{"flareName": {valid_flare}, "lightCastShadows": false}}'
        fixed, count, diags = fix_jbeam_content(raw, normalize_optics=True)
        assert fixed == raw, f"Valid flare {valid_flare} was improperly modified!"
        assert not any(d.rule == "flare_name_normalized" for d in diags)

    def test_flare_normalization_disabled(self):
        """When normalize_optics=False, flareName is NOT altered, but audit reports it."""
        raw = '{"flareName": "none", "lightCastShadows": true}'
        fixed, count, diags = fix_jbeam_content(raw, normalize_optics=False)
        assert count == 1
        assert '"lightCastShadows": false' in fixed
        assert '"flareName": "none"' in fixed  # Untouched

        # Diagnostics through direct audit
        audited = audit_spotlights(raw)
        assert any(d.rule == "flare_name_invalid" for d in audited)

    def test_flare_normalization_marks_jbeam_fix_result_modified(self):
        """Normalizing flareName even with 0 shadow fixes marks JBeamFixResult as modified."""
        raw = '{"flareName": "none", "lightCastShadows": false}'
        fixed, count, diags = fix_jbeam_content(raw, normalize_optics=True)
        assert count == 0
        assert fixed != raw

        res = JBeamFixResult(content=fixed, fix_count=count, diagnostics=diags)
        assert res.modified is True
        assert res.has_fixes is True


# ==============================================================================
# 3. Cookie Textures Adversarial Tests
# ==============================================================================

class TestCookieTexturesAdversarial:
    """Stress-test cookie texture auditing, path normalization, and obsolete path detection."""

    def test_obsolete_art_shapes_lights_paths(self):
        """Pre-PBR Torque3D cookie paths (art/shapes/lights/...) must emit obsolete warning."""
        raw = '{"cookieName": "art/shapes/lights/headlight_cookie.dds"}'
        diags = audit_spotlights(raw)
        assert any(d.rule == "cookie_path_obsolete" for d in diags)
        msg = next(d.message for d in diags if d.rule == "cookie_path_obsolete")
        assert "art/special/" in msg

    def test_modern_art_special_paths_clean(self):
        """Modern BeamNG cookies under art/special/ must NOT be flagged as missing."""
        raw = '{"cookieName": "art/special/BNG_light_cookie_headlight.png"}'
        available_files: Set[str] = {"vehicles/my_car/body.jbeam"}
        diags = audit_spotlights(raw, available_files=available_files)
        assert not any(d.rule == "cookie_file_missing" for d in diags)
        assert not any(d.rule == "cookie_path_obsolete" for d in diags)

    def test_missing_local_cookie_texture(self):
        """Local vehicle cookies not present in the archive must emit cookie_file_missing."""
        raw = '{"cookieName": "vehicles/my_car/headlight_mask.png"}'
        # Archive only has the jbeam, missing the png texture
        available_files = {"vehicles/my_car/my_car.jbeam"}
        diags = audit_spotlights(raw, filename="my_car.jbeam", available_files=available_files)
        assert any(d.rule == "cookie_file_missing" for d in diags)

    def test_case_insensitive_backslash_cookie_resolution(self):
        """Windows backslashes and case differences must match without false-positive missing warnings."""
        raw = '{"cookieName": "vehicles/super_car/textures/glass_cookie.dds"}'
        # Archive has Windows-style backslashes and uppercase letters
        available_files = {
            "Vehicles\\SUPER_CAR\\Textures\\GLASS_COOKIE.DDS",
            "vehicles/super_car/super_car.jbeam",
        }
        diags = audit_spotlights(raw, available_files=available_files)
        assert not any(d.rule == "cookie_file_missing" for d in diags)

    def test_lua_expression_cookie_ignored(self):
        """Dynamic Lua expressions (e.g. $cookiePath) must not trigger missing texture warnings."""
        raw = '{"cookieName": "$cookiePattern"}'
        available_files = {"vehicles/my_car/my_car.jbeam"}
        diags = audit_spotlights(raw, available_files=available_files)
        assert not any(d.rule == "cookie_file_missing" for d in diags)

    def test_invalid_cookie_normalization(self):
        """cookieName with 'none' or 'null' must normalize to empty string."""
        raw = '{"cookieName": "none", "lightCastShadows": false}'
        fixed, count, diags = fix_jbeam_content(raw, normalize_optics=True)
        assert '"cookieName": ""' in fixed
        assert any(d.rule == "cookie_name_normalized" for d in diags)


# ==============================================================================
# 4. Malformed Spotlight Structures Adversarial Tests
# ==============================================================================

class TestMalformedSpotlightsAdversarial:
    """Stress-test corrupted spotlight blocks, unclosed syntax, and invalid angles."""

    def test_inverted_and_negative_spotlight_angles(self):
        """Angles where inner > outer or negative values must be detected."""
        inverted_raw = '{"lightInnerAngle": 65, "lightOuterAngle": 40}'
        diags_inverted = audit_spotlights(inverted_raw)
        assert any(d.rule == "spotlight_angle_inverted" for d in diags_inverted)

        negative_raw = '{"lightInnerAngle": -15, "lightOuterAngle": 45}'
        diags_negative = audit_spotlights(negative_raw)
        assert any(d.rule == "spotlight_angle_invalid" for d in diags_negative)

    def test_empty_and_valid_spotlight_arrays(self):
        """Empty spotlight arrays or valid 4+ element definitions must pass cleanly."""
        empty_raw = '{"spotlights": []}'
        assert len(audit_spotlights(empty_raw)) == 0

        valid_raw = (
            '{"spotlights": [\n'
            '    ["type", "node1", "node2", "node3"],\n'
            '    ["headlight_L", "n1", "n2", "n3", {"lightInnerAngle": 20, "lightOuterAngle": 40}]\n'
            ']}'
        )
        assert len(audit_spotlights(valid_raw)) == 0

    def test_malformed_spotlight_rows_fewer_than_four_elements(self):
        """Spotlight rows with fewer than 4 elements (excluding header) must emit warning."""
        malformed_raw = (
            '{"spotlights": [\n'
            '    ["type", "node1", "node2", "node3"],\n'
            '    ["headlight_L", "n1"]\n'
            ']}'
        )
        diags = audit_spotlights(malformed_raw)
        assert any(d.rule == "spotlight_row_malformed" for d in diags)

    def test_unclosed_brackets_and_syntax_havoc(self):
        """Corrupted, truncated JBeam with unclosed brackets must NOT crash the auditor."""
        chaos = '{"spotlights": [ [ "incomplete", "node", '
        diags = audit_spotlights(chaos)
        assert isinstance(diags, list)

        # Truncated string with lightCastShadows
        fixed, cnt, _ = fix_jbeam_content(chaos + '"lightCastShadows": true')
        assert cnt == 1
        assert '"lightCastShadows": false' in fixed


# ==============================================================================
# 5. Exception Hierarchy & Dataclass Adversarial Tests
# ==============================================================================

class TestExceptionHierarchyAdversarial:
    """Stress-test exception hierarchy inheritance, polymorphism, and aliases."""

    @pytest.mark.parametrize("exc_class", [
        ModArchiveError,
        CorruptArchiveError,
        ArchiveCorruptedError,
        ArchiveLockedError,
        PasswordProtectedArchiveError,
        ArchiveEncryptedError,
        ArchivePermissionError,
        JBeamError,
        JBeamSyntaxError,
        SettingsError,
        SettingsNotFoundError,
        SettingsCorruptedError,
        BeamNGPathNotFoundError,
        CacheCleanError,
    ])
    def test_all_custom_exceptions_inherit_from_base(self, exc_class):
        """Every domain exception must inherit from BeamNGModFixerError and Exception."""
        assert issubclass(exc_class, BeamNGModFixerError)
        assert issubclass(exc_class, Exception)

    def test_archive_aliases(self):
        """Ensure backward/alternative compatibility aliases point to canonical classes."""
        assert ArchiveCorruptedError is CorruptArchiveError
        assert ArchiveEncryptedError is PasswordProtectedArchiveError

    def test_warnings_multi_inheritance(self):
        """Warnings must inherit from both UserWarning and BeamNGModFixerError."""
        assert issubclass(JBeamSyntaxWarning, UserWarning)
        assert issubclass(JBeamSyntaxWarning, BeamNGModFixerError)
        assert issubclass(EncryptedArchiveWarning, UserWarning)
        assert issubclass(EncryptedArchiveWarning, BeamNGModFixerError)
        assert issubclass(GameRunningWarning, UserWarning)

    def test_polymorphic_exception_catching(self):
        """Catching BeamNGModFixerError must catch all specialized exceptions."""
        def raise_locked():
            raise ArchiveLockedError("Archive is locked by BeamNG", details="WinError 32")

        with pytest.raises(BeamNGModFixerError) as exc_info:
            raise_locked()

        err = exc_info.value
        assert "Archive is locked by BeamNG" in str(err)
        assert "Details: WinError 32" in str(err)

    def test_models_serialization_and_contracts(self):
        """Verify models can convert to dict and satisfy all schema contracts."""
        notice = DiagnosticNotice(severity="warning", message="test notice", rule="rule_1")
        assert notice.to_dict() == {
            "severity": "warning",
            "message": "test notice",
            "file_path": "",
            "line_number": None,
            "rule": "rule_1",
        }

        report = ModArchiveReport(archive_path=Path("mods/car.zip"), status=ModStatus.FIXED.value)
        assert report.is_success is True
        assert report.to_dict()["status"] == "fixed"

        summary = OverallSummary(
            total_scanned=10,
            modified_archives=3,
            skipped_locked=1,
            skipped_corrupt=1,
            skipped_encrypted=1,
        )
        assert summary.total_skipped == 3
        assert summary.to_dict()["total_scanned"] == 10


# ==============================================================================
# 6. Regex Engine Precision & Edge Cases
# ==============================================================================

class TestRegexPrecisionAdversarial:
    """Stress-test regex engine with extreme variations, whitespace, and comments."""

    @pytest.mark.parametrize("raw_input,expected_output", [
        # Standard unquoted
        ('lightCastShadows: true', 'lightCastShadows: false'),
        # Double quotes
        ('"lightCastShadows": true', '"lightCastShadows": false'),
        # Single quotes
        ("'lightCastShadows': true", "'lightCastShadows': false"),
        # Backtick quotes
        ('`lightCastShadows`: true', '`lightCastShadows`: false'),
        # Mixed case
        ('LIGHTCASTSHADOWS: true', 'LIGHTCASTSHADOWS: false'),
        ('LightCastShadows: True', 'LightCastShadows: false'),
        # String true
        ('"lightCastShadows": "true"', '"lightCastShadows": false'),
        ("'lightCastShadows': 'true'", "'lightCastShadows': false"),
        # Numeric 1
        ('"lightCastShadows": 1', '"lightCastShadows": false'),
        ('"lightCastShadows": "1"', '"lightCastShadows": false'),
        # Spaces and tabs
        ('"lightCastShadows"  \t: \t  true', '"lightCastShadows"  \t: \t  false'),
        # Inline comments between colon and value
        ('"lightCastShadows": /* enable shadow */ true', '"lightCastShadows": /* enable shadow */ false'),
        # Trailing comma preserved
        ('"lightCastShadows": true,', '"lightCastShadows": false,'),
    ])
    def test_regex_variations(self, raw_input, expected_output):
        fixed, count = patch_jbeam_text(raw_input)
        assert count == 1
        assert fixed == expected_output

    def test_idempotency_already_false_unmodified(self):
        """Files where lightCastShadows is already false must NOT be modified."""
        clean = '{\n  "lightCastShadows": false,\n  "lightCastShadows": "false",\n  "lightCastShadows": 0\n}'
        assert detect_light_cast_shadows(clean) is False
        fixed, count, _ = fix_jbeam_content(clean)
        assert count == 0
        assert fixed is clean  # Exact object identity preserved
