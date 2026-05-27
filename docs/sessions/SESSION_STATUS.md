# Session Status — 2026-05-26 — PARALLEL hex-flag bug burn-down (2.9.56)

## Current State

- **Three PARALLEL hex-flag bugs closed across 2.9.55–2.9.56**, all from
  the "drift-risk cleanup batch" that turned out to contain real active
  bugs (audit's "no current bug" hypothesis overturned):
  - **`PARALLEL-001`** + **`PARALLEL-004`** (`1d675fe`, 2.9.55):
    `mud/commands/misc_player.py` `do_config` display table now reads
    canonical `int(PlayerFlag.X)` / `int(CommFlag.X)` instead of mismatched
    hex literals; module-local `COMM_AFK` re-pointed at `int(CommFlag.AFK)`.
    Pre-fix: `config` always showed wrong ON/OFF for autoloot/autosac/
    autoexit/afk; brief toggle lit up "combine ON" due to bit collision.
  - **`PARALLEL-005`** (`3e71334`, 2.9.56): `mud/commands/obj_manipulation.py`
    `_can_drop_obj` now reads `int(ExtraFlag.NODROP)` (bit 7) instead of
    inline `0x0010` (bit 4 = `ExtraFlag.EVIL`). Pre-fix: NODROP cursed
    gear droppable; EVIL items spuriously blocked. Existing test that
    encoded the same wrong hex fixed per "ROM is source of truth".
- **Audit re-classification**: PARALLEL_REPRESENTATIONS.md
  3 ⚠️ DRIFT-RISK → MEDIUM active bug → ✅ FIXED. Remaining ⚠️ rows
  (PARALLEL-002 partial, PARALLEL-003, PARALLEL-006) need inspection —
  the audit's "drift-risk only" framing is no longer trustworthy.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md](SESSION_SUMMARY_2026-05-26_PARALLEL_HEX_FLAG_BUGS.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-26_META_BURNDOWN_MATH001_PARALLEL010.md](SESSION_SUMMARY_2026-05-26_META_BURNDOWN_MATH001_PARALLEL010.md),
  [SESSION_SUMMARY_2026-05-26_META_AUDITS_CLASS_1_7_8.md](SESSION_SUMMARY_2026-05-26_META_AUDITS_CLASS_1_7_8.md),
  [SESSION_SUMMARY_2026-05-26_RESTORE_AFFECT_STRIP.md](SESSION_SUMMARY_2026-05-26_RESTORE_AFFECT_STRIP.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.56 |
| Tests | 125 ✅ across `test_do_config_flag_alignment` + `test_can_drop_obj_nodrop_bit` + adjacent config/auto_flags/player_config/drop/put/give suites. Full suite not re-run; flee-adjacent (45) and weapon-damage-adjacent (29) still green from 2.9.54. |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | 23 of ~20 enforced (unchanged) |
| Meta-audit progress | 4 of 8 META classes audited. Class 1 BROADCAST_COVERAGE: not started (29 ❌, helper-transitivity caveat). Class 7 PARALLEL_REPRESENTATIONS burn-down: **4 active bugs closed** (PARALLEL-001/004/005/010); 3 more ⚠️ rows suspected to be active bugs (PARALLEL-002 partial, PARALLEL-003, PARALLEL-006). Class 8 MATH_AND_RNG burn-down: **MATH-001 closed**. |
| Branch | `master` — local 2.9.56 (5 commits pending push approval: `4197fec`, `5d5e246`, `90aa8ce`, `1d675fe`, `3e71334` + intervening handoff commits) |

## Next Intended Task

1. **Push approval** required for 2.9.52–2.9.56 (5 commits since
   `origin/master`). Per standing rule, no push without explicit
   per-cluster approval ("yes push v2.9.56 to origin/master" or
   similar).
2. **Continue PARALLEL hex-bit burn-down** — these are all single
   gap-closers with targeted regression tests:
   - **`PARALLEL-003a`** (`do_train` trainer-lookup): `mud/commands/remaining_rom.py:211`
     `ACT_GAIN = 0x00100000` vs canonical `1<<27 = 0x8000000`. Wrong bit
     means trainer NPCs likely can't be found. Test: spawn NPC with
     `ActFlag.GAIN`, place in room, call `do_train`, assert trainer
     found.
   - **`PARALLEL-003b`** (`COMM_QUIET`): `remaining_rom.py:105`
     `COMM_QUIET = 0x00000004` vs canonical `1<<0 = 0x1`. Wrong bit
     means `do_quiet` toggle and the canonical CommFlag.QUIET disagree.
   - **`PARALLEL-006`** (`do_purge`): `mud/commands/imm_load.py:176-177`
     `ACT_NOPURGE = 0x00002000` (canonical `1<<21`) and
     `ITEM_NOPURGE = 0x00000040` (canonical `1<<14`). Wrong bits mean
     NOPURGE-flagged NPCs/objects may get purged anyway. Affects the
     immortal `purge` command.
   - **`PARALLEL-002`** (`IMM_SUMMON`): `mud/commands/player_config.py:76`
     `IMM_SUMMON = 0x00000010` vs canonical `1<<0 = 0x1`. Affects NPC
     `nosummon` toggle (NPC branch only — PLR_CANLOOT/NOSUMMON/NOFOLLOW
     coincidentally have correct values).
3. **Then PARALLEL-008 / PARALLEL-011** (genuine cleanup — dead
   `.carrying` fallback in `consumption.py:308-316` + stale docstring
   at `handler.py:694`). Single mechanical commit.
4. **Then Class 1 BROADCAST_COVERAGE burn-down**: walk
   `audits/BROADCAST_COVERAGE.md` ❌/⚠️ rows in agent-priority order.
   **Before promoting each row to a gap-closer, verify helper
   coverage** — door commands likely covered by `world/movement.py`;
   combat skills routed through `damage()`. Helper hits collapse rows
   to ✅ without a commit; misses become gap-closers.
   - **Top 3 ranked**: BCAST-disarm/trip/dirt/surrender;
     BCAST-goto-001/002 (poofin/poofout); BCAST-invis-001 / BCAST-incognito-001.
5. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — order-dependent shared-state failure. Single gap-closer once
   isolated; probable root cause is `character_registry` state leakage
   breaking wiznet broadcast resolution to the immortal mailbox.
6. **GitNexus refresh**: index now 8 commits stale (last indexed
   `069f17f`). Run `npx gitnexus analyze --skip-agents-md` before
   any new probe.
7. **Locked Class 1 worktree hygiene**:
   `.claude/worktrees/agent-a1b07201d504ce97b` is still locked from
   the parallel-audit session. Unlock + remove in a separate hygiene
   pass (`git worktree unlock` then `git worktree remove -f`).
8. **Remaining META classes** (when ready to audit more): Class 2
   ARITHMETIC_BOUNDARY (half-session), Class 3 GATE_CONSISTENCY
   (session), Class 4 TRIGGER_CALL_SITE_MIGRATION (half-session),
   Class 5 LIFECYCLE_STAGING (session+).
