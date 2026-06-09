# Session Summary — 2026-06-09 — MEdit exit/exall/grall mobprog runtime probe

## Scope

Continued Class 11 / dynamic differential widening from the MEdit `TRIG_ENTRY`,
`TRIG_GREET`, `TRIG_SPEECH`, `TRIG_ACT`, `TRIG_BRIBE`, `TRIG_GIVE`,
`TRIG_FIGHT`/`TRIG_HPCNT`, `TRIG_SURR`, and `TRIG_KILL`/`TRIG_DEATH` runtime
probes. This session added coverage for OLC-created `exit`, `exall`, and `grall`
mobprogs reaching the correct ROM dispatch branches via `move_character`, without
changing production behavior. These are the last three deterministic MEdit trigger
types; all non-RNG OLC-created trigger paths are now covered end-to-end.

## Outcomes

### MEdit-created `TRIG_EXIT` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:81`,
  `src/mob_prog.c:1262-1269`
- **Gap**: none found. The existing implementation correctly carries builder-set
  `TRIG_EXIT` bits and `MobProgram` rows into spawned mobs, and `mp_exit_trigger`
  fires `_program_flow` when the mob is at `default_pos` and can see the exiting
  PC.
- **Coverage**: added
  `test_addmprog_created_exit_trigger_fires_when_pc_leaves_room` — runs
  `_interpret_medit("addmprog ... exit 0")`, spawns the edited prototype at
  `Position.STANDING` in the start room, moves a PC north via `move_character`,
  and verifies `_program_flow` is called with the correct vnum, code, mob, and
  actor binding.

### MEdit-created `TRIG_EXALL` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:81`,
  `src/mob_prog.c:1271-1276`
- **Gap**: none found. EXALL has no position or visibility guard — the existing
  implementation fires unconditionally, matching ROM C.
- **Coverage**: added
  `test_addmprog_created_exall_trigger_fires_regardless_of_mob_position` — same
  structure as EXIT probe but mob is set to `Position.SLEEPING`, proving the
  EXALL vs EXIT discriminator: EXIT would skip a sleeping mob, EXALL does not.

### MEdit-created `TRIG_GRALL` runtime path — ✅ COVERED

- **Python**: `tests/integration/test_olc_009_medit_missing_cmds.py`
- **ROM C**: `src/olc_act.c:4900-4904`, `src/act_move.c:243`,
  `src/mob_prog.c:1325-1345`
- **Gap**: none found. GRALL is the fallback branch inside `mp_greet_trigger`:
  when the mob is not at `default_pos` (or can't see the PC) it fires GRALL
  via `mp_percent_trigger` instead of GREET. The existing implementation matches.
- **Coverage**: added
  `test_addmprog_created_grall_trigger_fires_when_mob_not_at_default_pos` — gives
  the mob both GREET and GRALL mprogs (to confirm correct branch selection), sets
  the mob to `Position.SLEEPING` in the destination room, moves a PC north, and
  verifies `mp_percent_trigger` is called with `Trigger.GRALL` (not `Trigger.GREET`).

## Files Modified

- `tests/integration/test_olc_009_medit_missing_cmds.py` — added three MEdit →
  spawn → `move_character` → exit/exall/grall-trigger probes (VNUMs 61040–61046,
  rooms 61048–61053).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — recorded the Class 11 coverage
  expansion; updated the "next step" note to reflect all deterministic MEdit
  trigger types now covered.
- `CHANGELOG.md` — added `2.13.52` entry for the three new probes.
- `pyproject.toml` — `2.13.51` → `2.13.52`.
- `docs/sessions/SESSION_STATUS.md` — refreshed the current pointer.

## Test Status

- `pytest -q -n0 tests/integration/test_olc_009_medit_missing_cmds.py` —
  43 passed (40 pre-existing + 3 new).
- `ruff check .` — clean (confirmed by pre-commit hook).
- Full suite not rerun this session; previous session baseline was 5474 passed,
  5 skipped.

## Next Steps

All deterministic MEdit trigger types are now covered by end-to-end integration
probes. The remaining Class 11 surfaces are:

- **RNG-locked paths** (`TRIG_RANDOM`, `TRIG_DELAY`) — avoid until seed
  alignment has a grounded probe of its own.
- **Diff-harness scenario** — author a `move_character`-based scenario in
  `tools/diff_harness/scenarios/` to give movement-triggered mobprogs C-oracle
  ground truth rather than Python-authored expectations.
- **Other divergence classes** — consult `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
  for the next highest-priority unverified class.
