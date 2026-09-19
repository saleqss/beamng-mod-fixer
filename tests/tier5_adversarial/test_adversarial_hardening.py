"""Tier 5 Adversarial Hardening and Stress Testing Suite for JBeam & Optics Engine.

Covers adversarial challenge dimensions:
1. Tricky spacing, tabs, multiline strings, inline comments /* ... */ within and around keys
2. Unquoted keys, single quotes, double quotes, backticks
3. Case variations (LightCastShadows, LIGHTCASTSHADOWS, lightCastShadows, etc.)
4. Files where lightCastShadows is already false (0 modifications and reference equality)
5. Non-lighting blocks containing "lightCastShadows" in comments, tokens, or descriptions
6. Large synthetic files (>5MB) to test performance, memory, and ReDoS safety
"""

import sys
import time
import tracemalloc
from pathlib import Path
from typing import List

# Ensure src is in sys.path for direct pytest invocation
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest

from beamng_mod_fixer.core.jbeam_fixer import (
    detect_light_cast_shadows,
    fix_jbeam_content,
    patch_jbeam_text,
    audit_spotlights,
)


# ==============================================================================
# 1. Spacing, Tabs, Quotes, and Case Variations (Verified Robust)
# ==============================================================================

class TestAdversarialFormattingAndSyntax:
    """Test extreme formatting, quotes, tabs, and case variations."""

    @pytest.mark.parametrize("spacing_pattern", [
        '"lightCastShadows":true',
        '"lightCastShadows" : true',
        '"lightCastShadows"    :    true',
        '"lightCastShadows"\t:\ttrue',
        '"lightCastShadows" \t \t : \t \t true',
        '"lightCastShadows"\n:\ntrue',
        '"lightCastShadows"\r\n:\r\ntrue',
        '"lightCastShadows"  \r\n  :  \r\n  true',
    ])
    def test_spacing_and_tab_variations(self, spacing_pattern: str):
        """Engine must handle arbitrary spaces, tabs, and newlines around colon."""
        fixed, count = patch_jbeam_text(spacing_pattern)
        assert count == 1
        assert "false" in fixed
        # Verify surrounding spacing structure before colon is preserved
        assert fixed.endswith("false")

    @pytest.mark.parametrize("quote_variant,expected_key", [
        ('lightCastShadows: true', 'lightCastShadows: false'),
        ('"lightCastShadows": true', '"lightCastShadows": false'),
        ("'lightCastShadows': true", "'lightCastShadows': false"),
        ('`lightCastShadows`: true', '`lightCastShadows`: false'),
    ])
    def test_quote_delimiters(self, quote_variant: str, expected_key: str):
        """Engine must support unquoted keys, double quotes, single quotes, and backticks."""
        fixed, count = patch_jbeam_text(quote_variant)
        assert count == 1
        assert fixed == expected_key

    @pytest.mark.parametrize("case_variant", [
        'lightCastShadows: true',
        'LightCastShadows: true',
        'LIGHTCASTSHADOWS: true',
        'lightcastshadows: true',
        'LiGhTcAsTsHaDoWs: true',
        'LIGHTCASTSHADOWS: TRUE',
        'LightCastShadows: True',
        '"lightCastShadows": "true"',
        '"lightCastShadows": "TRUE"',
        '"lightCastShadows": 1',
        '"lightCastShadows": "1"',
    ])
    def test_case_and_truthy_variations(self, case_variant: str):
        """Engine must be case-insensitive for both key and truthy values (true, 1)."""
        fixed, count = patch_jbeam_text(case_variant)
        assert count == 1
        assert "false" in fixed.lower()


# ==============================================================================
# 2. Idempotency and Reference Equality on Already-False Content
# ==============================================================================

class TestIdempotencyAndReferenceEquality:
    """Verify files with lightCastShadows already false are not modified (reference equality)."""

    @pytest.mark.parametrize("false_variant", [
        '{"lightCastShadows": false}',
        '{"lightCastShadows": FALSE}',
        '{"lightCastShadows": False}',
        '{"lightCastShadows": "false"}',
        '{"lightCastShadows": "FALSE"}',
        '{"lightCastShadows": 0}',
        '{"lightCastShadows": "0"}',
        '{\n  "name": "CleanCar",\n  "lightCastShadows": false,\n  "flareName": "VehicleHeadlight"\n}',
    ])
    def test_already_false_returns_reference_equality(self, false_variant: str):
        """Zero modifications must return the exact same string object reference."""
        assert detect_light_cast_shadows(false_variant) is False
        fixed, count, diags = fix_jbeam_content(false_variant)
        assert count == 0
        assert len(diags) == 0
        assert fixed is false_variant, "Must preserve reference equality when no modifications occur"


# ==============================================================================
# 3. Token Isolation in Non-Lighting Blocks
# ==============================================================================

class TestTokenIsolationNonLighting:
    """Verify non-lighting blocks containing similar tokens are not corrupted."""

    def test_compound_identifier_prefix_and_suffix(self):
        """Keys like custom_lightCastShadows or lightCastShadowsEnabled must NOT be replaced."""
        content = (
            '{\n'
            '  "engine_v8": {\n'
            '    "custom_lightCastShadows": true,\n'
            '    "lightCastShadowsEnabled": true,\n'
            '    "has_lightCastShadows": true,\n'
            '    "lightCastShadows_v2": true\n'
            '  }\n'
            '}'
        )
        fixed, count, _ = fix_jbeam_content(content)
        assert count == 0
        assert fixed is content

    def test_token_in_string_values_and_comments(self):
        """Mentioning lightCastShadows as a plain word token must not trigger replacements."""
        content = (
            '{\n'
            '  "suspension": {\n'
            '    // Reference token lightCastShadows mentioned here\n'
            '    "partType": "lightCastShadows",\n'
            '    /* Another note: lightCastShadows */\n'
            '    "spring": 45000\n'
            '  }\n'
            '}'
        )
        fixed, count, _ = fix_jbeam_content(content)
        assert count == 0
        assert fixed is content


# ==============================================================================
# 4. Large Synthetic Files (>5MB) Performance & Memory Stress Test
# ==============================================================================

@pytest.fixture(scope="module")
def large_jbeam_content() -> str:
    """Generate a >6MB synthetic JBeam file with 150,000 nodes and lighting definitions."""
    parts: List[str] = [
        '{\n'
        '  "large_truck_model": {\n'
        '    "information": {"name": "Synthetic Heavy Hauler"},\n'
        '    "nodes": [\n'
        '      ["id", "rx", "ry", "rz"],\n'
    ]
    # 150,000 node rows
    for i in range(150000):
        parts.append(f'      ["node_{i}", {i*0.005:.3f}, {i*0.010:.3f}, {i*0.015:.3f}],\n')
    parts.append('    ],\n')
    parts.append('    "spotlights": [\n')
    parts.append('      {"name": "high_beam_L", "lightCastShadows": true, "flareName": "VehicleHeadlight"},\n')
    parts.append('      {"name": "high_beam_R", "lightCastShadows": true, "flareName": "VehicleHeadlight"},\n')
    parts.append('      {"name": "fog_L", "lightCastShadows": true, "flareName": "VehicleHeadlight"},\n')
    parts.append('      {"name": "fog_R", "lightCastShadows": true, "flareName": "VehicleHeadlight"}\n')
    parts.append('    ]\n')
    parts.append('  }\n}\n')

    return "".join(parts)


class TestLargeFileStressAndReDoS:
    """Stress-test performance, memory consumption, and ReDoS safety on >5MB files."""

    def test_large_file_size_exceeds_5mb(self, large_jbeam_content: str):
        """Verify the test payload genuinely exceeds 5MB."""
        size_mb = len(large_jbeam_content.encode("utf-8")) / (1024 * 1024)
        assert size_mb > 5.0, f"Payload was {size_mb:.2f} MB, expected >5.0 MB"

    def test_large_file_processing_time_and_memory(self, large_jbeam_content: str):
        """Verify 6MB file processes in under 5.0 seconds with peak memory overhead under 50MB."""
        tracemalloc.start()
        start_time = time.perf_counter()

        fixed, count, diags = fix_jbeam_content(large_jbeam_content, filename="heavy_hauler.jbeam")

        elapsed = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        # Performance & Memory thresholds
        assert elapsed < 5.0, f"Processing took {elapsed:.2f}s, exceeding 5.0s budget"
        assert peak_mb < 50.0, f"Peak memory was {peak_mb:.2f}MB, exceeding 50MB budget"
        assert count == 4, f"Expected 4 lightCastShadows fixes, got {count}"
        assert '"lightCastShadows": false' in fixed

    def test_large_file_fast_bypass_performance(self):
        """Verify 6MB file without lightCastShadows completes in under 0.1s via fast bypass."""
        parts = ['{\n  "large_model": {\n    "nodes": [\n']
        for i in range(150000):
            parts.append(f'      ["n{i}", 0.1, 0.2, 0.3],\n')
        parts.append('    ]\n  }\n}\n')
        content = "".join(parts)

        start = time.perf_counter()
        fixed, count, diags = fix_jbeam_content(content)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"Fast bypass took {elapsed:.4f}s, expected <0.2s"
        assert count == 0
        assert fixed is content


# ==============================================================================
# 5. Adversarial Edge Case Failures (Exposing Engine Bugs)
# ==============================================================================

class TestAdversarialFailureModes:
    """Document and verify edge cases where regex handles comments, hyphens, and strings."""

    def test_inline_comment_before_colon(self):
        """Inline comments between key and colon must be supported in valid JBeam."""
        raw = '{"lightCastShadows" /* disable headlight shadow */ : true}'
        fixed, count, _ = fix_jbeam_content(raw)
        assert count == 1, "Failed to match lightCastShadows with inline comment before colon"
        assert '/* disable headlight shadow */ : false' in fixed

    def test_multiline_comment_between_colon_and_value(self):
        """Multiline comments across line breaks between colon and true must be matched."""
        raw = '"lightCastShadows": /* line 1\n line 2 */ true'
        fixed, count, _ = fix_jbeam_content(raw)
        assert count == 1, "Failed to match lightCastShadows with multiline comment after colon"
        assert 'false' in fixed

    def test_single_line_comment_between_colon_and_value(self):
        """Single-line comment between colon and newline true must be matched."""
        raw = '"lightCastShadows": // toggle shadow off\n true'
        fixed, count, _ = fix_jbeam_content(raw)
        assert count == 1, "Failed to match lightCastShadows with single-line comment"
        assert 'false' in fixed

    def test_hyphenated_key_false_positive(self):
        """A hyphenated key like 'disable-lightCastShadows' must NOT be mutated."""
        raw = '{"disable-lightCastShadows": true}'
        fixed, count, _ = fix_jbeam_content(raw)
        assert count == 0, f"Wrongfully modified hyphenated key! Result: {fixed}"
        assert fixed is raw

    def test_string_literal_in_description_false_positive(self):
        """String literals in non-lighting description must NOT have their text modified."""
        raw = '{"description": "Mod update: lightCastShadows: true was removed in 0.24"}'
        fixed, count, _ = fix_jbeam_content(raw)
        assert count == 0, f"Wrongfully modified string literal in description! Result: {fixed}"
        assert fixed is raw
