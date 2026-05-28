# `game_tick` Invariant Checker — Design

**Date:** 2026-05-28
**Status:** Design — approved in brainstorming, building TDD
**Topic:** An always-on, after-`game_tick` checker that asserts steady-state ROM
structural invariants over the live registries during the test suite, turning
existing `game_tick`-driving tests into continuous parity probes.

## Motivation

The cross-file invariant (INV) layer currently locks each invariant with *one*
dedicated enforcement test. This checker generalizes the strongest, steady-state
invariants into a post-condition that runs after **every** `game_tick` call in
the suite (~17 files / 45 call sites), so any test whose scenario violates a
contract fails — regardless of what it was written to test. It is the
complement to the differential harness (which checks parity against the C
reference); this checks internal structural coherence continuously.

## Decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Hook point | End of `mud/game_loop.py:game_tick`, gated by a module flag (default off) |
| Enablement | Autouse fixture in `tests/conftest.py` sets the flag for the test session; production stays off (zero overhead) |
| Enforcement | Always-on, fix-fallout: violations fail the test; artificial-setup tests opt out via `@pytest.mark.no_invariant_check` |
| v1 invariant set | FIGHTING-COHERENCE (INV-005/006) + ROOM-PEOPLE-COHERENCE (INV-010) only |
| Scope | `game_tick` only (not `process_command`); no production enablement; no CI changes |

## Architecture

```
mud/game_loop.py:game_tick()
    ... existing pulses ...
    if _INVARIANT_CHECK_ENABLED:        # module-level, default False
        check_world_invariants()        # read-only; raises InvariantViolation

mud/diagnostics/invariants.py
    InvariantViolation(AssertionError)
    check_world_invariants()            # walks character_registry / room_registry

tests/conftest.py
    autouse fixture: set mud.game_loop._INVARIANT_CHECK_ENABLED = True
        (honoring @pytest.mark.no_invariant_check to disable per-test)
```

Hooking inside `game_tick` (rather than monkeypatching the imported name)
catches every caller regardless of `import` style. The flag keeps the live game
loop unaffected.

## v1 invariants (steady-state, read-only)

1. **FIGHTING-COHERENCE (INV-005/006)** — for each character with `fighting`
   set: the target is in the **same room**, and is not `DEAD`/extracted. (ROM:
   combat only between co-located, living characters.)
2. **ROOM-PEOPLE-COHERENCE (INV-010)** — for each room, every character in
   `room.people` has `char.room is room`; and every registered character with a
   non-None `room` appears in that room's `people`.

Deferred to follow-up additions (each lands only after the suite is green under
it): REGISTRY-MEMBERSHIP (003), OBJECT-LOCATION-COHERENCE (013), AFFECT-EXPIRY
consistency (015).

## Failure mode

`check_world_invariants()` raises `InvariantViolation` (subclass of
`AssertionError`) with a message naming the invariant and the offending
entities, e.g. `FIGHTING-COHERENCE: 'Tester' fighting 'goblin' but they are in
different rooms (3001 vs 3054)`. The failure surfaces at the `game_tick` call
site in the violating test.

## Fallout triage

Running the always-on checker will likely fail some of the 17 `game_tick` files
that use artificial state. Each failure is triaged as either:
- a **real bug** (the invariant is genuinely broken) → fix it, or
- a **legitimately artificial** unit setup → add `@pytest.mark.no_invariant_check`.

No silent masking; the marker is the only escape hatch and is visible in the
test.

## Testing the checker itself

`tests/test_invariant_checker.py`:
- coherent world → `check_world_invariants()` returns without raising.
- char fighting a mob in another room → raises `InvariantViolation`
  (FIGHTING-COHERENCE).
- char in `room.people` whose `.room` points elsewhere → raises
  (ROOM-PEOPLE-COHERENCE).
- a registered char with a room but absent from that room's `people` → raises.
- `@pytest.mark.no_invariant_check` disables the autouse enforcement (verified by
  a test that would otherwise trip it).

## Definition of done

1. `mud/diagnostics/invariants.py` with `InvariantViolation` +
   `check_world_invariants()` (2 invariants).
2. Gated hook in `game_tick`; autouse fixture in `tests/conftest.py` honoring the
   marker.
3. `tests/test_invariant_checker.py` proving violations are caught and the marker
   disables enforcement.
4. Full suite green (real bugs fixed, artificial setups marked).
5. CHANGELOG entry + version bump.

## Future extensions (not in scope)

- Add the deferred invariants (003/013/015) one at a time.
- Extend the hook to after `process_command`.
- Optional production enablement as a runtime self-check (off by default).
