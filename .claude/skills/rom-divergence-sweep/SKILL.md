---
name: rom-divergence-sweep
description: Run a completeness sweep on ONE ROM↔Python divergence class (async-delivery, RNG, equipment-key, pointer-identity, signed-math, ordering, …) and route it to its correct verification layer. Use when measuring "how close to done" on a known class, validating that a class is clean, or converting a hand-verified contract into a self-maintaining guard. Encodes the convergence-probe + recall-oracle + layer-routing method. Status lives in docs/parity/DIVERGENCE_CLASS_ROSTER.md; this skill produces a guard test (Layer A), a domain-read note (Layer B), or a diff_harness scenario (Layer C) — never a bare ✅ in an instruction file. NOT a replacement for cross-INV probe-then-scope, rom-gap-closer, or rom-parity-audit — it points work INTO them.
---

# ROM Divergence Sweep (one class → its verification layer)

You are measuring/closing **one divergence class** — a place where the C engine
and the Python port differ *structurally* (sync vs async, pointer vs GC
identity, array vs dict, C-int vs Python-int, static-buffer reuse, fread
parsing). The roster of classes lives in
[`docs/parity/DIVERGENCE_CLASS_ROSTER.md`](../../docs/parity/DIVERGENCE_CLASS_ROSTER.md).

This is the **completeness lens** that sits above the per-file audit and the
cross-INV process. It does not replace them — it tells you *which method* a
contract needs and validates that the method actually has recall.

## What this finds vs. what it CANNOT find (read this first)

This skill **measures and locks invariants you already know about.** It does
**NOT discover new ones.** Concretely:

- ✅ **It does:** take a *known* contract (e.g. "messages cap + deliver once"),
  read the C source to enumerate every site the contract applies to, read the
  Python code to confirm nothing bypasses the canonical chokepoint, cross-check
  the trackers, and — if clean — install a self-maintaining guard test.
- ❌ **It does NOT:** read the C codebase and *surface a brand-new hidden
  cross-file rule*. It starts from a contract you hand it; it cannot tell you
  which contracts exist.

So this is a **checker/locker, not a finder.** Discovering new invariants stays
with two other processes, and you must not mistake a clean sweep here for "no
unknown invariants remain":

- **New rule discovery (human):** the cross-INV "probe-then-scope" process —
  read a C contract, notice the Python port could break it, write a failing
  test, file the next INV-NNN. (See AGENTS.md "Cross-File Invariants".)
- **Unknown-unknown discovery (automated):** `tools/diff_harness/` runs the C
  engine and the Python port on identical inputs and diffs the output — it
  surfaces divergences *no human named first*. This is the only
  enumeration-independent check (guardrail 3).

If a sweep here comes back clean, the honest claim is "this *known* class is
enforced," never "this class is bug-free" and never "we are close to parity."

## Read first

- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — the class roster + layer model.
- The "Cross-File Invariants" and "Completeness lens & verification epistemics"
  sections in `AGENTS.md`.

## The four guardrails (non-negotiable — they are why this skill exists)

1. **Durable surfaces hold method; trackers hold status.** Never write a number,
   a ✅, or "class X is clean" into a SKILL.md / CLAUDE.md / AGENTS.md. Status
   goes in the roster doc (expected to rot, re-verified on read).
2. **A committed guard beats a doc-✅.** A `rglob → forbid-pattern → assert`
   test is self-maintaining (a regression re-opens it); a tracker note rots.
   Prefer turning a verified contract into a test over writing "verified."
3. **The roster is enumeration-dependent — it is blind to classes nobody named.**
   The only enumeration-*independent* check is differential execution
   (`tools/diff_harness/`). Therefore **"close on the known surface" ≠ "close to
   ROM parity."** Never let those two sentences blur.
4. **Re-verify any ✅/status claim against ROM C source (or an empirical run on
   the installed tool) before relying on or relaying it.** (Reinforces the
   existing AGENTS.md rule.)

## Phase 1 — pick the class and its layer

Pick one class from the roster. Classify which verification layer fits:

- **Layer A — static bypass-guard.** Contract is "every site must route through
  one canonical chokepoint" (RNG → `rng_mm`; equipment → int key; delivery →
  `act_format`/`broadcast_room`/`push_message`). → committable scan.
- **Layer B — human domain-read.** Contract is domain-conditional, no single
  chokepoint (signed math: `c_div`/`c_mod` only where an operand can be
  negative). → enumerate sites, read each domain; no clean global scan.
- **Layer C — dynamic/temporal.** Contract is ordering/lifecycle, no chokepoint
  (prompt-after-`raw_kill`, tick ordering). → `diff_harness` scenario or
  behavioral INV test. This is where the **cross-INV process** lives.

If unsure A-vs-B, attempt the Layer-A pattern; if it false-positives on correct
code (e.g. a blanket `//` ban flagging non-negative uses), it is Layer B.

## Phase 2 — convergence probe

1. **Enumerate.** List every Python site/primitive that should honor the
   contract (grep / ast-grep / the chokepoint's callers).
2. **Check routing.** For each, confirm it routes through the canonical
   chokepoint (capped/canonicalized/registered) rather than bypassing it.
3. **Diff against the tracker.** Cross-reference what you found against what the
   trackers already document as open:
   - in sweep, not in tracker → **candidate new gap** (discovery).
   - in tracker, not in sweep → your query has a **recall hole** — fix it before
     trusting any "nothing found."
   - intersection → **convergence** (this is the completeness evidence).

## Phase 3 — recall oracle (do not skip)

Before trusting the sweep's silence, prove it has recall: take a contract the
trackers *already* list as open/deferred for this class and confirm the sweep
**independently re-derives it** without being told. If it does → trust the
residual. If it misses it → the query is holed; do not report "clean."

⚠️ A known-open item re-surfacing is **recall validation, NOT a fresh find.**
Counting it as discovery is the trap.

## Phase 4 — act on the result, by layer

- **Layer A, clean:** commit a bypass-guard test (`tests/test_*_convention.py`
  shape: `rglob("*.py")` → forbid-pattern → `assert not offenders`). This is the
  durable output — it locks the class self-maintainingly.
- **Layer A, bypass found:** that's a gap → hand to `rom-gap-closer` (one
  failing test, one fix, one commit). If the root cause crosses files, it's a
  cross-INV → file the next free INV-NNN.
- **Layer B:** record the domain-read as a note in the roster row; flag new
  `//`/`%` for PR review. No false "done."
- **Layer C:** write/extend a `diff_harness` scenario or behavioral INV test.
- **Doc-rot found** (tracker says open, code is closed, or vice-versa): fix the
  tracker row, citing the live cap/route sites. File durably per the AGENTS.md
  out-of-scope-bug routing table — a stale status claim is itself a finding.

## Phase 5 — update status (in the tracker, never the skill)

- Update the class's row in `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: guard
  status, layer, clean/open, evidence (test file or INV id).
- Add a CHANGELOG entry if a guard/test landed.
- Mark any cell you did **not** verify this pass as `unverified` — do not
  inherit a prior ✅ as live.

## What this skill does NOT do

- It does not claim to enumerate all parity risk — only the cross-class
  *structural* surface. Per-function logic errors → `rom-parity-audit`; unported
  features → `ROM_PARITY_FEATURE_TRACKER.md`; unknown-unknowns → only
  `diff_harness` coverage moves that needle (guardrail 3).
- It does not batch. One class per sweep, one guard/finding per commit.
