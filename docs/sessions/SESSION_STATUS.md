# Session Status — 2026-06-02 — Divergence-Class Completeness Lens (2.12.75)

## Current State

- **Active mode**: cross-file invariants — now organized under a new
  **completeness lens**. This session was process/tooling (zero `mud/` code, zero
  tests changed); it built the measurement framework that sits *above* the
  cross-INV process, not new gap fixes.
- **New: divergence-class completeness lens** (`docs/parity/DIVERGENCE_CLASS_ROSTER.md`,
  DRAFT) — ~11 ROM↔Python *structural* divergence classes, each routed to a
  verification **layer**: A static bypass-guard (committable `rglob` test),
  B human domain-read (signed math), C dynamic differential (`diff_harness` /
  cross-INV). The lens *contains* the existing processes (grep-guards = Layer A,
  cross-INV = Layer C); it does not replace them. Run via the new
  **`/rom-divergence-sweep`** skill (a checker/locker of KNOWN invariants — it
  does **not** discover new ones).
- **Latest commit — 2.12.75 — INV-029 reconcile + async-delivery reclassify**
  (`2ab8d02f`):
  - **INV-029 row-cell reconcile**: the row cell falsely listed `do_say`/`do_tell`
    cousins as OPEN/uncapped, contradicting its own watch-list (CLOSED via
    ACT-CAP-003/004, committed tests). Corrected to match.
  - **async-delivery reclassified A→C**: a clean static guard proved infeasible
    (`do_yell` correctly hand-rolls the `create_task(send_to_char)` XOR; diverse
    legit `.messages.append`), so any bypass-grep false-positives. Now Layer C
    (behavioral, INV-001/027/029 + ACT-CAP-001..004 tests) + Layer-B review.
  - **diff_harness widening proposal** added (`PROPOSAL_HYPOTHESIS_WIDENING.md`).
- **Prior commit — 2.12.74 — lens + skill** (`03397e07`): the roster doc, the
  `/rom-divergence-sweep` skill, the four AGENTS.md epistemic guardrails, the
  CLAUDE.md routing row.
- **Four durable guardrails** now in AGENTS.md: method-in-skills/status-in-trackers;
  committed-guard > doc-✅; enumeration-dependence ⇒ "close on the known surface"
  ≠ "close to parity"; re-verify ✅ via recall oracle.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_DIVERGENCE_CLASS_LENS.md](SESSION_SUMMARY_2026-06-02_DIVERGENCE_CLASS_LENS.md).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.75 |
| Tests | **5355 passed, 4 skipped** (110.31s; identical to 2.12.73 baseline — no code/tests changed this session) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 26 enforced; lens reclassified async-delivery A→C, INV-029 row cell reconciled (no new rows) |
| Divergence-class lens | Layer A 3/5 guarded (RNG, equipment-key, attribute-naming); classes 5/6 to-do |
| Lint | `ruff check .` shows 1762 pre-existing errors (none introduced this session — zero `.py` touched) |

## Next Intended Task

1. **Layer-A to-do (cheap, via `/rom-divergence-sweep`):** investigate class 5
   (flag-hex) and class 6 (pointer-identity) — each yields either a committed
   guard or an honest reclassification (as async-delivery did when its grep
   false-positived).
2. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences. Phase A (live-C oracle)
   is the cost center.
3. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt); INV tracker consolidation (26 rows, past the ~20 soft cap).

> **Push note:** 2.12.74 (`03397e07`), 2.12.75 (`2ab8d02f`), + this handoff are on
> local `master`, **not pushed** — on top of the unpushed 2.12.72/2.12.73 from the
> prior session. CHANGELOG/version reflect 2.12.75.
