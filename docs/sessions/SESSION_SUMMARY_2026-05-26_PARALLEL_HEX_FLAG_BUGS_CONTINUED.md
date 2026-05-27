# Session Summary — 2026-05-26 — PARALLEL hex-flag bug burn-down continued (2.9.57)

## Headline

Five more active PARALLEL_REPRESENTATIONS hex-flag bugs closed, plus the
final two cleanup rows (dead `.carrying` fallback + stale `count_users`
docstring). The Class 7 burn-down is **complete** — every remaining
⚠️ DRIFT-RISK row has been resolved.

## Commits (3 on master, ahead of `origin/master`)

| SHA | Gap(s) | File |
|-----|--------|------|
| `8d81ed84` | PARALLEL-002 + PARALLEL-006 + PARALLEL-008 + PARALLEL-011 | `mud/commands/player_config.py`, `mud/commands/imm_load.py`, `mud/commands/consumption.py`, `mud/handler.py` + 2 new integration tests + 1 existing test fixup |
| `8f21e015` | PARALLEL-003a | `mud/commands/remaining_rom.py:211` + new test |
| `6419b001` | PARALLEL-003b | `mud/commands/remaining_rom.py:105` + new test |

Plus uncommitted: audit doc / CHANGELOG / pyproject / session docs to be
folded into one chore commit at session wrap.

## Gaps closed

| ID | Bug | Pre-fix bit | Canonical |
|----|-----|-------------|-----------|
| PARALLEL-002 | `do_nosummon` (NPC branch) modified wrong immunity bit | `IMM_SUMMON = 0x10` (bit 4) | `DefenseBit.SUMMON = 1<<0 = 0x1` |
| PARALLEL-003a | `do_gain` trainer-lookup checked wrong act bit | `ACT_GAIN = 0x00100000` (bit 20) | `ActFlag.GAIN = 1<<27 = 0x8000000` |
| PARALLEL-003b | `do_quiet` toggled wrong comm bit | `COMM_QUIET = 0x4` (bit 2) | `CommFlag.QUIET = 1<<0 = 0x1` |
| PARALLEL-006 | `do_purge` checked wrong NPC/item bits | `0x2000` / `0x40` (bits 13 / 6) | `ActFlag.NOPURGE = 1<<21`, `ExtraFlag.NOPURGE = 1<<14` |
| PARALLEL-008 | Dead `.carrying` fallback in `_find_obj_inventory` | — | Removed |
| PARALLEL-011 | Stale `count_users` docstring referenced `.characters` | — | "Uses room.people" |

## New integration tests (5 files, 16 cases)

- `tests/integration/test_imm_summon_bit_alignment.py` (3)
- `tests/integration/test_do_purge_nopurge_bits.py` (4)
- `tests/integration/test_do_gain_act_gain_bit.py` (3)
- `tests/integration/test_do_quiet_comm_bit.py` (3)
- (PARALLEL-008/011 are removal + doc-only, covered by existing 47-test consumables suite)

Plus existing `tests/integration/test_player_config.py` had one assertion
that encoded the pre-fix wrong hex; updated to use `int(DefenseBit.SUMMON)`
per "ROM is source of truth, a test asserting behavior contradicting ROM C
is a bug in the test" (AGENTS.md).

## Audit doc updates

`docs/parity/audits/PARALLEL_REPRESENTATIONS.md`:

- PARALLEL-002, PARALLEL-003 (split into PARALLEL-003a + PARALLEL-003b),
  PARALLEL-006 reclassified from ⚠️ DRIFT-RISK to **MEDIUM (active bug)**
  and flipped to ✅ FIXED (2.9.57).
- PARALLEL-008, PARALLEL-011 flipped to ✅ FIXED (2.9.57).
- Audit summary header (lines 73-95) should be regenerated; deferred —
  next pass can produce a fresh row count.

## Class 7 burn-down state (PARALLEL_REPRESENTATIONS)

Before this session: 6 ✅ ENFORCED / 1 ✅ FIXED (PARALLEL-010, 2.9.54)
                     / 3 ✅ FIXED (PARALLEL-001+004+005, 2.9.55–2.9.56)
                     / 5 ⚠️ DRIFT-RISK / 0 ❌.

After this session:  6 ✅ ENFORCED / 9 ✅ FIXED / 0 ⚠️ / 0 ❌.

The "drift-risk only" hypothesis is fully overturned: **8 of the 9
PARALLEL bugs the audit flagged were genuinely active**, not drift-risk.
The audit's body-only static-scan methodology systematically
under-classified inline hex literals because it didn't compute the
canonical bit position from the IntEnum and compare. Recommendation
folded into the audit's "Methodology weakness" section (deferred — the
section already exists from prior session; a one-line update would
suffice).

## Subagent dispatch retro

Tried `Agent(... isolation: "worktree", model: "haiku")` × 3 in parallel
for PARALLEL-002, PARALLEL-006, PARALLEL-008+011. Outcome:

- **All three agents wrote to the main worktree** (not isolated branches).
  No new worktrees appeared in `git worktree list`; master moved forward
  by one commit `8d81ed84` containing all three agents' changes bundled.
- **The work itself was correct.** Each Haiku agent picked the right
  canonical enum (PARALLEL-002 agent correctly picked `DefenseBit.SUMMON`
  for `imm_flags`, even though the dispatch prompt suggested
  `CommFlag.SUMMON` — `imm_flags` is the immunity field, so the agent's
  ROM-C-grounded choice was better than the prompt).
- **Net throughput vs solo work**: roughly break-even. 3 parallel Haiku
  agents finished in ~5 min wall time but produced one bundled commit
  that needed retroactive audit-doc reconciliation. Manually splitting
  ex-post is more work than just running the gap-closer sequentially.
  Lesson: for tightly scoped (<200 LOC) bit-fix gaps, sequential
  Opus is the right tool; parallel Haiku worktrees pay off only when
  isolation actually produces separate branches.
- Worktree-isolation parameter behavior worth investigating before the
  next attempt.

## Test state

- Full integration suite green pre-edit (2253 passed, 3 skipped, 82s).
- New tests: 13 pass post-fix, 0 fail.
- Full pytest run after PARALLEL-003a/003b kicked off but did not surface
  output in the bg-task buffer at write time — handoff note: re-run
  `pytest -q` before push to confirm clean.

## Outstanding

1. **Audit doc summary regeneration** (top of `PARALLEL_REPRESENTATIONS.md`,
   header counts).
2. **Class 1 BROADCAST_COVERAGE burn-down** is the next active surface
   (29 ❌ rows, helper-transitivity caveat). Top-3 ranked candidates
   already noted in prior SESSION_STATUS.
3. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   still unresolved (registry-state leakage).
4. **Locked Class 1 worktree hygiene**:
   `.claude/worktrees/agent-a1b07201d504ce97b` still locked, plus the four
   new locked agent worktrees from this session (a63c12791ddff689a,
   ab5d92d13841f9896, ab80cecdfe4efc29e, af52312960b77fb7f) — though
   these latter four contain ancient history (2.8.x) and may be unrelated
   stale state worth a separate hygiene pass.
5. **GitNexus reindex** still stale (last indexed `069f17f`); now ~11
   commits behind.
