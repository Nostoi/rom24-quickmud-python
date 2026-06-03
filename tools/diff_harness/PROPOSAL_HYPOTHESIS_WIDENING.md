# Proposal — Hypothesis-driven scenario widening for the differential harness

> **Status:** IN PROGRESS (2026-06-03). Phase A's live C oracle and Phase B's
> bounded no-RNG Hypothesis state machine are complete. Phase C has started:
> object lifecycle widening (`__oload`, get/wield/wear/remove/drop) is live and
> already surfaced FINDING-016. Wider deterministic vocabulary / watch-set, then
> RNG-locked combat, remain next. This is the only
> thread that attacks **unknown unknowns** — divergences nobody has named (see
> the divergence-class roster's guardrail 3: behavior-diffing is the sole
> enumeration-independent check).

## Problem

`tools/diff_harness/` today replays **4 hand-written scenarios**
(`scenarios/*.json`: `affect_armor`, `combat_melee_rounds`, `movement_get_drop`,
`spell_combat`). Each is a fixed `steps` list diffed against a committed C
**golden**. That means the harness only ever compares the C engine and the
Python port on **4 narrow, human-authored paths**. The entire rest of the play
space — every command sequence nobody thought to script — is never diffed, so
any divergence living there is invisible. This is the harness's coverage limit,
and it is the dominant blind spot in our completeness story.

## Approach

Replace (augment) hand-written `steps` with **Hypothesis-generated** command
sequences, run both engines on each generated sequence, and diff the watched
state. Hypothesis explores paths a human never would and **auto-shrinks** any
failing sequence to a minimal reproducer.

### Component 1 — command-generating state machine

A Hypothesis `RuleBasedStateMachine` where each rule is a MUD command
(`move <dir>`, `get <obj>`, `drop`, `look`, `wear`, `remove`, `cast <known>`, …)
with **preconditions** drawn from current state (cannot drop what is not held;
cannot move through a closed door). Goal: generate *legal* play, not garbage —
too random and every step is a rejected no-op; too narrow and corners are
missed. This strategy design is the main intellectual effort.

### Component 2 — a LIVE C oracle (the real infrastructure lift)

Today's everyday replay needs **no C build** because it replays committed
goldens (`tests/data/golden/diff/`). A *generated* sequence has no golden, so the
instrumented C engine must be driven **live**: build `src/Makefile.diffshim`
once, then feed each generated sequence to the shim and capture its watched
state in-process, the same snapshot shape `pysnap.py` produces for Python.
Reuse `capture.py`/`compare.py`/`schema.py`; the new piece is a per-sequence
(not per-golden) C driver. This reintroduces the C-build dependency that the
fast replay path deliberately avoids — it is the bulk of the work.

### Component 3 — diff + shrink

After each sequence, diff Python's watch-set snapshot against the C oracle's. On
mismatch, Hypothesis shrinks to the minimal failing sequence — e.g. "reproduces
with just `cast armor; remove armor`." Pre-minimized repros are the single
biggest payoff over hand-scenarios.

### Component 4 — determinism plumbing

Both engines share the Mitchell-Moore RNG, so a fixed seed should keep their
draws aligned step-for-step. The current scenarios are deliberately **no-RNG**
to sidestep this. Combat widening requires *proving* seed alignment holds across
both engines per step before any combat diff is trusted (otherwise RNG skew
masquerades as a parity bug).

## Phasing

- **Phase A — live C oracle.** ✅ Complete 2026-06-03. `drive_c_oracle()`
  stands up per-sequence `diffshim` driving (no Hypothesis yet), accepts
  in-memory scenarios, and reuses the existing schema/compare path. The golden
  capture CLI delegates to the same driver.
- **Phase B — no-RNG state machine.** ✅ Complete 2026-06-03. A bounded
  Hypothesis `RuleBasedStateMachine` generates legal deterministic sequences
  over `look`, `inventory`, north/south movement, and `get/drop pit`, drives live
  C and Python, and diffs the traces. It intentionally stays small and cheap;
  Phase C owns vocabulary/watch-set widening.
- **Phase C — widen.** IN PROGRESS 2026-06-03. Added object injection plus
  legal get/wield/wear/remove/drop rules for deterministic sword/armor
  lifecycle paths, then an open container (bag `3032`) with put/get-from-container
  rules, keeping the generated budget bounded (`max_examples=4`,
  `stateful_step_count=5`). This surfaced FINDING-016 (`remove` left stale
  `worn_by`) and FINDING-017 (`add_object` appended instead of head-inserting,
  inverting inventory order vs ROM `obj_to_char` → INV-039), both now resolved.
  The container coverage needed no C shim or snapshot-schema change — both
  engines route `put`/get-from-container through the existing `interpret()` path,
  and the flat inventory/room-contents fields catch put→get round-trip
  divergences. Continue growing deterministic command vocabulary and the
  watch-set; add RNG-locked combat only after seed alignment is proven.
- **Each phase:** triage every mismatch into `FINDINGS.md` → a parity gap.
  Expect an initial *burst* of findings (untrodden paths) — that is the point,
  and it is real triage load.

## Honest limits (this is "wider," not "complete")

- **Only diffs the `watch` set.** A divergence in an un-watched field is
  invisible — widening paths also means widening watched state, which adds noise.
- **Only explores commands in the strategy.** A bug reachable solely via an
  un-modeled command stays hidden.
- **Compute-bounded.** Every generated case runs *two* engines; thousands of
  cases is real wall-clock — cap and `log()` what was sampled vs. skipped.
- **A divergence is a FINDING, not a golden to overwrite** (AGENTS.md). ROM is
  the source of truth; triage and fix Python/data, never edit the golden green.

## Rough effort

Multi-day, not a session. Phase A is the cost center (live C driving). Phases
B/C are incremental once A exists. Dependency add: `hypothesis` (dev-only).

## Why this is worth it despite the cost

It is the **only** method that finds invariants we have not enumerated. The
divergence-class roster and `/rom-divergence-sweep` lock down what we *know*;
this is how we discover what we *don't*. Until it (or equivalent broad
differential coverage) runs, "close on the known surface" must never be relayed
as "close to ROM parity."
