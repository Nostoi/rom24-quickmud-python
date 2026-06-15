# Session Status — 2026-06-15 — Tick aggression + spec-fun delivery (FIGHT-077 + SPEC-017)

## Current State

- **Active focus**: Cross-file / divergence-class sweep (per-file audit tracker
  exhausted). This session closed the two reported **tick-driven** symptoms
  (aggressive mobs not attacking; friendly mobs not casting) and confirmed via a
  broad tick-path sweep that no further live tick bugs remain.
- **Last completed**:
  - **FIGHT-077** (2.14.115, commit 5a93cec7) — removed a fabricated
    `is_safe` NPC level gate (`if victim_level < char_level - 10: return True`)
    with no ROM basis. ROM `src/fight.c:1075-1093` has only the safe-room and
    charmed-pet-owner checks; any mob >10 levels above a PC had silently refused
    to aggress. Aggression restored. Missed level-gate facet of INV-050.
  - **SPEC-017** (2.14.115, commit c47d550e) — `spec_funs.py:_append_message`,
    the single sink for all spec-fun room flavor, delivered mailbox-only (last
    helper missed by the INV-001 sweep). Now routed through the loop-aware
    chokepoint `push_message`, so idle connected players see spec-fun casting
    announcements on a tick (mirroring ROM `src/comm.c:act`). INV-001
    wrong-channel cousin.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-15_TICK_AGGRESSION_SPECFUN_DELIVERY_FIGHT077_SPEC017.md](SESSION_SUMMARY_2026-06-15_TICK_AGGRESSION_SPECFUN_DELIVERY_FIGHT077_SPEC017.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.115 |
| Tests | 5812 passed, 4 skipped (+2 new test files: FIGHT-077, SPEC-017) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants pass — FIGHT-077 + SPEC-017 closed |

## Next Intended Task

Both reported tick symptoms are fixed and verified. Open follow-ups, in priority
order:

1. **Vestigial dual-channel in `process_weapon_special_attacks`** —
   `mud/combat/engine.py` builds both `_push_message` and a `messages.append`
   return list; all `multi_hit` callers discard the return, so it is not a live
   bug, but it is a latent INV-001 footgun. Low-priority cleanup; not yet filed
   as a stable ID.
2. **Eddol data cleanup (needs user confirmation)** — the existing corrupt
   `Eddol` DB row is forward-only unaffected; deleting it is destructive.
3. **DELETE-002 🔄 OPEN** — `do_delete` lacks ROM's wiznet self-deletion
   broadcast (`src/act_comm.c`). Local divergence, low priority.
4. **STEAL-015 🔄 OPEN** — steal skill-handler `skills/handlers.py:steal` has no
   `is_safe` gate; converge onto `_kill_safety_message`.
5. **INV-050 bool-retirement** — gated on the `is_safe_spell`-vs-ROM audit
   (`safety.py:is_safe_spell` vs `src/fight.c:1126-1218`); message-half done,
   FIGHT-077 closed the missed level-gate facet.
6. **`mud/entrypoint.py`** dead code (`prompt_account_creation` / `prompt_login`,
   no callers) — candidate for removal in a hygiene pass.

Beyond these, per `docs/parity/DIVERGENCE_CLASS_ROSTER.md` the higher-yield open
lever remains the **Hypothesis state-machine → diff_harness widening** (Class 11
/ Phase C), enumeration-independent (guardrail 3).
