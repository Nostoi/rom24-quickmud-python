# Session Status — 2026-05-30 — ACT-CAP-002 Room.broadcast + _message_room + TO_ALL caster legs

## Current State

- **Active mode**: cross-file invariants (per-file audit tracker exhausted — no
  ⚠️ Partial / ❌ Not Audited rows). Today closed **ACT-CAP-002** (Room.broadcast
  + _message_room + TO_ALL caster legs), the parallel room-broadcast half of
  INV-029 left open by ACT-CAP-001.
- **Last completed** (this leg):
  - **`ACT-CAP-002` (Room.broadcast + _message_room + TO_ALL caster legs)** ✅ FIXED
    — `mud/models/room.py:Room.broadcast` caps at entry via `capitalize_act_line`
    (same pattern as `broadcast_room` in ACT-CAP-001); `mud/game_loop.py:_message_room`
    caps at entry (idempotent double-cap on the delegation path); the five
    object-spell TO_ALL handlers (`invis`, `poison`, `remove_curse`,
    `continual_light`, `create_food`) cap the shared `message` at each build site
    so both `_send_to_char(caster)` and `broadcast_room`/`room.broadcast` deliver
    capitalized lines. 8-assertion re-baseline across 5 test files.
    Test: `tests/integration/test_act_cap_002_room_broadcast.py` (8). Full suite
    5014 passed / 0 failed.
- **Earlier today**: ACT-CAP-001 (2.11.40), FIGHT-031 (2.11.39), INV-029 (2.11.38).
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-30_ACT-CAP-002_ROOM_BROADCAST_AND_TO_ALL_CASTER_LEGS.md](SESSION_SUMMARY_2026-05-30_ACT-CAP-002_ROOM_BROADCAST_AND_TO_ALL_CASTER_LEGS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.41 |
| Tests | 5014 passed, 4 skipped, 0 failed (full parallel suite; +8 ACT-CAP-002 tests) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Active focus | Cross-file invariants (INV-029 enforced at act_format + imm_commands + combat + broadcast_room + Room.broadcast + _message_room + TO_ALL caster legs; ⚠️ do_say-do_tell / broadcast_global OPEN) |

## Next Intended Task

The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows, so
**cross-file invariants remains the standing pass**. Concrete next options, in
rough priority:

1. **`do_say` / `do_tell`** (`mud/commands/communication.py`) — INV-029 cousin
   (`test_tell_parity.py:19` notes the cap as a known deferral).
2. **`broadcast_global`** — per-channel cap, NOT a blanket chokepoint (weather is
   `send_to_char`).
3. **`FIGHT-032`/`033`/`034`** — combat PERS / FROST-SHOCKING `$p` / auto-split
   (filed in the FIGHT-031 session).
4. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`). Larger scope; failing test first.

Carried-open: known **xdist flakes** (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.

## Commit / push state

- All changes on branch `feat/act-cap-002` (branched from `master` at `b20a73e0`).
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start,
  minus the pre-existing unstaged `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`.)