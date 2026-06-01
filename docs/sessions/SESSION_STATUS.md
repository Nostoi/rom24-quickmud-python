# Session Status — 2026-06-01 — CAST-009 + TRAIN-005 (open-gap queue drain) (2.12.42)

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted).
  The documented open-gap queue is now **empty** — both remaining 🔄 OPEN
  correctness gaps were closed this session.
- **Last completed (this session, 2.12.40 → 2.12.42)** — two single-gap TDD
  commits:
  - **CAST-009** (`3cc79497`, 2.12.41) — a failed cast now trains the spell
    skill (`_check_improve(char, skill, skill.name, False)` added to the
    concentration-lost branch of `do_cast`, ahead of the half-mana deduction;
    ROM `src/magic.c:553`). Message order verified async-deferred.
  - **TRAIN-005** (`b99a71ef`, 2.12.42) — bare `train` now shows the session
    count *and* the trainable-stat listing (no-arg branch emits a
    `session_prefix` then falls through with `args = "foo"`; ROM
    `src/act_move.c:1658-1663`).
  - **2 new integration tests** (one per gap); both failed-first, pass after.
    Area suites green (magic/skills 63, recall/train + advancement 59).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_CAST009_TRAIN005_QUEUE_DRAIN.md](SESSION_SUMMARY_2026-06-01_CAST009_TRAIN005_QUEUE_DRAIN.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.42 |
| Tests | **full suite green: 5242 passed, 4 skipped** (`-n0`, 12:54; `-n auto` hangs at worker startup under high machine load — use `-n0` if it recurs) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **none documented** — CAST-009 + TRAIN-005 closed; INV-025/027 structural queue already drained |

## Next Intended Task

The documented open-gap queue is drained. Next session:

1. **Open a fresh cross-file-invariants candidate area** (affect ticks, position
   transitions, mob script triggers, group/follower chain) per the AGENTS.md
   probe-then-scope method — read ROM C contract → read Python equivalent → one
   failing test → close as a gap or file the next free INV-NNN.

> **Push gate: CLEARED.** Full suite ran green (`5242 passed, 4 skipped`, `-n0`)
> once machine load recovered, and `master` was pushed to origin at `83c73b85`
> (2.12.42). This push also carried the prior session's 2.12.40 commits, which
> had likewise never been pushed (origin had been back at `0e9ced77`). All nine
> commits are covered by the green full-suite run.

> **Stale index note:** a `gitnexus analyze --skip-agents-md` reindex was started
> mid-session but **killed before completion** (it was contending with pytest for
> CPU under the machine overload). The GitNexus index is stale at `04f118e`. Run
> a reindex on a quiet machine before relying on `gitnexus_impact` /
> `gitnexus_detect_changes` results.

> **Distrust unverified audit-row ROM refs:** prior sessions found multiple rows
> with materially wrong ROM line numbers. Re-verify any ⚠️/❌ row against `src/`
> before relying on it.
