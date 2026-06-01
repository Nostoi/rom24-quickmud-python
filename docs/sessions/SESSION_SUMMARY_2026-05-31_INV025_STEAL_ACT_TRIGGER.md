# Session Summary — 2026-05-31 — INV025 steal ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep from the session pointer,
focusing on `do_steal` failure-path room narrations and probing immortal
command room narrations for future targets.

## Outcomes

### INV-025 — ✅ FIXED

- **Python**: `mud/commands/thief_skills.py:209-214` — `_steal_failure` now dispatches `mp_act_trigger` for the victim NPC (TO_VICT) and `mp_act_trigger_room` for bystander NPCs (TO_NOTVICT, excluding actor and victim).
- **ROM C**: `src/act_obj.c:2223-2224` — `act("$n tried to steal from you.", …, TO_VICT)` and `act("$n tried to steal from $N.", …, TO_NOTVICT)` are unsuppressed; per `src/comm.c:2384` NPC recipients receive `mp_act_trigger`.
- **Fix**: Added `import mud.mobprog as mobprog` and two dispatch calls after the existing `_send_to_char_sync` delivery: `mp_act_trigger(victim_msg, victim, char, None, victim, Trigger.ACT)` for the NPC victim, and `mp_act_trigger_room(notvict_msg, room, char, arg2=victim, exclude=(char, victim))` for room bystanders. Uses module-level import (not top-level) to match the test-probing pattern used across the INV-025 sweep.
- **Tests**: 4/4 passing — `tests/integration/test_inv025_steal_act_trigger_dispatch.py`

### INV-025 immortal command probe — SURVEYED

Probed all `act()` calls in `src/act_wiz.c` (33 total). Key findings for future gaps:

- Zero `MOBtrigger = FALSE` wrappers — every `act()` call is unsuppressed.
- Neither `imm_commands.py` nor `remaining_rom.py` imports `mp_act_trigger`/`mp_act_trigger_room`.
- Priority targets (already implemented): `do_transfer` (3), `do_goto`/`do_violate` (8), `do_force` single-target (1).

## Files Modified

- `mud/commands/thief_skills.py` — INV-025: added `mp_act_trigger` / `mp_act_trigger_room` dispatch in `_steal_failure`; lint cleanup
- `tests/integration/test_inv025_steal_act_trigger_dispatch.py` — new (4 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry: steal failure
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.16
- `CHANGELOG.md` — INV-025 steal entry under Fixed
- `pyproject.toml` — 2.12.15 → 2.12.16

## Test Status

- `pytest tests/integration/test_inv025_steal_act_trigger_dispatch.py -n0 -v` — 4/4 passing
- `pytest tests/integration/test_inv025_liquids_act_trigger_dispatch.py -n0 -v` — 4/4 passing
- Full suite: 5150 passed, 4 skipped (3m15s)
- `ruff check mud/commands/thief_skills.py` — clean

## Next Steps

Continue the INV-025 sweep for remaining non-combat room narrations whose ROM
sites use unsuppressed `act()`:

1. `mud/commands/imm_commands.py:do_transfer` — TO_ROOM mushroom-cloud/puff-of-smoke + TO_VICT "transferred you" (3 act calls).
2. `mud/commands/imm_commands.py:do_goto` / `do_violate` — trust-gated bamf per-recipient via `_act_room_invis_gated` (8 act calls).
3. `mud/commands/imm_commands.py:do_force` single-target — TO_VICT "forces you to" (1 act call).