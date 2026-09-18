import sys
from pathlib import Path
sys.path.insert(0, 'src')

from beamng_mod_fixer.models import DiagnosticNotice, JBeamFixResult
from beamng_mod_fixer.core.jbeam_fixer import (
    RE_LIGHT_CAST_SHADOWS,
    _is_inside_string_literal,
    fix_jbeam_content,
    detect_light_cast_shadows,
    decode_jbeam_bytes,
    audit_spotlights
)

print("=== RUNNING INDEPENDENT ADVERSARIAL AUDIT TESTS ===")

# --- Test 1: Complex String Literal Escapes and Multiple Keys on Same Line ---
# On the same line: a string containing "lightCastShadows: true", followed by actual key
line_mixed = '{"note": "Ignore lightCastShadows: true in here", "lightCastShadows": true}'
fixed, count, diags = fix_jbeam_content(line_mixed)
assert count == 1, f"Expected 1 fix, got {count}"
assert '{"note": "Ignore lightCastShadows: true in here", "lightCastShadows": false}' == fixed, f"Got: {fixed}"
print("Test 1 Passed: Correctly distinguished string literal content from genuine key on the same line")

# --- Test 2: Escaped Backslashes in String Literals ---
line_escapes = r'{"folder": "C:\\games\\BeamNG\\", "lightCastShadows": true}'
fixed, count, diags = fix_jbeam_content(line_escapes)
assert count == 1, f"Expected 1 fix, got {count}"
assert r'{"folder": "C:\\games\\BeamNG\\", "lightCastShadows": false}' == fixed, f"Got: {fixed}"
print("Test 2 Passed: Handled escaped backslashes before quote closure")

# --- Test 3: Escaped Quotes Inside String Literals ---
line_escaped_quotes = r'{"desc": "He said: \"lightCastShadows: true is deprecated\" in 0.25", "lightCastShadows": true}'
fixed, count, diags = fix_jbeam_content(line_escaped_quotes)
assert count == 1, f"Expected 1 fix, got {count}"
assert r'{"desc": "He said: \"lightCastShadows: true is deprecated\" in 0.25", "lightCastShadows": false}' == fixed
print("Test 3 Passed: Handled escaped quotes inside string literals")

# --- Test 4: False Positive Token Boundaries ---
false_positives = [
    '{"disable_lightCastShadows": true}',
    '{"disable-lightCastShadows": true}',
    '{"$lightCastShadows": true}',
    '{"lightCastShadows_enabled": true}',
    '{"lightCastShadows-enabled": true}',
    '{"mylightCastShadows": true}',
    '{"lightCastShadowsExtra": true}',
]
for fp in false_positives:
    fixed, count, _ = fix_jbeam_content(fp)
    assert count == 0, f"False positive matched on {fp}! Got count={count}, fixed={fixed}"
    assert fixed is fp, f"Expected reference equality on {fp}"
print("Test 4 Passed: All prefix/suffix/boundary false positives rejected with 0 modifications")

# --- Test 5: Symmetrical Quote Enforcement ---
# Mismatched quotes should NOT match as a valid key
mismatched_quotes = [
    '{"lightCastShadows\': true}',
    '{\'lightCastShadows": true}',
    '{"lightCastShadows`: true}',
]
for mq in mismatched_quotes:
    fixed, count, _ = fix_jbeam_content(mq)
    assert count == 0, f"Mismatched quote incorrectly matched on {mq}"
print("Test 5 Passed: Symmetrical quote enforcement strictly verified")

# --- Test 6: Extreme Comment Nesting & Line Breaks ---
extreme_comment = (
    '{\n'
    '  "lightCastShadows" /* c1 */ // single line 1\n'
    '  /* c2 \n'
    '     multiline */ : /* c3 */ // single line 2\n'
    '  /* c4 */ true\n'
    '}'
)
fixed, count, _ = fix_jbeam_content(extreme_comment)
assert count == 1, f"Failed on extreme comment nesting: count={count}"
assert "/* c1 */" in fixed
assert "// single line 1\n" in fixed
assert "/* c2 \n     multiline */" in fixed
assert "/* c3 */" in fixed
assert "// single line 2\n" in fixed
assert "/* c4 */ false" in fixed
print("Test 6 Passed: Extreme comment nesting preserved verbatim while replacing true -> false")

# --- Test 7: Multilingual Encoding Heuristic Stress Test ---
# French with CP1252
fr_bytes = '// Phare avant gauche été 2024: modèle spécial\n{"spotlights": []}'.encode('cp1252')
text, enc = decode_jbeam_bytes(fr_bytes)
assert enc == 'cp1252', f"Expected cp1252, got {enc}"
assert 'été 2024: modèle spécial' in text

# German with CP1252
de_bytes = '// Scheinwerfer Weiß & Grün für Überwachung\n{"spotlights": []}'.encode('cp1252')
text, enc = decode_jbeam_bytes(de_bytes)
assert enc == 'cp1252', f"Expected cp1252, got {enc}"
assert 'Weiß & Grün für Überwachung' in text

# Spanish with CP1252
es_bytes = '// Iluminación para el camión pequeño\n{"spotlights": []}'.encode('cp1252')
text, enc = decode_jbeam_bytes(es_bytes)
assert enc == 'cp1252', f"Expected cp1252, got {enc}"
assert 'Iluminación para el camión pequeño' in text

# Russian with CP1251
ru_bytes = '// Фары дальнего света ВАЗ-2107\n{"spotlights": []}'.encode('cp1251')
text, enc = decode_jbeam_bytes(ru_bytes)
assert enc == 'cp1251', f"Expected cp1251, got {enc}"
assert 'Фары дальнего света ВАЗ-2107' in text

# UTF-8 with Russian
utf8_ru_bytes = '// Фары дальнего света ВАЗ-2107\n{"spotlights": []}'.encode('utf-8')
text, enc = decode_jbeam_bytes(utf8_ru_bytes)
assert enc == 'utf-8', f"Expected utf-8, got {enc}"
assert 'Фары дальнего света ВАЗ-2107' in text

# UTF-8 with BOM
import codecs
bom_bytes = codecs.BOM_UTF8 + '{"name": "bom_test"}'.encode('utf-8')
text, enc = decode_jbeam_bytes(bom_bytes)
assert enc == 'utf-8-sig', f"Expected utf-8-sig, got {enc}"
assert '{"name": "bom_test"}' == text

# Arbitrary byte sequence fallback to latin-1
raw_bin = bytes(range(1, 256))
text, enc = decode_jbeam_bytes(raw_bin)
assert enc in ('latin-1', 'cp1252', 'cp1251'), f"Unexpected encoding: {enc}"
print("Test 7 Passed: Multilingual encoding heuristic passed all language stress-tests")

# --- Test 8: JBeamFixResult Post-Init Flag Integrity ---
# Case A: Pure warning without normalization -> modified=False
res_warn = JBeamFixResult(
    content="sample",
    fix_count=0,
    diagnostics=[
        DiagnosticNotice(severity="warning", message="Inverted spotlight angles", rule="spotlight_angle_inverted")
    ]
)
assert res_warn.modified is False, "Warning must not mark file as modified"
assert res_warn.has_fixes is False, "Warning must not mark has_fixes as True"

# Case B: Cookie normalization info -> modified=True, has_fixes=True
res_cookie = JBeamFixResult(
    content="sample",
    fix_count=0,
    diagnostics=[
        DiagnosticNotice(severity="info", message='Normalized invalid cookieName "none" to empty string ""', rule="cookie_name_normalized")
    ]
)
assert res_cookie.modified is True, "Cookie normalization must mark file as modified"
assert res_cookie.has_fixes is True, "Cookie normalization must mark has_fixes as True"

# Case C: Flare normalization warning -> modified=True, has_fixes=True
res_flare = JBeamFixResult(
    content="sample",
    fix_count=0,
    diagnostics=[
        DiagnosticNotice(severity="warning", message='Normalized invalid flareName "none" to empty string ""', rule="flare_name_normalized")
    ]
)
assert res_flare.modified is True, "Flare normalization must mark file as modified"
assert res_flare.has_fixes is True, "Flare normalization must mark has_fixes as True"

# Case D: Shadows fixed -> modified=True, has_fixes=True
res_shadow = JBeamFixResult(content="sample", fix_count=2, diagnostics=[])
assert res_shadow.modified is True
assert res_shadow.has_fixes is True
print("Test 8 Passed: JBeamFixResult post-init state transitions are 100% sound")

print("\nALL 8 INDEPENDENT ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
