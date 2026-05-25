# Session Summary — 2026-05-25 — INV-016 BCAST-ON-POSITION-TRANSITION closure (2.9.10)

## Scope

Continuation of the cross-file invariants pass. The 2.9.9 session
filed INV-016 ❌ BROKEN with a documenting `xfail(strict=True)`
test; this session closed it. Per the SESSION_STATUS recommendation
(option B — factor the broadcast helper out rather than route every
spell through `apply_damage`), extracted
`mud/combat/engine.py:apply_position_change(victim, old_pos)` as
the shared enforcement point and wired it into the 16 damage-spell
sites that bypass `apply_damage`. One enforcement test flipped from
xfail-strict to passing.

## Outcomes

### `INV-016` — ✅ ENFORCED

- **Python**: `mud/combat/engine.py:745` (helper), `mud/combat/engine.py:616` (delegation), 16 spell sites in `mud/skills/handlers.py`.
- **ROM C**: `src/fight.c:837-861` — `act(... TO_ROOM)` lines emitted by `damage()` after `update_pos`.
- **Fix**: New `apply_position_change(victim, old_pos)` helper in `mud/combat/engine.py` calls `_position_change_message` (which broadcasts via `_broadcast_pos_change`) and `_push_message` only when `victim.position != old_pos`. `_apply_damage` now delegates to it. Each damage-spell handler that bypassed `apply_damage` captures `old_pos = target.position` before the `hit -=` line and calls `apply_position_change(target, old_pos)` after `update_pos`. Heals correctly skip the helper (ROM does not broadcast upward STUNNED → STANDING transitions); `cause_*` already routed through `apply_damage` and inherits the broadcast there.
- **Tests**: `tests/integration/test_inv016_position_transition_broadcast.py::test_spell_damage_broadcasts_death_transition_to_room` — flipped from `xfail(strict=True)` documenting test to passing strict-fail assertion. (Rewrote the assertion target from INCAP to DEAD because the existing fixture — level-30 caster, 1-hp target — overshoots INCAP for `acid_blast`; same invariant, different threshold.)

### Spell sites wired (16)

acid_blast, acid_breath, burning_hands, call_lightning, chill_touch,
colour_spray, demonfire, dispel_evil, dispel_good, fire_breath,
frost_breath, gas_breath, harm, heat_metal, lightning_breath,
shocking_grasp.

Heals deliberately skipped (4): `cure_critical`, `cure_light`,
`cure_serious`, `heal` — ROM's broadcast block lives in `damage()`,
not on `update_pos` calls that move position upward.

### Anti-pattern avoided

Tempting to route every damage spell through `apply_damage` (option
A from SESSION_STATUS). Rejected because `apply_damage` carries
combat-specific side effects (autoflee triggers, fighting setup,
kill XP routing) that have no analog in ROM `magic.c` spell paths
— wiring spells through it would double-trigger autoflee on
spell-induced INCAP. Option B (factor the helper out) is the
minimal blast radius change that closes the invariant without
incurring side effects.

## Files Modified

- `mud/combat/engine.py` — new public `apply_position_change(victim, old_pos)` helper; `_apply_damage` delegates to it.
- `mud/skills/handlers.py` — import `apply_position_change`; 16 damage-spell sites capture `old_pos` and call the helper after `update_pos`.
- `tests/integration/test_inv016_position_transition_broadcast.py` — removed `pytest.mark.xfail(strict=True)`; flipped assertion from INCAP to DEAD (matches the level-30 / 1-hp fixture's damage range for `acid_blast`).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-016 row flipped ❌ BROKEN → ✅ ENFORCED; budget note updated to "16 of ~20; INV-001 … INV-016 ✅ ENFORCED".
- `CHANGELOG.md` — added `## [2.9.10] Fixed` entry.
- `pyproject.toml` — 2.9.9 → 2.9.10.

## Test Status

- `pytest tests/integration/test_inv016_position_transition_broadcast.py -v` — 1/1 passing.
- Full suite (`pytest`): **4715 passed, 4 skipped, 0 failed, 0 xfailed** (was 4714 passed + 1 xfailed pre-fix). 8m19s wall-clock.

## Next Steps

INV-016 closed; tracker now at 16 of ~20 budget, all ✅ ENFORCED.
Next candidates from the 2026-05-25 prompt's queue:

- **Mob script triggers** (ENTRY / GIVE / KILL / RANDOM / HPCNT
  firing across `mob_cmds`, `game_loop`, `handler`, `dispatcher`)
  — candidate area #3.
- **Group / follower chain** — leader/master pointers, group XP
  split, follow propagation, disband-on-death — candidate area #4.

Probe-then-scope as usual: 5-minute read of ROM C contract + Python
equivalent + one failing test, then close as a gap or file as the
next free INV-NNN. No push to origin until explicit per-cluster
approval.
