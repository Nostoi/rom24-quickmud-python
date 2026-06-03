"""Guard: production code must use the canonical IntFlag enums, never a
hardcoded hex bit value re-defined under a ROM flag name.

AGENTS.md "ROM Parity Rules" mandates:
    use enums (`PlayerFlag.AUTOLOOT`, `CommFlag.DEAF`, `OffFlag.ASSIST_ALL`, …);
    never hardcode hex bit values — ROM C uses bit shifts and the hex you'd
    guess from the constant name is often wrong.

The danger is concrete and has bitten this port: a function that re-declares
`ASSIST_PLAYERS = 0x00000001` (bit 0) silently disagrees with the canonical
`OffFlag.ASSIST_PLAYERS = 1 << 18` (bit 18) — the ROM letter macro is `(S)`,
not `(A)`. Two such landmine functions (`handler.is_friend`,
`handler.check_immune`) shipped as dead duplicates with wrong bit positions
before this guard; the divergence-class sweep (DIVERGENCE_CLASS_ROSTER.md
class 5, 2026-06-02) deleted them and migrated the live `PLR_*`/`COMM_DEAF`
parallel constants to the canonical enums.

Canonical chokepoint: the IntFlag enums in `mud/models/constants.py` (defined
hex-free, via `1 << n`). The ONE legitimate file that defines flag members with
hex literals is `mud/wiznet.py` (the `WiznetFlag` enum body itself — that IS the
chokepoint, not a bypass), so it is allowlisted. Every other
`FLAGPREFIX_NAME = 0x...` assignment is a parallel hardcoded bitvalue and must
instead reference / derive from the canonical enum.

This scanner is the same shape as `test_rng_determinism.py` (bans `random.*`),
`test_equipment_key_convention.py` (bans string-keyed equipment), and
`test_attribute_convention.py` (bans `.carrying`/`.characters`/`.equipped`): it
is the Layer-A bypass-guard for divergence class 5 (flag-hex).

Scope note (honest limit): this catches hex re-definitions under a ROM flag
name. It does NOT catch a decimal-literal bypass (`if act & 32768:`) — a bare
int is indistinguishable from arbitrary arithmetic by a line scanner. The guard
locks "no flag-prefixed hex constant redefined outside the enum modules," not
"no flag-literal bypass." If a legitimate future hex flag definition appears,
move it into an enum class (or extend the allowlist with justification) — do
not delete the guard.
"""

from __future__ import annotations

import re
from pathlib import Path

# ROM bitvector prefixes (merc.h). A hex literal assigned to a name with one of
# these prefixes is a hardcoded flag bit — exactly the anti-pattern.
_FLAG_PREFIXES = (
    "PLR",
    "ACT",
    "AFF",
    "COMM",
    "OFF",
    "ASSIST",
    "IMM",
    "RES",
    "VULN",
    "ITEM",
    "WEAR",
    "EXTRA",
    "ROOM",
    "EX",
    "WIZ",
    "FORM",
    "PART",
    "AREA",
    "CONT",
    "SEX",
)
_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_FLAG_PREFIXES) + r")_\w*\s*=\s*0x[0-9A-Fa-f]+",
)

_SCAN_DIR = "mud"

# The sole legitimate file: WiznetFlag's enum body defines its members with hex
# literals. That file IS the canonical chokepoint for wiznet flags, not a bypass.
_ALLOWLIST = {Path("mud/wiznet.py")}


def test_no_hardcoded_flag_hex_in_production() -> None:
    offenders: list[str] = []
    for path in sorted(Path(_SCAN_DIR).rglob("*.py")):
        if path in _ALLOWLIST:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            code = line.split("#", 1)[0]  # ignore comments that cite the anti-pattern
            if _PATTERN.search(code):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "hardcoded hex flag bit found — use the canonical IntFlag enum "
        "(e.g. `int(PlayerFlag.CANLOOT)`, `int(CommFlag.DEAF)`, "
        "`OffFlag.ASSIST_PLAYERS`) per AGENTS.md ROM Parity Rules. The hex you "
        "guess from the constant name is often the wrong bit:\n" + "\n".join(offenders)
    )
