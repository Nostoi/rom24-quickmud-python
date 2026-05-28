# Session Status — 2026-05-28 — invariant checker (2.10.0) + differential harness v1

## Current State

- **Active mode**: parity-verification *tooling* pass. The per-file audit tracker
  has no ⚠️/❌ rows; this session built infrastructure to make cross-file /
  cross-engine parity verification systematic rather than judgment-driven.
- **Last completed**:
  - **`room_registry` xdist isolation leak** ✅ FIXED (2.9.91, `5396c067`) — see
    `SESSION_SUMMARY_2026-05-28_ROOM_REGISTRY_ISOLATION_LEAK.md`.
  - **`game_tick` invariant checker** ✅ SHIPPED (2.10.0, `04e8f67d`) —
    `mud/diagnostics/invariants.py` asserts steady-state ROM invariants
    (FIGHTING-COHERENCE, ROOM-PEOPLE-COHERENCE) after every `game_tick` in the
    suite; gated off in production; opt out via `@pytest.mark.no_invariant_check`.
    Surfaced 3 artificial-setup tests (marked), zero real bugs.
  - **Differential testing harness v1** ✅ BUILT on branch `diff-harness`
    (unmerged; 2.11.0 on the branch) — ROM C ⇄ Python golden capture/replay.
    First run surfaced **FINDING-001** (NPC `look` name vs ROM long_descr;
    ambiguous root cause incl. malformed `area/midgaard.are`); gated xfail,
    triage deferred.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_INVARIANT_CHECKER_AND_DIFF_HARNESS.md](SESSION_SUMMARY_2026-05-28_INVARIANT_CHECKER_AND_DIFF_HARNESS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | 2.10.0 (branch `diff-harness`: 2.11.0, unmerged) |
| Tests (master) | **4905 passed, 4 skipped, 0 failed** (parallel, `-n auto`). Branch adds 6 diff-harness unit tests + 1 xfail (FINDING-001) → 4911 passed / 1 xfailed there. |
| ROM C files audited | 40 / 43 ✅ (3 N/A). Per-file queue drained. |
| Cross-file invariants | 24 ENFORCED. New: an always-on `game_tick` checker generalizes 2 of them (INV-005/006, INV-010) into continuous suite-wide probes. |
| Branch | `master` — **6 commits ahead** of `origin/master` (2.9.91 + 2.10.0 + specs/plan). `diff-harness` — 12 commits, local-only, unmerged. |

## Next Intended Task

1. **FINDING-001 triage** (branch `diff-harness`) — pin the `mob_registry`
   long_descr diagnostic nondeterminism, reconcile C/Python inputs (repair
   `area/midgaard.are` to match stock ROM vs point Python at the repaired
   overlay), fix the real cause; the harness xfail auto-clears. See
   `tools/diff_harness/FINDINGS.md`.
2. **Extend the invariant checker** — add INV-003 (REGISTRY-MEMBERSHIP),
   INV-013 (OBJECT-LOCATION), INV-015 (AFFECT-EXPIRY) one at a time, fix-fallout.
3. **Merge `diff-harness`** once FINDING-001 is resolved; then add a combat/RNG
   differential slice (the RNG is already bit-matched).
4. **INV-025 non-combat narration sweep** — still open from earlier.
5. **GitNexus** — on-disk graph stale (`2272b2e`) and the MCP DB has been
   read-only all session; re-run `npx gitnexus analyze --skip-agents-md` once the
   lock clears.
