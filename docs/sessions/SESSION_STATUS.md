# Session Status — 2026-05-26 — INV-025 enforced (2.9.40); budget at 25/~20

## Current State

- **INV-025 (MOBPROG-ACT-TRIGGER-DISPATCH)** enforced 2.9.40. Ports
  ROM's `bool MOBtrigger` global (`src/comm.c:311`) and the per-
  recipient `mp_act_trigger` dispatch inside `act()` (`src/comm.c:2384-2385`).
  New `MOBtrigger` flag + `disable_mobtrigger()` context manager +
  `mp_act_trigger_room()` per-room dispatcher in `mud/mobprog.py`;
  `do_emote` is the first wired callsite (the canonical ROM TRIG_ACT
  producer at `src/act_comm.c:1091`). Three regression tests lock the
  contract: PC emote fires dispatch, `disable_mobtrigger()` suppresses,
  NPC emoter does not self-fire.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-26_INV025_ENFORCED.md](SESSION_SUMMARY_2026-05-26_INV025_ENFORCED.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.40 |
| Tests | 93/93 ✅ on related suites (mobprog + emote + npc-speaker + comm + interp + inv025); full suite pending CI |
| ROM C files audited | per-file P0/P1/P2 at 100%, P3 at 75% (unchanged) |
| Cross-file invariants | **25 of ~20 enforced** — over-budget by five. INV-001 … INV-025 ✅ ENFORCED. Trips AGENTS.md consolidation threshold. |
| Meta-audit progress | DUPLICATE_IMPLEMENTATIONS ✅ CLOSED; 7 meta classes remain |
| Branch | `master` — local 2.9.40 commit pending push approval |

## Next Intended Task

**Consolidate INV budget back toward ~20** before adding more rows. Four
documented dual pairs in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
footer; each merge frees one slot without losing a distinct contract:

1. **INV-014 + INV-021** → OBJECT-REGISTRY-LIFECYCLE (creation +
   recursive extract on `object_registry`; both pin the same list).
2. **INV-015 + INV-018** → AFFECT-EXPIRY-LIFECYCLE (affect-tick
   lifecycle + raw-affect wear-off message; both pin the same expiry
   loop in `tick_spell_effects`).
3. **INV-023 + INV-010** → ROOM-PEOPLE-COHERENCE (area.nplayer +
   room.people both flow from `Room.add_character` / `remove_character`).
4. **INV-001 + INV-002** → MESSAGE-DELIVERY-COHERENCE (single-delivery
   + message routing on the broadcast surface).

Alternative: continue probe-then-scope at the higher budget if each
new INV keeps surfacing real bugs (INV-023, INV-024, INV-025 all
did — pre-existing systemic silences, not synthetic contracts).

**INV-025 follow-up sweep** (independent of consolidation): wire
`mp_act_trigger_room` into remaining ROM act() callsites — `do_give`
(uses `disable_mobtrigger()` per ROM `src/act_obj.c:832-836`), `do_drop`,
`do_get`, `do_put`, `do_sacrifice`, equipment commands, position-
transition broadcasts in `mud/combat/engine.py`. One callsite per
commit. The contract is already locked at the emote site; the sweep
extends coverage but cannot regress what INV-025 enforces.

GitNexus index refreshed at start of 2.9.40 session (covers through
`19951769`). Re-run `npx gitnexus analyze --skip-agents-md` before
the next session if intervening commits land.
