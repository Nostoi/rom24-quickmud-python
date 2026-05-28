# Session Summary — 2026-05-28 — FIGHT-016 weapon-poison affect + ARITH-004 reclass (2.9.88)

## Scope

Picked up from the equipment-key canonicalization session (2.9.87) with the
per-file audit tracker exhausted (no ⚠️ Partial / ❌ Not Audited rows), so the
active mode is the cross-file / remaining-documented-gap pass. The push of the
2.9.87 commits had already landed (`origin/master` == `master` at session
start). Targeted the remaining open `ARITHMETIC_BOUNDARY.md` gaps; the highest
"reachable" candidate (ARITH-004, weapon-proc level floor) turned out to be
behaviorally dead, but reading the ROM C around it surfaced a **real** poison
divergence — the session pivoted to filing and closing that (FIGHT-016).

GitNexus was unavailable all session (read-only index DB — `Cannot execute
write operations`; reindex itself fails). Impact analysis used `grep` + the
test suite per the CLAUDE.md documented fallback (single production caller of
`process_weapon_special_attacks`: `engine.py:467` in the `apply_damage` path —
LOW risk).

## Outcomes

### `ARITH-004` — ⛔ N/A (reclassified)

- **Python**: `mud/combat/engine.py:1561-1562` (`process_weapon_special_attacks`)
- **ROM C**: `src/fight.c:606` (`level = wield->level`, raw)
- **Finding**: `max(1, weapon_level)` is a behaviorally dead floor. Every
  consumer of the weapon level divides it by ≥2 (`level // 2`, `// 4 + 1`,
  `// 5 + 1/2`, `// 6 + 2`, `fire/cold/shock_effect(weapon_level // 2)`), and
  `0 // N == 1 // N == 0` for N ≥ 2, so flooring a level-0 weapon to 1 never
  changes an observable value. `weapon_level` is also pre-floored at line 1556
  (`_weapon_level(wield) or 1`), making the inner `max(1, …)` doubly dead. Same
  shape as the already-N/A'd ARITH-020/021/022/023.
- **Action**: row 38 + header tally flipped (Effective open ❌ MISSING 7 → 6);
  ROM-cite comment added at the site. Commit `094536dd`.

### `FIGHT-016` — ✅ FIXED (the real divergence behind ARITH-004)

- **Python**: `mud/combat/engine.py:1561-1593` (WEAPON_POISON branch)
- **ROM C**: `src/fight.c:616-624`
- **Gap**: WEAPON_POISON applied only a bare `victim.add_affect(AffectFlag.POISON)`
  — an untimed flag that never wore off, applied no STR penalty, and skipped
  `affect_join` merge. ROM `affect_join`s a structured affect: `af.level =
  level*3/4`, `af.duration = level/2`, `af.location = APPLY_STR`, `af.modifier
  = -1`, `af.bitvector = AFF_POISON`.
- **Fix**: the branch now builds `SpellEffect(name="poison",
  level=c_div(level*3,4), duration=c_div(level,2), stat_modifiers={Stat.STR:-1},
  affect_flag=AffectFlag.POISON, wear_off_message="You feel less sick.")` and
  routes it through `Character.apply_spell_effect` (the Python `affect_join`
  port at `mud/models/character.py:673`), matching `spell_poison`'s pattern
  (differing only in params: STR -1 not -2, `level*3/4`, `level/2`). Falls back
  to the bare `add_affect` only if the target lacks `apply_spell_effect`.
- **Tests**: `tests/integration/test_weapon_poison_affect.py` — 2/2
  (`test_fight_016_weapon_poison_applies_timed_str_reducing_affect` verified
  failing pre-fix; `test_fight_016_successful_save_applies_no_poison`). Commit
  `2024e071`.

### `test_weapon_flaming_fire_damage` — de-flaked (user-requested)

- **File**: `tests/test_weapon_special_attacks.py:154`
- **Finding**: the WEAPON_FLAMING proc rolls `rng_mm.number_range` twice — once
  for the fire-damage roll `(1, 4)` and once inside `fire_effect` — but the test
  pinned `assert_called_once_with(1, 4)` on the shared mock, so it **failed in
  isolation** and only passed under full-suite ordering. Pre-existing (failed at
  `HEAD~1`); not caused by this session's changes (verified via stash). Switched
  to `assert_any_call(1, 4)`. Test-only; no production change. Commit `73e96228`.

### Test infrastructure — parallel execution by default (pytest-xdist)

Enabled `pytest -n auto --dist loadscope` as the default (`pyproject.toml`
`addopts` + `pytest-xdist` dev dep). **Full suite ~517s → ~94s (~5.5×)** on a
10-core machine; serial still available via `-n0` (verified 4896 passed, 510s).
Parallel + serial both green: **4896 passed, 4 skipped**.

Enabling parallelism surfaced 5 latent test-isolation bugs (cross-worker shared
state / cross-file dependencies that serial ordering masked). All fixed
test-side, no production change:

- **Shared SQLite DB** (`mud/db/session.py` fixed `sqlite:///mud.db`) — per-worker
  `DATABASE_URL` from `PYTEST_XDIST_WORKER`, set at the top of `tests/conftest.py`
  before the engine imports. Fixed 2 websocket failures.
- **`registry.descriptor_list` leak** — `wiznet()` uses descriptors when present,
  else `character_registry`; a leaked list flipped delivery. Autouse
  snapshot/restore in `tests/conftest.py`. Fixed the wiznet failure.
- **`area_registry` pollution** — `_get_area_for_vnum(100)` resolved to a leaked
  real area, tripping the mpedit security gate. `test_mpedit_001…` autouse fixture
  now snapshots/clears/restores `area_registry`. Fixed 9 mpedit failures.
- **Global-time dependency** — `test_movement_npc` relied on ambient daytime
  (`time_info.sunlight`) for `room_is_dark()`; rooms now explicitly lit.
- **Repo-file pollution** — OLC `asave` tests (`test_olc_save.py`,
  `test_olc_builders.py`) let `save_area_list()`'s default path rewrite the real
  `data/areas/area.lst` (dropping `test.json`); a `tests/conftest.py` autouse
  fixture now redirects the default write to a per-test tmp file.

AGENTS.md gained a "Parallel test execution & isolation" subsection documenting
`-n0` for debugging and the rules for keeping new tests parallel-safe.

## Files Modified

- `mud/combat/engine.py` — WEAPON_POISON structured affect (FIGHT-016) + ARITH-004 ROM-cite comment; `SpellEffect` / `Stat` imports.
- `tests/integration/test_weapon_poison_affect.py` — new (2 cases, FIGHT-016).
- `tests/test_weapon_special_attacks.py` — flaming `number_range` assert de-flaked.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — ARITH-004 ❌ → ⛔ N/A (row 38 + header).
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-016 filed + flipped ✅ FIXED; FIGHT-017 filed ❌ MISSING; status header updated.
- `CHANGELOG.md` — 2.9.88 section (FIGHT-016, flaming de-flake, ARITH-004 reclass, FIGHT-017 filing).
- `pyproject.toml` — 2.9.87 → 2.9.88.

## Test Status

- `tests/integration/test_weapon_poison_affect.py` — 2/2.
- `tests/test_weapon_special_attacks.py` — 12/12 (flaming now passes in isolation and in-file).
- `tests/integration/test_weapon_proc_pers.py` + `test_invisibility_combat.py` — 17/17 (no regression on the FIGHT-009..013 PERS surface).
- Full suite: **4896 passed, 4 skipped, 0 failed** in 516.82s (= prior 4894 + the 2 new FIGHT-016 tests; no regressions).
- `ruff check` on changed files — clean.

## Outstanding / Next Steps

1. **`FIGHT-017`** (filed this session, ❌ MISSING) — temporary-envenomed-weapon
   level source (`affect_find(wield->affected, gsn_poison)` → `poison->level`
   else `wield->level`) + per-hit weakening (`poison->level -= 2`,
   `duration -= 1`, "The poison on $p has worn off." to the wielder) per ROM
   `src/fight.c:605-608, 627-636`. Depends on / extends FIGHT-016. Next
   `/rom-gap-closer` target.
2. **Remaining open ARITH (6 ❌ MISSING)**: ARITH-017/018/019 (spell-handler
   level floors — likely N/A like ARITH-020..023, verify reachability first),
   ARITH-114 (per-race/class stat ceiling — larger), ARITH-206/207 (reset arg
   floors — likely N/A like ARITH-209, shipped areas use arg4==1), ARITH-208
   (template dice+bonus floor — genuinely reachable).
3. **`_wear_all` light handling** (carried over) — `wear all` won't equip a
   light; ROM's `wear all` → `wear_obj` → WEAR_LIGHT would.
4. **`CLEANUP-001`** — ~41 hardcoded hex flag literals → enum refs.
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes`/reindex
   unavailable; fix DB perms/lock outside the session.
