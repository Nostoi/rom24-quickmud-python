# Session Summary — 2026-06-01 — INV-025 spell-effect/healer/spec_fun ACT trigger dispatch

## Scope

Continued the INV-025 cross-file-invariant sweep. The session pointer (SESSION_STATUS)
listed four remaining high-value surfaces: spell-effect room broadcasts in handlers.py,
healer utterance, spec_fun broadcasts, and remaining movement-adjacent calls.

## Outcomes

### Spell-effect `broadcast_room` → `_act_room` sweep — ✅ CLOSED

- **Python**: `mud/skills/handlers.py` — added module-level `_act_room(room, message, actor, *, arg1=None, arg2=None, exclude=None)` helper combining `broadcast_room` + `mp_act_trigger_room`, matching ROM `act(TO_ROOM)` which dispatches `mp_act_trigger` at `src/comm.c:2384`.
- Converted ~50 `broadcast_room` call sites to `_act_room`, covering: bless object branches, cancellation wear-off messages (`_broadcast_room_msg`), chain_lightning, change_sex, disarm, dirt, envenom, faerie_fire, faerie_fog, flamestrike, dispel_evil/good, floating_disc, gate, holy_word, energy_drain, invis, mass_invis, create_portal, pick, plague, poison, portal, protection, recall, recharge, remove_curse, sanctuary, shield, slow, haste, stone_skin, weaken, frenzy, giant_strength, fly, heat_metal, teleport, word_of_recall, and all other spell-effect room broadcasts.
- Every `act(TO_ROOM)` in `src/magic.c` / `src/magic2.c` without a `MOBtrigger = FALSE` wrap now dispatches TRIG_ACT in Python.

### Cancellation `_broadcast_room_msg` — ✅ CLOSED

- **Python**: `mud/skills/handlers.py:cancellation`'s `_broadcast_room_msg` helper now dispatches `mp_act_trigger_room` after `broadcast_room` for all 15 wear-off messages (`$n is no longer blinded.`, `$n no longer looks so peaceful...`, etc.), matching ROM `src/magic.c:1062-1196`.

### Healer utterance — ✅ CLOSED

- **Python**: `mud/commands/healer.py:234` — added `mp_act_trigger_room` dispatch for the `broadcast_room` utterance line, matching ROM `src/healer.c:183` `act("$n utters the words '$T'.", ...)`.

### Spec_fun broadcasts — ✅ CLOSED

- **Python**: `mud/spec_funs.py` — modified both `_broadcast_room` and `_broadcast_room_message` helpers to dispatch `mp_act_trigger_room` for NPC recipients after the per-recipient message loop, matching ROM `src/comm.c:2384` which fires `mp_act_trigger` inside `act()` for every spec_fun utterance/taunt broadcast.

## Files Modified

- `mud/skills/handlers.py` — added `_act_room` helper; added `mp_act_trigger_room` import; converted ~50 `broadcast_room` calls to `_act_room`; modified `_broadcast_room_msg` inside `cancellation` to dispatch TRIG_ACT.
- `mud/spec_funs.py` — added `mp_act_trigger_room` import; modified `_broadcast_room` and `_broadcast_room_message` to dispatch TRIG_ACT.
- `mud/commands/healer.py` — added `mp_act_trigger_room` import; added TRIG_ACT dispatch after the healer utterance `broadcast_room`.
- `tests/integration/test_inv025_spell_effect_act_trigger.py` — new enforcement tests (6: cancellation wear-off, spec_fun broadcast_room, spec_fun broadcast_room_message, _act_room dispatch, _act_room excludes actor, MOBtrigger suppression).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 sweep entry updated (spell-effect/healer/spec_fun surfaces).
- `docs/sessions/SESSION_STATUS.md` — updated to 2.12.23.
- `CHANGELOG.md` — added INV-025 spell-effect/healer/spec_fun entry under Fixed.
- `pyproject.toml` — 2.12.22 → 2.12.23.

## Test Status

- `pytest -n0 tests/integration/test_inv025_spell_effect_act_trigger.py -v` — 6/6 passed.
- `pytest tests/integration/ -k "inv025" -v` — 72/72 passed.
- `pytest tests/test_spec_funs.py tests/test_healer.py tests/test_spell_cancellation_rom_parity.py` — 42/42 passed.
- `ruff check` — clean on all modified files (only pre-existing B007/F841 warnings in handlers.py).

## Remaining INV-025 Surfaces

The INV-025 principle is now fully applied to all major `broadcast_room` call sites:
- Combat broadcasts ✅ (prior sessions)
- Equipment/get/put/drop/give broadcasts ✅ (prior sessions)
- Door/open/close/lock/unlock/pick broadcasts ✅ (prior sessions)
- Movement/quit/scan broadcasts ✅ (prior sessions)
- Consumption/liquid broadcasts ✅ (prior sessions)
- Thief/steal broadcasts ✅ (prior sessions)
- Imm command broadcasts ✅ (prior sessions)
- Communication act() broadcasts ✅ (prior sessions)
- **Spell-effect broadcasts ✅ (this session)**
- **Healer utterance ✅ (this session)**
- **Spec_fun broadcasts ✅ (this session)**

Lower-priority remaining surfaces:
1. Music broadcasts (`mud/music/__init__.py`)
2. Remaining command broadcasts (`do_where`, `do_who`, etc.)