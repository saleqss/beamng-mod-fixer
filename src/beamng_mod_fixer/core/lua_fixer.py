"""Vehicle Lua & Script Crash Guard Engine for BeamNG.drive mods.

Provides:
- Detection and repair of deprecated vehicle Lua API calls that trigger fatal Lua errors.
- Guarding of unguarded global tables (v.data, electrics.values).
- Replacing obsolete engine bridge calls (obj:queueGameEngineLua).
- Ensuring custom vehicle dashboard, gauge, and accessory scripts don't crash game simulation.
"""

import logging
import re
from typing import List, Optional, Tuple

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

# Patterns for deprecated Lua calls in older BeamNG vehicle scripts
RE_UNGUARDED_VDATA = re.compile(r'(?<![.\w])v\.data\.([a-zA-Z0-9_]+)')
RE_QUEUE_GE_LUA = re.compile(r'obj:queueGameEngineLua\s*\(')
RE_GUIHOOKS_TRIGGER = re.compile(r'guihooks\.trigger\s*\(')


def fix_lua_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Audit and patch vehicle Lua script content for modern BeamNG compatibility.

    Args:
        content: Raw Lua text content.
        filename: Optional filename for diagnostics.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Patched Lua script.
            - fix_count: Number of patches applied.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    fix_count = 0

    # 1. Guard deprecated obj:queueGameEngineLua calls with pcall/exist check
    if "obj:queueGameEngineLua" in text:
        def _fix_queue(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="warning",
                    message="Safely guarded deprecated obj:queueGameEngineLua call",
                    file_path=filename,
                    rule="lua_queue_ge_guarded",
                )
            )
            return "(obj.queueGameEngineLua and obj:queueGameEngineLua or function(...) end)("

        text = RE_QUEUE_GE_LUA.sub(_fix_queue, text)

    # 2. Guard guihooks.trigger calls against nil guihooks
    if "guihooks.trigger" in text and "if guihooks" not in text:
        def _fix_guihooks(m: re.Match) -> str:
            nonlocal fix_count
            fix_count += 1
            diagnostics.append(
                DiagnosticNotice(
                    severity="info",
                    message="Safely guarded guihooks.trigger call against missing GUI subsystem",
                    file_path=filename,
                    rule="lua_guihooks_guarded",
                )
            )
            return "(guihooks and guihooks.trigger or function(...) end)("

        text = RE_GUIHOOKS_TRIGGER.sub(_fix_guihooks, text)

    # 3. Add safety preamble if script uses v.data without local check
    if "v.data" in text and "local v = v or" not in text and "if not v" not in text:
        preamble = (
            "-- [GBEAM FIX] Guard against uninitialized v / v.data\n"
            "local v = v or { data = {} }\n"
            "if type(v) == 'table' and not v.data then v.data = {} end\n"
        )
        text = preamble + text
        fix_count += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Injected safe initialization preamble for global v.data table",
                file_path=filename,
                rule="lua_vdata_guard_injected",
            )
        )

    if fix_count == 0 or text == content:
        return content, 0, diagnostics

    return text, fix_count, diagnostics
