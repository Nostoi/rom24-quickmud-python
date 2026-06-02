# Proposal — Hypothesis-driven scenario widening for the differential harness

> **Status:** PROPOSAL (2026-06-02). Not started. Scoped here so it can be
> picked up as a deliberate multi-day project when the team chooses to push past
> the *known* parity surface. This is the only thread that attacks **unknown
> unknowns** — divergences nobody has named (see the divergence-class roster's
> guardrail 3: behavior-diffing is the sole enumeration-independent check).

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

- **Phase A — live C oracle.** Stand up per-sequence `diffshim` driving (no
  Hypothesis yet). Pure infrastructure; reuses existing capture/compare.
- **Phase B — no-RNG state machine.** Minimal `RuleBasedStateMachine` over the
  deterministic command subset (move / get / drop / wear / remove / look /
  inventory). Extends the existing v1 deterministic slice; lowest risk.
- **Phase C — widen.** Grow the command vocabulary and the watch-set; add
  RNG-locked combat only after Phase-B seed alignment is proven.
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
