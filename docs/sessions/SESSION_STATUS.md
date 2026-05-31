# Session Status — 2026-05-31 — GL-032 mob affect application (2.12.11)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
- **Last completed (this session, 2.12.11)**:
  - **GL-032 — CLOSED** (commit `42270566`). `MobInstance.apply_spell_effect`
    was a "simplified" applier that moved only `hitroll`/`damroll` and set the
    affect flag, ignoring `ac_mod` / `saving_throw_mod` / `stat_modifiers` /
    `sex_delta`. ROM `affect_modify` (`src/handler.c:1018-1164`) is one function
    for PCs and NPCs and applies every `APPLY_*` location uniformly, so a charmed
    pet buffed with armor (AC), giant strength (STR), a save spell, or a
    sex-changing spell gained nothing from those locations. Brought the mob
    applier to parity with `Character`: added a `MobInstance.mod_stat` list,
    `get_curr_stat` now reads `perm_stat + mod_stat`, `apply_spell_effect`
    applies + `affect_join`-merges ac/saving/stat/sex (new `_apply_stat_modifier`
    / `_shift_sex` helpers), `remove_spell_effect` unwinds all four. No serializer
    change needed — `_serialize_pet` already persists folded-in runtime
    `armor`/`saving_throw`/`mod_stat`/`sex`, and GL-031's data-only restore
    re-counts nothing, so reload carries the bonus counted exactly once. Test:
    `tests/integration/test_gl032_mob_affect_application.py` (3: live apply
    verified red-first, symmetric removal, round-trip-counted-once including sex).
  - **GL-033 — FILED (OPEN)** (commit `42270566`). `MobInstance.get_curr_stat`
    clamps its lower bound to `0` where ROM `get_curr_stat` (`src/handler.c:868-874`)
    uses `URANGE(3, …)` — minimum 3. Latent before GL-032; the new `mod_stat`
    makes sub-3 effective stats reachable via a negative stat affect. Raising the
    floor to 3 breaks 4 directly-constructed sub-3-stat mob fixtures in
    `tests/test_skill_combat_rom_parity.py` (bash/disarm/dirt-kick) — confirming
    the floor is behaviorally live — so it was scoped out of GL-032. See
    `UPDATE_C_AUDIT` GL-033.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-31_GL032_MOB_AFFECT_APPLICATION.md](SESSION_SUMMARY_2026-05-31_GL032_MOB_AFFECT_APPLICATION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.11 |
| Tests | 5134 passed, 4 skipped |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 24 enforced |
| Open correctness gaps | One filed (OPEN): **GL-033** (`UPDATE_C_AUDIT` — `MobInstance.get_curr_stat` lower clamp is 0, ROM uses min 3; now reachable via a negative stat affect). GL-032 closed (2.12.11). |
| Active focus | cross-file invariants probe pass |

## Next Intended Task

GL-032 closed. Two options for the next session:

1. **Close GL-033** (`rom-gap-closer GL-033`) — raise `MobInstance.get_curr_stat`
   lower clamp from 0 to ROM's 3 (matching `Character.get_curr_stat`), and
   re-derive the sub-3-stat bash/disarm/dirt-kick fixtures in
   `tests/test_skill_combat_rom_parity.py` against ROM `get_curr_stat`. Small,
   but it touches combat-parity expectations — read each affected fixture's
   intended mob stats before changing assertions.
2. **Resume the cross-file-invariants probe pass** — remaining candidates:
   position transitions, group/follower chain, and the broader INV-025 sweep
   (non-combat `_push_message`/`broadcast_room` narration where the matching
   ROM site uses `act()`).

Method: probe-then-scope (read ROM C contract → read Python equivalent →
one failing test for the contract → close as a gap or file as next INV-NNN).
