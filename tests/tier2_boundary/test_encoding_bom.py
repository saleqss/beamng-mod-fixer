"""Tier 2: Boundary Tests for Character Encodings & BOM Handling.

Verifies:
- UTF-8 with Byte Order Mark (BOM: \xef\xbb\xbf) decoding, patching, and BOM re-encoding
- Windows-1251 (CP1251 Cyrillic commonly found in Russian BeamNG community mods)
- Windows-1252 (CP1252 Western European with special accents)
- Latin-1 fallback with surrogateescape
- Non-destructive preservation of non-ASCII characters, quotes, and comments
- Empty byte decoding safety
"""

import codecs
import pytest
from beamng_mod_fixer.core.jbeam_fixer import (
    decode_jbeam_bytes,
    encode_jbeam_str,
    fix_jbeam_content,
)


def test_utf8_with_bom_handling() -> None:
    """Test that a JBeam with UTF-8 BOM is decoded properly and re-encoded with BOM."""
    raw_text = '{"spotlights": [["hl", "a", "b", "c", {"lightCastShadows": true}]]}'
    raw_bytes = codecs.BOM_UTF8 + raw_text.encode("utf-8")

    decoded_str, detected_enc = decode_jbeam_bytes(raw_bytes)
    assert detected_enc == "utf-8-sig"
    assert "lightCastShadows" in decoded_str

    fixed_str, count, _ = fix_jbeam_content(decoded_str)
    assert count == 1
    assert '"lightCastShadows": false' in fixed_str

    re_encoded = encode_jbeam_str(fixed_str, detected_enc)
    assert re_encoded.startswith(codecs.BOM_UTF8)
    assert b'"lightCastShadows": false' in re_encoded


def test_cp1251_cyrillic_mod_comments() -> None:
    """Test Russian mod with comments encoded in CP1251 (e.g. VAZ 2107 / Lada)."""
    cyrillic_comment = '// Фары ближнего света ВАЗ 2107 - модификация 2026\n'
    jbeam_body = '{"spotlights": [["hl_ru", "n1", "n2", "n3", {"lightCastShadows": true}]]}'
    full_text = cyrillic_comment + jbeam_body
    raw_bytes = full_text.encode("cp1251")

    decoded_str, detected_enc = decode_jbeam_bytes(raw_bytes)
    assert detected_enc in ("cp1251", "utf-8")
    assert "Фары ближнего света" in decoded_str

    fixed_str, count, _ = fix_jbeam_content(decoded_str)
    assert count == 1
    assert "Фары ближнего света" in fixed_str

    re_encoded = encode_jbeam_str(fixed_str, detected_enc)
    assert b"lightCastShadows\": false" in re_encoded


def test_cp1252_western_european_accents() -> None:
    """Test mod with single-byte accented characters decodes safely and patches shadows."""
    accented_text = '// Spécial: éclairage avant\n{"spotlights": [["hl", "a", "b", "c", {"lightCastShadows": true}]]}'
    raw_bytes = accented_text.encode("cp1252")

    decoded_str, detected_enc = decode_jbeam_bytes(raw_bytes)
    assert isinstance(decoded_str, str)
    assert "lightCastShadows" in decoded_str

    fixed_str, count, _ = fix_jbeam_content(decoded_str)
    assert count == 1
    assert '"lightCastShadows": false' in fixed_str



def test_latin1_surrogateescape_fallback() -> None:
    """Test that arbitrary binary bytes inside comments do not crash decoder."""
    # Invalid UTF-8 and invalid CP1251 byte sequence
    arbitrary_bytes = b'// Random comment: \x81\x8d\x8f \n{"spotlights": [["hl", "a", "b", "c", {"lightCastShadows": true}]]}'

    decoded_str, detected_enc = decode_jbeam_bytes(arbitrary_bytes)
    assert detected_enc in ("cp1251", "cp1252", "latin-1")

    fixed_str, count, _ = fix_jbeam_content(decoded_str)
    assert count == 1
    assert '"lightCastShadows": false' in fixed_str


def test_empty_bytes_decoding() -> None:
    """Test that empty byte stream returns empty string without error."""
    text, enc = decode_jbeam_bytes(b"")
    assert text == ""
    assert enc == "utf-8"


def test_explicit_with_bom_parameter() -> None:
    """Test encode_jbeam_str with explicit with_bom=True parameter."""
    text = '{"test": true}'
    encoded = encode_jbeam_str(text, encoding="utf-8", with_bom=True)
    assert encoded.startswith(codecs.BOM_UTF8)

