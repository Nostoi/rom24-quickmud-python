# Differential Testing Harness (ROM C ⇄ Python) — Design

**Date:** 2026-05-28
**Status:** Design — approved in brainstorming, pending written-spec review
**Topic:** A local differential-testing tool that compares the Python port against
the original ROM 2.4b6 C engine by running both through identical scripted
scenarios and diffing observable state + output.

## Motivation

The project's parity verification has two layers today: the per-file function
audit (systematic, drained) and the cross-file invariant (INV) layer
(judgment-driven, reactive). Three production bugs shipped this year against
files marked ≥95% audited because the broken contract lived *between* modules
(duplicate combat-message delivery, PC missing from `character_registry` after
WS login, negative HP leaking into the prompt).

Differential (back-to-back) testing is the research-canonical method for
validating a reimplementation against a reference (McKeeman 1998; used by
compiler test suites, SQLite, protocol reimplementations). It surfaces
observable divergences *mechanically* — no human enumeration of guarantees.

This is unusually viable for this codebase because the usual blocker —
nondeterminism — is **already solved**: the Mitchell-Moore RNG is replicated
bit-for-bit in `mud/utils/rng_mm.py`, and C integer semantics are replicated via
`mud/math/c_compat.py`. The C engine, compiled with `-DOLD_RAND` and seeded to a
fixed value, produces the same RNG stream as the Python port.

## Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sub-project sequencing | Spec the differential harness now; defer the always-on `game_tick` invariant checker to its own later cycle | The harness has the real design questions |
| C engine instrumentation | **Additive only** — new code under `src/diff_shim/`, ROM `src/*.c` untouched | Preserves the AGENTS.md "read-only `src/`" rule; robust structured comparison |
| What to diff | **Both** structured state **and** normalized output, every step | Catches both bug classes (state/ordering *and* delivery/wording) |
| First vertical slice | **Deterministic smoke slice** (no-RNG commands) | De-risk the snapshot/normalization plumbing before tackling combat |
| Target maturity | **Local dev/research tool** | Fastest to a working prototype; no per-PR cost or CI toolchain maintenance |
| Harness architecture | **Approach B — golden-trace capture/replay** | Keeps the slow/fragile C dependency out of the everyday loop; extends the existing `tests/data/golden/` convention; divergences show up as reviewable git diffs |

## Architecture

Two phases sharing one snapshot schema:

```
CAPTURE (occasional, needs C build)
  scenario.json ──▶ capture.py ──▶ [instrumented C binary]
                                        │ stdin: commands
                                        │ stdout: JSON output + snapshots per step
                                        ▼
                     tests/data/golden/diff/<scenario>.golden.json   (committed)

REPLAY (every run, pure Python — the pytest test)
  scenario.json ──▶ replay driver ──▶ [Python engine: process_command + game_tick]
                          │                     │ snapshot per step (pysnap.py)
                          │                     ▼
                          └──▶ compare.py ◀── golden.json
                                    │
                                    ▼
                          first-diverging-step field-level diff report
```

The Python snapshot logic (`pysnap.py`) and comparator (`compare.py`) are shared
with a possible future live dual-drive mode (Approach A); only the capture source
would swap. Choosing B now does not foreclose A.

### Component layout

| Module | Purpose | Depends on |
|--------|---------|-----------|
| `tools/diff_harness/schema.py` | Canonical snapshot dataclass + JSON (de)serialization — the single shared contract | stdlib only |
| `tools/diff_harness/scenario.py` | Scenario loader (seed, start room, char, watch-set, steps) | schema |
| `tools/diff_harness/capture.py` | Drives the C binary over stdin/stdout; writes golden traces. Manual. | schema, scenario, compare.normalize |
| `tools/diff_harness/pysnap.py` | Builds a snapshot from live Python engine state | schema, `mud.*` |
| `tools/diff_harness/compare.py` | `normalize()` + `diff()` + report rendering | schema |
| `src/diff_shim/` | Additive C: deterministic boot+seed, scripted-input driver, `__snapshot` command | ROM objects (link-time) |
| `tests/test_differential_smoke.py` | Pure-Python replay test: load golden, drive Python, assert zero diff | all of the above |

The C additive code is quarantined under `src/diff_shim/` so the "read-only
`src/`" rule is visibly preserved; ROM's `src/*.c` are unchanged and only linked.

## Snapshot schema

After each step, the harness captures only a declared **watch set** (the
scenario's character(s) + rooms they touch) — not the whole world (too large,
too noisy).

```jsonc
{
  "step": 3,
  "command": "get sword",
  "chars": [
    { "key": "Tester",                 // stable identity, never a pointer/object-id
      "room": 3001,
      "position": "STANDING",
      "hp": 100, "max_hp": 100, "mana": 100, "move": 100,
      "level": 5, "align": 0, "gold": 0,
      "fighting": null,                 // char key or null
      "affects": ["bless", "sanctuary"],          // sorted by spell name
      "affect_flags": ["INFRARED","SANCTUARY"],   // sorted enum names
      "inventory": [{"vnum": 3022, "n": 1}],      // ORDER-PRESERVED (see below)
      "equipment": {"wield": 3022, "light": 1}    // slot-name → vnum
    }
  ],
  "rooms": [
    { "vnum": 3001,
      "people": ["Tester","fido"],               // sorted char keys
      "contents": [{"vnum": 3010, "n": 2}] }      // sorted by vnum
  ],
  "output": ["You pick up a sword."]              // normalized message lines, ORDER-PRESERVED
}
```

A golden file wraps the trace with provenance:

```jsonc
{
  "scenario": "movement_get_drop",
  "c_commit": "<git sha of the C build>",
  "build_flags": "-DOLD_RAND",
  "seed": 1234,
  "trace": [ <snapshot>, ... ]
}
```

### Normalization rules

Both `capture.py` (C trace) and the replay test call the **same**
`compare.normalize()` so canonicalization cannot drift between sides.

- **Identity** — never compare pointers/object-ids. Characters keyed by name;
  objects keyed by `vnum` with duplicates collapsed into a `{"vnum","n"}` count.
  The harness assigns unique names to test characters.
- **Ordering** — declared per list in the schema, not guessed per-diff:
  - *Sorted* (ROM linked-list order not behaviorally meaningful): room `people`,
    room `contents`, char `affects`, `affect_flags`.
  - *Order-preserved* (ROM semantics depend on order): `output` (message
    sequence is observable) and `inventory` (ROM prepends on pickup, so
    `get`/`drop`/`get all` ordering is observable).
- **Output text** — strip ANSI escapes, `\r\n`→`\n`, strip trailing whitespace.
  The **prompt line is excluded** from the smoke slice (format-heavy; gets its
  own scenario later). Message bodies compared verbatim otherwise.
- **Transient noise** — smoke scenarios disable time/weather/hunger ticks and use
  a fixed RNG seed, so there is no tick noise to filter. Anything still
  nondeterministic (should not exist in the smoke slice) fails loudly rather than
  being silently masked.

### Diff reporting

The comparator reports the **first** diverging step with a field-level diff,
e.g. `step 3 · chars[Tester].inventory · C=[3022,3010] py=[3010,3022]`. Once a
step diverges, everything downstream is suspect, so the first divergence is the
actionable signal.

## C-side additive instrumentation

All new code under `src/diff_shim/`; ROM `src/*.c` stay byte-for-byte untouched.
Built via a separate makefile (`src/Makefile.diffshim`) that compiles the ROM
objects + the shim with `-DOLD_RAND`.

1. **Deterministic boot + seed** — a shim entry calls ROM's `boot_db()` then
   forces `init_mm` to the scenario's fixed seed, bypassing the
   `srandom(time^pid)` default. With `-DOLD_RAND` the generator matches
   `mud/utils/rng_mm.py` exactly.
2. **Scripted-input driver** — replaces `game_loop_unix`'s `select()`/socket path
   with a loop that: reads commands line-by-line from **stdin**; creates one
   in-memory test character (no network descriptor) in the start room; feeds each
   line to ROM's real `interpret()` (exercising genuine ROM logic, not a
   reimplementation); and captures the character's output by pointing its output
   buffer at an in-memory sink drained after each command.
3. **`__snapshot` meta-command** — a line the driver intercepts (not passed to
   `interpret`): walks the watch-set (chars by name, rooms by vnum) and writes one
   schema-conformant JSON object to **stdout**, tagged so `capture.py` separates
   snapshots from game output.

### stdin/stdout protocol (line-oriented)

```
< boot seed=1234 start_room=3001 char=Tester
< get sword
> {"type":"output","lines":["You pick up a sword."]}
< __snapshot chars=Tester rooms=3001
> {"type":"snapshot","step":3,...}
```

### Primary implementation risk

Capturing ROM's per-character output. ROM writes via `send_to_char`/`act` →
`write_to_buffer` on `ch->desc`. The shim gives the test char a synthetic
`DESCRIPTOR_DATA` whose buffer we drain after each command — the established ROM
descriptor pattern, just memory-backed instead of socket-backed. If a command
path needs a fuller descriptor lifecycle than the shim provides, that command is
out of the smoke slice until the shim grows. This is the spec's #1 risk.

## Scenario format

`tools/diff_harness/scenarios/<name>.json` — the single source both phases read,
guaranteeing identical steps:

```jsonc
{
  "name": "movement_get_drop",
  "seed": 1234,
  "start_room": 3001,
  "char": { "name": "Tester", "level": 5 },
  "watch": { "chars": ["Tester"], "rooms": [3001, 3054] },
  "steps": ["look", "get sword", "inventory", "north", "drop sword", "south"]
}
```

The harness auto-inserts a `__snapshot` over the watch-set after every step, so
scenarios stay readable — just the command list.

## Phases in detail

### Capture (manual, needs C build)

`capture.py` builds (or assumes-built) the shim binary, spawns it, replays
`steps` over stdin, collects the per-step `output`+`snapshot` JSON into a golden
file stamped with the C commit sha, build flags, and seed. Writes atomically
(temp file → rename) so a failed capture never leaves a partial golden.
`--check` mode re-captures and fails if the new trace differs from the committed
one (catches "did the C reference shift?").

### Replay (every run, pure Python — the pytest test)

For each golden file: seed `rng_mm`, `initialize_world()`, spawn the named char
in `start_room`, then for each step call `process_command`, build a Python
snapshot via `pysnap.py` over the same watch-set, normalize both sides
identically, assert the traces match — reporting the first diverging step/field.
The smoke slice runs **no `game_tick`** (commands are direct effects; ticks are
disabled on both sides) — tick-driven pulses arrive with the later combat/affect
slices, and the C shim's deterministic boot omits the periodic-pulse loop
correspondingly.

## Smoke slice scope (first deliverable)

Deterministic, no-RNG commands only: `look`, `north/south/east/west`,
`get <obj>`, `drop <obj>`, `inventory`, `wear <obj>`, `remove <obj>`. 2–3
scenarios exercising movement + object handling in real Midgaard rooms
(3001/3054).

**Out of scope for v1:** combat, casting, shops, anything RNG-driven, the prompt
line, multi-player rooms, mob AI ticks. Those are follow-on slices once the
pipeline is trusted.

## Testing the harness itself

The harness is test infrastructure, so it gets its own tests:

- `compare.normalize()` / `compare.diff()` — unit tests including deliberately
  divergent trace pairs proving the comparator *catches* a known field
  difference (a comparator that never reports diffs is worse than none).
- `pysnap.py` — snapshot a hand-built Character/Room, assert schema shape.
- `schema.py` — round-trip (serialize → deserialize → equal).
- `tests/test_differential_smoke.py` — the integration test; `pytest.skip`s
  cleanly when a golden file is missing (matching the existing `load_golden_file`
  skip pattern) so a fresh checkout without captured goldens does not hard-fail.

## Error handling (boundaries only)

- **Capture:** C binary nonzero exit, malformed JSON, or a step with no snapshot
  → fail with the offending step + raw stdout/stderr. Atomic writes; no partial
  goldens.
- **Replay:** missing golden → skip; malformed golden → fail loudly; unknown
  command in a scenario → fail at load time, not mid-run.
- A **divergence** is a normal result, not an error: report first diverging
  step + field-level diff, exit nonzero.

## Re-capture workflow

Documented in `tools/diff_harness/README.md`:

```
make -C src -f Makefile.diffshim                  # build instrumented binary (once)
python3 -m tools.diff_harness.capture --all       # regenerate all goldens
python3 -m tools.diff_harness.capture --check     # verify goldens vs current C
pytest tests/test_differential_smoke.py            # everyday pure-Python run
```

Goldens are committed with the C commit sha baked in, so a reviewer sees exactly
which reference produced them.

## YAGNI — explicitly cut from v1

- No live dual-drive (Approach A) — golden replay only; A is a documented future
  upgrade sharing the same schema.
- No CI integration — local tool.
- No FFI, no TCP, no telnet parsing.
- No whole-world snapshots — watch-set only.
- No combat/RNG/prompt/shop/mob-tick coverage in v1.
- No auto-generated scenarios (Hypothesis) — hand-written scenarios first;
  generation is a later layer.

## Definition of done (v1)

1. The instrumented C binary builds on macOS via `src/Makefile.diffshim`.
2. 2–3 smoke scenarios captured to committed goldens under
   `tests/data/golden/diff/`.
3. `pytest tests/test_differential_smoke.py` drives the Python engine through
   them and passes — or reports a real divergence we then triage as a parity gap.
4. Harness modules (`schema`, `scenario`, `pysnap`, `compare`) unit-tested,
   including a comparator test that proves divergences are caught.
5. `tools/diff_harness/README.md` documents the re-capture loop.

## Future upgrade paths (not in scope, recorded for continuity)

- **Live dual-drive (Approach A):** swap golden-load for a live C drive, reusing
  schema + comparator.
- **Combat / RNG slices:** extend scenarios once the pipeline is trusted; the RNG
  is already aligned.
- **Prompt parity scenario:** dedicated slice for the prompt line.
- **Generated scenarios:** Hypothesis `RuleBasedStateMachine` emitting command
  sequences, with the snapshot invariants as properties.
- **The always-on `game_tick` invariant checker** (the deferred sub-project):
  complementary — it checks invariants continuously across the existing suite,
  whereas this harness checks parity against the C reference.
