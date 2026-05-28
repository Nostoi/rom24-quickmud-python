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
