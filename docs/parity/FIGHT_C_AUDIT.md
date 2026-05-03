# `fight.c` ROM Parity Audit

- **Status**: ⚠️ Partial 95% — 2 CRITICAL combat-path gaps open
- **Date**: 2026-05-03
- **Source**: `src/fight.c` (ROM 2.4b6)
- **Python primaries**:
  - `mud/combat/engine.py`
  - `mud/combat/safety.py`
  - `mud/commands/combat.py`
  - `mud/game_loop.py`

This audit doc exists to track the two combat-path regressions surfaced during the 2026-05-02 death/combat triage. `fight.c` was already broadly audited; the remaining work is to restore two ROM-critical call-site contracts: `do_kill()` must enter combat via `multi_hit()`, and `damage()` must re-run `is_safe()` at function entry so safe-room transitions stop combat immediately.

## Phase 1 — Function inventory

| ROM function | ROM lines | Python counterpart | Status | Notes |
|--------------|-----------|--------------------|--------|-------|
| `multi_hit` | `src/fight.c:187-247` | `mud/combat/engine.py:312` | ⚠️ PARTIAL | Core player multi-attack loop exists, but `do_kill()` does not call it. |
| `damage` | `src/fight.c:688-1016` | `mud/combat/engine.py:498` | ⚠️ PARTIAL | Damage pipeline exists, but the ROM `is_safe(ch, victim)` entry gate is missing. |
| `is_safe` | `src/fight.c:1018-1124` | `mud/combat/safety.py:14` | ⚠️ PARTIAL | Port exists, but `damage()` and special-attack call chains do not consistently use it. |
| `is_safe_spell` | `src/fight.c:1126-1221` | `mud/combat/safety.py:75` | ✅ AUDITED | Present; separate from the open melee-damage gap. |
| `do_kill` | `src/fight.c:2758-2819` | `mud/commands/combat.py:94` | ⚠️ PARTIAL | Command entry exists, but ends with `attack_round()` instead of `multi_hit()`. |

## Phase 2 — Verification highlights

### `do_kill` — ROM `src/fight.c:2815-2817`

ROM explicitly enters combat through the full multi-attack entrypoint:

```c
WAIT_STATE (ch, 1 * PULSE_VIOLENCE);
check_killer (ch, victim);
multi_hit (ch, victim, TYPE_UNDEFINED);
```

Python `mud/commands/combat.py:123-125` currently does:

```python
skill_registry._apply_wait_state(char, get_pulse_violence())
check_killer(char, victim)
return attack_round(char, victim)
```

That drops the entire ROM `multi_hit()` chain (`src/fight.c:209-244`): first swing, haste extra swing, second-attack skill roll, third-attack skill roll, and the post-first-hit `check_assist()` path already mirrored by `mud/combat/engine.py:338-341`.

### `damage` entry gate — ROM `src/fight.c:725-733`

ROM re-checks attack safety inside `damage()` itself:

```c
if (victim != ch)
{
    if (is_safe (ch, victim))
        return FALSE;
    check_killer (ch, victim);
```

Python `mud/combat/engine.py:528-620` has no corresponding `is_safe()` call at function entry. That means once combat is underway, subsequent `attack_round()` / `multi_hit()` passes keep landing even if one combatant is moved into a safe room. This is a direct behavioral divergence from ROM and from the already-ported `mud/combat/safety.py:is_safe`.

### Special-attack call chains

ROM applies the same safety contract by routing attack variants through `damage()` (`one_hit`, skills, weapon procs, mobprog damage paths). Python likewise funnels the core physical path through `mud/combat/engine.py:488` `apply_damage(...)`, and weapon special procs call `apply_damage(...)` at `mud/combat/engine.py:1502`, `mud/combat/engine.py:1522`, `mud/combat/engine.py:1532`, and `mud/combat/engine.py:1546`. Because the entry gate is missing there, every caller inherits the bug until `apply_damage()` is fixed.

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `FIGHT-001` | CRITICAL | `src/fight.c:2815-2817`, `src/fight.c:209-244` | `mud/commands/combat.py:123-125`, `mud/combat/engine.py:312-388` | `do_kill()` calls a single `attack_round()` instead of ROM `multi_hit(ch, victim, TYPE_UNDEFINED)`, so `kill` starts combat with one swing instead of the full ROM multi-attack sequence. | ❌ OPEN — add integration test that proves `kill` produces at least the ROM baseline multi-hit behavior, then swap the command entrypoint to `multi_hit()`. |
| `FIGHT-002` | CRITICAL | `src/fight.c:725-733`, plus all attack variants that rely on `damage()` | `mud/combat/engine.py:528-620` (`apply_damage`) and downstream callers such as `mud/combat/engine.py:1502`, `mud/combat/engine.py:1522`, `mud/combat/engine.py:1532`, `mud/combat/engine.py:1546` | The ROM `damage()` function early-exits through `is_safe(ch, victim)` before any fighting-state or HP mutation. Python never re-checks `is_safe()` inside the damage path, so combat continues after safe-room transitions. | ❌ OPEN — add integration test that teleports an active target into a safe room and proves the next damage tick exits cleanly; then gate `apply_damage()` and all special-attack paths through `is_safe()`. |

## Phase 4 — Closures

None yet. The intended closure order for this session is:

1. `FIGHT-001` — failing integration test first, then swap `do_kill()` to `multi_hit()` and update this row with commit SHA.
2. `FIGHT-002` — failing integration test first, then add the missing `is_safe()` gate at the `apply_damage()` entrypoint and verify the inherited special-attack callers.

## Phase 5 — Completion summary

`fight.c` remains at 95% audited pending the two combat-path gaps above. Both are CRITICAL because they change live combat behavior, not just internal structure:

- `FIGHT-001` reduces a ROM combat command to a single swing.
- `FIGHT-002` violates ROM’s safe-room stop-combat contract once a fight is already in progress.

No tracker flip is appropriate until both gaps are closed with integration coverage.
