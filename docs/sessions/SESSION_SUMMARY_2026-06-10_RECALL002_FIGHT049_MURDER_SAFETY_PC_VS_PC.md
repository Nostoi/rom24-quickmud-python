# Session Summary — 2026-06-10 — RECALL-002 check_improve + FIGHT-049 murder safety PC-vs-PC

## Scope

Continuation from v2.13.94 (FIGHT-048 + RECALL-001 closed). Active pass: cross-file
invariants. Session picked up the two OPEN gaps left by the previous handoff — RECALL-002
(`check_improve` for recall skill) and FIGHT-049 (`_murder_safety_check` missing PC-vs-PC
clan/level guards) — and closed both. FIGHT-050 filed for remaining `is_safe` gaps in
`mud/combat/safety.py` that were scoped out of FIGHT-049 due to CRITICAL blast radius.

## Outcomes

### RECALL-002 `do_recall` check_improve not called — ✅ FIXED (2.13.94)

- **Python**: `mud/commands/session.py:do_recall` (~`:353`, `:391`)
- **ROM C**: `src/act_move.c:1601` — `check_improve(ch, gsn_recall, FALSE, 6)` on failure;
  `src/act_move.c:1610` — `check_improve(ch, gsn_recall, TRUE, 4)` on success
- **Gap**: Both `check_improve` calls existed only as `# TODO: check_improve(...)` stubs.
  The recall skill never improved from use — skill XP tracking was completely silent.
- **Fix**: Added `from mud.skills.registry import check_improve` top-level import in
  `session.py`; replaced `# TODO` stubs with `check_improve(ch, "recall", False, 6)`
  (failure) and `check_improve(ch, "recall", True, 4)` (success). Note: `number_percent`
  is imported lazily inside `do_recall`'s body, so patching it requires targeting
  `"mud.utils.rng_mm.number_percent"` (the source module), not the session-module name.
- **Tests**: `tests/integration/test_recall002_check_improve.py` — **2/2 passing**
  (failure path calls `check_improve(ch, "recall", False, 6)`; success path with `skill=0`
  calls `check_improve(ch, "recall", True, 4)`)

### FIGHT-049 `_murder_safety_check` PC-vs-PC clan/level guards missing — ✅ FIXED (2.13.95)

- **Python**: `mud/commands/murder.py:_murder_safety_check`
- **ROM C**: `src/fight.c:1096-1121` — PC-doing-the-killing `else` branch inside `is_safe`
- **Gap**: `_murder_safety_check` had room-safe, kill-stealing, and charm-master guards but
  none of the PC-vs-PC clan/level path. A non-clan PC could freely murder any other PC;
  a high-level PC could murder a low-level PC; non-clan victims were unprotected.
- **Fix**: Added PC-vs-PC block guarded by `not char.is_npc and not victim.is_npc`:
  (1) `is_clan_member(char)` → "Join a clan if you want to kill players."
  (2) `victim.act & PlayerFlag.KILLER or ... PlayerFlag.THIEF` → return None (allow attack)
  (3) `is_clan_member(victim)` → "They aren't in a clan, leave them alone."
  (4) `char.level > victim.level + 8` → "Pick on someone your own size."
  Imported `is_clan_member` from `mud.characters` and `PlayerFlag` from `mud.models.constants`.
- **Impact analysis**: `_murder_safety_check` — LOW risk, 1 direct caller (`do_murder`).
- **Tests**: `tests/integration/test_fight049_murder_safety_pc_vs_pc.py` — **6/6 passing**
  (non-clan attacker blocked; KILLER/THIEF bypass; non-clan victim blocked; level-diff blocked;
  equal-clan-level baseline allowed)

## Open Gaps Filed This Session

- **FIGHT-050** (`docs/parity/FIGHT_C_AUDIT.md`) — `mud/combat/safety.py:is_safe` missing
  three guards from ROM C `src/fight.c:1040-1094`: ACT_PET check, charm-ownership-for-non-owner
  check, NPC charmed-mob-PC-attack guard. Scoped out of FIGHT-049 due to `is_safe` CRITICAL
  blast radius (46 transitive impacts). `🔄 OPEN`.

## Files Modified

- `mud/commands/session.py` — RECALL-002: top-level import `check_improve`; replaced TODO stubs
  with `check_improve(ch, "recall", False, 6)` / `check_improve(ch, "recall", True, 4)`
- `mud/commands/murder.py` — FIGHT-049: added `is_clan_member` + `PlayerFlag` imports;
  PC-vs-PC waterfall block in `_murder_safety_check`
- `tests/integration/test_recall002_check_improve.py` — new file, 2 enforcement tests
- `tests/integration/test_fight049_murder_safety_pc_vs_pc.py` — new file, 6 enforcement tests
- `docs/parity/ACT_MOVE_C_AUDIT.md` — RECALL-002 row flipped ✅ FIXED (2.13.94)
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-049 row flipped ✅ FIXED (2.13.95); FIGHT-050 filed OPEN
- `CHANGELOG.md` — `[2.13.95]` Fixed entry for FIGHT-049
- `pyproject.toml` — 2.13.94 → 2.13.95

## Test Status

- `pytest tests/integration/test_recall002_check_improve.py -v` — **2/2 passing**
- `pytest tests/integration/test_fight049_murder_safety_pc_vs_pc.py -v` — **6/6 passing**
- `pytest tests/integration/test_fight0*.py tests/integration/test_recall*.py -v` — **65/65 passing**
- Full suite: not re-run this session (prior session: 2903 passed, 3 skipped)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.
Suggested next candidates:

1. **FIGHT-050 — `mud/combat/safety.py:is_safe` missing NPC-attacker guards** — ACT_PET check
   ("But $N looks so cute and cuddly..."), charm-ownership-for-non-owner ("You don't own that
   monster."), NPC charmed-mob-PC-attack guard ("Players are your friends!"). Requires caution:
   `is_safe` has 46 transitive impacts (CRITICAL blast radius). Approach: write failing tests
   first, then limit fix to the three missing sub-arms inside the existing victim-NPC and NPC-
   attacker branches; do NOT restructure the function. Run full integration suite after.

2. **Cross-file probe — `do_kill` safety path** — Python `do_kill` in `mud/commands/combat.py`
   has its own `_kill_safety_message` helper. Compare it against ROM `is_safe` to confirm the
   same PC-vs-PC clan/level checks exist there too (they were added to `_murder_safety_check`
   this session but `_kill_safety_message` may have the same gap). Quick grep+read probe.

3. **INV-044 candidate — `stop_fighting` invariant** — Probe whether `stop_fighting` always
   clears both sides of the combat pointer (`ch.fighting = None` + `opponent.fighting = None`)
   to match ROM `src/fight.c:1221-1241`. A one-sided clear could leave a ghost fighting pointer
   causing infinite combat loops.
