# Session Summary — 2026-05-26 — `check_assist` dispatch scope (2.9.44)

## Scope

Resuming from 2.9.43 (INV-026 VIOLENCE-TRIGGER-DISPATCH-SCOPE shipped to
origin/master; 4760 passed, 4 skipped). The 2.9.43 SESSION_SUMMARY
flagged a documented adjacent gap: `check_assist` (ROM
`src/fight.c:90`) was misplaced inside `mud/combat/engine.py:multi_hit`
instead of in `violence_update` after `multi_hit` returns. Same
misplacement shape as INV-026, intentionally split off for commit
hygiene. This session closes it.

GitNexus index refreshed at session start (was stale at `6b21fa9` from
the 2.9.43 push). Combat files still hit the 32 KB scope-extraction cap
on rc.13 (engine.py, game_loop.py, mob_cmds.py, mobprog.py); fell back
to grep for caller analysis, per CLAUDE.md.

## Outcomes

### `check_assist` misplacement — ✅ CLOSED (`cf126f0`)

- **Python**:
  - `mud/combat/engine.py:multi_hit` (lines 314 area) — removed the
    `from mud.combat.assist import check_assist; check_assist(...)`
    call after the victim-died guard. Replaced with a 5-line comment
    pointing to `violence_tick` as the canonical dispatch site
    (matches INV-026 comment shape).
  - `mud/game_loop.py:violence_tick` (lines 1336-1366 area) — added
    `check_assist(ch, victim)` between the post-`multi_hit`
    victim-died re-read and the NPC trigger dispatch, mirroring ROM
    `src/fight.c:84-98` ordering. Added a second re-read of
    `attacker.fighting is victim` after `check_assist` so a helper's
    killing blow during the assist round skips the
    `TRIG_FIGHT`/`TRIG_HPCNT` dispatch (ROM falls out via the same
    pointer guard).
- **ROM C**: `src/fight.c:60-99 violence_update`. Per-iteration
  sequence: `multi_hit(ch, victim, TYPE_UNDEFINED)` →
  `if ((victim = ch->fighting) == NULL) continue;` →
  `check_assist(ch, victim);` → `if (IS_NPC(ch))` then HPCNT/FIGHT.
- **Pre-2.9.44 symptom**: every direct caller of `multi_hit` provoked
  another assist round. The three caller sites:
  - `mud/combat/assist.py` — `check_assist` recursively called
    `multi_hit(rch, victim, TYPE_UNDEFINED)` on helpers (ROM
    `src/fight.c:122, 132, ~170`). That `multi_hit` would then
    re-enter `check_assist` from inside, kicking off another assist
    sweep per helper joining combat. ROM only sweeps once per
    `violence_update` iteration.
  - `mud/spec_funs.py` — special-function mob attacks (`spec_cast_*`,
    breath specs) called `multi_hit` directly with no business
    triggering assist.
  - `mud/mob_cmds.py` — the `mob kill` mobprog directive called
    `multi_hit` and likewise pulled in assist that ROM never fires
    from this path.
- **Tracker update**: folded under INV-026's "Adjacent check_assist
  misplacement closed (2.9.44)" note instead of creating a new
  INV-NNN. Both contracts derive from `src/fight.c:60-99
  violence_update`; splitting them into two rows would have
  artificially inflated the invariant budget.
- **Test rewrites**:
  - `tests/test_combat_assist.py::TestAssistIntegration::test_assist_triggered_during_combat`
    asserted that calling `multi_hit` directly should trigger an
    assist round — that contradicts ROM (per AGENTS.md, "a test
    asserting a behavior that contradicts ROM C is a bug in the
    test, not in the implementation"). Renamed to
    `test_assist_triggered_during_violence_tick` and rewritten to
    drive `mud.game_loop.violence_tick(do_combat=True)` instead.
- **Tests**:
  `tests/integration/test_check_assist_dispatch_scope.py` — 3/3:
  - `test_multi_hit_does_not_call_check_assist_directly` — proves
    the bug pre-fix; calls `multi_hit` and asserts no
    `check_assist` invocation.
  - `test_violence_tick_calls_check_assist_after_multi_hit` — the
    positive case; drives `violence_tick(do_combat=True)` and
    asserts `check_assist(Guard, Hero)` was recorded.
  - `test_violence_tick_skips_check_assist_when_victim_died` —
    stubs `multi_hit` to clear `attacker.fighting` (simulating a
    killing blow) and asserts no `check_assist` call.
  Full suite: **4767 passed, 4 skipped** in 666s.

## Files Modified

- `mud/combat/engine.py` — removed `check_assist` import + call from
  `multi_hit`, replaced with comment pointing to `violence_tick`
- `mud/game_loop.py` — added `check_assist` call between the
  post-`multi_hit` victim re-read and the NPC trigger dispatch; added
  the second post-`check_assist` re-read of `attacker.fighting`
- `tests/integration/test_check_assist_dispatch_scope.py` — NEW
  (3 tests)
- `tests/test_combat_assist.py::TestAssistIntegration` — renamed +
  rewritten to drive `violence_tick`; dropped now-unused `multi_hit`
  import (the lone in-module usage moved out)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-026 "Adjacent
  check_assist misplacement closed (2.9.44)" note replaces the prior
  "Out of scope but adjacent" deferral
- `CHANGELOG.md` — 2.9.44 section
- `pyproject.toml` — 2.9.43 → 2.9.44

## Test Status

- `tests/integration/test_check_assist_dispatch_scope.py` — 3/3 ✅
- `tests/test_combat_assist.py` — 22/22 ✅ (incl. the rewrite)
- `tests/integration/test_inv026_violence_trigger_dispatch.py` — 3/3 ✅
- `tests/integration/test_hpcnt_once_per_pulse.py` — 2/2 ✅
- `tests/test_mobprog_triggers.py` — 6/6 ✅
- `tests/integration/test_mob_ai.py` — 15/15 ✅
- Full suite: **4767 passed, 4 skipped** in 666s wall-clock

## Next Steps

1. **GitNexus refresh** — index stale again at `5d3ce9d` (one commit
   behind after `cf126f0`). Cheap; run `npx gitnexus analyze
   --skip-agents-md` before the next probe so impact-analysis numbers
   reflect the new state.
2. **Continue probe-then-scope at 23/~20 INV budget**. The combat-
   trigger contract is now fully ROM-correct
   (`multi_hit → victim guard → check_assist → re-guard → IS_NPC
   then HPCNT/FIGHT`); no more deferred items in this area.
   Candidate areas not yet covered by an INV row:
   - **Affect ticks** — `mud/handler.py:affect_update` /
     `Character.affect_remove` cross-module contracts (e.g. wear-off
     message ordering vs `affect_modify(ch, paf, FALSE)`, and the
     follower-charm-expiry race covered partially by INV-015).
   - **Group/follower chain on raw_kill** — INV-020 covers
     `die_follower`; the adjacent `nuke_pets` /
     `stop_follower(pet)` chain on PC quit may have a contract gap.
   - **Mob script triggers beyond TRIG_FIGHT/HPCNT** — TRIG_KILL,
     TRIG_DEATH dispatch sites (the engine.py audit noted they're
     wired correctly but no INV row pins it).
3. **Push approval** required before `2.9.44` reaches origin/master.
   Per standing instruction: do NOT push without explicit
   per-cluster user approval ("yes push v2.9.44 to origin/master").
