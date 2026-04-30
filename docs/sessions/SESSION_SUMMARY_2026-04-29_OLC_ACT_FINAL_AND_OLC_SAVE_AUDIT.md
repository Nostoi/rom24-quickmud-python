# Session Summary — 2026-04-29 — `olc_act.c` MINORs closed + `olc_save.c` audit filed

## Scope

Picked up from the prior session that closed `olc_act.c` IMPORTANT tier
(OLC_ACT-007..012). This session: (1) closed the two remaining MINOR
structural gaps in `olc_act.c` (OLC_ACT-013/014) — both
"structural-divergence-with-equivalent-behavior" closures with locked
regression tests; and (2) filed the Phase 1–3 audit doc for
`src/olc_save.c` (1136 lines, 17 ROM functions), the last unaudited OLC
editor file. JSON-authoritative framing locked: Python writes JSON, not
`.are`.

## Outcomes

### `OLC_ACT-013` — ✅ FIXED

- **Python**: `mud/commands/build.py:1352` (`_get_area_for_vnum`)
- **ROM C**: `src/olc_act.c:588-599` (`get_vnum_area`)
- **Gap**: ROM walks `area_first` linked list; Python iterates
  `area_registry.values()` (dict).
- **Fix**: CPython dicts preserve insertion order (3.7+), so load-order
  traversal is equivalent to ROM's linked-list walk. Added a ROM-cite
  comment to the helper. No behavior change — locked the equivalence.
- **Tests**: `tests/integration/test_olc_act_013_get_area_for_vnum_order.py`
  (3 cases: lookup, first-match-on-overlap, insertion-order). All passing.
- **Commit**: `61c2b5a`

### `OLC_ACT-014` — ✅ FIXED

- **Python**: `mud/commands/build.py:220` (`_mark_area_changed`) +
  per-handler imperative `area.changed = True` calls
- **ROM C**: `src/olc.c:452-463`/`:510-521` (AREA_CHANGED dispatcher)
- **Gap**: ROM dispatchers `SET_BIT(pArea->area_flags, AREA_CHANGED)` when
  a subcommand returns TRUE; Python uses imperative `area.changed = True`
  per handler. Structural divergence with equivalent behavior.
- **Fix**: ROM-cite comment added to `_mark_area_changed`. No code
  behavior change — locked the imperative protocol.
- **Tests**: `tests/integration/test_olc_act_014_area_changed_protocol.py`
  (6 cases: name on all four editors, aedit `security`, plus a
  failed-mutation no-op mirroring ROM's "handler returned FALSE → no
  SET_BIT" path). All passing.
- **Commit**: `dfb811e`

### `olc_save.c` audit — ⚠️ Phase 1–3 filed

- **Audit doc**: `docs/parity/OLC_SAVE_C_AUDIT.md` (new, 254 lines)
- **ROM C**: `src/olc_save.c` (1136 lines, 17 functions)
- **Architectural framing locked**: JSON is canonical write format; `.are`
  is read-only legacy input. ROM `.are` byte-format helpers
  (`fwrite_flag` A–Za–z encoding, `fix_string` tilde strip, column
  widths) are documented as **N/A** under this framing.
- **Gap IDs**: OLC_SAVE-001..020 (stable) —
  - **8 CRITICAL** (round-trip data loss): mob `off`/`imm`/`res`/`vuln`
    flags, `form`/`parts`/`size`/`material`, mprog list, shop binding,
    spec_fun binding; object `level`, structured affect chain,
    structured extra-descr.
  - **5 IMPORTANT**: no help-save path, `cmd_asave area` only handles
    `redit` (ROM dispatches AREA/ROOM/OBJECT/MOBILE/HELP), no autosave
    entry, NPC security gate gap, `save_area_list` missing `social.are`
    + HELP_AREA prepend.
  - **7 MINOR**: 4 message-string drifts, condition-letter ladder, exit
    lock-flag normalization, door-reset synthesis.
- **Tracker**: `olc_save.c` row flipped ❌ Not Audited → ⚠️ Partial.
- **Commit**: `2c088e7`

**Key finding (CRITICAL)**: a save→reboot→reload cycle on JSON areas
currently silently drops mob shop bindings, spec_fun bindings, mprog
lists, defensive flag sets (off/imm/res/vuln), form/parts/size/material;
object level, affect chains, extra-descs. This is a data-loss bug in the
OLC pipeline, not just a cosmetic divergence.

## Files Modified

- `mud/commands/build.py` — ROM-cite comments on `_get_area_for_vnum`
  and `_mark_area_changed` (no behavior change).
- `tests/integration/test_olc_act_013_get_area_for_vnum_order.py` — new,
  3 cases.
- `tests/integration/test_olc_act_014_area_changed_protocol.py` — new,
  6 cases.
- `docs/parity/OLC_ACT_C_AUDIT.md` — flipped rows: OLC_ACT-013,
  OLC_ACT-014 (both ✅ FIXED).
- `docs/parity/OLC_SAVE_C_AUDIT.md` — new audit doc, 20 stable gap IDs.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `olc_save.c` row
  flipped to ⚠️ Partial.
- `CHANGELOG.md` — `Fixed: OLC_ACT-013, OLC_ACT-014`; `Added: olc_save.c
  audit Phase 1–3`.
- `pyproject.toml` — 2.6.84 → 2.6.87 (three patch bumps, one per commit).

## Test Status

- `pytest tests/integration/test_olc_act_013_get_area_for_vnum_order.py
  tests/integration/test_olc_act_014_area_changed_protocol.py` — 9/9
  passing.
- Full integration suite not re-run this session (changes were
  comment-only in `mud/commands/build.py` plus new tests; no risk of
  regression).

## Next Steps

`olc_act.c` is now at TIER A/B = 100% closed (OLC_ACT-001..014). It
**cannot flip to ✅ AUDITED** until the ~78 TIER C functions
(`*_show`-helpers, flag-name lookups, etc.) receive a deep-audit pass.
Three sub-gaps from OLC_ACT-010 also remain (10b/c/d — dice/AC byte
format, shop/mprogs/spec_fun rendering, ROM-faithful flag-table names).
These depend on data-model alignment and should be deferred until that
alignment is in scope.

For next session, two viable paths:

1. **Begin OLC_SAVE closures, CRITICAL block first**: OLC_SAVE-001..008
   (the round-trip data-loss block). Each closure adds one missing
   field/section to JSON serialization and one round-trip integration
   test (load .are → save JSON → load JSON → assert proto equals
   original). Recommend starting with OLC_SAVE-001 (mob defensive flag
   sets) since it has the largest blast radius for combat balance and
   is mechanically simple. Note: OLC_SAVE closures of mob defensive
   flags depend on a corresponding `mud/loaders/json_loader.py` change
   to read them back — both sides land in one commit per the audit's
   locked closure rule.

2. **`olc_mpcode.c` audit** — last unaudited OLC editor file (mobprog
   editor). Smaller surface than olc_save (~300 lines) and would close
   out the OLC editor cluster's audit phase entirely.

Recommended start: **option 1, OLC_SAVE-001** (mob off/imm/res/vuln
flags). Smallest and clearest of the CRITICAL block; a passing
round-trip test there is the template for the rest of the data-loss
gaps. Use `rom-gap-closer` per gap, sequentially. Expect each closure
to land in 30–60 min including the round-trip test.

### Subagent reliability note (carried forward)

Sonnet subagents continue to terminate mid-investigation in this
codebase (now four sessions). For multi-step parity work, prefer inline
execution. Haiku subagents remain reliable for small string-drift /
single-keyword closures only. The `olc_save.c` audit was run inline per
the session brief.
