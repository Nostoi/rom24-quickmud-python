# Session Summary — 2026-04-29 — `olc_act.c` audit + OLC_ACT-001..006 closures

## Scope

Single-day continuation arc: lifted the `olc_act.c` sibling-audit hold,
filed the audit doc with stable gap IDs, and closed all six CRITICAL
OLC_ACT gaps. Side effect: the four CRITICAL OLC-016/017/018/019 sibling
gaps in `olc.c` flip ✅ FIXED transitively (Python's `cmd_*edit`
dispatcher and the per-editor `*_create` builder live in the same
function).

Two earlier subagent attempts to close all six gaps in one delegated run
failed (Sonnet terminated mid-investigation, no commits landed). Pivoted
to inline work — six tool calls per gap on average, with one combined
commit for the three redit branches since they're interleaved in ROM's
single `do_redit` function.

## Outcomes

### `olc_act.c` audit doc filed (Phases 1–3)

- `docs/parity/OLC_ACT_C_AUDIT.md` — 5007-line file with ~108 functions
  inventoried across four editors (aedit / redit / oedit / medit).
  TIER A (line-by-line): 9 functions; TIER B (moderate): 8 functions;
  TIER C (inventory only): ~78 functions. mpedit/hedit out of scope
  (sibling audits).
- 14 stable gap IDs filed (OLC_ACT-001..014): 6 CRITICAL, 6 IMPORTANT,
  2 MINOR. Three human-decision flags raised and locked the same day.
- Tracker: `olc_act.c` flipped ❌ Not Audited → ⚠️ Partial.
- Commit: `e5d6015`.

### Locked human-decision flags (commit `93db16f`)

1. **`aedit_create` defaults**: replicate ROM verbatim
   (`min_vnum=0`/`max_vnum=0`/`security=1`/`name="New area"`/etc. from
   `src/mem.c:91-122`). Parity-faithful ROM quirk, not a bug to patch.
2. **`redit <vnum>` silent teleport**: reuse existing
   `_char_from_room`/`_char_to_room` primitives from
   `mud.commands.imm_commands`. No new movement infra required.
3. **`medit_shop`** (185 lines, ROM 3932-4117): stay TIER C; revisit
   after the six anchor closures land.

### `OLC_ACT-001` — `aedit create` ✅ FIXED

- **Python**: `mud/commands/build.py:_aedit_create` + `cmd_aedit`
  + `_interpret_aedit` create-keyword wiring.
- **ROM C**: `src/olc_act.c:667-679` (`aedit_create`)
  + `src/mem.c:91-122` (`new_area` defaults).
- **Fix**: explicit `aedit create` keyword path. New area initialized with
  authoritative ROM defaults (`name="New area"`, `builders="None"`,
  `security=1`, `min/max_vnum=0`, `empty=True`, `area_flags=AreaFlag.ADDED`,
  `file_name="area<vnum>.are"`). Vnum allocation via
  `max(area_registry) + 1` (Python adaptation; ROM uses `top_area`
  counter). Reachable from both top-level `@aedit create` and from
  inside an active aedit session.
- **Audit-doc correction**: original notes claimed `name="(unnamed)"`
  and `security=9`; ROM source actually uses `"New area"` and `1`.
- **Tests**: `tests/integration/test_olc_act_001_aedit_create.py`
  (9 cases, green).
- **Commit**: `664e074`. Unblocks **OLC-016**.

### `OLC_ACT-005` — `oedit create <vnum>` ✅ FIXED

- **Python**: `mud/commands/build.py:_oedit_create`.
- **ROM C**: `src/olc_act.c:3178-3225` + `src/mem.c:297-335`
  (`new_obj_index`).
- **Fix**: explicit `create <vnum>` keyword + full ROM validation chain
  (vnum required, area assignment via `_get_area_for_vnum`, IS_BUILDER
  security, already-exists). Verbatim ROM error strings ("Syntax:  oedit
  create [vnum]\n\r", "OEdit:  That vnum is not assigned an area.\n\r",
  "OEdit:  Vnum in an area you cannot build in.\n\r", "OEdit:  Object
  vnum already exists.\n\r"). Defaults applied: `name="no name"`,
  `short_descr="(no short description)"`, `description="(no description)"`,
  `item_type="trash"`, `material="unknown"`, `value=[0]*5`,
  `new_format=True`. **Removed** pre-existing auto-create-on-unknown-vnum
  bug — `@oedit <unknown_vnum>` without `create` keyword now errors.
- **Drive-by**: fixed `tests/integration/test_olc_builders.py::test_obj_proto`
  fixture which registered protos in the wrong registry
  (`mud.registry.obj_registry` vs canonical
  `mud.models.obj.obj_index_registry`).
- **Tests**: `tests/integration/test_olc_act_005_oedit_create.py`
  (11 cases, green).
- **Commit**: `bfcc10c`. Unblocks **OLC-018**.

### `OLC_ACT-006` — `medit create <vnum>` + `ACT_IS_NPC` fix ✅ FIXED

- **Python**: `mud/commands/build.py:_medit_create`.
- **ROM C**: `src/olc_act.c:3704-3753` + `src/mem.c:365-424`
  (`new_mob_index`).
- **CRITICAL fix flagged in audit**: `ActFlag.IS_NPC` now set on both
  `act_flags` (modern) and legacy `act` field per ROM `src/olc_act.c:3745`
  `pMob->act = ACT_IS_NPC;`. Without this, every `is_npc` check
  downstream misclassified freshly-built mobs as players.
- Full ROM validation chain wired with verbatim error strings. Defaults:
  `player_name="no name"`, `short_descr="(no short description)"`,
  `long_descr="(no long description)\n\r"`, `description=""`, `level=0`,
  `sex=Sex.NONE`, `size=Size.MEDIUM`, `start/default_pos="standing"`,
  `material="unknown"`, `new_format=True`. Auto-create-on-unknown-vnum
  bug removed.
- **Drive-by**: `test_olc_builders.py::test_mob_proto` fixture patched
  to write to canonical `mud.models.mob.mob_registry`.
- **Tests**: `tests/integration/test_olc_act_006_medit_create.py`
  (12 cases, green).
- **Commit**: `cacf0c6`. Unblocks **OLC-019**.

### `OLC_ACT-002` + `OLC_ACT-003` + `OLC_ACT-004` — `redit create/reset/<vnum>` ✅ FIXED (combined commit)

- **Python**: `mud/commands/build.py:cmd_redit` (rewritten)
  + `_redit_create` + `_redit_vnum_teleport`
  + `_apply_resets_for_redit`.
- **ROM C**: `src/olc.c:745-821` (`do_redit`)
  + `src/olc_act.c:1716-1766` (`redit_create`)
  + `src/mem.c:181-218` (`new_room_index`).
- **Combined commit rationale**: all three gaps are branches of ROM's
  single `do_redit` function. Splitting them would create intermediate
  broken states. Each gap has its own dedicated test file.
- **OLC_ACT-002** (`redit create <vnum>`): full ROM validation chain.
  `new_room_index` defaults applied (`heal_rate=100`, `mana_rate=100`,
  rest zeroed). After create, builder is silently relocated into the
  new room via `_char_from_room`/`_char_to_room`.
- **OLC_ACT-003** (`redit reset`): security gate, verbatim "Room
  reset.\n\r", `area.changed = True`, calls `apply_resets(area)` via
  `_apply_resets_for_redit` wrapper. Documented broader-scope
  divergence: ROM uses `reset_room(pRoom)` (`src/olc.c:765`); a
  per-room reset port from `src/db.c` is deferred.
- **OLC_ACT-004** (`redit <vnum>` silent teleport): reuses existing
  silent primitives `_char_from_room`/`_char_to_room` per the locked
  human-decision flag — no new movement infra. Validates target room
  exists, IS_BUILDER on TARGET area, relocates, sets descriptor edit
  pointer.
- **Tests**:
  - `tests/integration/test_olc_act_002_redit_create.py` (8 cases)
  - `tests/integration/test_olc_act_003_redit_reset.py` (4 cases)
  - `tests/integration/test_olc_act_004_redit_vnum_teleport.py` (5 cases)
- **Commit**: `d1edae1`. Unblocks **OLC-017** (all three halves).

### `OLC-016/017/018/019` — sibling closures (commit `1cf81df`)

Cross-audit linkage flip. The OLC-NNN gaps in `OLC_C_AUDIT.md` described
missing `do_*edit` dispatcher subcommands; the OLC_ACT-NNN gaps in
`OLC_ACT_C_AUDIT.md` are the corresponding builder logic. In Python
both halves live in the same `cmd_*edit` function — closing the
OLC_ACT side automatically closes the OLC side. Tracker rows flipped;
no code change.

## Files Modified

- `mud/commands/build.py` — six new helpers (`_aedit_create`,
  `_oedit_create`, `_medit_create`, `_redit_create`,
  `_redit_vnum_teleport`, `_apply_resets_for_redit`) + dispatcher
  rewrites in all four `cmd_*edit` and three `_interpret_*edit`
  functions. Imports extended for `ActFlag`, `AreaFlag`, `Sex`, `Size`.
- `mud/models/area.py` — unchanged; existing `Area` dataclass already
  had every field needed.
- 6 new integration test files under `tests/integration/test_olc_act_*.py`
  (49 cases total, all green).
- `tests/integration/test_olc_builders.py` — `test_obj_proto` and
  `test_mob_proto` fixtures patched (drive-by registry-mismatch fixes).
- `docs/parity/OLC_ACT_C_AUDIT.md` — created (Phases 1–3); rows
  OLC_ACT-001..006 flipped 🔄 OPEN → ✅ FIXED.
- `docs/parity/OLC_C_AUDIT.md` — OLC-016/017/018/019 rows flipped
  ⚠️ PARTIAL → ✅ FIXED.
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` — `olc_act.c` row
  flipped ❌ Not Audited → ⚠️ Partial.
- `CHANGELOG.md` — six new gap entries under `[Unreleased]`.
- `pyproject.toml` — 2.6.73 → 2.6.78 (5 patch bumps).

## Test Status

- `pytest tests/integration/test_olc_*.py tests/integration/test_olc_act_*.py
  tests/integration/test_string_*.py tests/integration/test_bit_*.py
  tests/test_olc_aedit.py tests/test_building.py` — **348 passing**, 14
  failing (all pre-existing in `tests/test_building.py::test_redit_*`,
  unchanged baseline; verified via `git stash` round-trip).
- 49 new integration tests this session, all green.
- Full suite not re-run.

## Commits this session

| SHA | Gap | Severity |
|-----|-----|----------|
| `e5d6015` | `olc_act.c` audit (Phases 1–3, OLC_ACT-001..014 filed) | — |
| `93db16f` | Lock 3 human-decision flags | — |
| `664e074` | OLC_ACT-001 `aedit create` | CRITICAL |
| `bfcc10c` | OLC_ACT-005 `oedit create` | CRITICAL |
| `cacf0c6` | OLC_ACT-006 `medit create` + ACT_IS_NPC | CRITICAL |
| `d1edae1` | OLC_ACT-002+003+004 `redit create/reset/<vnum>` | CRITICAL |
| `1cf81df` | OLC-016..019 transitive flip in OLC_C_AUDIT.md | — |

## Subagent failure notes (for future reference)

Two Sonnet subagent runs were dispatched for this work and both
terminated mid-investigation with no commits landed. Both runs
correctly identified key intel before terminating (`MobIndex` uses
`act_flags`, two separate `obj_registry` bindings exist, etc.) but ran
out of context budget while still in the discovery phase. Six TDD
cycles in one delegated run is too ambitious for current Sonnet
subagent reliability. Smaller scope (one gap per subagent run, or
inline work) is more reliable.

## Next Steps

The OLC editor cluster's CRITICAL backbone is now closed. Carried
forward:

1. **OLC_ACT IMPORTANT gaps (OLC_ACT-007..012)** — `*_show` formatting
   completeness, success-message string drift across editors, missing
   `aedit_reset`. None block gameplay but degrade builder UX.
2. **OLC_ACT TIER C deep-audit pass** — ~78 functions still at
   "🔄 NEEDS DEEP AUDIT". Required before flipping `olc_act.c` row from
   ⚠️ Partial → ✅ AUDITED.
3. **`olc_save.c` / `olc_mpcode.c` / `hedit.c` audits** — three
   remaining ❌ Not Audited rows in the OLC cluster.
4. **OLC-021 (MINOR)** — `add_reset` linked-list edge cases.
5. **`board.c` ⚠️ Partial 95%** — last non-OLC partial row; deferrals
   could be retired or formally closed.

Recommended next-session start: option 1 (`OLC_ACT-007..012` IMPORTANTs)
since they're discrete and gap-closer-friendly. Alternatively option 3
(begin `olc_save.c` audit) if the user wants the OLC cluster
fully retired before pivoting elsewhere.
