# Session Summary — 2026-06-14 — act_obj.c entry-gate sweep (RECITE-006)

## Scope

Continued the cross-file / divergence-class sweep (per-file audit tracker has no
⚠️ Partial / ❌ Not Audited rows). Following the act_comm.c → act_obj.c
"category-error" lead — a precondition checked in the wrong order or **borrowed
from the wrong command family**, where the *first failing gate selects the
player-facing message* (SHOUT-005, TELL-009, GIVE-003 shape) — into the magic-item
verbs in `magic_items.py` (do_recite / do_brandish / do_zap).

Method per verb: read the ROM C gate sequence top-to-bottom → diff against the
Python early-returns for *presence, order, and message* → one failing test if
they diverge.

`do_brandish` and `do_zap` were verified gate-order **clean** against ROM
(`src/act_obj.c:1978-2064` / `:2068-2157`). `do_recite` carried one borrowed
gate — closed.

## Outcomes

### `RECITE-006` — ✅ FIXED (v2.14.99)

- **Python**: `mud/commands/magic_items.py:do_recite` (was lines 120-121)
- **ROM C**: `src/act_obj.c:1910-1974` (do_recite), `src/handler.c:942-943`
  (the `is_name("")==FALSE` guard)
- **Gap**: borrowed-gate divergence. Python `do_recite` opened with
  `if not arg1: return "What do you want to recite?"` — a gate ROM `do_recite`
  does **not** have. It was borrowed from the sibling `do_quaff`'s "Quaff what?"
  (`src/act_obj.c:1872`). ROM goes straight to `get_obj_carry(ch, arg1, ch)`
  (`:1921`).
- **Fix**: removed the borrowed gate. With an empty arg, ROM's
  `get_obj_carry` → `is_name("")` returns FALSE (`src/handler.c:942-943`, the
  explicit *"fixed to prevent is_name on '' returning TRUE"* guard), so nothing
  matches and the lookup returns NULL → "You do not have that scroll." — even
  while holding a non-scroll. Python's own `is_name`/`get_obj_carry` already
  short-circuit on empty input, so they match this **fixed** ROM source exactly;
  **no helper change was needed**.
- **Key correction**: the prior-session hypothesis (carried into the handoff)
  that ROM `is_name("")` returns TRUE and matches the *first* carried item was
  **overturned** by re-reading `src/handler.c:941-943` — this QuickMUD ROM source
  carries the upstream fix, so the feared HIGH-blast-radius `get_obj_carry`/
  `is_name` change does **not** exist. (Per AGENTS.md "re-verify ✅/status claims
  against ROM C source before relying on them.")
- **Tests**: 1 new —
  `tests/integration/test_consumables.py::test_recite_empty_arg_has_no_borrowed_what_gate`
  (discriminating case: empty arg while holding a *non-scroll*, which separates
  the three possible outcomes — borrowed "What…?" gate / pre-fix first-match
  "only scrolls" / faithful "do not have"). Green; the 5 pre-existing recite
  tests stayed green.

### `do_brandish` / `do_zap` — ✅ VERIFIED CLEAN (no change)

- **Python**: `mud/commands/magic_items.py:do_brandish` / `do_zap`
- **ROM C**: `src/act_obj.c:1978-2064` / `:2068-2157`
- Gate sequences match ROM in presence + order: `get_eq_char(WEAR_HOLD)` NULL →
  "You hold nothing in your hand."; wrong item_type → "You can brandish only with
  a staff." / "You can zap only with a wand."; bad sn → bug+return; WAIT_STATE
  before the charge/cast loop. `do_zap`'s empty-arg-while-not-fighting →
  "Zap whom or what?" matches `:2076-2080`. No borrowed or missing gate.

## Files Modified

- `mud/commands/magic_items.py` — removed the borrowed empty-arg gate in
  `do_recite`; added a ROM-citing comment (RECITE-006).
- `tests/integration/test_consumables.py` — added
  `test_recite_empty_arg_has_no_borrowed_what_gate`.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — appended RECITE-006 ✅ FIXED to the
  `do_recite()` row.
- `CHANGELOG.md` — added the 2.14.99 (RECITE-006) section.
- `pyproject.toml` — 2.14.98 → 2.14.99.

## Test Status

- `pytest tests/integration/test_consumables.py -k recite` — 6/6 passing.
- `pytest tests/integration/test_consumables.py tests/integration/test_inv025_obj_command_pers_sweep.py`
  — 64/64.
- Full suite: **5788 passed, 4 skipped** (was 5787; +1 RECITE-006 test).
- `ruff check` (changed files) — clean.
- GitNexus `detect_changes` — scope confined to `do_recite` + its test + the
  audit doc, 0 affected processes, LOW risk. Reindexed post-commit.

## Next Steps

The `magic_items.py` entry-gate probe is done (recite closed; brandish/zap
clean). The act_obj.c entry-gate sweep across get/give/drop/put/recite/brandish/
zap has now found and closed GIVE-003 + RECITE-006 with everything else verified
clean — this verb family's borrowed-gate surface looks exhausted. Continuing the
"category-error" lead, the next untouched candidates are the **position/condition
gate families** elsewhere (e.g. `act_move.c` / `fight.c` entry gates), though
those are mostly single-gate sites (low borrowing surface). Per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`, the explicitly-named open lever with
higher expected yield remains the **Hypothesis state-machine → diff_harness
widening** (Class 11/Phase C) — enumeration-independent (guardrail 3), where most
recent FINDING-0xx originated.
