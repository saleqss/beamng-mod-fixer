"""Tier 1: Feature Tests for JBeam Optics Diagnostics & Normalization Engine.

Verifies:
- Detection of invalid flareName ('none', 'null', 'undefined')
- Automatic normalization of invalid flareName to empty string ""
- Detection of obsolete pre-PBR cookie texture paths ('art/shapes/lights/...')
- Detection of broken local cookie references missing from the mod archive
- Detection of inverted spotlight angles (innerAngle > outerAngle) or negative angles
- Detection of malformed spotlight rows (< 4 items)
- Clean vehicle headlights produce zero diagnostics
"""

import pytest
from beamng_mod_fixer.core.jbeam_fixer import audit_spotlights, fix_jbeam_content
from tests.fixtures.factory import SAMPLE_JBEAM_OPTICS_ISSUES, SAMPLE_JBEAM_STANDARD_HEADLIGHT


def test_detect_invalid_flare_name() -> None:
    """Test detection of invalid flareName strings that cause Torque3D particle errors."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"flareName": "none", "lightCastShadows": true}]]}'
    diags = audit_spotlights(content)
    rules = [d.rule for d in diags]
    assert "flare_name_invalid" in rules
    assert any("none" in d.message for d in diags)


def test_normalize_invalid_flare_name() -> None:
    """Test normalization converts flareName: "none" to flareName: ""."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"flareName": "none", "lightCastShadows": true}]]}'
    fixed, count, diags = fix_jbeam_content(content, normalize_optics=True)
    assert 'flareName": ""' in fixed
    assert 'flareName": "none"' not in fixed
    rules = [d.rule for d in diags]
    assert "flare_name_normalized" in rules


def test_detect_obsolete_cookie_path() -> None:
    """Test detection of deprecated pre-PBR Torque3D cookie texture paths."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"cookieName": "art/shapes/lights/old_lens.dds"}]]}'
    diags = audit_spotlights(content)
    rules = [d.rule for d in diags]
    assert "cookie_path_obsolete" in rules
    assert any("art/shapes/lights/" in d.message for d in diags)


def test_detect_missing_cookie_in_archive() -> None:
    """Test warning when custom vehicle cookie texture is not packed inside mod archive."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"cookieName": "vehicles/my_car/textures/custom_cookie.dds"}]]}'
    archive_files = {"vehicles/my_car/headlights.jbeam", "vehicles/my_car/body.dae"}
    diags = audit_spotlights(content, available_files=archive_files)
    rules = [d.rule for d in diags]
    assert "cookie_file_missing" in rules
    assert any("custom_cookie.dds" in d.message for d in diags)


def test_valid_cookie_in_archive_passes() -> None:
    """Test that when referenced cookie exists in archive, no warning is emitted."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"cookieName": "vehicles/my_car/textures/custom_cookie.dds"}]]}'
    archive_files = {
        "vehicles/my_car/headlights.jbeam",
        "vehicles/my_car/textures/custom_cookie.dds"
    }
    diags = audit_spotlights(content, available_files=archive_files)
    rules = [d.rule for d in diags]
    assert "cookie_file_missing" not in rules


def test_detect_inverted_spotlight_angles() -> None:
    """Test detection of innerAngle > outerAngle causing inverted cone cutoff."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"lightInnerAngle": 80, "lightOuterAngle": 45}]]}'
    diags = audit_spotlights(content)
    rules = [d.rule for d in diags]
    assert "spotlight_angle_inverted" in rules


def test_detect_negative_spotlight_angles() -> None:
    """Test detection of negative spotlight angle values."""
    content = '{"spotlights": [["hl", "a", "b", "c", {"lightInnerAngle": -10, "lightOuterAngle": 45}]]}'
    diags = audit_spotlights(content)
    rules = [d.rule for d in diags]
    assert "spotlight_angle_invalid" in rules


def test_detect_malformed_spotlight_row() -> None:
    """Test warning emitted for spotlight rows with fewer than 4 items."""
    content = '{"spotlights": [["hl_broken", "node1"]]}'
    diags = audit_spotlights(content)
    rules = [d.rule for d in diags]
    assert "spotlight_row_malformed" in rules


def test_clean_optics_produce_zero_warnings() -> None:
    """Test that standard well-formed headlights produce no warnings."""
    diags = audit_spotlights(SAMPLE_JBEAM_STANDARD_HEADLIGHT)
    assert len(diags) == 0


def test_optics_issues_sample_collects_multiple_diagnostics() -> None:
    """Test aggregate diagnostics on sample file containing multiple defects."""
    fixed, count, diags = fix_jbeam_content(SAMPLE_JBEAM_OPTICS_ISSUES, normalize_optics=True)
    assert count >= 2
    assert len(diags) >= 3
    # Check normalization occurred
    assert 'flareName": "none"' not in fixed
    assert 'flareName": "null"' not in fixed

