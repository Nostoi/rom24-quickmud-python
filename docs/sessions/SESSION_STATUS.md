# Session Status — 2026-05-28 — FIGHT-018 combat dam_message TRIG_ACT dispatch (2.9.90)

## Current State

- **Active mode**: cross-file / remaining-documented-gap pass (the per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows — all 40 audit-bound ROM C
  files ✅, 3 N/A). This session scoped the whole backlog for Ralph-loop
  suitability (verdict: no actionable queue — loop is the wrong tool), and closed
  the one genuinely-uncovered gap it surfaced: the INV-025 act()-dispatch
  follow-up as it applies to combat.
- **Last completed**:
  - **`FIGHT-018`** ✅ FIXED (2.9.90) — combat `dam_message` now fires TRIG_ACT on
    room NPCs. ROM `dam_message` broadcasts the hit line TO_ROOM/TO_NOTVICT via
    `act()` with no `MOBtrigger = FALSE` wrap, so per `src/comm.c:2384` every NPC
    in the room (other than attacker/victim) fires `mp_act_trigger`. Python's
    `_broadcast_damage_messages` rendered the per-recipient text but never
    dispatched TRIG_ACT. Now calls
    `mp_act_trigger_room(<rendered room line>, room, attacker, exclude=victim)`.
    ROM `src/fight.c:2215-2226`. Test:
    `tests/integration/test_fight_018_dam_message_act_trigger_dispatch.py`
    (2 cases). Commit `f2bd9723`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_018_DAM_MESSAGE_ACT_TRIGGER.md](SESSION_SUMMARY_2026-05-28_FIGHT_018_DAM_MESSAGE_ACT_TRIGGER.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_FIGHT_017_ENVENOM_WEAKENING.md](SESSION_SUMMARY_2026-05-28_FIGHT_017_ENVENOM_WEAKENING.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.9.90 |
| Tests | **4902 passed, 4 skipped** — parallel by default (`-n auto --dist loadscope`), ~90s. One intermittent xdist isolation flake (`test_group_combat` / `room_registry` leak) — passes alone + on re-run; see latest summary "Outstanding". |
| ROM C files audited | 40 / 43 ✅ (3 N/A: recycle/mem/imc). Per-file audit queue drained. `fight.c` ~95% in the top tracker (historical broader-sweep debt; no named implementation gap open — FIGHT-001..018 all closed). |
| Cross-file invariants | 24 ENFORCED. INV-025 act()-dispatch follow-up partly extended (combat `dam_message` now covered; non-combat `_push_message`/`broadcast_room` still open). |
| Branch | `master` — **2 commits ahead** of `origin/master` (`dbcd5735` FIGHT-017 / 2.9.89 + `f2bd9723` FIGHT-018 / 2.9.90). Not pushed. |

## Next Intended Task

1. **Pin the `room_registry` isolation leaker** (latest summary "Outstanding") —
   intermittent `AttributeError` at `reset_handler.py:178` in `test_group_combat`
   when a sibling test leaves `room_registry` polluted. Run the full suite a few
   times to identify the leaking file, then snapshot/clear/restore
   `room_registry` in its autouse fixture. Highest-value test-infra cleanup.
2. **INV-025 non-combat narration sweep** (optional, ad-hoc) — the
   `_push_message` / `broadcast_room` surface for non-combat ROM `act()` lines
   that should also feed `mp_act_trigger_room`. One callsite per commit, each
   gated on whether the ROM site carries a `MOBtrigger = FALSE` wrap. Surface a
   concrete gap, then close it directly — not a Ralph-loop queue.
3. **Push approval** — 2 commits ahead of `origin/master` shipping 2.9.89 +
   2.9.90. Awaiting approval.
4. **GitNexus** — MCP query path read-only this session; on-disk graph stale
   (`last indexed: 6b7f80d`). Re-run `npx gitnexus analyze --skip-agents-md`
   once the DB lock clears.
