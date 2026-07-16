# Session Status — 2026-07-16 — Extract-cleanup matrix divergence sweep (INV-020/047 pet+raw_kill legs, FIGHT-095)

## Current State

- **Active focus**: **cross-file invariants / divergence-class probe** mode
  remains the parity default (per-file audit tracker at 100%, documented
  backlog drained). This session ran a multi-iteration divergence sweep of the
  **split-extract-funnel** class.
- **This run (v2.14.315 → v2.14.317):** 2 real gaps closed + 1 finding filed.
  - **INV-020 (pet leg)** — `_nuke_pets` inlined a *partial* pet-extraction; now
    runs the full `extract_char(pet, TRUE)` cleanup (`die_follower(pet)` +
    `clear_extract_target_refs(pet)`). A character following a dismissed pet no
    longer dangles at the extracted corpse.
  - **INV-047 (raw_kill leg)** — the primary combat-death funnel was missing the
    `reply`/`mprog_target` sweep; NPC leg now runs `clear_extract_target_refs`,
    gated on `is_npc` (ROM fPull semantics).
  - **FIGHT-095 (OPEN)** — filed: `check_assist`'s inner target-selection loop
    iterates room-people in Python but the global `char_list` in ROM
    (`vch->next`, 2.4b6 quirk). Needs a C-oracle diff-harness scenario before
    fixing (RNG-draw-count facet).
  - **5 clean probes** (convergent, no change): obj_update decay, position
    transitions, voluntary do_quit leg, char_update affect decay, xp_compute
    signed math. Differential harness rebuilt + 97/97 (64 scenarios) convergent.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md](SESSION_SUMMARY_2026-07-16_EXTRACT_CLEANUP_MATRIX_DIVERGENCE_SWEEP.md)
- **Prior session** (DATABASE_URL CWD-relative persistence fix):
  [SESSION_SUMMARY_2026-07-15_DATABASE_URL_CWD_PERSISTENCE_FIX.md](SESSION_SUMMARY_2026-07-15_DATABASE_URL_CWD_PERSISTENCE_FIX.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.317 |
| Tests | **6208 passed, 4 skipped, 0 failed** — clean parallel run (260s). (+4 vs last session's 6204, from this session's 4 new regression tests.) |
| ROM C files audited | 43 / 43 |
| Push status | **Local only** — 5 commits on `master`, NOT pushed (autonomous-loop commit-local directive); operator to review + push/publish. |
| Active focus | Cross-file invariants / divergence-class probe (split-extract vein now exhausted on all enumerated legs × steps) |

## Outstanding — deferred by design

- **FIGHT-095** (OPEN) — `check_assist` inner-loop iteration-domain quirk; author
  a C-oracle diff-harness scenario, then `/rom-gap-closer FIGHT-095`.
- **FIGHT-094** (OPEN) — `check_killer` placement inside `damage()` vs command layer.
- **DESC-001** (latent) — unreachable plain-replace description path.
- **OLC spell-name lookup** (`build.py:2617/2637`) — Tier-C deferred.
- **IS_BUILDER** (`look.py:261`) — TODO, area-builder subsystem not yet added.
- **Stray unused SQLite files** — `data/quickmud.db` (0 bytes), `doc/game.db`
  (stale). Confirm unused, then clean up.

## Next Intended Task

Close **FIGHT-095** (the one open, actionable gap from this session) by authoring
a `check_assist` diff-harness scenario with a cross-room group member and
validating the RNG-draw-count facet against the live C oracle. Otherwise resume
the divergence-class sweep on un-probed surfaces — but note the split-extract
vein (the reliable gap source this session) is exhausted; further probes on
faithful functions are expected to be mostly clean.
