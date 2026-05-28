# Session Status — 2026-05-28 — LOOK-001/002 (harness first catch) + invariant checker → opt-in

## Current State

- **Active mode**: parity-verification tooling + the gaps it surfaced. The
  differential testing harness (built this day) produced its first real catch,
  which closed two ROM-parity gaps on `master`; the always-on invariant checker
  was converted to opt-in after proving flaky against the suite's un-isolated
  global registries.
- **Loop closed (end-to-end harness demonstration):** `master` pushed to origin;
  `master` merged into `diff-harness` (`c878dd41`); re-running the differential
  harness confirmed the LOOK-001 fix — the room/output divergence is **gone**, the
  reference now matches. The harness then advanced to its next divergence
  (**FINDING-002**: test-character hp C=20 vs py=0), a harness char-creation
  asymmetry (C shim `new_char` vs Python `create_test_character`), not a parity
  bug — filed in `tools/diff_harness/FINDINGS.md`, scenario stays xfailed on it.
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
| Differential harness | v1 complete on `diff-harness`; **master merged in** (`c878dd41`). Loop demonstrated end-to-end: FINDING-001 (LOOK-001/002) fixed → re-run → room/output divergence gone. Now xfailed on **FINDING-002** (test-char hp asymmetry). |
| Branch | `master` — pushed to `origin` (`b3f52e2d`), in sync. `diff-harness` — local-only, merged with master, **2 open soundness follow-ups** (FINDING-002 char-creation + `.are`/JSON input asymmetry). |

## Next Intended Task

1. **Reconcile the harness soundness asymmetries** so its diffs are fully
   trustworthy: (a) **FINDING-002** — make the C shim and Python
   `create_test_character` produce identically-statted test chars (or seed
   hp/level on both); (b) **input source** — C reads `.are` (repaired midgaard
   overlay), Python reads `data/areas/*.json`; reconcile (regenerate JSON from the
   repaired `.are`, or repair the malformed `area/midgaard.are`). See
   `tools/diff_harness/FINDINGS.md`.
2. **Extend the harness** — combat/RNG slice, generated scenarios (per the spec's
   future paths); each as its own spec→plan.
3. **Merge `diff-harness` to master** once the soundness follow-ups are closed and
   the differential scenario goes fully green (no xfail).
4. **INV-025 non-combat narration sweep** — still open from earlier.
5. **GitNexus** — on-disk graph stale (`2272b2e`), MCP DB read-only all session;
   re-run `npx gitnexus analyze --skip-agents-md` once the lock clears.
