"""Vehicle Lua & Script Safety Engine for BeamNG.drive mods.

Provides:
- Non-invasive diagnostic auditing of vehicle Lua scripts.
- Purging of destructive chunk-level global shadowing preambles (local v, local electrics).
- Reverting broken engine bridge calls back to standard BeamNG API syntax.
- Preservation of pristine vehicle Lua execution environments.
"""

import logging
import re
from typing import List, Optional, Tuple

from beamng_mod_fixer.models import DiagnosticNotice

logger = logging.getLogger(__name__)

RE_TOXIC_PREAMBLE = re.compile(
    r"-- \[GBEAM FIX\][^\n]*\n(?:local (?:v|electrics)[^\n]*\n|if type\((?:v|electrics)\)[^\n]*\n)*",
    re.MULTILINE
)


def fix_lua_content(
    content: str,
    filename: str = "",
) -> Tuple[str, int, List[DiagnosticNotice]]:
    """Audit and safely sanitize vehicle Lua scripts.

    Purges destructive preamble injections while preserving vehicle controller integrity.

    Args:
        content: Raw Lua text content.
        filename: Optional filename for diagnostics.

    Returns:
        Tuple[str, int, List[DiagnosticNotice]]:
            - fixed_content: Sanitized Lua script.
            - fix_count: Number of issues repaired.
            - diagnostics: List of diagnostic notices.
    """
    diagnostics: List[DiagnosticNotice] = []
    text = content
    fix_count = 0

    # 1. Strip harmful preamble if present
    if "-- [GBEAM FIX]" in text:
        text = RE_TOXIC_PREAMBLE.sub("", text)
        fix_count += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Purged harmful global shadowing preamble (restored native v/electrics bindings)",
                file_path=filename,
                rule="lua_preamble_purged",
            )
        )

    # 2. Revert broken obj:queueGameEngineLua wrapper if present
    if "(obj.queueGameEngineLua and obj:queueGameEngineLua or function(...) end)(" in text:
        text = text.replace(
            "(obj.queueGameEngineLua and obj:queueGameEngineLua or function(...) end)(",
            "obj:queueGameEngineLua("
        )
        fix_count += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Restored native obj:queueGameEngineLua call syntax",
                file_path=filename,
                rule="lua_queue_syntax_restored",
            )
        )

    # 3. Revert broken guihooks wrapper if present
    if "(guihooks and guihooks.trigger or function(...) end)(" in text:
        text = text.replace(
            "(guihooks and guihooks.trigger or function(...) end)(",
            "guihooks.trigger("
        )
        fix_count += 1
        diagnostics.append(
            DiagnosticNotice(
                severity="info",
                message="Restored native guihooks.trigger call syntax",
                file_path=filename,
                rule="lua_guihooks_syntax_restored",
            )
        )

    return text, fix_count, diagnostics

