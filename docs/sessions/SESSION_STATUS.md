# Session Status — 2026-05-28 — FIGHT-016 weapon-poison affect + ARITH-004 reclass (2.9.88)

## Current State

- **Active mode**: cross-file / remaining-documented-gap pass (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows). This session worked the
  open `ARITHMETIC_BOUNDARY.md` gaps and the `fight.c` weapon-proc surface.
- **Last completed**:
  - **`FIGHT-016`** ✅ FIXED (2.9.88) — WEAPON_POISON now applies a timed,
    STR-reducing poison affect via `affect_join` (`SpellEffect` +
    `Character.apply_spell_effect`), replacing the bare `add_affect(POISON)`
    flag. ROM `src/fight.c:616-624`. Test:
    `tests/integration/test_weapon_poison_affect.py`.
  - **`ARITH-004`** ⛔ N/A — behaviorally dead weapon-proc level floor
    (every consumer divides by ≥2; `0//N == 1//N`). Effective open ARITH
    ❌ MISSING: 7 → 6.
  - **`test_weapon_flaming_fire_damage`** de-flaked (`assert_any_call` instead
    of `assert_called_once_with`; `fire_effect` makes a second `number_range`
    roll on the shared mock).
- **Filed this session (not closed)**: **`FIGHT-017`** — temporary-envenomed
  weapon level source + per-hit poison weakening (ROM `src/fight.c:605-608,
  627-636`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_016_WEAPON_POISON_AFFECT.md](SESSION_SUMMARY_2026-05-28_FIGHT_016_WEAPON_POISON_AFFECT.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_EQUIPMENT_KEY_CANONICALIZATION.md](SESSION_SUMMARY_2026-05-28_EQUIPMENT_KEY_CANONICALIZATION.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.88 |
| Tests | **Full suite: 4896 passed, 4 skipped, 0 failed** in 516.82s. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75%; `fight.c` 95% (FIGHT-017 open). |
| Cross-file invariants | 24 ENFORCED. |
| Branch | `master` — 3 commits ahead of `origin/master` (094536dd reclass, 2024e071 FIGHT-016, 73e96228 flaming de-flake). Not pushed. |

## Next Intended Task

1. **`FIGHT-017`** — close the temporary-envenomed-weapon level source +
   per-hit poison weakening via `/rom-gap-closer` (extends FIGHT-016; shares the
   `level` variable). ROM `src/fight.c:605-608, 627-636`.
2. **Remaining open ARITH (6 ❌ MISSING)**: ARITH-017/018/019 (verify
   reachability — likely N/A like ARITH-020..023), ARITH-114 (per-race/class
   stat ceiling, larger), ARITH-206/207 (likely N/A like ARITH-209), ARITH-208
   (template dice+bonus floor — genuinely reachable).
3. **Push approval** — 3 commits ahead of `origin/master` shipping 2.9.88. Not
   pushed (awaiting approval).
4. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes`/reindex
   unavailable; fix DB perms/lock outside the session.
5. **`_wear_all` light handling** and **`CLEANUP-001`** (hex flag literals) carried over.
