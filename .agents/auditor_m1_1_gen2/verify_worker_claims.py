import sys
sys.path.insert(0, 'src')

from beamng_mod_fixer.models import JBeamFixResult
from beamng_mod_fixer.core.jbeam_fixer import fix_jbeam_content, decode_jbeam_bytes

# 1. Verify Reviewer 2 Finding 1
raw = '{"cookieName": "none"}'
fixed, count, diags = fix_jbeam_content(raw)
res = JBeamFixResult(content=fixed, fix_count=count, diagnostics=diags)
assert count == 0, f"Expected count 0, got {count}"
assert res.modified is True, "Expected res.modified is True"
assert res.has_fixes is True, "Expected res.has_fixes is True"
print("VERIFICATION 1 SUCCESS: Cookie normalization modified flag is True")

# 2. Verify CP1252 vs CP1251
raw_fr = '// Spécial: éclairage avant\n{"spotlights": []}'.encode('cp1252')
_, enc_fr = decode_jbeam_bytes(raw_fr)
assert enc_fr == 'cp1252', f"Expected cp1252, got {enc_fr}"

raw_ru = '// Фары ВАЗ-2107 передние\n{"name": "vaz"}'.encode('cp1251')
_, enc_ru = decode_jbeam_bytes(raw_ru)
assert enc_ru == 'cp1251', f"Expected cp1251, got {enc_ru}"
print("VERIFICATION 2 SUCCESS: Encodings accurately differentiated")
