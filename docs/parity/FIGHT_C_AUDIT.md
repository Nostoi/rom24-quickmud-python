# `fight.c` ROM Parity Audit

- **Status**: ✅ Audited 95% — named combat-path regressions closed; remaining 5% is broader sweep debt, not a live documented gap
- **Date**: 2026-05-03
- **Source**: `src/fight.c` (ROM 2.4b6)
- **Python primaries**:
  - `mud/combat/engine.py`
  - `mud/combat/safety.py`
  - `mud/commands/combat.py`
  - `mud/game_loop.py`

This audit doc was opened to track the two combat-path regressions surfaced during the 2026-05-02 death/combat triage. Both named regressions are now closed. `fight.c` remains at 95% in the top-level tracker only because the file has not had a full post-triage refresh sweep; there is no remaining named `FIGHT-*` implementation gap in this document.

## Phase 1 — Function inventory

| ROM function | ROM lines | Python counterpart | Status | Notes |
|--------------|-----------|--------------------|--------|-------|
| `multi_hit` | `src/fight.c:187-247` | `mud/combat/engine.py:312` | ✅ AUDITED | `do_kill()` now enters combat through `multi_hit()` as ROM does. |
| `damage` | `src/fight.c:688-1016` | `mud/combat/engine.py:498` | ✅ AUDITED | `apply_damage()` now re-runs `is_safe()` at entry, matching ROM `damage()`. |
| `is_safe` | `src/fight.c:1018-1124` | `mud/combat/safety.py:14` | ✅ AUDITED | Port exists and the combat damage path now consistently uses it at the ROM-critical entry point. |
| `is_safe_spell` | `src/fight.c:1126-1221` | `mud/combat/safety.py:75` | ✅ AUDITED | Present; separate from the open melee-damage gap. |
| `do_kill` | `src/fight.c:2758-2819` | `mud/commands/combat.py:94` | ✅ AUDITED | Command now routes through `multi_hit()` instead of a single `attack_round()`. |

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

1. `FIGHT-001` — ✅ closed with `tests/integration/test_fight_c_do_kill_parity.py`.
2. `FIGHT-002` — ✅ closed with `tests/integration/test_fight_c_safe_room_damage_gate.py`.

## Phase 5 — Completion summary

`fight.c`'s remaining named combat-path regressions from the 2026-05-02 triage are closed. Keep the tracker row at 95% until a broader refresh sweep is done, but this audit doc no longer carries open implementation work. Verification is locked by `tests/integration/test_fight_c_do_kill_parity.py` and `tests/integration/test_fight_c_safe_room_damage_gate.py`.
