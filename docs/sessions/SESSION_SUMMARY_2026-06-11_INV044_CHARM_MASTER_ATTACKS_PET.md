# Session Summary — 2026-06-11 — INV-044: charm-master attacks own pet must break follow

## Scope

Continuation from v2.14.4 (FIGHT-058 closed). The session executed the three
INV-044 probe candidates listed in the previous handoff — mob script trigger
ordering, group/follower chain iterator safety, and position transitions under
multi-attack — using the probe-then-scope method (read ROM C contract → read
Python equivalent → write one failing test if divergence exists).

Probes 1–2 and most of probe 3 were completed in the prior context window.
The remaining unverified area from that sweep was the "charm-master attacks
own pet" path: ROM `src/fight.c:756-757` calls `stop_follower(victim)` inside
`damage()` when `victim->master == ch`. Python's `apply_damage` was missing
this check entirely. This session completed the verification, found the
divergence, and closed it as INV-044.

## Outcomes

### Probe results (all three INV-044 candidates)

| Candidate | ROM C reference | Python equivalent | Verdict |
|-----------|----------------|-------------------|---------|
| Mob script trigger ordering | `src/fight.c:883-924` (`group_gain` → `TRIG_DEATH` → `raw_kill`) | `mud/combat/engine.py:_handle_death` | ✅ CLEAN |
| Group/follower chain iterator safety | `src/fight.c:1727-1806` (`group_gain`), `src/fight.c:66-100` (`violence_update`) | `mud/groups/xp.py:group_gain`, `mud/game_loop.py:violence_tick`, `mud/combat/assist.py:check_assist` | ✅ CLEAN |
| Position transitions under multi-attack | `src/fight.c:187-288` (`multi_hit`/`mob_hit`) | `mud/combat/engine.py:multi_hit`/`mob_hit` | ✅ CLEAN |
| Charm-master attacks own pet | `src/fight.c:756-757` (`if (victim->master == ch) stop_follower(victim)`) | `mud/combat/engine.py:apply_damage` | ❌ DIVERGENCE → fixed as INV-044 |

### `INV-044` — ✅ ENFORCED

- **Python**: `mud/combat/engine.py:apply_damage` (after `set_fighting(attacker, victim)` block)
- **ROM C**: `src/fight.c:756-757`
- **Divergence**: Python `apply_damage` had no equivalent of ROM's
  `if (victim->master == ch) stop_follower(victim)` check. When a PC attacked
  their own charmed follower, the follow/charm relationship was never broken by
  the attack. In ROM, the bond severs on the first damaging hit.
- **Fix**: Added `if getattr(victim, "master", None) is attacker: stop_follower(victim)`
  inside the `if victim != attacker:` block in `apply_damage`, after the
  `set_fighting` block — matching ROM's exact position relative to
  `set_fighting(ch, victim)` at fight.c:750.
- **Tests**: `tests/test_combat.py::test_apply_damage_charm_master_breaks_follow`
  (1 test): verified red before fix, green after. Full suite 5608/5608.

## Files Modified

- `mud/combat/engine.py` — added charm-master follow-break check inside `apply_damage`
  (4 lines, after `set_fighting(attacker, victim)`)
- `tests/test_combat.py` — new test `test_apply_damage_charm_master_breaks_follow`
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added INV-044 row (✅ ENFORCED 2.14.5);
  updated maintenance footer (27 → 28)
- `CHANGELOG.md` — added `[2.14.5]` Fixed entry
- `pyproject.toml` — 2.14.4 → 2.14.5

## Test Status

- `pytest tests/test_combat.py::test_apply_damage_charm_master_breaks_follow -n0` — 1/1 passing
- Full suite: **5608/5608 passing, 4 skipped** (run 2026-06-11, post-fix)

## Next Steps

The three original INV-044 probe candidates have been fully verified. INV-044
is now closed and enforced. The next session should continue the cross-file
invariants pass with fresh probe candidates. Suggested areas:

1. **Position-transition broadcast** — when a character is knocked from
   FIGHTING → STUNNED, does Python send the correct ROM act() messages to the
   room? (INV-016 covers the silent-promotion-on-heal side; the knocked-down
   path has no lock yet.)
2. **`stop_fighting` sweep completeness** — ROM `src/fight.c:stop_fighting`
   walks ALL of `char_list` and clears any `ch->fighting == victim` pointers;
   Python `stop_fighting(ch, both=True)` does the same via
   `character_registry`. Verify Python also handles the `both=False`
   (victim-only) path correctly in all call sites.
3. **`check_killer` cross-file contract** — ROM `src/fight.c:check_killer`
   sets `PLR_KILLER` on the attacker when a non-PK flag is violated; Python
   `check_killer` in `apply_damage` and the `_mark_killer_if_needed` path
   should be audited for cross-file coherence.

For each: read ROM C contract → read Python equivalent → write one failing test
if divergence found → close as gap or file as INV-NNN.
