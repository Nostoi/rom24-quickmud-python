# Session Summary — 2026-07-16 — Follower-disband sweep (clean + guard) & FIGHT-095 de-risk

## Scope

Continuation session (same date, distinct topic from the earlier
`EXTRACT_CLEANUP_MATRIX` sweep) in **cross-file-invariants / divergence-class
probe** mode. Two deliverables: (1) a divergence sweep of the **group/follower
disband-edge** class (skill args: die/quit/extract follower-chain cleanup) —
came back clean, and the one previously-untested leg was locked with a
behavioral guard; (2) drove the one open actionable gap, **FIGHT-095**, to
de-risked-and-precisely-characterized — retiring its stated blocker empirically
and identifying its real nature as an unconformed INV-045 site, stopping short of
a rushed RNG-sensitive fix (a multi-commit harness-extension task).

## Outcomes

### Follower-disband edges — ✅ CLEAN PROBE + new guard

- **Python**: `mud/characters/follow.py` (`add_follower`/`stop_follower`/`die_follower`)
- **ROM C**: `src/act_comm.c:1591-1680`, call sites `handler.c:2122`,
  `act_info.c:1003`, `fight.c:757/1266`, `magic.c:1377`
- **Result**: the disband chain and its full ROM call-site set are faithful and
  fully wired. Two subtleties verified convergent:
  - `die_follower`'s global `char_list` walk is correctly mirrored by
    `character_registry` — and here global iteration IS ROM-faithful (contrast
    FIGHT-095's `check_assist`, where following the global list was the bug). The
    discriminator: `die_follower` is **order-insensitive** (resets a pointer for
    every match), so the ROM prepend vs Python append ordering diff is irrelevant.
  - `stop_follower`'s `if/elif` charm-strip is behaviorally equivalent to ROM's
    single `REMOVE_BIT + affect_strip` branch — `remove_spell_effect` clears the
    CHARM bit (via `remove_affect`) AND strips all matching affects; bitfields
    aren't refcounted, so there is no double-charm divergence.
- **Guard (new)**: `tests/integration/test_player_config.py::test_nofollow_detaches_existing_followers`
  locks the one previously-untested leg — `do_nofollow` enabling NOFOLLOW must run
  `die_follower` and detach existing followers (ROM `act_info.c:1003`). The
  existing toggle tests asserted only the `PLR_NOFOLLOW` flag + message, never the
  `die_follower` side effect. **Mutation-tested**: the guard fails when the
  `_die_follower` call is removed from `do_nofollow`, green when restored.
- **Commit**: `2bf19447`.

### FIGHT-095 — ⚠️ still OPEN, but de-risked and re-characterized

- **Python**: `mud/combat/assist.py:164` (inner target-selection loop)
- **ROM C**: `src/fight.c:161` — `for (vch = ch->in_room->people; vch; vch = vch->next)`
- **Stated blocker RETIRED**: the recorded concern that the differential C oracle
  is nondeterministic on RNG scenarios is false. Capturing every RNG-adjacent
  scenario (`combat_melee_rounds`, `mob_fight_trigger`, `spell_combat`,
  `aggression_onset`) **twice with the current `src/diffshim` binary** yields
  byte-identical traces. The `capture --check` CHANGED on ~20 scenarios is
  cross-build provenance drift (fresh binary vs committed OLD goldens), NOT
  within-build nondeterminism — so a fresh `check_assist` golden is trustworthy.
- **Real nature identified**: FIGHT-095 is an unconformed **NESTED** site of
  **INV-045 (CHAR-LIST-WALK-ORDER)**. ROM head-inserts `char_list`
  (`src/db.c:2256-2257`, newest-first) vs Python `character_registry.append`
  (oldest-first — the reverse). INV-045 already conformed the tick walks +
  `get_char_world` via `reversed(<registry>)`; the character-side fix pattern is
  proven by **GROUP-006 (✅ 2.14.202)**, the identical bug in `do_group`. The
  `check_assist` inner reservoir loop is a global-list walk nested inside the
  already-conforming outer violence tick, so the 2026-06-12 INV-045 sweep missed
  it. It is **order-sensitive** on both facets: draw-count needs **domain** parity,
  target-selection needs **reservoir order** parity.
- **Remaining blocker** is NOT fix design — it is a **harness-primitive gap**:
  building the locking scenario requires (a) a mob `off_flags` (ASSIST_*) directive
  and (b) cross-room grouped-member placement, both additive
  `src/diff_shim/diffmain.c` + `pyreplay.py` extensions. Multi-commit +
  RNG-sensitive; deliberately not started on a replay turn to avoid a rushed
  wrong fix. Full closure spec recorded in `FIGHT_C_AUDIT.md`.
- **Commit**: `4ba46807` (docs-only: FIGHT_C_AUDIT + INV-045 tracker note +
  roster note + CHANGELOG).

## Files Modified

- `tests/integration/test_player_config.py` — new guard
  `test_nofollow_detaches_existing_followers`.
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — follower-disband clean-probe note +
  FIGHT-095/INV-045 list-order class note.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-095 row rewritten (blocker retired, real
  nature + closure spec).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-045 nested-residual note
  (check_assist / FIGHT-095).
- `CHANGELOG.md` — Added (nofollow guard) + Changed (FIGHT-095 de-risk) entries.
- `pyproject.toml` — 2.14.317 → 2.14.319 (two patch bumps).

## Test Status

- New guard + `test_player_config.py` — 11/11 passing (10 existing + 1 new).
- Focused follower/config/INV-020/047 regression — 23/23 passing.
- Full suite: **6209 passed, 4 skipped, 0 failed** (299s, clean parallel run).
  +1 vs the prior session's 6208 (the new nofollow guard).

## Policy note

Ran under the **commit-locally-only** directive (no push, no PyPI publish). The 2
commits are local on `master`; the operator reviews and pushes/publishes manually.

## Next Steps

- **FIGHT-095 closure** is now a well-specified but multi-commit
  harness-extension task: extend `src/diff_shim/diffmain.c` + `pyreplay.py` with a
  mob-`off_flags` directive and cross-room grouped-member placement (identical
  C/Python semantics) → author `check_assist_cross_room_assist.json` → capture the
  C golden → port `assist.py` to the reversed positional-slice per the
  GROUP-006/GL-040 pattern → lock via the replay test. Route:
  `/rom-gap-closer FIGHT-095`.
- Carry-over (unchanged): FIGHT-094 (`check_killer` placement), DESC-001, OLC
  spell-name lookup, IS_BUILDER, stray `data/quickmud.db` (0 bytes) / `doc/game.db`
  (stale) cleanup pending confirmation.
