# Session Summary — 2026-05-28 — differential-harness soundness + MOVE-003 / LOOK-004

## Scope

Continuation of the same day's differential-harness work
(`SESSION_SUMMARY_2026-05-28_LOOK_GAPS_AND_CHECKER_OPT_IN.md`). Two threads:

1. **Reconcile the harness's soundness asymmetries** so its diffs are fully
   trustworthy (the prior session's #1 follow-up — FINDING-002 + input/capture
   fairness). Work on branch `diff-harness`.
2. **Fix the two real ROM parity bugs the now-sound harness surfaced**
   (FINDING-003, FINDING-004) on `master`, then merge to clear the differential
   xfail — demonstrating the build→catch→fix→merge→clean loop a second time.

## Outcomes

### Harness soundness — 4 comparison-fairness asymmetries reconciled (branch `diff-harness`, commit `67eb0609`)

The harness compared an unfair start state / output channel, so its per-field
diffs weren't trustworthy. All four fixes are harness-only (no `mud/` or `src/`
edits) — they are *not* parity bugs, they were unfairness in the comparison:

- **FINDING-002 (hp/mana/move):** the Python replay seeded the test char from the
  dataclass defaults (0); the C shim's `make_test_char` uses ROM `new_char()`
  defaults (recycle.c:299-304 — 20/100/100). Replay now seeds those.
- **level:** `capture.py:_drive` never passed `level=` to the C shim, so C booted
  level 1 while Python set the scenario level — a second divergence the
  first-divergence comparator masked behind the hp diff. Boot line now carries it.
- **people-key:** `pysnap` keyed room occupants by `MobInstance.name` (display
  "the healer") vs the C shim's `char_key` (first word of ROM `ch->name` =
  keyword `player_name` "healer"). pysnap now matches.
- **output channel:** the replay captured only `process_command`'s return value;
  the C shim captures the full descriptor buffer. Replay now captures the full
  player-visible output — return value + drained `char.messages` — mirroring the
  live server loop (`mud/net/connection.py:1979-2000`).

Golden recaptured (only `char.level` 1→5; output arrays unchanged). The fairer
capture immediately surfaced FINDING-003 + FINDING-004 (below).

### `MOVE-003` ✅ FIXED (master, 2.10.4, commit `ab8f9bd9`)

- **Python**: `mud/world/movement.py::move_character`
- **ROM C**: `src/act_move.c:204` — `do_function(ch, &do_look, "auto")`
- **Gap**: directional movement returned `"You walk {dir} to {room}."`, which the
  dispatcher delivered to the player as an extra, non-ROM line. ROM's mover sees
  only the destination room (auto-look); others get the leave/arrive broadcasts.
- **Fix**: `move_character` now returns the destination room view (`look(char)`,
  the Python command-output convention; computed before followers move per ROM
  order). Followers still receive the room via their own message stream.
- **Significance**: the `act_move.c` audit had this at "100% parity" (40/40) — it
  verified broadcasts/logic but not the mover's own visible output. Audit
  corrected.
- **Tests**: `tests/integration/test_move_003_walk_line.py`; ~25 existing
  assertions across 14 files updated from the walk-line to ROM-faithful room
  output. Full suite green.

### `LOOK-004` ✅ FIXED (master, 2.10.5, commit `2e5ebf3f`)

- **Python**: `mud/world/look.py::_describe_room` (object loop)
- **ROM C**: `src/act_info.c` `format_obj_to_char(obj, ch, fShort=FALSE)`
- **Gap**: room object listing showed `obj.short_descr` ("the donation pit")
  instead of the ROM ground `description` ("A pit for sacrifices is in front of
  the altar."), and listed all objects. ROM lists ground objects by
  `obj->description` and skips any object whose description is empty.
- **Fix**: the object loop now emits `obj.description` and skips
  description-less objects (object analog of the LOOK-001 NPC `long_descr` fix).
- **Significance**: the `format_obj_to_char` row was marked "100% PARITY" on
  `do_look 9/9` smoke tests that never asserted the ground-description text. Audit
  corrected. (Aura/stat prefixes — `(Glowing)`/`(Humming)`/`(Invis)`/detect auras
  — remain a separate latent gap, noted in the audit.)
- **Tests**: `tests/integration/test_look_004_room_object_description.py`; one
  existing `do_look` test updated (its synthetic object had no description). Full
  suite green.

### Loop closure (branch `diff-harness`, commit `91608b0f`)

Merged `master` (MOVE-003 + LOOK-004) into `diff-harness`. The `movement_get_drop`
differential now matches the C reference **exactly** — the `KNOWN_DIVERGENCES`
entry was removed (self-clearing) and FINDING-003/004 marked ✅ RESOLVED in
`tools/diff_harness/FINDINGS.md`. Second end-to-end demonstration of
build→catch→fix-on-master→merge→re-run→diff-clean.

## Files Modified

- **master**: `mud/world/movement.py`, `mud/world/look.py` (engine fixes);
  `tests/integration/test_move_003_walk_line.py`,
  `tests/integration/test_look_004_room_object_description.py` (new); ~15 existing
  test files re-asserted to ROM-faithful output; `docs/parity/ACT_MOVE_C_AUDIT.md`
  (MOVE-003 row + corrected 100% claim), `docs/parity/ACT_INFO_C_AUDIT.md`
  (LOOK-004 row + corrected 100% claim); `CHANGELOG.md` (2.10.4, 2.10.5);
  `pyproject.toml` (→ 2.10.5).
- **branch `diff-harness`**: `tools/diff_harness/{capture,pysnap,compare}.py`,
  `tests/test_differential_smoke.py`, `tools/diff_harness/FINDINGS.md`,
  `tests/data/golden/diff/movement_get_drop.golden.json`.

## Test Status

- Full suite (master, post-merge state): **4915 passed, 4 skipped, 0 failed**.
- `tests/test_differential_smoke.py` (branch): **1 passed** (xfail cleared; diff
  matches C reference exactly).

## Outstanding

- **Harness input-source asymmetry** (the remaining soundness item): the C side
  reads `.are` files (repaired midgaard overlay), the Python side reads
  `data/areas/*.json`. Reconcile before trusting midgaard divergences broadly.
  Also: `area/midgaard.are` is malformed vs stock ROM. See
  `tools/diff_harness/FINDINGS.md`.
- **`format_obj_to_char` aura/stat prefixes** (latent gap from LOOK-004): room
  object lines don't yet prepend `(Glowing)`/`(Humming)`/`(Invis)`/detect auras.
  Noted in `docs/parity/ACT_INFO_C_AUDIT.md`.
- **Merge `diff-harness` to master** once the input-source asymmetry is closed and
  the harness is extended (combat/RNG slice, generated scenarios).
- **INV-025 non-combat narration sweep** — still open from earlier.
- **GitNexus** — on-disk graph stale (`2272b2e`), MCP DB read-only all session;
  re-run `npx gitnexus analyze --skip-agents-md` once the lock clears.

## Next Steps

1. Reconcile the harness input-source asymmetry (`.are` overlay vs JSON) — the
   last soundness follow-up before `diff-harness` can merge.
2. Extend the harness with a combat/RNG scenario slice (the OLD_RAND bit-match is
   already in place), each as its own spec→plan.
3. Close the `format_obj_to_char` aura-prefix latent gap (its own gap-closer).
