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
| `FIGHT-001` | CRITICAL | `src/fight.c:2815-2817`, `src/fight.c:209-244` | `mud/commands/combat.py:123-128`, `mud/combat/engine.py:312-388` | `do_kill()` calls a single `attack_round()` instead of ROM `multi_hit(ch, victim, TYPE_UNDEFINED)`, so `kill` starts combat with one swing instead of the full ROM multi-attack sequence. | ✅ FIXED — `do_kill()` now routes through `multi_hit()` and preserves the first combat message as the command return. Regression test: `tests/integration/test_fight_c_do_kill_parity.py::test_do_kill_uses_rom_multi_hit_sequence`. Commit SHA recorded in session report for this one-gap commit. |
| `FIGHT-002` | CRITICAL | `src/fight.c:725-733`, plus all attack variants that rely on `damage()` | `mud/combat/engine.py:503-535` (`apply_damage`) and downstream callers such as `mud/combat/engine.py:1508`, `mud/combat/engine.py:1528`, `mud/combat/engine.py:1538`, `mud/combat/engine.py:1552` | The ROM `damage()` function early-exits through `is_safe(ch, victim)` before any fighting-state or HP mutation. Python never re-checks `is_safe()` inside the damage path, so combat continues after safe-room transitions. | ✅ FIXED — `apply_damage()` now re-checks `is_safe()` at entry, which also covers weapon special attacks and skill handlers because they already funnel through `apply_damage()`. Regression test: `tests/integration/test_fight_c_safe_room_damage_gate.py::test_attack_round_does_no_damage_after_fight_moves_into_safe_room`. Commit SHA recorded in session report for this one-gap commit. |

## Phase 4 — Closures

None yet. The intended closure order for this session is:

1. `FIGHT-001` — ✅ closed in this session with `tests/integration/test_fight_c_do_kill_parity.py`.
2. `FIGHT-002` — ✅ closed in this session with `tests/integration/test_fight_c_safe_room_damage_gate.py`.

## Phase 5 — Completion summary

`fight.c`'s remaining named combat-path regressions from the 2026-05-02 triage are now closed. The audit tracker can stay at 95% until the next full sweep reconciles any adjacent findings, but `FIGHT-001` and `FIGHT-002` are both covered by dedicated integration tests and no longer block live combat parity in the documented surfaces.
