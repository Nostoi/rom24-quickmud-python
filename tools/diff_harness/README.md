# Differential Testing Harness (ROM C ⇄ Python)

A local tool that runs the Python port and the original ROM 2.4b6 C engine
through identical scripted scenarios and diffs observable state + output, so
parity divergences surface mechanically. Design:
`docs/superpowers/specs/2026-05-28-differential-testing-harness-design.md`.

## How it works

Two phases sharing one snapshot schema (`schema.py`):

- **Capture** (occasional, needs the C build): `capture.py` drives the
  instrumented C binary (`src/diffshim`) through a scenario over stdin and writes
  a golden trace to `tests/data/golden/diff/<name>.golden.json` (committed).
- **Replay** (every test run, pure Python): `tests/test_differential_smoke.py`
  drives the Python engine through the same scenario, snapshots its state
  (`pysnap.py`), normalizes both sides identically (`compare.py`), and asserts
  equality — reporting the first diverging step/field.

The Python snapshot logic and comparator are shared with a possible future live
dual-drive mode; only the capture source would swap.

## One-time: build the instrumented C binary

```bash
cd src && make -f Makefile.diffshim diffshim
```

The build is **additive** — ROM's `src/*.c` / `*.h` are byte-for-byte unchanged;
all macOS portability is via compile flags + new headers under `src/diff_shim/`.
Notes (macOS / Apple clang):

- Compiled with `-DOLD_RAND` so the C Mitchell-Moore RNG matches
  `mud/utils/rng_mm.py` bit-for-bit when seeded identically.
- `-Dunix` fires merc.h's unix block (clang doesn't predefine `unix`);
  `src/diff_shim/malloc.h` + `endian.h` shim missing Linux/BSD headers; no
  `-lcrypt` needed (crypt is in libSystem).
- `comm.c` IS linked (so output is real ROM `send_to_char`/`act`) with
  `-Dmain=rom_main_unused`; `diffmain.c` provides `main()`.
- The C binary must be run with cwd = `src/` (area paths are relative); it reads
  a generated `src/diff_shim/area/` overlay that repairs the malformed
  `midgaard.are` (see FINDINGS.md) — `area/` itself is never modified.

## Everyday run (no C build needed)

```bash
pytest tests/test_differential_smoke.py tests/test_diff_harness_unit.py
```

Replay runs pure-Python against the committed goldens. A missing golden skips;
a documented known-divergence xfails (see FINDINGS.md).

## Regenerate / verify goldens (needs the C binary)

```bash
python3 -m tools.diff_harness.capture --scenario movement_get_drop   # one
python3 -m tools.diff_harness.capture --all                          # all
python3 -m tools.diff_harness.capture --check                        # diff vs committed (CI-style)
```

Goldens are stamped with the C commit sha + build flags + seed.

## Authoring a scenario

`tools/diff_harness/scenarios/<name>.json`:

```json
{
  "name": "movement_get_drop",
  "seed": 1234,
  "start_room": 3001,
  "char": { "name": "Tester", "level": 5 },
  "watch": { "chars": ["Tester"], "rooms": [3001, 3054] },
  "steps": ["look", "north", "get pit", "drop pit", "south"]
}
```

A `__snapshot` over the watch-set is auto-inserted after every step. v1 is a
**deterministic smoke slice** (no-RNG commands: look, movement, get/drop,
inventory, wear/remove). Combat/casting/shops/prompt/RNG are later slices.

Steps can also be **meta-commands** — harness-internal directives that
manipulate engine state without producing output. They are handled identically
by `diffmain.c` (C side) and `pyreplay.py` (Python side):

| Meta-command | Effect |
|---|---|
| `__seed=N` | Reseed the Mitchell-Moore RNG mid-scenario |
| `__hour=N` | Set `time_info.hour` (daylight/night transitions) |
| `__level=N` | Set the PC's level |
| `__hp=N` | Set PC `hit` (and `max_hit` if lower) |
| `__mana=N` | Set PC `mana` (and `max_mana` if lower) |
| `__move=N` | Set PC `move` (and `max_move` if lower) |
| `__gold=N` | Set PC gold |
| `__silver=N` | Set PC silver |
| `__goto=VNUM` | Teleport PC to room (no movement output) |
| `__cond_hunger=N` | Set `COND_HUNGER` (0=starving, 48=full) |
| `__cond_thirst=N` | Set `COND_THIRST` |
| `__cond_full=N` | Set `COND_FULL` |
| `__cond_drunk=N` | Set `COND_DRUNK` |
| `__learn=NAME` | Teach the PC skill/spell `NAME` at 100% |
| `__learn_pct=NAME=N` | Teach the PC skill/spell `NAME` at a specific learned percent |
| `__mload=VNUM` | Spawn mob into the PC's room |
| `__oload=VNUM` | Spawn object into the PC's room |
| `__mob_gold=N` | Set first NPC in room's gold |
| `__mob_silver=N` | Set first NPC in room's silver |
| `__mob_hp=N` | Set first NPC in room's hit points |
| `__mob_hold=VNUM` | Spawn object and place it in first NPC's HOLD slot |
| `__mob_carry=VNUM` | Spawn object into first NPC's inventory |
| `__mob_position=N` | Set first NPC's position (ROM `Position` integer) |
| `__mob_delay=N` | Set first NPC's `mprog_delay` countdown |
| `__mob_prog=TYPE:PHRASE:CODE` | Prepend a mobprog to the first NPC |
| `__charm_mob=DUR` | Charm first NPC with given duration (bypasses spell path) |
| `__set_affect_duration=N` | Set all PC affects' duration to N |
| `__tick` | Run one violence tick (combat round) |
| `__char_update` | Run one `char_update` pulse (regen, condition decay, affect expiry) |
| `__mobile_update` | Run one `mobile_update` pulse (TRIG_RANDOM, TRIG_DELAY) |
| `__instant_kill` | Deal a killing blow to the first NPC in the room |

## Normalization rules (both sides, identical)

- Identity by stable key: character name; object vnum (never pointers/ids).
- `inventory` and `output`: order-preserved (ROM prepend / message sequence are
  observable). `room.people`, `room.contents`, `affects`, `affect_flags`: sorted.
- Output: ANSI stripped, all CR removed (ROM uses `\n\r`), blank lines dropped,
  compared as the sequence of non-empty trimmed text lines.

## A divergence is a finding, not a golden to overwrite

When the replay test fails with a real divergence: ROM is the source of truth.
Triage it, record it in `FINDINGS.md`, file a parity gap, and fix Python (or the
data). **Do not** edit the golden to make the test pass. Known, not-yet-resolved
divergences are listed in `KNOWN_DIVERGENCES` in the replay test (self-clearing
xfail). See `FINDINGS.md` for the open items (notably FINDING-001 + the
`midgaard.are` input-asymmetry caveat).
