# Session Summary — 2026-06-10 — FIGHT-048 do_murder yell + RECALL-001 gain_exp floor

## Scope

Continuation from v2.13.91 (FIGHT-044/047 check_killer call-sites). Active pass:
cross-file invariants. Session resolved all three suggested probes from the previous
handoff, then filed and closed two gaps discovered during those probes.

**Probe 1 — `check_killer` internal parity audit**: Read ROM C `src/fight.c:1276-1279`
(`IS_NPC(ch) || ch == victim || ch->level >= LEVEL_IMMORTAL || !is_clan(ch) ||
IS_SET(ch->act, PLR_KILLER) || ch->fighting == victim`). The session handoff note said
Python had an `is_clan_member` guard that ROM C "does not have" — this is incorrect.
ROM C line 1277 has `|| !is_clan(ch)` in the same combined early-return block.
Python splits it into a separate `if not is_clan_member(attacker): return` statement —
same logic, different style. **CLEAN — no FIGHT-048 from this probe.**

**Probe 2 — `do_murder` delivery gap**: ROM C `src/fight.c:2888` calls
`do_function(victim, &do_yell, buf)` making the VICTIM yell area-wide. Python built
`yell_msg` but returned it as part of the command response string (sent to attacker)
and never called `do_yell(victim, ...)`. Closed as FIGHT-048. Also surfaced FIGHT-049
(`_murder_safety_check` missing level-difference and other `is_safe` PC-vs-PC guards)
— filed as OPEN.

**Probe 3 — `do_recall` message ordering**: The specific question ("is the recall
message sent after `stop_fighting`?") is CLEAN — Python delivers everything as a
return string, so ordering relative to `stop_fighting` is irrelevant to the player.
Two incidental gaps surfaced: RECALL-001 (`ch.exp -= lose` bypasses `gain_exp` XP
floor — closed) and RECALL-002 (`check_improve` for recall skill not called — filed
OPEN).

## Outcomes

### FIGHT-048 `do_murder` victim yell not delivered — ✅ FIXED (2.13.92)

- **Python**: `mud/commands/murder.py:do_murder` (~`:79-100`)
- **ROM C**: `src/fight.c:2888` — `do_function(victim, &do_yell, buf)`
- **Gap**: ROM makes the VICTIM yell "Help! I am being attacked by X!" area-wide.
  Python built `yell_msg` but returned it to the attacker as the command response,
  silencing the victim and sending no area broadcast. Also returned an extra
  "You attack {victim_name}!" message that ROM never sends.
- **Fix**: added `from mud.commands.communication import do_yell` and
  `from mud.combat.engine import _push_message` imports; replaced the return-string
  with `to_char_yell = do_yell(victim, yell_msg)` + `_push_message(victim, to_char_yell)`
  before `check_killer`; return changed to `""`.
- **Tests**: `tests/integration/test_fight048_murder_yell.py` — **2/2 passing**
  (victim receives "You yell '...'" in messages; return value does not contain
  the yell text)

### RECALL-001 `do_recall` XP floor bypass — ✅ FIXED (2.13.93)

- **Python**: `mud/commands/session.py:do_recall` (~`:391`)
- **ROM C**: `src/act_move.c:1609` — `gain_exp(ch, 0 - lose)`;
  `src/update.c:127` — `ch->exp = UMAX(exp_per_level(ch), ch->exp + gain)`
- **Gap**: Python used `ch.exp -= lose` directly, bypassing the XP floor check.
  A PC with XP within 25-50 of the level floor who recalled in combat would have
  their XP correctly clamped at the floor by ROM but go below the floor in Python.
- **Fix**: replaced `ch.exp -= lose` with `gain_exp(ch, -lose)` (lazy import from
  `mud.advancement`).
- **Tests**: `tests/integration/test_recall001_exp_floor.py` — **1/1 passing**
  (character with exp=floor+10, lose=50, no desc → exp clamped at floor=1000, not 960)

## Open Gaps Filed This Session

- **FIGHT-049** (`docs/parity/FIGHT_C_AUDIT.md`) — `_murder_safety_check` bypasses
  `is_safe(ch, victim)`. Missing level-difference check (`ch->level > victim->level + 8`
  → "Pick on someone your own size."), ACT_PET check, charm-ownership check, NPC
  charmed mob PC-attack guard. `🔄 OPEN`.
- **RECALL-002** (`docs/parity/ACT_MOVE_C_AUDIT.md`) — `check_improve` for recall
  skill not called. ROM lines 1601, 1610 call `check_improve(ch, gsn_recall, ...)` on
  failure and success. Python has stale TODO comments. Minor gameplay gap (skill XP
  tracking only). `🔄 OPEN`.

## Files Modified

- `mud/commands/murder.py` — FIGHT-048: added `do_yell` + `_push_message` imports;
  victim yell delivered via `do_yell(victim, yell_msg)` + push to victim;
  return changed to `""`
- `mud/commands/session.py` — RECALL-001: `ch.exp -= lose` → `gain_exp(ch, -lose)`
- `tests/integration/test_fight048_murder_yell.py` — new file, 2 enforcement tests
- `tests/integration/test_recall001_exp_floor.py` — new file, 1 enforcement test
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-048 filed + ✅ FIXED; FIGHT-049 filed OPEN
- `docs/parity/ACT_MOVE_C_AUDIT.md` — RECALL-001 filed + ✅ FIXED; RECALL-002 filed OPEN
- `CHANGELOG.md` — `[2.13.92]` and `[2.13.93]` Fixed entries
- `pyproject.toml` — 2.13.91 → 2.13.93

## Test Status

- `pytest tests/integration/test_fight048_murder_yell.py -v` — **2/2 passing**
- `pytest tests/integration/test_recall001_exp_floor.py -v` — **1/1 passing**
- `pytest tests/integration/test_recall_train_commands.py -v` — **19/19 passing**
- Full integration suite: **2903 passed, 3 skipped** (117.5s)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.
Suggested next candidates:

1. **FIGHT-049 — `_murder_safety_check` level-difference gap** — `do_murder` missing
   `ch->level > victim->level + 8` check ("Pick on someone your own size.") and other
   `is_safe` PC-vs-PC guards (ACT_PET, charm-ownership, NPC charmed-mob). Requires
   understanding how `_murder_safety_check` vs `is_safe` should be reconciled — may
   need `is_safe` itself extended (PC-vs-PC branch) before `do_murder` can just call it.

2. **RECALL-002 — `check_improve` for recall skill** — ROM calls
   `check_improve(ch, gsn_recall, FALSE, 6)` on failure and `check_improve(ch, gsn_recall,
   TRUE, 4)` on success. Python has stale `# TODO: check_improve(...)` comments. Minor fix.

3. **`do_murder` `is_safe` bypass (`_murder_safety_check` vs `is_safe`)** — Broader audit:
   Python's `is_safe` (`mud/combat/safety.py`) also lacks the PC-vs-PC clan/level checks
   (`!is_clan(ch)`, `!is_clan(victim)`, `ch->level > victim->level + 8`). These live in
   `_kill_safety_message` for `do_kill` and `_murder_safety_check` for `do_murder`. Assessing
   whether to consolidate into `is_safe` or keep the split is a cross-file design question.
