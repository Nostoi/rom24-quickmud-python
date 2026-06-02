# Session Status — 2026-06-01 — INV-025 combat re-probe: FIGHT-041/042 + NUKEPET-001 (2.12.51)

## Current State

- **Active mode**: cross-file invariants — the **INV-025 `mud/combat/`
  re-probe has begun**. Three gaps closed (all in `mud/combat/death.py`):
  - **FIGHT-041** (`50242279`, 2.12.49) — `death_cry`'s in-room gore line
    baked `victim.name` via `expand_placeholders` + `room.broadcast`
    (leaking an invisible victim's name); converted to
    `act_to_room(room, message_template, victim, exclude=victim)`. Test
    `test_fight041_death_cry_pers_masking.py` (2: invisible→"Someone",
    sighted→name).
  - **FIGHT-042** (2.12.50) — the neighbor-room cry
    (`_broadcast_neighbor_cry`, ROM `fight.c:1685` `act(TO_ROOM)` per exit,
    no MOBtrigger wrap) delivered visible text but never dispatched
    TRIG_ACT to listening NPCs in adjacent rooms (INV-025's primary
    contract). Surfaced by advisor review of FIGHT-041's over-claimed
    "plain broadcast" note. Converted to `act_to_room(target, message,
    victim)`; cry has no `$n` so PERS unchanged. Test
    `test_fight042_death_cry_neighbor_trig_act.py`.
  - **NUKEPET-001** (2.12.51, filed in `ACT_COMM_C_AUDIT.md`) — `_nuke_pets`
    (the shared pet-dismissal chokepoint: combat death, PC-extract, quit,
    mob_cmds, imm slay), ROM `nuke_pets` `act_comm.c:1648`
    `act("$N slowly fades away.", ch, NULL, pet, TO_NOTVICT)`. Baked `$N`=pet
    name + `broadcast(exclude=pet)` → (1) leaked an invisible pet's name,
    (2) wrongly showed the **owner** the line (TO_NOTVICT excludes both
    owner+pet), (3) no TRIG_ACT. Converted to
    `act_to_room(pet_room, "$N slowly fades away.", victim, arg2=pet,
    exclude=pet)`; removed the now-unused `expand_placeholders` import. Test
    `test_nukepet001_pet_fade_pers_and_notvict.py` (3). Surfaced by advisor
    review of the unclassified `expand_placeholders` grep hit in `death.py`.
- The **INV-025 command-layer PERS sweep is CLOSED** (all confirmed
  `mud/commands/` baked-name `room.broadcast(f"{char.name} …")` sites
  converted to `act_to_room`).
- **Today's progression (all pushed green):**
  - 2.12.40 → 2.12.42: CAST-009 + TRAIN-005 (full suite 5242).
  - 2.12.42 → 2.12.44: MAGIC-012 (frenzy) + MAGIC-013 (cure_disease) —
    manual-room-loop `$n`/`$s` PERS + channel (full suite 5246).
  - 2.12.44 → 2.12.45: **MAGIC-014** (`ed9b35e0`) — batch closure of the ~11
    `$n`-only single-actor spell room lines → `act_to_room` (full suite 5249).
  - 2.12.45 → 2.12.46: **FIGHT-039** (`83e42d33`) — trip self-trip lines colour
    + `$n` PERS + `$s` possessive (full suite 5251).
  - 2.12.46 → 2.12.47: **FIGHT-040** (`4015cccb`) — dirt-kick already-blinded
    uses ROM gendered `$E` in ROM order; deleted Python-invented guards
    (full suite 5256).
  - 2.12.47 → 2.12.48: **INV-025 command-layer sweep** (`ad4ae4aa`) — 10
    baked-name `room.broadcast` sites in `advancement.py` (practice ×2, train
    ×3), `session.py` (recall pray/disappear/appear), `notes.py` (note
    start/finish, restored `{G..{x` colour + `$s` possessive, removed
    `_possessive` helper) → `act_to_room(room, "$n …", char, exclude=char)`,
    each verified vs its exact ROM `act()` string. New
    `test_inv025_command_layer_pers.py` (invisible→"Someone", visible→name);
    re-baselined `test_do_practice_command::test_practice_room_messages` from a
    mocked `room.broadcast` to a sighted-witness assertion. **Full suite 5259
    passed, 4 skipped.**

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-01_INV025_COMMAND_LAYER_PERS.md](SESSION_SUMMARY_2026-06-01_INV025_COMMAND_LAYER_PERS.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.51 |
| Tests | **full suite green: 5265 passed, 4 skipped** (run `pytest -p no:xdist -o addopts="" -q`; under high load `-n auto` hangs at worker fork and `-n0` can hit a broken xdist `sessionfinish` teardown) |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | 25 enforced |
| Open correctness gaps | **INV-025 re-probe** — rest of `mud/combat/`, `mud/world/`, `mud/commands/communication.py` (`do_say`/`do_tell`) not yet swept for the same baked-name `room.broadcast` / missing-TRIG_ACT pattern (`death_cry` done: FIGHT-041 PERS + FIGHT-042 TRIG_ACT) |

## Next Intended Task

1. **Finish the INV-025 baked-name re-probe** — `mud/combat/`, `mud/world/`,
   and `mud/commands/communication.py` (`do_say`/`do_tell`) for the same
   `room.broadcast(f"…{name}…")` pattern that bypasses `act_to_room` PERS
   masking. Confirm each against its ROM `act()` string, then close as a batch.
2. Other cross-file-invariants candidate areas (position transitions, mob script
   triggers) remain once the PERS sweep is exhausted.

> **Push note:** work through 2.12.48 is pushed to `master`; **2.12.49
> (FIGHT-041, `50242279`), 2.12.50 (FIGHT-042, `56201629`), and 2.12.51
> (NUKEPET-001) are committed locally but NOT yet pushed.**
> **Index:** GitNexus reindexed clean after each commit (2026-06-01); re-run
> after the NUKEPET-001 commit.
