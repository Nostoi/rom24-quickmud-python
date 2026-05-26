# Session Status — 2026-05-26 — INV tracker consolidated to 22/~20 (2.9.41)

## Current State

- **2.9.40 INV-025 (MOBPROG-ACT-TRIGGER-DISPATCH)** enforced and
  pushed (`3dbc421`). MOBtrigger global + `disable_mobtrigger()` +
  `mp_act_trigger_room()` in `mud/mobprog.py`; `do_emote` wired.
  Three regression tests lock the contract.
- **2.9.41 consolidation** — three dual pairs merged in
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` to bring the
  invariant budget from 25/~20 back to 22/~20 without losing any
  contracts:
  - INV-014 + INV-021 → INV-014 OBJECT-REGISTRY-LIFECYCLE
    (creation + extract on `object_registry`).
  - INV-015 + INV-018 → INV-015 AFFECT-EXPIRY-LIFECYCLE
    (stat-mod un-apply + wear-off message on `tick_spell_effects`).
  - INV-010 + INV-023 → INV-010 ROOM-PEOPLE-COHERENCE
    (bidirectional coherence + area.nplayer on
    `char_from_room`/`char_to_room`).

  INV-001 + INV-002 were *not* merged — the 2.9.39 footer
  mis-described them as duals; INV-001 is SINGLE-DELIVERY
  (broadcast routing) and INV-002 is PROMPT-CLAMP (display
  formatting), no shared enforcement point.

  Retired IDs (INV-018, INV-021, INV-023) kept as forward-pointer
  stubs in a new "Retired IDs (consolidated)" tracker section.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV_CONSOLIDATION.md](SESSION_SUMMARY_2026-05-26_INV_CONSOLIDATION.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.41 |
| Tests | 22/22 ✅ on six affected enforcement tests; full suite carries forward from 2.9.40 (2215 integration + 2534 unit) |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **22 of ~20 enforced** — over by two, within margin per AGENTS.md soft cap |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.41 commit pending push approval |

## Next Intended Task

1. **Continue probe-then-scope** at the 22/~20 budget. The
   methodology is still earning its keep — INV-023, INV-024,
   INV-025 each surfaced real production bugs. No pressure to
   consolidate further unless the count climbs back above 25
   without a real bug to anchor the new row.
2. **INV-025 follow-up sweep** (independent track): wire
   `mp_act_trigger_room` into remaining ROM act() callsites —
   `do_give` (uses `disable_mobtrigger()` per ROM
   `src/act_obj.c:832-836`), `do_drop`, `do_get`, `do_put`,
   `do_sacrifice`, equipment commands, position-transition
   broadcasts in `mud/combat/engine.py`. One callsite per commit.
   Contract is already locked at the emote site; the sweep widens
   coverage but cannot regress.
3. **Future consolidation candidates** (don't merge yet):
   - INV-016 / INV-019 (position transition broadcast / silent
     promotion-on-heal duals on `update_pos`).
   - INV-006 / INV-009 (fighting-pointer coherence after death /
     registry-disconnect cleanup on `character_registry` membership
     transitions).

GitNexus index covers through `3dbc421`. Refresh with
`npx gitnexus analyze --skip-agents-md` if commits land before
the next session.
