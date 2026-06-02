# Session Status — 2026-06-02 — INV-033 FURNITURE-ON-POINTER-COHERENCE CLOSED (2.12.66)

## Current State

- **Active mode**: cross-file invariants (sole active pass — no per-file audit
  gaps remain). This session probed the recommended **position-transition**
  candidate and closed one cross-file contract.
- **This session — one commit (local on `master`, NOT yet pushed):**
  - **2.12.66 — INV-033 FURNITURE-ON-POINTER-COHERENCE**: a Character's `ch->on`
    furniture pointer must clear whenever the furniture leaves their room. ROM
    clears it in two primitives — `char_from_room` (`src/handler.c:1532`, already
    mirrored in `Room.remove_character`) and `obj_from_room`
    (`src/handler.c:1915-1917`, fired via `extract_obj`). Python's canonical
    `mud/game_loop.py:_extract_obj` removed furniture from `room.contents` but
    never cleared occupants' `on`, so furniture that **decayed/was purged out
    from under a sitter** left a dangling pointer that kept feeding the regen
    heal/mana bonus (`hit_gain`/`mana_gain`, ROM `src/update.c:217-218,299-300`)
    and corrupted the no-arg `do_rest`/`do_sit`/`do_sleep` default. Added the
    `obj_from_room`-style occupant sweep — a no-op for non-furniture.
    `gitnexus_impact` rated `_extract_obj` HIGH (6 direct callers); full suite
    **5333 passed, 4 skipped** — zero fallout. The guarded cousins `do_get` /
    `do_sacrifice` already refuse to remove occupied furniture, so they never
    strand the pointer (true ✅ ENFORCED, not partial). New
    `tests/integration/test_inv033_furniture_on_pointer_coherence.py` (4 tests).

- **Open gaps**: **none** (per-file). All per-file audit rows ✅; cross-file
  invariants is the active probe-then-scope pass.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_INV033_FURNITURE_ON_POINTER.md](SESSION_SUMMARY_2026-06-02_INV033_FURNITURE_ON_POINTER.md)
  (prior: [README_HONESTY_HANDLER_004](SESSION_SUMMARY_2026-06-02_README_HONESTY_HANDLER_004.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.66 |
| Tests | **full suite green: 5333 passed, 4 skipped** (`pytest`, ~140s parallel); INV-033 (`_extract_obj`, HIGH blast radius) caused zero fallout |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | **26 enforced** (was 25; INV-033 added — now past the ~20 soft cap, consider consolidation) |
| Open gaps | **none** — INV-033 CLOSED this session (2.12.66) |

## Next Intended Task

Cross-file invariants is the sole active pass. Tracker is now at 26 INV rows —
past the ~20 soft cap AGENTS.md flags; a future session should weigh
consolidation (INV-014/INV-015 precedent) before adding more. Remaining
uncovered cross-file candidates:

1. **Group/follower chain** ordering — `add_follower`/`stop_follower`/
   `die_follower` membership + leader/master pointer coherence across
   death/extract/quit.
2. **Mob trigger** ordering — TRIG_* dispatch sequence vs ROM.

Method: probe-then-scope (read ROM C contract → read Python equivalent → one
failing test → close as a gap or file as next free INV-034).

> **Push note:** 2.12.66 (one commit) is committed locally on `master` but **NOT
> yet pushed** — awaiting user confirmation. The prior session's 2.12.65
> (`7689e971` + `fc450d41`) is likewise still unpushed. CHANGELOG/version reflect
> 2.12.66.
