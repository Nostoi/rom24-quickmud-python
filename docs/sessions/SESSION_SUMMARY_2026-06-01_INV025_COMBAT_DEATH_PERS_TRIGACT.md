# Session Summary — 2026-06-01 — INV-025 combat re-probe: death.py PERS + TRIG_ACT

## Scope

Continuation of the day's INV-025 work, picking up the next SESSION_STATUS task:
the baked-name `room.broadcast` re-probe of `mud/combat/`. The session began from
a work-in-progress for FIGHT-041 (a pre-written failing test + an unused
`act_to_room` import in `death.py`) and closed three related gaps, all in
`mud/combat/death.py`. Two of the three were surfaced by advisor review — FIGHT-042
from an over-claimed "plain broadcast" note left on FIGHT-041, and NUKEPET-001 from
an unclassified `expand_placeholders` grep hit in the file being edited. The
session ended with `death.py` **provably swept** for the INV-025 baked-name /
missing-TRIG_ACT pattern.

## Outcomes

### `FIGHT-041` — ✅ FIXED (commit `50242279`, 2.12.49)

- **Python**: `mud/combat/death.py:death_cry` (`~330`)
- **ROM C**: `src/fight.c:1640` — `act(msg, ch, NULL, NULL, TO_ROOM)`
- **Gap**: the selected death/gore line (`"$n hits the ground ... DEAD."` or a
  gore variant carrying `$n`/`$s`) was baked once via
  `expand_placeholders(message_template, victim)` + `room.broadcast`, leaking an
  invisible victim's name to every listener (no per-recipient PERS masking; an NPC
  rendered `name` instead of `short_descr`).
- **Fix**: `act_to_room(room, message_template, victim, exclude=victim)` — `$n`
  masks an invisible victim to "Someone" per recipient (INV-027), `$s` renders the
  gendered possessive, a visible NPC renders short_descr, and the actor (victim)
  is auto-excluded matching ROM's TO_ROOM.
- **Tests**: `tests/integration/test_fight041_death_cry_pers_masking.py` (2:
  invisible victim → "Someone", sighted witness → name; `number_bits→0` pins the
  clean `$n`-only template). Green.

### `FIGHT-042` — ✅ FIXED (commit `56201629`, 2.12.50)

- **Python**: `mud/combat/death.py:_broadcast_neighbor_cry` (`~234`)
- **ROM C**: `src/fight.c:1677-1688` — per-exit `act(msg, ch, NULL, NULL, TO_ROOM)`
  (`:1685`), no `MOBtrigger = FALSE` wrap anywhere in `death_cry`.
- **Gap**: the adjacent-room death cry delivered visible text via
  `target.broadcast(message)` — no actor threaded through, so an NPC in a neighbor
  room with a matching `TRIG_ACT` mprog never fired (INV-025's primary contract).
  Sibling of FIGHT-041; surfaced by advisor review, which flagged that FIGHT-041's
  "correctly a plain broadcast" note was true for PERS but false for TRIG_ACT.
- **Fix**: `act_to_room(target, message, victim)` — adds per-NPC TRIG_ACT dispatch;
  the cry has no `$n`/name so PERS rendering is unchanged. Softened the
  FIGHT-041 audit/CHANGELOG/INV-025 wording to reference FIGHT-042.
- **Tests**: `tests/integration/test_fight042_death_cry_neighbor_trig_act.py` (NPC
  listener in adjacent room → `mp_act_trigger` fires with "death cry"). Green.

### `NUKEPET-001` — ✅ FIXED (commit `c516a827`, 2.12.51; filed in `ACT_COMM_C_AUDIT.md`)

- **Python**: `mud/combat/death.py:_nuke_pets` (`~528`) — the shared pet-dismissal
  chokepoint for combat death, PC-extract (`game_loop`), quit/disconnect
  (`connection`), `mob_cmds`, and imm slay (`imm_load`).
- **ROM C**: `src/act_comm.c:1648` (`nuke_pets`, 1641-1655) —
  `act("$N slowly fades away.", ch, NULL, pet, TO_NOTVICT)`
- **Gap**: three divergences — (1) baked `$N`=pet name via `expand_placeholders`,
  leaking an invisible pet's name; (2) `broadcast(..., exclude=pet)` excluded only
  the pet, but ROM `TO_NOTVICT` excludes **both** `ch` (owner) and pet, so the
  owner wrongly saw the fade line; (3) no actor threaded → no TRIG_ACT dispatch.
  Surfaced by advisor review of the unclassified `expand_placeholders` grep hit.
- **Fix**: `act_to_room(pet_room, "$N slowly fades away.", victim, arg2=pet,
  exclude=pet)` — `$N` renders `PERS(pet)` per recipient (invisible pet →
  "Someone"), the actor (owner) is auto-excluded + `exclude=pet` supplies the
  second TO_NOTVICT exclusion, and per-NPC TRIG_ACT dispatches. Removed the
  now-unused `expand_placeholders` import (FIGHT-041 took the file's only other use).
- **Tests**: `tests/integration/test_nukepet001_pet_fade_pers_and_notvict.py` (3:
  invisible pet → "Someone", owner excluded, TRIG_ACT fires). Green.

## Files Modified

- `mud/combat/death.py` — 3 delivery sites converted to `act_to_room` (death_cry
  in-room + neighbor cry + nuke_pets pet-fade); removed `expand_placeholders` import.
- `tests/integration/test_fight041_death_cry_pers_masking.py` — new (2).
- `tests/integration/test_fight042_death_cry_neighbor_trig_act.py` — new (1).
- `tests/integration/test_nukepet001_pet_fade_pers_and_notvict.py` — new (3).
- `docs/parity/FIGHT_C_AUDIT.md` — added FIGHT-041 + FIGHT-042 rows (✅ FIXED).
- `docs/parity/ACT_COMM_C_AUDIT.md` — added NUKEPET-001 row (✅ FIXED).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 trail: combat re-probe progress.
- `CHANGELOG.md` — 3 `Fixed` entries.
- `pyproject.toml` — 2.12.48 → 2.12.51.
- `docs/sessions/SESSION_STATUS.md` — refreshed to point here.

## Test Status

- New tests: 6/6 passing across the three files.
- Area suites green throughout (combat/death 249→273; pet/follow/quit 108).
- **Full suite: 5265 passed, 4 skipped** (= 5259 + 6 new cases), serial run
  (`pytest -p no:xdist -o addopts="" -q`, ~10m). `ruff check` clean.
- `gitnexus_detect_changes` low-risk / 0 affected processes on each commit; index
  reindexed clean after each.

## Next Steps

`mud/combat/death.py` is provably swept (grep
`broadcast|broadcast_room|messages.append|send_to_char|push_message` returns only
the `_broadcast_neighbor_cry` def/comment/call, whose body is `act_to_room`). The
INV-025 baked-name / missing-TRIG_ACT re-probe continues into the **rest of
`mud/combat/`** (`engine.py` et al.), **`mud/world/`**, and
**`mud/commands/communication.py`** (`do_say`/`do_tell`). Once the PERS/TRIG_ACT
sweep is exhausted, the remaining cross-file-invariants candidates (position
transitions, mob script triggers, group/follower chains) are next.
