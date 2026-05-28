# Session Status — 2026-05-28 — LOOK-001/002 (harness first catch) + invariant checker → opt-in

## Current State

- **Active mode**: parity-verification tooling + the gaps it surfaced. The
  differential testing harness (built this day) produced its first real catch,
  which closed two ROM-parity gaps on `master`; the always-on invariant checker
  was converted to opt-in after proving flaky against the suite's un-isolated
  global registries.
- **Last completed** (on `master`):
  - **`LOOK-001`** ✅ FIXED (2.10.1, `506d2633`) — room `look` shows an NPC's
    `long_descr`, not its name (ROM `show_char_to_char_0`); `MobInstance` now
    carries `long_descr` from its prototype (ROM `create_mobile`). Found by the
    differential harness (FINDING-001) against an `act_info.c` row falsely marked
    "100% PARITY".
  - **`LOOK-002`** ✅ FIXED (2.10.2, `3888ff2a`) — `look <mob>` shows the NPC
    `description`; `MobInstance` now copies it too.
  - **Invariant checker → opt-in** (2.10.3, `7cb1194a`) — the 2.10.0 always-on
    `game_tick` checker was flaky (walks global registries the suite doesn't
    isolate); now opt-in via `@pytest.mark.check_invariants`. Checker + hook +
    unit tests retained.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_LOOK_GAPS_AND_CHECKER_OPT_IN.md](SESSION_SUMMARY_2026-05-28_LOOK_GAPS_AND_CHECKER_OPT_IN.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_INVARIANT_CHECKER_AND_DIFF_HARNESS.md](SESSION_SUMMARY_2026-05-28_INVARIANT_CHECKER_AND_DIFF_HARNESS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | 2.10.3 (branch `diff-harness`: 2.11.0, unmerged) |
| Tests (master) | **4909 passed, 4 skipped, 0 failed** — green across 3 consecutive parallel runs after the opt-in change (the xdist invariant-checker flake is resolved). |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `act_info.c` `show_char_to_char_0` row corrected from a false "100% PARITY" to LOOK-001 FIXED. |
| Cross-file invariants | 24 ENFORCED. The `game_tick` world-invariant checker (`mud/diagnostics/invariants.py`) is now an **opt-in** tool (`@pytest.mark.check_invariants`), not always-on. |
| Differential harness | v1 complete on branch `diff-harness` (unmerged). Its first catch (FINDING-001 → LOOK-001/002) is fixed on master. Branch xfail clears on merge. |
| Branch | `master` — **3 commits ahead** of `origin/master` (2.10.1 + 2.10.2 + 2.10.3), not pushed. `diff-harness` — local-only, unmerged. |

## Next Intended Task

1. **Push `master`** — 3 commits ahead (LOOK-001/002 + checker opt-in). Awaiting approval.
2. **Merge `master` → `diff-harness`** to clear the differential `xfail` and confirm
   the full capture/replay loop closes on the LOOK-001 fix.
3. **Reconcile the harness input-source asymmetry** — C reads `.are` (repaired
   midgaard overlay), Python reads `data/areas/*.json`; reconcile before trusting
   midgaard divergences broadly. Consider repairing the malformed `area/midgaard.are`.
   See `tools/diff_harness/FINDINGS.md`.
4. **Extend the harness** — combat/RNG slice, generated scenarios (per the spec's
   future paths); each as its own spec→plan.
5. **INV-025 non-combat narration sweep** — still open from earlier.
6. **GitNexus** — on-disk graph stale (`2272b2e`), MCP DB read-only all session;
   re-run `npx gitnexus analyze --skip-agents-md` once the lock clears.
