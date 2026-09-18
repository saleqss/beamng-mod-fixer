"""Tier 1: Feature Tests for JBeam Regular Expression Replacement Engine.

Verifies:
- Standard double-quoted "lightCastShadows": true -> false
- Single-quoted 'lightCastShadows': true -> false
- Unquoted lightCastShadows: true -> false (relaxed JSON)
- Whitespace variations (no spaces, extra spaces, tabs, newlines)
- Boolean literal variants (True, TRUE, 1, "true")
- Preservation of inline /* ... */ and trailing // ... comments
- Idempotency on already-false files (no false positive modifications)
- Multi-headlight configurations (low beam, high beam, fog lights)
- Non-lighting JBeam files remain untouched
- Fast pre-check token detection
"""

import pytest
from beamng_mod_fixer.core.jbeam_fixer import (
    detect_light_cast_shadows,
    fix_jbeam_content,
    patch_jbeam_text,
)
from tests.fixtures.factory import (
    SAMPLE_JBEAM_ALREADY_FALSE,
    SAMPLE_JBEAM_BOOLEAN_VARIANTS,
    SAMPLE_JBEAM_MULTIPLE_LIGHTS,
    SAMPLE_JBEAM_NO_LIGHTS,
    SAMPLE_JBEAM_SINGLE_QUOTES,
    SAMPLE_JBEAM_SPACING_VARIANTS,
    SAMPLE_JBEAM_STANDARD_HEADLIGHT,
    SAMPLE_JBEAM_UNQUOTED,
    SAMPLE_JBEAM_WITH_COMMENTS,
)


def test_regex_standard_double_quotes() -> None:
    """Test standard JSON double-quoted keys are replaced accurately."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_STANDARD_HEADLIGHT)
    assert count >= 3
    assert '"lightCastShadows": true' not in fixed
    assert '"lightCastShadows": false' in fixed
    # Ensure sibling properties are intact
    assert '"lightRange": 50' in fixed
    assert '"flareName": "vehicleHeadLightFlare"' in fixed


def test_regex_single_quotes() -> None:
    """Test single-quoted keys and values from informal community mods."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_SINGLE_QUOTES)
    assert count == 1
    assert "'lightCastShadows': true" not in fixed
    assert "'lightCastShadows': false" in fixed


def test_regex_unquoted_key() -> None:
    """Test unquoted keys permitted by BeamNG relaxed C++ parser."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_UNQUOTED)
    assert count == 1
    assert "lightCastShadows: true" not in fixed
    assert "lightCastShadows: false" in fixed


def test_regex_whitespace_variations() -> None:
    """Test various spacing styles: compact, multiple spaces, tabs."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_SPACING_VARIANTS)
    assert count == 4
    # Compact
    assert '"lightCastShadows":false' in fixed
    # Extra space
    assert '"lightCastShadows" : false' in fixed
    # Tabs
    assert '\t"lightCastShadows"\t:\tfalse' in fixed


def test_regex_boolean_literals_case_variants() -> None:
    """Test booleans formatted with Python/Lua True, uppercase TRUE, and strings."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_BOOLEAN_VARIANTS)
    assert count == 4
    assert '"lightCastShadows": false' in fixed
    # None of the old truthy variants remain
    assert "True" not in fixed
    assert "TRUE" not in fixed


def test_regex_comments_preservation() -> None:
    """Test that inline /* */ and trailing // comments are fully preserved."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_WITH_COMMENTS)
    assert count == 1
    assert "// Top level comment" in fixed
    assert "// Headlight row with trailing comment" in fixed
    assert "/* inline comment before key */" in fixed
    assert "/* inline before value */" in fixed
    assert "// comment after value" in fixed
    assert "false" in fixed


def test_regex_idempotency_already_false() -> None:
    """Test that a clean mod with lightCastShadows: false is not modified."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_ALREADY_FALSE)
    assert count == 0
    assert fixed == SAMPLE_JBEAM_ALREADY_FALSE


def test_regex_multiple_spotlights() -> None:
    """Test vehicle with 6 distinct spotlights across low/high/fog assemblies."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_MULTIPLE_LIGHTS)
    assert count == 6
    assert '"lightCastShadows": true' not in fixed
    assert fixed.count('"lightCastShadows": false') == 6


def test_regex_no_lights_jbeam_untouched() -> None:
    """Test that suspension or mechanical JBeams without lights remain untouched."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_NO_LIGHTS)
    assert count == 0
    assert fixed == SAMPLE_JBEAM_NO_LIGHTS


def test_detect_light_cast_shadows_accuracy() -> None:
    """Test quick pre-filter detection function returns boolean correctly."""
    assert detect_light_cast_shadows(SAMPLE_JBEAM_STANDARD_HEADLIGHT) is True
    assert detect_light_cast_shadows(SAMPLE_JBEAM_SINGLE_QUOTES) is True
    assert detect_light_cast_shadows(SAMPLE_JBEAM_UNQUOTED) is True
    assert detect_light_cast_shadows(SAMPLE_JBEAM_ALREADY_FALSE) is False
    assert detect_light_cast_shadows(SAMPLE_JBEAM_NO_LIGHTS) is False


def test_patch_jbeam_text_convenience_helper() -> None:
    """Test patch_jbeam_text returns (patched_text, fix_count) tuple directly."""
    fixed, count = patch_jbeam_text(SAMPLE_JBEAM_STANDARD_HEADLIGHT)
    assert count >= 3
    assert '"lightCastShadows": false' in fixed


def test_regex_inline_dictionary_in_props() -> None:
    """Test inline dictionary within props table."""
    snippet = '["light_R", "n1", "n2", "n3", {"lightRange": 40, "lightCastShadows": true}]'
    fixed, count, _ = fix_jbeam_content(snippet)
    assert count == 1
    assert '{"lightRange": 40, "lightCastShadows": false}' in fixed

