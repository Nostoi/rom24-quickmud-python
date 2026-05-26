# Session Status — 2026-05-26 — `affect_check` prototype fallback (2.9.45)

## Current State

- **`affect_check` prototype walk added** (`1ffc06f`, 2.9.45). ROM
  `src/handler.c:1240-1257` walks `obj->pIndexData->affected` on every
  equipped (unenchanted) item; Python only walked per-instance
  `obj.affected`, dropping any bitvector grant that lived on the
  prototype. Symptom: a `+sanc` ring whose grant comes from the
  prototype lost AFF_SANCTUARY on the wearer when a temporary
  sanctuary spell expired. `equip_char` / `unequip_char` were already
  walking the prototype correctly; only `affect_check` had the
  asymmetry. Now symmetric, with the same `obj.enchanted` gate as ROM.
  Single-function intra-module fix; no new INV-NNN row.
- **`check_assist` misplacement closed** (`cf126f0`, 2.9.44 — pushed
  to origin/master earlier this session). The combat-trigger contract
  is now fully ROM-correct (`multi_hit → victim-died guard →
  check_assist → re-guard → IS_NPC then HPCNT/FIGHT`).
- **Tests**: 2 new (`test_affect_check_prototype_fallback.py`) +
  3 new + 1 rewritten earlier this session. Full suite: **4769
  passed, 4 skipped** in 628s.
- **INV budget at 23/~20** — unchanged.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md](SESSION_SUMMARY_2026-05-26_AFFECT_CHECK_PROTOTYPE_FALLBACK.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md](SESSION_SUMMARY_2026-05-26_CHECK_ASSIST_DISPATCH_SCOPE.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.45 |
| Tests | **4769 passed, 4 skipped** (full suite, 628s) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **23 of ~20 enforced** — over by three, within margin per AGENTS.md soft cap |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.45 (1 commit pending push approval: `1ffc06f`) |

## Next Intended Task

1. **Push approval** required for 2.9.45 (`1ffc06f`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.45 to origin/master").
2. **GitNexus refresh** — index stale at `5d3ce9d` (two commits behind:
   `cf126f0` 2.9.44, `1ffc06f` 2.9.45). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Continue probe-then-scope at 23/~20 INV budget**. Affect-tick
   area is now fully ROM-correct. Remaining candidate probe areas:
   - **PC-quit follower/pet cleanup vs INV-020** — quit-path
     `nuke_pets` / `stop_follower(pet)` may have a contract gap.
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     wired correctly but no INV row pins it.
   - **Position-transition adjacency** — `update_pos` callers
     (do_yell, do_emote-while-down) could surface a missing
     transition beyond INV-016 / INV-019.
