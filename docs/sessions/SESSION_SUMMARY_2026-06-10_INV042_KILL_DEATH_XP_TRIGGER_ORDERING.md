# Session Summary — 2026-06-10 — INV-042 Kill-Death-XP-Trigger Ordering

## Scope

Continuation from v2.13.83 (INV-006 position-ordering sub-contract). Active pass: cross-file
invariants. Session picked up the two remaining probe candidates from the previous handoff:
(1) `mob_update` loop contracts and (2) Group XP delivery ordering.

**mob_update probe** — confirmed Python `mobile_update` in `mud/ai/__init__.py` uses
`list(character_registry)` — a full snapshot identical in semantics to ROM's `ch_next`
pre-cache in `src/update.c:mobile_update`. The `room is None` check additionally skips any
extracted mob still in the snapshot. INV-017 already documents this pattern for `char_update`;
`mobile_update` uses the identical approach. No new gap; no new INV row needed. (Note: the
SESSION_STATUS.md had stale line references claiming `mobile_update` was at `src/update.c:893-983`;
the function actually starts at line 408. The status stale note was noted and not forwarded.)

**Group XP delivery ordering probe** — `src/fight.c:883-924` mandates a three-step call order
in the death path: `group_gain` → `mp_death_trigger` (TRIG_DEATH) → `raw_kill`. Python
`_handle_death` already implements the correct order, but no enforcement test locked it.
Filed as INV-042 and locked with two mutation-verified call-order spy tests. Session ends at v2.13.84.

## Outcomes

### INV-042 KILL-DEATH-XP-TRIGGER-ORDERING — ✅ ENFORCED (new)

- **ROM C**: `src/fight.c:883-924` — `group_gain(ch, victim)` (line 883) → `mp_percent_trigger(TRIG_DEATH)` (line 921, gated on `HAS_TRIGGER`) → `raw_kill(victim)` (line 924)
- **Python**: `mud/combat/engine.py:_handle_death` lines 1351-1368 — correct ordering already present
- **Gap before**: ordering was correct but not locked; any refactor could silently swap calls
- **Fix**: two mutation-verified call-order spy tests in `tests/integration/test_inv042_kill_death_xp_trigger_ordering.py`:
  - `test_kill_death_xp_trigger_ordering_with_trig_death` — asserts `["group_gain", "mp_death_trigger", "raw_kill"]` when victim has TRIG_DEATH; patches all three callees as spies plus surrounding noise (`_send_wiznet_death`, `_clear_pk_flags`, `_handle_auto_actions`)
  - `test_kill_xp_before_raw_kill_no_trig_death` — asserts `["group_gain", "raw_kill"]` when no TRIG_DEATH; XP-before-kill is unconditional
- **Mutation verification**: both tests capture the actual call sequence in a `call_log` list; swapping any adjacent pair in `_handle_death` produces a different list → assertion fails (RED)
- **Rationale for ordering**: `group_gain` reads `victim.level`/`victim.exp` (must precede extraction); `TRIG_DEATH` fires while victim is still in registry with `position = STANDING` (must precede extraction); `raw_kill` extracts victim from registry (always last)
- **Tests**: `pytest tests/integration/test_inv042_kill_death_xp_trigger_ordering.py` — **2/2 passing**

### mob_update loop contracts — ✅ CONFIRMED NO GAP

- ROM `src/update.c:mobile_update` (line 408, not 893-983 as stale status doc stated) uses `ch_next = ch->next` pre-cache before every loop body — snapshot-safe mid-iteration extraction.
- Python `mud/ai/__init__.py:mobile_update` uses `for mob in list(character_registry):` — full snapshot equivalent. Same pattern as INV-017 (`char_update`).
- No divergence found; no new INV row needed.

## Files Modified

- `tests/integration/test_inv042_kill_death_xp_trigger_ordering.py` — new file, 2 enforcement tests (+148 lines)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-042 row added (27 enforced, next free: INV-043); maintenance budget note updated
- `CHANGELOG.md` — `[2.13.84]` Fixed entry
- `pyproject.toml` — 2.13.83 → 2.13.84

## Test Status

- `pytest tests/integration/test_inv042_kill_death_xp_trigger_ordering.py -v` — **2/2 passing**
- Full suite: **5552 passed, 4 skipped** (was 5550; +2 new enforcement tests)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-043**.

Both session probe candidates are now resolved:
- ✅ `mob_update` loop contracts — confirmed no gap (Python snapshot ≡ ROM `ch_next`)
- ✅ Group XP delivery ordering — locked as INV-042

Remaining probe candidates (none yet covered by an INV row):

1. **Group XP delivery during PC-death XP penalty** — `_handle_death` line 1352-1358 computes
   the PC dying penalty (`floor - victim.exp` × 2/3 + 50) using `c_div`. Cross-file: `c_div` vs
   bare `//` for a *negative* operand (`floor - victim.exp` can be negative when over-level). This
   is a signed-math site (MATH class) not yet reviewed under the INV lens.
2. **`char_update` autosave slot coherence** — ROM `src/update.c:686-700` uses a `save_number`
   modulo fan-out to avoid saving all PCs every tick. Python `mud/game_loop.py:char_update`
   has an equivalent slot check; cross-file contract is that the slot distribution and the
   trigger condition (`desc is not None`) match ROM. INV-038 covers the idle-timer reset path
   but not the save-slot fan-out.
3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
