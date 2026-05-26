# Session Summary — 2026-05-26 — `do_slay` routes through `raw_kill` (2.9.48)

## Scope

Continuation of the 2026-05-26 session series. INV-020 fully enforced
in 2.9.47 (pushed). Probe-then-scope: TRIG_KILL / TRIG_DEATH dispatch
contract. Read ROM `src/fight.c:725-745, 905-924, 3252-3287` vs Python
`mud/combat/engine.py:520-602` and `mud/commands/imm_load.py:290-321`.

The main dispatch sites (fight.c:740 TRIG_KILL on first hit;
fight.c:918 TRIG_DEATH before raw_kill) matched ROM cleanly — no gap.
The probe surfaced an adjacent bug: `do_slay` was calling a stripped
local `_extract_char` stub instead of `raw_kill`, leaking the entire
death pipeline (corpse, death_cry, gold drop, INV-020 cleanup).

## Outcomes

### `SLAY-001` — ✅ FIXED (`f4da2a7`, 2.9.48)

- **Python**: `mud/commands/imm_load.py:do_slay` (line 319) — replaced
  `_extract_char(victim)` with `raw_kill(victim)` (lazy import of
  `mud.combat.death.raw_kill`). The slain NPC now goes through the
  full ROM death pipeline.
- **ROM C**: `src/fight.c:3285` — `do_slay` calls `raw_kill(victim)`
  directly (deliberately skipping TRIG_DEATH, which `damage()` would
  have fired). raw_kill produces corpse + death_cry + gold drop and
  runs the INV-020 cleanup chain.
- **Gap (pre-fix)**: the local `_extract_char` stub
  (`mud/commands/imm_load.py:351`) only stops fighting, unlinks from
  `room.people`, and removes from `registry.char_list`. No corpse,
  no death_cry, no gold drop, no INV-020 cleanup — charmed pets and
  group followers leaked with dangling pointers when an immortal
  slew their owner.
- **Probe finding (not a gap)**: TRIG_KILL and TRIG_DEATH dispatch
  in the main combat path (`engine.py:520-602`) match ROM. Python's
  try/finally restoring `victim.position` to DEAD after TRIG_DEATH
  (where ROM leaves it STANDING) is a benign cosmetic divergence —
  raw_kill is called immediately after either way.
- **Tests**: `tests/integration/test_slay_routes_through_raw_kill.py`
  — 1/1:
  - `test_slay_produces_corpse_for_npc` — pins the visible
    corpse-spawn contract. The pet/follower legs are already locked
    by INV-020's test grid (the fix shares `raw_kill`, so all four
    INV-020 sub-contracts come along for free).
  Full suite: **4774 passed, 4 skipped** in 457s.
- **No new INV row** — single-function intra-module fix.

### Deferred (next gap-closer candidates)

- **`do_slay` missing TO_VICT / TO_NOTVICT broadcasts** — ROM
  `src/fight.c:3282-3284` calls three `act` messages
  ("You slay $M…", "$n slays you…", "$n slays $N…") before
  `raw_kill`. Python only returns the TO_CHAR message. Separate
  one-line fix.
- **`do_purge` uses the same stripped `_extract_char` stub** —
  3 call sites in `mud/commands/imm_load.py` (lines 187, 216, 220).
  ROM `do_purge` (`src/act_wiz.c:2645-2647`) calls `extract_char`
  (the chokepoint mapped to `mud/mob_cmds.py:_extract_character`),
  which runs the INV-020 cleanup chain. Python's purge leaks pets/
  followers the same way slay did. Adjacent INV-020 leg.

## Files Modified

- `mud/commands/imm_load.py` — `do_slay` calls `raw_kill` instead of
  `_extract_char`
- `tests/integration/test_slay_routes_through_raw_kill.py` — NEW (1 test)
- `CHANGELOG.md` — 2.9.48 section
- `pyproject.toml` — 2.9.47 → 2.9.48

## Test Status

- `tests/integration/test_slay_routes_through_raw_kill.py` — 1/1 ✅
- Slay/imm_load/death-area suites (60 tests) — 60/60 ✅
- Full suite: **4774 passed, 4 skipped** in 457s wall-clock

## Next Steps

1. **Push approval** required for 2.9.48 (`f4da2a7`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.48 to origin/master").
2. **GitNexus refresh** — index stale at `069f17f`. Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Adjacent gap-closer**: `do_purge` INV-020 leak (3 call sites).
   ROM mirrors `extract_char` chokepoint; Python calls the stripped
   stub. Same routing fix shape.
4. **`do_slay` broadcast gap** — TO_VICT/TO_NOTVICT act messages.
5. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing
     transition beyond INV-016 / INV-019.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with the dangling pointer
     reconstituted from save format.
