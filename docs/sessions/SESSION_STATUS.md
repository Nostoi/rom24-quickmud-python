# Session Status — 2026-06-02 — INTERP-025 self-targeted socials CLOSED (2.12.57)

## Current State

- **Active mode**: cross-file invariants. **INTERP-025 is now CLOSED** —
  self-targeted socials (`smile self` / `smile <ownname>`) reach
  `char_auto`/`others_auto` instead of "They aren't here." This was the last
  Outstanding item from the 2.12.56 INV-025 socials session.
- **This session — one commit (local, NOT pushed):**
  - **2.12.57 / `d15025b5`** — `perform_social`'s victim search now maps
    `"self"` → `char` and no longer skips `char`, mirroring ROM `get_char_room`
    (`src/handler.c:2194-2214`: returns `ch` for `"self"`, people loop has no
    self-skip). Done **socials-local** — the shared `get_char_room` was
    deliberately not touched (its own self-by-name divergence + CRITICAL
    14-caller blast radius). New test
    `tests/integration/test_interp025_social_self_target.py`; flipped
    `test_socials.py::test_social_targeting_self` to ROM-correct. Carries the
    version bump + CHANGELOG + audit-row flips.
  - **Filed durably (out-of-scope, ❌ OPEN):** **HANDLER-001**
    (`HANDLER_C_AUDIT.md`) — shared `get_char_room` skips self-by-name (ROM
    doesn't); 14-caller sweep needed; corrected its false-✅ "Verified" row.
    **INTERP-026** (`INTERP_C_AUDIT.md`) — socials' hand-rolled search lacks
    `can_see` gating (presence leak) and `N.name`; natural fix is migrating
    socials onto the shared `get_char_room` after HANDLER-001 lands.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INTERP025_SOCIAL_SELF_TARGET.md](SESSION_SUMMARY_2026-06-02_INTERP025_SOCIAL_SELF_TARGET.md)
  (prior: [INV025_SOCIALS_PERS](SESSION_SUMMARY_2026-06-02_INV025_SOCIALS_PERS.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.57 |
| Tests | **full suite green: 5310 passed, 4 skipped** (`pytest`, ~114s parallel) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open gaps | **HANDLER-001** (shared `get_char_room` self-by-name skip, 14 callers) + **INTERP-026** (socials search lacks can_see/N.name) — both filed, OPEN. |

## Next Intended Task

Cross-file invariants remains the active pass. Two tracks:

1. **Close HANDLER-001 + INTERP-026 together** — fix the shared `get_char_room`
   self-by-name skip (`char_find.py:51`) with a 14-caller `victim == ch` sweep
   (each caller's self-target branch re-checked against its ROM counterpart),
   then migrate `perform_social` onto the shared helper — that also closes
   INTERP-026's can_see presence leak + N.name. Test-first per the gap rows.
2. **Or probe a fresh cross-file candidate** — position transitions
   (`do_stand`/`do_sit`/`do_rest`/`do_sleep`/`do_wake` — tightest, deterministic,
   no RNG), group/follower chains, or mob trigger ordering. Method: read ROM C
   contract → read Python equivalent → one failing test → close as gap or file
   as next free INV-NNN.

> **Push note:** everything through 2.12.48 is on `master`; **2.12.49–57** are
> committed locally but **NOT yet pushed**. README/CHANGELOG/version all reflect
> 2.12.57. GitNexus reindex was completed after the commit (index fresh at
> `d15025b5`).
