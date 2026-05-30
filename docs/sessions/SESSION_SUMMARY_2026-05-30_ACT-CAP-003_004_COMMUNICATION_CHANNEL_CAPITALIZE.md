# Session Summary — 2026-05-30 — ACT-CAP-003/004 Communication + Channel Capitalization

## Scope

Continuation of the INV-029 ACT-FIRST-LETTER-CAP cross-file invariant. Previous sessions
closed the `act_format` return (2.11.38), the `imm_commands` PERS-f-strings
(2.11.35–37), the combat render boundaries (FIGHT-031, 2.11.39), `broadcast_room`
(ACT-CAP-001, 2.11.40), `Room.broadcast`/`_message_room`/TO_ALL caster legs
(ACT-CAP-002, 2.11.41). This session closes the remaining two cousin surfaces:

1. **ACT-CAP-003** — `do_say`/`do_tell`/`do_shout`/`do_yell`/`do_emote` build
   per-listener f-strings that bypassed `capitalize_act_line`.
2. **ACT-CAP-004** — `broadcast_global` channel callers (auction, gossip, grats,
   quote, question, answer, music, clan, immtalk) build f-strings that bypassed
   `capitalize_act_line`. Weather messages correctly remain uncapped (ROM delivers
   weather via `send_to_char`, not `act_new`).

Two version bumps: 2.11.42 (ACT-CAP-003) and 2.11.43 (ACT-CAP-004).

## Outcomes

### `ACT-CAP-003` (communication command capitalization) — ✅ FIXED (2.11.42)

- **Python**: `mud/commands/communication.py` (6 output sites across 5 functions)
- **ROM C**: `src/comm.c:2376-2379` (`act_new` first-letter cap)
- **Fix**: Applied `capitalize_act_line` to all six output sites:
  - `do_say` per-listener message + TO_CHAR return
  - `_handle_buffered_tell` TO_VICT (covers all three paths: live/AFK/linkdead)
  - `do_tell` TO_CHAR return
  - `do_shout` per-listener message + TO_CHAR return
  - `do_yell` per-listener message + TO_CHAR return
  - `do_emote` per-listener message + TO_CHAR return
- **Tests**: `tests/integration/test_act_cap_003_communication_capitalize.py` (6 —
  say visible + invisible, tell visible + invisible, reply, shout)
- **Re-baselined**: 4 stale lowercase assertions (`test_tell_parity`,
  `test_say_parity`, `test_shout_yell_parity`, `test_emote_parity` —
  "someone" → "Someone"). TELL-006 (buffered tell cap) closed.

### `ACT-CAP-004` (broadcast_global channel capitalization) — ✅ FIXED (2.11.43)

- **Python**: `mud/commands/communication.py` (9 channel callers)
- **ROM C**: `src/comm.c:2376-2379` (`act_new` first-letter cap) for all channel
  commands; `src/update.c:658-660` (weather uses `send_to_char`, no cap)
- **Fix**: Applied `capitalize_act_line` to each channel command's
  `broadcast_global` message and TO_CHAR return: `do_auction`, `do_gossip`,
  `do_grats`, `do_quote`, `do_question`, `do_answer`, `do_music`, `do_clantalk`,
  `do_immtalk`. The `broadcast_global` function itself is NOT capped because ROM
  weather (`src/update.c:weather_update`) delivers via `send_to_char` (no cap)
  and both channels and weather share that delivery primitive.
- **Tests**: `tests/integration/test_act_cap_004_broadcast_global_capitalize.py` (6 —
  auction, gossip, grats, clan, weather-no-cap, immtalk)
- **INV-029 status**: With ACT-CAP-001/002/003/004, the `act_new` first-letter-cap
  invariant is now fully enforced across all delivery surfaces. Only `broadcast_global`
  weather remains uncapped (correct — ROM sends weather via `send_to_char`).

## Files Modified

- `mud/commands/communication.py` — `capitalize_act_line` applied to 6 comm sites
  (ACT-CAP-003) + 9 channel `broadcast_global` callers (ACT-CAP-004); unused
  `mp_speech_trigger` import removed by ruff
- `tests/integration/test_act_cap_003_communication_capitalize.py` — new (6)
- `tests/integration/test_act_cap_004_broadcast_global_capitalize.py` — new (6)
- `tests/integration/test_tell_parity.py` — re-baselined TELL-003 assertion
  ("someone" → "Someone"); TELL-006 note updated to ✅ FIXED
- `tests/integration/test_say_parity.py` — re-baselined SAY-002 ("someone" → "Someone")
- `tests/integration/test_shout_yell_parity.py` — re-baselined SHOUT-003, YELL-001
  ("someone" → "Someone")
- `tests/integration/test_emote_parity.py` — re-baselined EMOTE-001
  ("someone" → "Someone")
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 cousins updated:
  ACT-CAP-003 and ACT-CAP-004 closed; `broadcast_global` weather noted as
  correctly uncapped
- `docs/parity/FIGHT_C_AUDIT.md` — ACT-CAP-001 follow-up updated (broadcast_global
  channels now closed); ACT-CAP-003 and ACT-CAP-004 follow-up entries added
- `CHANGELOG.md` — 2.11.42 (ACT-CAP-003) and 2.11.43 (ACT-CAP-004) entries
- `pyproject.toml` — 2.11.41 → 2.11.42 → 2.11.43

## Test Status

- `pytest tests/integration/test_act_cap_003_communication_capitalize.py` — 6/6 passing
- `pytest tests/integration/test_act_cap_004_broadcast_global_capitalize.py` — 6/6 passing
- `pytest tests/integration/test_tell_parity.py tests/integration/test_say_parity.py tests/integration/test_shout_yell_parity.py tests/integration/test_emote_parity.py` — all passing
- Full suite: 5030 passed, 4 skipped, 0 failed (parallel, ~170s wall-clock)

## Next Steps

With ACT-CAP-001/002/003/004, the INV-029 `act_new` first-letter-cap invariant is
fully enforced across all delivery surfaces. Concrete remaining work from the tracker
(no longer capitalization-related):

1. **`FIGHT-032`** — defense TO_CHAR/TO_VICT lines bypass PERS (raw `name`);
   route through `pers()` per recipient.
2. **`FIGHT-033`** — WEAPON_FROST/SHOCKING victim lines drop `$p` weapon name.
3. **`FIGHT-034`** — auto-split per-member line not capitalized + bypasses PERS.
4. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`).

Carried-open: known xdist flakes (`test_combat_death.py`,
`test_backstab_uses_position_and_weapon`); pet-shop haggle / "now follows you"
wrong-channel (INV-001 family); `Character.pet` stale type annotation; `do_cast`
object-targeting legs.