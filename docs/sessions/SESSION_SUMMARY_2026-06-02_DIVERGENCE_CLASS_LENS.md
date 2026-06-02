# Session Summary — 2026-06-02 — Divergence-Class Completeness Lens (process/tooling)

## Scope

A **methodology session, not a gap-close session** — zero `mud/` code and zero
tests changed. It began as a question: *"is there a realistic way to measure how
close the cross-file-invariants work is to done, and build a complete-ish
to-do list?"* That unfolded into: (1) establishing that cross-file invariants
have no countable denominator but **structural divergence classes** do; (2) a
hand-run convergence probe proving the measurement technique works; (3)
encoding the technique durably as a new skill + lens without disturbing the
existing parity processes; and (4) acting on the lens's first findings —
reconciling a stale INV-029 row cell and honestly reclassifying the
async-delivery class when its static guard proved infeasible.

The session repeatedly demonstrated its own central lesson (AGENTS.md guardrail
4): **re-verifying source caught the agent over-claiming twice** — a
sample-based "async is clean" claim missed `do_yell`/`communication.py:768`
until a broader grep, and a "doc-rot" label was imprecise until the source
showed an internal contradiction.

## Outcomes

### Divergence-class completeness lens — ✅ CREATED

- **Artifact**: `docs/parity/DIVERGENCE_CLASS_ROSTER.md` (DRAFT). Enumerates ~11
  ROM↔Python *structural* divergence classes and routes each to a verification
  **layer**: **A** static bypass-guard (committable `rglob → forbid → assert`,
  self-maintaining), **B** human domain-read (signed `c_div`/`c_mod`), **C**
  dynamic differential (`diff_harness` / cross-INV behavioral tests).
- **Key property**: the lens *contains* the existing processes — the three
  grep-guards (`test_rng_determinism` / `test_equipment_key_convention` /
  `test_attribute_convention`) are Layer A; the cross-INV process is Layer C. It
  does not replace them.
- **Denominator**: "number of classes" (~11), not "number of unknown bugs."
  Layer A is 3 of 5 guarded today.

### `/rom-divergence-sweep` skill — ✅ CREATED

- **Artifact**: `.claude/skills/rom-divergence-sweep/SKILL.md`. Encodes the
  convergence-probe + recall-oracle + layer-routing method.
- **Critical scoping**: leads with a "What this finds vs. CANNOT find" section —
  it **measures and locks KNOWN invariants; it does NOT discover new ones**.
  Discovery stays with the human cross-INV probe-then-scope and the
  enumeration-independent `diff_harness`.

### Four epistemic guardrails — ✅ ADDED to AGENTS.md

New "Completeness lens & verification epistemics" subsection (additive, +42/−0,
cross-INV section untouched): (1) durable surfaces hold *method*, trackers hold
*status*; (2) a committed guard beats a doc-✅; (3) the roster is
enumeration-dependent → **"close on the known surface" ≠ "close to parity"**,
only `diff_harness` is enumeration-independent; (4) re-verify ✅ claims via a
recall oracle. `CLAUDE.md` gained one routing-table row.

### INV-029 row-cell reconcile — ✅ FIXED

- **Finding**: the INV-029 **row cell** in `CROSS_FILE_INVARIANTS_TRACKER.md`
  still listed `do_say`/`do_tell` cousins as "remaining OPEN / still uncapped" —
  contradicting its **own watch-list**, which already recorded them CLOSED via
  ACT-CAP-003/004 (2.11.42–43, committed tests `test_act_cap_003/004_*.py`,
  verified to exist).
- **Fix**: corrected the stale status + enforcement clauses to match the
  (correct) watch-list. Only the `broadcast_global` **weather** path stays
  correctly uncapped (ROM uses `send_to_char`).

### Async-delivery class — ✅ RECLASSIFIED A→C (guard infeasible)

- **Attempt**: tried to lock async-delivery as a committed Layer-A guard.
- **Result**: a clean static bypass-guard is **infeasible** — `do_yell`
  (`communication.py:765-770`) correctly hand-rolls the
  `create_task(send_to_char)` XOR + `continue`, and `.messages.append` has many
  legitimate sites (`Character.send_to_char`, the broadcast primitives,
  actor-self lines). Any blanket grep false-positives. Per the skill's Phase-1
  rule, that means **not Layer A**.
- **Resolution**: reclassified to **Layer C** (enforced behaviorally by the
  INV-001 ×5 / INV-027 / INV-029 + ACT-CAP-001..004 integration tests), with a
  Layer-B "review new delivery sites" element. Roster row, the "3 of 5 Layer-A"
  count, and the to-do list updated.

### diff_harness widening proposal — ✅ SCOPED (not started)

- **Artifact**: `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`. A
  multi-day plan (Phase A live-C oracle → Phase B no-RNG `RuleBasedStateMachine`
  → Phase C widen + RNG-locked combat) for Hypothesis-driven differential
  coverage — the **only enumeration-independent path to *unknown* divergences**.

## Files Modified

- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — **new** (the lens)
- `.claude/skills/rom-divergence-sweep/SKILL.md` — **new** (the skill)
- `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md` — **new** (proposal)
- `AGENTS.md` — +"Completeness lens & verification epistemics" subsection (+42/−0)
- `CLAUDE.md` — +1 routing-table row
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 row-cell reconcile
- `CHANGELOG.md` — Added (lens/skill) + Fixed (reconcile/reclassify) entries
- `pyproject.toml` — 2.12.73 → 2.12.74 → 2.12.75
- **No `mud/` code, no tests** — purely docs/skill/tracker/proposal.

## Test Status

- **No code or tests changed this session**, so behavior is unchanged from the
  2.12.73 baseline (`5355 passed, 4 skipped`). Full suite re-run this session for
  a live number: **5355 passed, 4 skipped in 110.31s** — identical, confirming
  zero behavioral drift.
- `ruff check .` reports **1762 pre-existing errors** across the repo's Python
  (mostly import-organization) — **none introduced this session** (zero `.py`
  touched). Flagged as a separate, out-of-scope finding; AGENTS.md's "ruff clean"
  expectation does not currently match repo reality.

## Next Steps

1. **Layer-A to-do (cheap):** investigate classes 5 (flag-hex) and 6
   (pointer-identity). Expect either a clean committed guard *or* — as with
   async-delivery — an honest reclassification to Layer B/C when a bypass-grep
   false-positives. Run via `/rom-divergence-sweep`.
2. **Highest-ceiling (deliberate project):** the `diff_harness` Hypothesis
   widening (`PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only thread that attacks
   *unknown unknowns*. Multi-day; Phase A (live-C oracle) is the cost center.
3. **Standing cross-INV candidate** (carried from prior session): mob-trigger
   ordering contracts (bribe/exit/fight/kill/hpcnt); INV tracker consolidation
   (26 rows, past the ~20 soft cap).
4. **Do NOT** mistake Layer-A completeness for parity — guardrail 3.

> **Push note:** this session's commits — 2.12.74 (`03397e07`), 2.12.75
> (`2ab8d02f`), + this handoff — are on local `master`, **not pushed**. They sit
> on top of the unpushed 2.12.72/2.12.73 from the prior session.
