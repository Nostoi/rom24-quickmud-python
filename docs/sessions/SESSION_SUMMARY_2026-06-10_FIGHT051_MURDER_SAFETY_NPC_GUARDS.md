# Session Summary — 2026-06-10 — FIGHT-051 _murder_safety_check victim-NPC guards

## Scope

Continuation from v2.13.96 (FIGHT-050 closed). Active pass: cross-file invariants.
This session closed FIGHT-051 — `_murder_safety_check` in `mud/commands/murder.py` was missing
the same two victim-NPC guards that FIGHT-050 added to `is_safe`. The structural divergence:
ROM `do_murder` calls `is_safe(ch, victim)` first (line 2861), so those guards are reached for
the murder path in ROM. Python `do_murder` bypasses `is_safe` and calls `_murder_safety_check`
directly, so the victim-NPC guards had to be duplicated there explicitly.

## Outcomes

### FIGHT-051 `_murder_safety_check` missing ACT_PET and AFF_CHARM non-owner guards — ✅ FIXED (2.13.97)

- **Python**: `mud/commands/murder.py:_murder_safety_check`
- **ROM C**: `src/fight.c:2861` (`do_murder` → `is_safe` call) + `:1059`/`:1067`
- **Gap**: `_murder_safety_check` had the charm-master guard for the ATTACKER but not the
  victim-side guards. A PC could murder a pet NPC (should be blocked by ROM `:1059`), and
  could murder a charmed NPC they don't own (should be blocked by ROM `:1067`).
- **Fix**: Added `if victim_is_npc and not getattr(char, "is_npc", False)` sub-block after
  the kill-stealing check:
  1. `victim_act & ActFlag.PET` → `"But {name} looks so cute and cuddly..."` (ROM `:1059`)
  2. `victim_affected & AffectFlag.CHARM and victim.master is not char` →
     `"You don't own that monster."` (ROM `:1067`)
- **Impact analysis**: LOW risk — 1 direct caller (`do_murder`).
- **Tests**: `tests/integration/test_fight051_murder_safety_npc_guards.py` — **4/4 passing**
  - `test_fight051_murder_blocked_on_pet_npc` — guard fires with cuddly message
  - `test_fight051_murder_allowed_on_plain_npc` — baseline allowed
  - `test_fight051_murder_blocked_on_charmed_npc_not_owned` — guard fires with ownership message
  - `test_fight051_murder_allowed_on_own_charmed_npc` — owner is not blocked

## Files Modified

- `mud/commands/murder.py` — FIGHT-051: added victim-NPC sub-block (ACT_PET + AFF_CHARM
  non-owner) after kill-stealing check in `_murder_safety_check`
- `tests/integration/test_fight051_murder_safety_npc_guards.py` — new file, 4 enforcement tests
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-051 filed and flipped ✅ FIXED (2.13.97)
- `CHANGELOG.md` — `[2.13.97]` Fixed entry for FIGHT-051
- `pyproject.toml` — 2.13.96 → 2.13.97

## Test Status

- `pytest tests/integration/test_fight051_murder_safety_npc_guards.py -v` — **4/4 passing**
- `pytest tests/integration/test_fight04*.py tests/integration/test_fight05*.py` — **39/39 passing**
- Full suite: not re-run this session

## Next Steps

Cross-file invariants remains the active pass. Next free INV ID: **INV-044**.

1. **INV-044 candidate — `stop_fighting` both-sides invariant** — Probe whether `stop_fighting`
   in `mud/combat/engine.py` clears both sides of the combat pointer (`ch.fighting = None` AND
   `opponent.fighting = None`) to match ROM `src/fight.c:1221-1241`. A one-sided clear leaves a
   ghost fighting pointer that could cause infinite combat loops. Method: read ROM C → read Python
   `stop_fighting` → write one failing test → file as INV-044 if cross-module.

2. **FIGHT-052 candidate — `_kill_safety_message` NPC-attacker-vs-PC safe room ordering** —
   In ROM `is_safe`, the NPC-attacker-vs-PC branch checks safe room FIRST (`:1083`) then the
   charmed-mob guard (`:1087`). In `_kill_safety_message` (combat.py), the charmed-mob guard
   is checked FIRST (lines 71-74), then safe room (lines 75-76). This ordering diverges from
   ROM. Low severity since both paths return a message, but the wrong message may reach the
   player for a charmed-mob-in-safe-room scenario. Quick read-and-compare to confirm.
