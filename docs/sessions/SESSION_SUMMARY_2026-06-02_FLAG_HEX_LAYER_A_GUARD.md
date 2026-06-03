# Session Summary — 2026-06-02 — Flag-hex divergence class locked as Layer-A guard

## Scope

Picked up from the prior session's handoff (2.12.75, divergence-class
completeness lens), whose documented next task was the cheap **Layer-A to-do**:
investigate divergence class 5 (flag-hex) and class 6 (pointer-identity) via
`/rom-divergence-sweep`, each yielding either a committed guard or an honest
reclassification.

This session ran the sweep on **class 5 (flag-hex)** — the AGENTS.md "never
hardcode hex bit values; use the IntEnum" rule. Unlike async-delivery (class 4,
which reclassified A→C last session when its bypass-grep false-positived),
flag-hex came back the **other** way: a tight prefix-anchored grep had exactly
one legitimate hit, so the class proved Layer-A **feasible**. Closing it required
resolving four offender sites (2 mechanical enum migrations + 2 dead-code
deletions), then committing the guard green. **No live parity bug existed** — the
two live offenders carried correct values; the two wrong-valued ones were dead.

## Outcomes

### Divergence class 5 (flag-hex) — ✅ LOCKED as Layer-A guard

- **Guard**: `tests/test_flag_hex_convention.py` — the **fourth** static
  bypass-guard, same `rglob → forbid-pattern → assert` shape as
  `test_rng_determinism` / `test_equipment_key_convention` /
  `test_attribute_convention`.
- **Pattern**: forbids `FLAGPREFIX_X = 0x…` (PLR_/OFF_/ASSIST_/COMM_/IMM_/…)
  outside the enum modules. **Sole legitimate hit**: `mud/wiznet.py`'s
  `WiznetFlag` enum body (the canonical chokepoint — allowlisted).
- **Recall validated** (Phase 3): the grep correctly does *not* flag the two
  past instances of this class — PARALLEL-005 (`0x0010`→ExtraFlag.EVIL) and
  ACT_TRAIN (`0x200`) — which now appear only as comments documenting their
  fixes, proving the query would have caught them when live.
- **Honest limit** (recorded in the roster row): locks "no flag-prefixed *hex*
  constant redefined outside the enum modules" — does **not** catch a
  *decimal*-literal bypass (`if act & 32768:`), indistinguishable from arithmetic.

### `HANDLER-DEAD-001` — `is_friend` dead duplicate, wrong assist bits — ✅ REMOVED

- **Python**: `mud/handler.py` `is_friend` (deleted).
- **ROM C**: `src/handler.c:50-93`; assist flags are letter macros
  `ASSIST_ALL = (P)` = bit 15, `ASSIST_PLAYERS = (S)` = bit 18.
- **Gap**: hardcoded `ASSIST_PLAYERS = 0x1` (bit 0), `ASSIST_ALL = 0x2` (bit 1),
  … bits 0–4 — **all wrong** vs canonical `OffFlag` bits 15–20. Dead (no callers;
  live mob-assist path is `mud/combat/assist.py`, which uses `OffFlag`).
- **Fix**: deleted; left a note citing the live path.

### `HANDLER-DEAD-002` — `check_immune` dead duplicate, wrong RIV bits — ✅ REMOVED

- **Python**: `mud/handler.py` `check_immune` (deleted).
- **ROM C**: `src/handler.c:213-304`; `IMM_MAGIC = (C)` = bit 2,
  `IMM_WEAPON = (D)` = bit 3.
- **Gap**: hardcoded `IMM_WEAPON = 0x1` (bit 0), `IMM_MAGIC = 0x2` (bit 1) —
  wrong vs canonical `DefenseBit.WEAPON = 1<<3` / `MAGIC = 1<<2`; only a
  WEAPON/MAGIC TODO stub. Dead (no callers; live RIV path is
  `mud/affects/saves.py::_check_immune`, tested by `test_saves_rom_parity.py`).
- **Fix**: deleted; left a note citing the live path.

### Live offenders migrated to canonical enums (no behavior change)

- `mud/commands/player_config.py`: `PLR_CANLOOT/NOSUMMON/NOFOLLOW` →
  `int(PlayerFlag.X)`. Values already correct (`CANLOOT = 1<<15 = 0x8000`, …).
- `mud/commands/remaining_rom.py`: `COMM_DEAF = 0x2` → `int(CommFlag.DEAF)` (the
  pattern the very next line already used for `COMM_QUIET`). Value already correct.

## Files Modified

- `mud/handler.py` — deleted dead `is_friend` + `check_immune` (notes left)
- `mud/commands/player_config.py` — PLR_* derive from `PlayerFlag`
- `mud/commands/remaining_rom.py` — `COMM_DEAF` derives from `CommFlag`
- `tests/test_flag_hex_convention.py` — **new** Layer-A bypass-guard
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 5 row → ✅ guarded; Layer-A 4/5; to-do item 3 closed
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-DEAD-001/002 filed
- `CHANGELOG.md` — Added (guard) + Fixed (offender resolution) entries
- `pyproject.toml` — 2.12.75 → 2.12.76

## Test Status

- `tests/test_flag_hex_convention.py` — RED (4 offender sites) → GREEN after fixes.
- Targeted regression (combat/saves/resistance/affects/combat): **114 passed**.
- Full suite: **5356 passed, 4 skipped** in 201.91s — the +1 vs the 2.12.75
  baseline (5355) is the new guard test; **zero regressions**.
- `gitnexus_detect_changes`: **low risk, 0 affected processes** — confirms the
  deleted functions had no upstream callers (validates deadness).
- `ruff`: touched code lines clean; the two "would reformat" hits on
  player_config/remaining_rom are **pre-existing** docstring-whitespace / long-line
  drift, not from this session's edits (repo carries 1762 pre-existing ruff issues).

## Commits

- `568639b7` — `fix(parity): flag-hex class — drop dead wrong-bit handler dupes, route PLR_/COMM_DEAF through enums`
- `6ce23769` — `test(parity): lock flag-hex divergence class as Layer-A bypass-guard (2.12.76)`

## Next Steps

1. **Class 6 (pointer-identity) sweep** — the last open Layer-A to-do. Scope a
   pattern for `==`/`!=` between two `Character` references; high false-positive
   risk → may reclassify to Layer B/C (like async-delivery), or prove feasible
   (like flag-hex). Run via `/rom-divergence-sweep`. Roster Layer-A is now 4 of 5.
2. **Highest-ceiling (deliberate project):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Standing cross-INV candidate:** mob-trigger ordering
   (bribe/exit/fight/kill/hpcnt); INV tracker consolidation (26 rows, past the
   ~20 soft cap).
4. **Do NOT** mistake Layer-A completeness for parity — guardrail 3.

> **Push note:** 2.12.76 (`568639b7`, `6ce23769`) + this handoff are on local
> `master`, **not pushed** — on top of the unpushed 2.12.72–2.12.75 from prior
> sessions.
