# Session Summary — 2026-06-10 — FINDING-033: COMM_COMBINE fix, Hypothesis state-machine clean

## Scope

Single-bug continuation from v2.13.64. FINDING-033 was filed in the previous session
after Hypothesis generated the sequence `['south', '__char_update', '__oload=3135',
'look']` — two fountains in a room — and found that Python listed each object
individually while ROM C grouped them as `( 2) A small white fountain gushes forth
here.`. Investigation showed the game-engine `show_list_to_char` already had the
correct combine logic; only the diff-harness test-character setup was wrong.

## Outcomes

### FINDING-033: COMM_COMBINE flag missing on test character — ✅ RESOLVED

- **Root cause**: `drive_python_replay` never set `char.comm`, so `CommFlag.COMBINE`
  was absent. `show_list_to_char` tests `is_npc or bool(comm_flags & COMBINE)` and
  took the non-combining branch, listing each object on its own line.
  ROM C `diffmain.c:462` sets `ch->comm = COMM_COMBINE | COMM_PROMPT` for the test
  character. Python's `Character.from_orm` defaults to the same flags when `comm <= 0`,
  but `create_test_character` bypasses `from_orm`, leaving `comm` unset.
- **ROM C reference**: `src/act_info.c:130-243 show_list_to_char`; `diffmain.c:462`
- **Python fix**: `tools/diff_harness/pyreplay.py` — added
  `char.comm = int(CommFlag.COMBINE) | int(CommFlag.PROMPT)` in `drive_python_replay`
  after the existing `make_test_char` mirrors.
- **Note**: `show_list_to_char` in `mud/utils/act.py` was already correct — no
  game-engine code changed; harness setup only.
- **Verification**: After the fix, two `__oload=3135` spawns followed by `look`
  produce `( 2) A small white fountain gushes forth here.` in Python output,
  matching the C golden.
- **Hypothesis test**: `test_generated_no_rng_sequences_match_live_c` — `xfail`
  decorator removed; test is now fully passing (no longer replaying the stored
  counterexample as a failure).
- **Enforcement test**: `test_drive_python_replay_comm_combine_groups_identical_room_objects`
  added to `tests/test_diff_harness_unit.py` — pins that two identical room objects
  produce one `( 2) ...` grouped line in Python replay output.
- **FINDINGS.md**: FINDING-033 marked ✅ RESOLVED.

## Files Modified

- `tools/diff_harness/pyreplay.py` — `char.comm = CommFlag.COMBINE | CommFlag.PROMPT`
- `tests/test_diff_harness_unit.py` — new enforcement test
- `tests/test_diff_harness_generated.py` — `xfail` decorator removed from `test_generated_no_rng_sequences_match_live_c`
- `tools/diff_harness/FINDINGS.md` — FINDING-033 marked RESOLVED with root-cause correction
- `CHANGELOG.md` — added [2.13.65] Fixed entry
- `pyproject.toml` — 2.13.64 → 2.13.65

## Test Status

- Diff harness: **44 passed, 0 xfailed** (26 smoke + 17 unit; was 42 passed, 1 xfailed)
- Full suite: **5507 passed, 4 skipped** (no regressions)

## Next Steps

Cross-file invariants and diff-harness coverage remain the active pass. All known
open findings are now resolved (FINDING-033 ✅). Concrete candidates:

1. **`drink`/`eat`/`food` consumption scenario** — condition decay, THIRST/FULL/HUNGER
   bitvectors; no current diff-harness coverage. `pyreplay.py` already has
   `__cond_full=` / `__cond_thirst=` meta-commands; `diffmain.c` needs them for
   C golden capture.

2. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
