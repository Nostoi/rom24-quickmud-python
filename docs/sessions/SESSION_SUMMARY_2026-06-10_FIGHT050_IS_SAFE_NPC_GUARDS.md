# Session Summary — 2026-06-10 — FIGHT-050 is_safe NPC guards

## Scope

Continuation from v2.13.95 (RECALL-002 + FIGHT-049 closed). Active pass: cross-file
invariants. This session closed FIGHT-050 — the three guards from ROM `src/fight.c:1040-1094`
that were absent from `mud/combat/safety.py:is_safe`. These had been filed as OPEN during the
FIGHT-049 investigation but deferred due to `is_safe`'s CRITICAL blast radius (46 transitive
impacts). All three guards were already present in `_kill_safety_message` (the `do_kill` path)
but missing from every other caller: spells, backstab, kick, assist, mob specials.

## Outcomes

### FIGHT-050 `is_safe` missing ACT_PET / AFF_CHARM / charmed-mob-PC guards — ✅ FIXED (2.13.96)

- **Python**: `mud/combat/safety.py:is_safe`
- **ROM C**: `src/fight.c:1040-1094`
- **Gap**: Three ROM guards absent from `is_safe`, leaving pets attackable, non-owned charmed
  NPCs attackable, and charmed NPCs able to attack any PC (not just their master's target).
- **Fix**:
  - Inside the `if getattr(victim, "is_npc", False)` block, added a `if not getattr(char, "is_npc", False)` sub-block containing:
    1. `ActFlag.PET` check (ROM `:1059`) → returns `True` (safe/blocked)
    2. `AffectFlag.CHARM` non-owner check (ROM `:1067`) — `victim.affected_by & CHARM` and
       `victim.master is not char` → returns `True`
  - Inside the NPC-attacker-vs-PC block, added the charmed-mob guard before the existing level
    check (ROM `:1087-1093`) — `char.affected_by & CHARM` and `master is not None` and
    `master.fighting is not victim` → returns `True`
  - Added `AffectFlag` to the lazy import line inside `is_safe`.
  - Added `# noqa: C901` to signature (function complexity increased from three guards).
- **Impact analysis**: CRITICAL blast radius pre-fix (46 transitive impacts). Changes are
  purely additive (new True-return paths), confirmed LOW risk by `gitnexus_detect_changes`
  post-commit (only `is_safe`, `is_safe_spell`, and local `proto` variable touched).
- **Tests**: `tests/integration/test_fight050_is_safe_npc_guards.py` — **6/6 passing**
  - `test_fight050_pc_cannot_attack_pet_npc` — guard fires
  - `test_fight050_npc_attacker_can_attack_pet_npc` — guard correctly scoped to PC-only
  - `test_fight050_pc_cannot_attack_charmed_npc_if_not_owner` — guard fires
  - `test_fight050_owner_can_attack_own_charmed_npc` — guard does not fire for owner
  - `test_fight050_charmed_npc_blocked_from_attacking_non_master_target` — guard fires
  - `test_fight050_charmed_npc_allowed_to_attack_masters_target` — guard does not fire when
    master is already fighting victim

## Files Modified

- `mud/combat/safety.py` — FIGHT-050: added PC-attacker sub-block (ACT_PET + AFF_CHARM
  non-owner); added charmed-mob guard in NPC-attacker branch; added `AffectFlag` to lazy import
- `tests/integration/test_fight050_is_safe_npc_guards.py` — new file, 6 enforcement tests
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-050 row flipped ✅ FIXED (2.13.96)
- `CHANGELOG.md` — `[2.13.96]` Fixed entry for FIGHT-050
- `pyproject.toml` — 2.13.95 → 2.13.96

## Test Status

- `pytest tests/integration/test_fight050_is_safe_npc_guards.py -v` — **6/6 passing**
- `pytest tests/integration/test_fight0*.py` — **55/55 passing**
- Full suite: not re-run this session (prior session: 2903 passed, 3 skipped)

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.
Suggested candidates:

1. **Cross-file probe — `stop_fighting` invariant (INV-044 candidate)** — Probe whether
   `stop_fighting` always clears both sides of the combat pointer (`ch.fighting = None` +
   `opponent.fighting = None`) to match ROM `src/fight.c:1221-1241`. A one-sided clear could
   leave a ghost fighting pointer causing infinite combat loops. Method: read ROM C → read
   Python `stop_fighting` in `mud/combat/engine.py` → write one failing test. File as INV-044
   if the contract crosses modules.

2. **Cross-file probe — `do_kill` vs `_murder_safety_check` consistency** — Now that `is_safe`
   has all three NPC guards, verify that `_murder_safety_check` (used by `do_murder`) is still
   consistent with `is_safe` for those paths. The `do_murder` path calls `_murder_safety_check`
   and does NOT call `is_safe` directly — so the new `is_safe` guards do not protect the murder
   path. Grep check: does `_murder_safety_check` have ACT_PET and AFF_CHARM non-owner guards?
   (Quick read of `mud/commands/murder.py` — likely a new gap FIGHT-051.)

3. **FIGHT-051 candidate** — `_murder_safety_check` likely missing ACT_PET and AFF_CHARM
   non-owner guards (it has the charm-master guard for the attacker but not for the victim).
   ROM `do_murder` calls `is_safe(ch, victim)` first (line 2861), so these guards ARE
   reached in ROM for the murder path. Python bypasses them by going directly to
   `_murder_safety_check`. File as FIGHT-051 after confirming with a read of the function.
