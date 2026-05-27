# Session Status — 2026-05-27 — BCAST wiz/imm + bug-filing discipline (2.9.60)

## Current State

- **Active audit**: META Class 1 BROADCAST_COVERAGE burn-down (in progress).
- **Last completed**:
  - **Fix**: BCAST-018 `do_quit` (TO_ROOM `$n has left the game.`).
  - **COVERED collapses**: BCAST-007 (envenom), BCAST-020 (report),
    BCAST-029 (violate).
  - **⚠️ BLOCKED annotations**: BCAST-002 (clone obj branch), BCAST-014
    (mload), BCAST-015 (oload) — all by new WIZLOAD-001 bug (3 layered
    name typos in wiz-load/clone surface).
  - **Workflow upgrade**: AGENTS.md + `rom-gap-closer` SKILL.md now
    require durable filing of out-of-scope bugs surfaced mid-audit.
  - **New cross-file invariant candidate**: INV-027 ACT-INVIS-TRUST-GATE
    on Watch list (Python `_act_room` / `broadcast_room` lack ROM's
    per-recipient `get_trust >= invis_level` filter).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md](SESSION_SUMMARY_2026-05-27_BCAST_WIZIMM_PROBE_DISCIPLINE.md)
  (predecessors:
  [SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md](SESSION_SUMMARY_2026-05-27_BCAST_DOOR_COMMANDS.md),
  [SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md](SESSION_SUMMARY_2026-05-26_BCAST_BURNDOWN_OPENING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.60 |
| Tests | Integration suite 2270/2270 + 3 documented skips (2:13) — last full run earlier today during 2.9.59 push. This sub-session: `tests/integration/test_quit_broadcasts.py` 3/3 new + 24/24 adjacent `quit`/`session` green. Full `pytest -q` still hangs past 15min on this machine (pre-existing). |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged). |
| Cross-file invariants | 23 ENFORCED + 1 candidate (INV-027 ACT-INVIS-TRUST-GATE, Watch list). |
| Meta-audit progress | **5 of 8 META classes audited.** Class 1 BROADCAST_COVERAGE burn-down: **21 of 29 ❌ rows resolved or routed since 2.9.58 opening** (8 fixed, 7 COVERED collapses, 3 ⚠️ BLOCKED by WIZLOAD-001, 3 deferred). 8 ❌ + 10 ⚠️ remain (out of 209 ✅ baseline). Class 7 PARALLEL_REPRESENTATIONS: COMPLETE. Class 8 MATH_AND_RNG: MATH-001 closed. |
| Branch | `master` — local 2.9.60 (3 prep commits + 1 chore commit to come) ahead of `origin/master` by 4 commits. |

## Next Intended Task

1. **Finalize session chore commit** — pyproject 2.9.60, CHANGELOG
   2.9.60 header, this SUMMARY, refreshed STATUS. Single chore
   commit.
2. **Push approval** required for 2.9.60 (4 commits to push).
3. **WIZLOAD-001 closure** (next session, ~25-line bundle):
   - `mud/commands/imm_load.py:68` → use `mob_registry`.
   - `mud/commands/imm_load.py:121, 126-127` → use `obj_registry`
     and `spawn_object` (drop unused `level` arg from the call;
     verify against ROM what to do with the level computation).
   - `mud/commands/imm_search.py:417, 424` → use `spawn_object`.
   - 3 regression tests: register a prototype, assert success.
4. **BCAST-002 / BCAST-014 / BCAST-015 gap closures** — standard
   `rom-gap-closer` per ID after WIZLOAD-001 lands. Single broadcast
   each.
5. **Other viable BCAST real gaps** (cheap, 1-2 broadcasts each):
   BCAST-017 `do_order`, BCAST-019 `do_reply`, BCAST-010 `do_gtell`,
   BCAST-028 `do_value`. Also verify BCAST-009 `do_group` — 2.9.20
   reportedly shipped a fix that the regex may have missed.
6. **Expensive remaining BCAST** (large act counts, defer): BCAST-006
   `enter` (5), BCAST-021-024 `rest`/`sit`/`sleep`/`stand` (4-12 each).
7. **⚠️ Partial BCAST closures** (BCAST-030 through 039) — bulk pass
   when the ❌ list is exhausted.
8. **INV-027 promotion** (ACT-INVIS-TRUST-GATE): introduce
   `_can_witness(actor, witness)` helper, thread through `_act_room`
   and `broadcast_room`, regression test in
   `tests/integration/test_inv027_act_invis_trust_gate.py`.
9. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   — still unresolved.
10. **GitNexus reindex** still stale (last `069f17f`); now ~25 commits
    behind. FTS index reported read-only/broken throughout this
    session. Run `npx gitnexus analyze --skip-agents-md` before next
    probe session.
11. **Worktree hygiene**: 5 locked worktrees in `.claude/worktrees/`
    from prior sessions.
12. **Remaining META classes**: Class 2 ARITHMETIC_BOUNDARY,
    Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION,
    Class 5 LIFECYCLE_STAGING.
