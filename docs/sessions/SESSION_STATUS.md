# Session Status — 2026-05-28 — FIGHT-017 envenom level source + per-hit poison weakening (2.9.89)

## Current State

- **Active mode**: cross-file / remaining-documented-gap pass (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows). This session closed the
  remaining open `fight.c` weapon-poison gap (FIGHT-017), the temporary-envenom
  half left open by FIGHT-016.
- **Last completed**:
  - **`FIGHT-017`** ✅ FIXED (2.9.89) — WEAPON_POISON now sources its level from
    a temporary envenom affect on the weapon (`affect_find(wield->affected,
    gsn_poison)` → `poison->level`, else `wield->level`) and weakens that
    envenom per hit (`level -= 2`, `duration -= 1`), emitting `"The poison on $p
    has worn off."` to the **wielder** when either hits 0 — independent of the
    victim's save. Permanent WEAPON_POISON weapons are unchanged. ROM
    `src/fight.c:605-608, 627-636`. Test:
    `tests/integration/test_weapon_poison_affect.py::test_fight_017_*` (4 cases).
    Commit `6b7f80d4`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_017_ENVENOM_WEAKENING.md](SESSION_SUMMARY_2026-05-28_FIGHT_017_ENVENOM_WEAKENING.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_FIGHT_016_WEAPON_POISON_AFFECT.md](SESSION_SUMMARY_2026-05-28_FIGHT_016_WEAPON_POISON_AFFECT.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.89 |
| Tests | **4900 passed, 4 skipped, 0 failed** — parallel by default (`-n auto --dist loadscope`): ~112s. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75%; `fight.c` ~95% (FIGHT-004..008 PERS surface still open; FIGHT-016/017 both closed). |
| Cross-file invariants | 24 ENFORCED. |
| Branch | `master` — 1 commit ahead of `origin/master` (6b7f80d4 FIGHT-017 / 2.9.89). Not pushed. |

## Next Intended Task

1. **Remaining open ARITH (6 ❌ MISSING)** in
   `docs/parity/audits/ARITHMETIC_BOUNDARY.md`: ARITH-017/018/019 (spell-handler
   level floors — verify reachability, likely N/A like ARITH-020..023),
   ARITH-114 (per-race/class stat ceiling — larger), ARITH-206/207 (reset arg
   floors — likely N/A like ARITH-209), ARITH-208 (template dice+bonus floor —
   genuinely reachable). Start with ARITH-208 (the one confirmed reachable).
2. **`fight.c` FIGHT-004..008** — PERS position-change broadcast surface
   (`_position_change_message`), opened 2026-05-23, still open.
3. **Push approval** — 1 commit ahead of `origin/master` shipping 2.9.89.
   Awaiting approval.
4. **`_wear_all` light handling** and **`CLEANUP-001`** (hex flag literals)
   carried over.
5. **GitNexus** — MCP query path was read-only this session; CLI `analyze`
   succeeded and the graph is fresh. If the MCP path is still read-only next
   session, fix DB perms/lock outside the session.
