# Session Summary — 2026-05-31 — GL-032 mob affect application

## Scope

Picked up from the GL-031 handoff (`SESSION_STATUS.md` listed **GL-032** as the
single open correctness gap). Closed GL-032 — `MobInstance.apply_spell_effect`
ignored the `ac_mod` / `saving_throw_mod` / `stat_modifiers` / `sex_delta` affect
locations, so a charmed pet (NPC) gained nothing from armor / giant-strength /
save-modifying / sex-changing buffs except hitroll/damroll — via the standard
gap-closer TDD flow (failing test → fix → tracker/changelog → commit). Two
advisor course-corrections en route; a newly-reachable stat-floor divergence was
filed as **GL-033 (open)**.

## Outcomes

### `GL-032` — ✅ FIXED (2.12.11, commit `42270566`)

- **Python**: `mud/spawning/templates.py` — `MobInstance.apply_spell_effect` /
  `remove_spell_effect` / `get_curr_stat`; new `mod_stat` field, new
  `_apply_stat_modifier` / `_shift_sex` helpers.
- **ROM C**: `src/handler.c:1018-1164` (`affect_modify`), `:868-874`
  (`get_curr_stat`). `affect_modify` is one function for PCs and NPCs — it
  applies every `APPLY_*` location uniformly.
- **Gap**: GL-032 — the mob applier was a "simplified" version that moved only
  `hitroll`/`damroll` and set the affect flag, silently ignoring `ac_mod`,
  `saving_throw_mod`, `stat_modifiers`, and `sex_delta`. `Character.apply_spell_effect`
  applies all of them; `MobInstance`'s did not, so charmed-pet buffs were
  no-ops on those locations (both live and on reload).
- **Fix**: added `MobInstance.mod_stat` (ROM stores stat affects in
  `ch->mod_stat[]` for NPCs too); `get_curr_stat` now reads `perm_stat + mod_stat`.
  `apply_spell_effect` applies — and `affect_join`-merges on a re-cast — `ac_mod`
  (across all four armor classes), `saving_throw_mod`, `stat_modifiers` (via new
  `_apply_stat_modifier`), and `sex_delta` (via new `_shift_sex`, stored as an
  `int` to match `Character` and the reload path). `remove_spell_effect` unwinds
  all four symmetrically. **No serializer change was needed**: `_serialize_pet`
  already persists the folded-in runtime `armor`/`saving_throw`/`mod_stat`/`sex`,
  and GL-031's data-only restore re-counts nothing — so reload carries the bonus
  counted exactly once.
- **Tests**: `tests/integration/test_gl032_mob_affect_application.py` (3 tests,
  passing). Live ac/save/stat/sex apply (verified **red-first** — armor stayed at
  base `-150` instead of `-170`), symmetric removal back to base, and a
  save/reload-counted-once round-trip (armor + effective STR + saving_throw +
  sex; discriminating — drops to `perm+0` or double-counts if either mod_stat
  serialization or data-only restore breaks).

### `GL-033` — ⚠️ FILED (commit `42270566`, OPEN)

- **Python**: `mud/spawning/templates.py` — `MobInstance.get_curr_stat`.
- **ROM C**: `src/handler.c:868-874` (`get_curr_stat` = `URANGE(3, perm+mod, max)`).
- **Gap**: the mob `get_curr_stat` clamps its lower bound to `0`
  (`max(0, min(25, perm+mod))`) where ROM uses a minimum of **3**, uniformly for
  PCs and NPCs. Latent before GL-032 (a `from_prototype` mob has `perm_stat ≥ ~11`),
  but GL-032's new `mod_stat` makes sub-3 effective stats reachable via a negative
  stat affect (a STR-draining debuff).
- **Surfaced by**: closing GL-032 — raising the floor to 3 (the advisor's
  suggested opportunistic fix) broke 4 `tests/test_skill_combat_rom_parity.py`
  bash/disarm/dirt-kick tests that construct `MobInstance(perm_stat=[0,…])`
  fixtures directly, confirming the floor is behaviorally **live, not inert**.
- **Fix (deferred)**: raise the mob floor to 3 (matching `Character.get_curr_stat`)
  and re-derive the affected skill-parity fixtures against ROM `get_curr_stat`.
  Scoped out of GL-032 to keep that fix to affect *application*.

## Files Modified

- `mud/spawning/templates.py` — `MobInstance.mod_stat` field; `get_curr_stat`
  reads perm+mod; `apply_spell_effect`/`remove_spell_effect` apply/unwind+merge
  ac/saving/stat/sex; new `_apply_stat_modifier` / `_shift_sex` helpers.
- `tests/integration/test_gl032_mob_affect_application.py` — new regression
  (3 tests: live apply, symmetric removal, round-trip-counted-once).
- `docs/parity/UPDATE_C_AUDIT.md` — GL-032 flipped ⚠️ OPEN → ✅ FIXED; new
  GL-033 ⚠️ OPEN row; GL-028's now-superseded "never applies ac/saving/stat/sex"
  note annotated with a GL-032 forward-ref.
- `CHANGELOG.md` — added `Fixed: GL-032` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.10 → 2.12.11.

## Test Status

- `tests/integration/test_gl032_mob_affect_application.py` — 3/3 passing
  (test 1 verified red-first before the fix).
- `tests/test_skill_combat_rom_parity.py` — 71/71 passing (the 4 that the
  reverted min-3 floor would have broken stay green under the kept min-0 floor).
- GL-affect family + charm + persistence sweep (GL-026/027/028/031/032 +
  inv015 + charm + spell_affects + `test_affects.py`) — 64/64 passing.
- `ruff check tests/integration/test_gl032_mob_affect_application.py` — clean;
  `mud/spawning/templates.py` — 0 new errors (10 pre-existing in-file, identical
  on master).
- `gitnexus_detect_changes` — LOW risk, `affected_count: 0` (scope confined to
  `MobInstance` methods/fields).
- Full suite: **5134 passed, 4 skipped**.

## Next Steps

Per-file audit tracker remains exhausted; cross-file-invariants is the active
mode. Options for the next session:

1. **Close GL-033** (`rom-gap-closer GL-033`) — raise `MobInstance.get_curr_stat`
   lower clamp from 0 to ROM's 3, and re-derive the sub-3-stat
   bash/disarm/dirt-kick fixtures in `tests/test_skill_combat_rom_parity.py`
   against ROM `get_curr_stat`. Small but touches combat-parity expectations —
   read each affected fixture's intended mob stats before changing assertions.
2. **Resume the cross-file-invariants probe pass** — remaining candidates:
   position transitions, group/follower chain, and the broader INV-025 sweep
   (non-combat `_push_message`/`broadcast_room` narration where the matching ROM
   site uses `act()`).

Method: probe-then-scope (read ROM C contract → read Python equivalent → one
failing test for the contract → close as a gap or file as next INV-NNN).
