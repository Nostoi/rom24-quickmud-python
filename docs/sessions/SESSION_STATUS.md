# Session Status — 2026-06-02 — INV-034 pointer-identity fully closed (2.12.80)

## Current State

- **Active mode**: cross-file invariants under the **divergence-class
  completeness lens**. This session executed the prior session's documented
  next task: the **root fix of INV-034** (pointer-identity, divergence class 6).
- **INV-034 (pointer-identity) → ✅ ENFORCED, class 6 → ✅ FULLY CLOSED**
  (2.12.78–80). **All five entity runtime types** are now `@dataclass(eq=False)`:
  `Character` (PCs), `MobInstance` (mobs — `spawn_mob` return type, highest-risk
  twin case), `Object`, `Room` (rooms — `ROOM_INDEX_DATA *`, 2.12.80), and legacy
  `ObjectInstance`. `__eq__`/`__hash__` inherited from `object` (identity = ROM
  pointer semantics; entities also become hashable). Each flip was gated on a
  value-eq test-reliance sweep that came up empty, and driven RED-first. The
  strict-xfail demos flipped xfail→pass; added Character + Room behavioral tests
  and a class-level regression guard over all five types. **`MobInstance`/
  `ObjectInstance` were caught by adversarial review after the first
  `Character`/`Object` commit** — `eq=False` does not propagate to sibling
  non-subclass entity dataclasses, and a green suite can't detect the gap (combat
  mobs differ in hp/position, so `attacker != victim` stays True under value-eq).
  Production `attacker != victim` / `object_registry.remove` / mob-membership
  sites are *corrected*, not regressed. **No class-6 follow-up remains.**
- **Layer A remains at its feasible ceiling** (4/4 static-guardable classes:
  RNG, equipment-key, attribute-naming, flag-hex). The two behavioral classes
  (async-delivery class 4, pointer-identity class 6) are Layer C — and class 6 is
  now enforced via the model-level fix rather than a per-site grep.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV034_POINTER_IDENTITY_ROOT_FIX.md](SESSION_SUMMARY_2026-06-02_INV034_POINTER_IDENTITY_ROOT_FIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.80 |
| Tests | 5361 passed, 4 skipped (full run) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 27 rows (INV-034 now ✅ ENFORCED) |
| Divergence-class lens | Layer A 4/4 feasible; **class 6 (pointer-identity) ✅ FULLY CLOSED** (Character/MobInstance/Object/Room/ObjectInstance eq=False) |
| Lint | `ruff check` clean on edited files (repo carries 1762 pre-existing errors; none introduced) |

## Next Intended Task

Divergence class 6 (pointer-identity) is now **fully closed** — no INV-034
follow-up remains. Candidate next passes:

1. **Highest-ceiling (deliberate multi-day project):** `diff_harness` Hypothesis
   widening (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences (the roster is
   enumeration-dependent; "close on the known surface" ≠ "close to parity").
2. **Standing cross-INV candidate:** mob-trigger ordering (bribe/exit/fight/kill/
   hpcnt) via the probe-then-scope method.
3. **Housekeeping:** INV tracker consolidation (now 27 rows, past the ~20 soft
   cap per AGENTS.md).

> **Push note (re-verified 2026-06-02):** `origin/master` is at `e0071711`
> (2.12.77 — this session's starting point), so prior work **is** pushed. Only
> this session's 4 commits are unpushed: `199827b4`, `fb4b6c0f`, `8ceb2561`,
> `420ffe66` (2.12.78–80, INV-034 / class-6 closure). CHANGELOG/version reflect
> 2.12.80. (The prior "2.12.72–2.12.77 unpushed" note was stale — corrected
> against `git log origin/master..master`.)
