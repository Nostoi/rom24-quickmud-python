# Session Summary — 2026-06-21 — Reset mob-level fix (DB-004, game-wide)

## Scope

User-driven bug report from live play: sacrificing a Mud School "wimpy
monster" corpse paid only **1 silver**, and the user asked whether that
(and the absence of silver loot drops) was ROM-correct. Triaging the
sacrifice-reward formula led — via the user's insistence that the server
was freshly started — to a **game-wide area-reset parity bug** (every
reset-spawned mob 2 levels too low). Closed it as `DB-004` and locked the
AUTOSAC reward formula with a guard test. Two follow-up observations
(fast school respawn, reconnect-resumes-combat) were investigated and
confirmed ROM-correct (no code change).

## Outcomes

### `DB-004` — ✅ FIXED

- **Python**: `mud/spawning/reset_handler.py` (`apply_resets` M-case;
  `_compute_object_level`)
- **ROM C**: `src/db.c:1750` (M-case object-fuzz local), `src/db.c:2071`
  (`create_mobile` keeps prototype level), G/E fuzz at `1818`/`1942`
- **Gap**: `DB-004` — area-reset M-case wrongly decremented every
  reset-spawned mob's level by 2.
- **Root cause**: ROM's `level = URANGE(0, pMob->level - 2, LEVEL_HERO-1)`
  is a **local** variable that fuzzes the levels of objects the mob is
  given/equipped/dropped (O/G/E resets); it is never written back to the
  mob. Python misread it and did `mob.level = fuzzed_level`, so a level-1
  school wimpy monster (vnum 3703, resets into room 3715) became level 0.
  Its NPC corpse inherited level 0 → `do_sacrifice`/AUTOSAC paid
  `max(1, 0*3)` = 1 silver instead of ROM's `max(1, 1*3)` = 3. The
  decrement also lowered THAC0/damage/saving-throw/XP scaling for **every**
  reset-spawned mob. `spawn_mob()` (direct) was already correct — only the
  reset path diverged, which is why a direct-spawn reproduction showed 3
  silver while the live (reset-populated) server showed 1.
- **Fix** (two coupled edits): (1) M-case no longer assigns `mob.level`;
  the mob keeps its prototype level from `create_mobile`. The `mob_level-2`
  value now lives only in `last_mob_level` as the object-fuzz base.
  (2) `_compute_object_level` derives its base as
  `max(0, min(mob_level - 2, hero_cap))` (was reading the pre-decremented
  mob level and skipping the −2), so G/E equipment/loot levels stay
  ROM-correct. O-reset already consumed `last_mob_level`, so O/G/E now
  agree on ROM's local `level`.
- **False test corrected**: `test_m_reset_level_calculation` →
  `test_m_reset_preserves_mob_prototype_level` (was `assert mob.level == 21`
  for a level-23 weaponsmith — encoded the misread; now asserts the
  prototype level survives the reset).
- **Tests**: `tests/test_db_resets_rom_parity.py::test_m_reset_preserves_mob_prototype_level`
  (RED→GREEN). Object-level parity (`test_reset_levels.py`,
  `test_spawning.py` G/E fuzz) stay green. Full suite **6017 passed / 4
  skipped — zero fallout**.

### AUTOSAC reward guard — ✅ ADDED (commit `8de18809`)

- **Python**: `mud/combat/engine.py:_auto_sacrifice` (behavior already
  correct; previously unguarded)
- **ROM C**: `src/act_obj.c:1822` `silver = UMAX(1, obj->level * 3)`
- **Test**: `tests/integration/test_auto_sacrifice_reward_scaling.py` —
  parametrized over corpse level 0/1/2/5 → 1/3/6/15 silver, asserting both
  the silver delta and the singular/plural reward message. Closes the gap
  where only the AUTOSAC *flag* toggles and the TO_ROOM broadcast were
  tested, not the reward amount.

### Investigated, ROM-correct (no change)

- **Mud School fast respawn** — ROM `src/db.c:1627` `area_update` sets
  `pArea->age = 15 - 2` for the school so it repops on a ~3-minute cycle
  (vs ~15 for normal areas). Python's `reset_tick` `area.age = 13` matches
  exactly. Intended ROM behavior (newbie practice mobs).
- **Reconnect resumes mid-combat** — ROM `nanny` link-dead reattach: a
  disconnected character stays in the world (still fighting); reconnecting
  binds to the same character. Expected.

## Files Modified

- `mud/spawning/reset_handler.py` — M-case keeps mob prototype level;
  object-fuzz base (`mob_level-2`) via `last_mob_level` /
  `_compute_object_level`.
- `tests/test_db_resets_rom_parity.py` — corrected false test → asserts
  prototype level survives reset.
- `tests/integration/test_auto_sacrifice_reward_scaling.py` — new AUTOSAC
  reward-scaling guard.
- `docs/parity/DB_C_AUDIT.md` — added `DB-004` row (✅ FIXED) + fix record.
- `CHANGELOG.md` — `Fixed: DB-004`.
- `pyproject.toml` — 2.14.204 → 2.14.205.

## Test Status

- `tests/test_db_resets_rom_parity.py` — green.
- Full suite: **6017 passed, 4 skipped** (297s). Zero fallout from the
  game-wide level change (tests build mobs with explicit levels rather than
  relying on reset-spawned levels — same clean-fallout pattern as DB-001).

## Next Steps

- **Redeploy note**: the fix corrects mob level at every reset, so a
  backend restart picks it up — no JSON regeneration needed.
- **Resume harness widening** (the pre-DB-004 active focus): `practice`
  differential (partial-skill shim meta), FIGHT-079 (PC corpse half-coin
  gate), auto-loot/auto-gold death scenarios. See the 2026-06-20 death-
  lifecycle summary's Next Steps.
- **Diagnostic lesson for live-only bugs**: a long-running
  `python -m mud websocketserver` loads source once at startup and does
  **not** hot-reload; and reproduce reset-population bugs via the **reset
  system** (`reset_area`/`apply_resets`), not `spawn_mob()` directly — the
  two paths diverged here and only the reset path carried the bug.
