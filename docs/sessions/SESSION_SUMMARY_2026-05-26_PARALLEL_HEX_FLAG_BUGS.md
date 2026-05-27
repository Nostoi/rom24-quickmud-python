# Session Summary — 2026-05-26 — PARALLEL hex-flag bugs (2.9.55–2.9.56)

## Scope

Continuation of the 2026-05-26 META burn-down (now at 2.9.54). Picked up
the "drift-risk cleanup batch" (8 PARALLEL ⚠️ rows) — intended as one
mechanical commit — and immediately discovered the audit's "drift-risk
only, no current bug" hypothesis was wrong: the inline hex literals
**did not match** the canonical IntEnum bit values. Several rows are
real active bugs. Per the "one gap = one test = one commit" rule, split
the batch into individual gap-closers. This session closed two: the
highest-impact `do_config` display table (PARALLEL-001/004) and the
`_can_drop_obj` gate (PARALLEL-005).

## Why the "drift-risk" hypothesis broke

ROM letter macros are bit-shifts: `A=1<<0`, `B=1<<1`, `C=1<<2`, …
`mud/models/constants.py` mirrors them with `IntFlag` values. The hex
literals scattered through `mud/commands/*.py` came from a different
(wrong) convention — likely guessed from constant names or copied from
non-ROM sources. Whenever a Python file declares e.g.
`ITEM_NODROP = 0x0010` inline instead of importing `ExtraFlag.NODROP`,
the comparison points at a wrong bit (in this case bit 4 = `EVIL`).

This is the exact pitfall AGENTS.md "ROM Parity Rules" warns about:
> "Never hardcode hex bit values — ROM C uses bit shifts and the hex
> you'd guess from the constant name is often wrong."

## Outcomes

### `PARALLEL-001` + `PARALLEL-004` — ✅ FIXED (`1d675fe`, 2.9.55)

- **Python**: `mud/commands/misc_player.py:19, 68-107` (`do_config`)
- **ROM C**: `src/merc.h:703-721` (letter macros), `:1398-1449` (PLR_/COMM_)
- **Gap**: The `configs` display table hardcoded hex literals
  (`autoloot = 0x00008000`, `autosac = 0x00010000`, `compact = 0x00000200`,
  `afk = COMM_AFK = 0x00000800`, …) that did **not** match the IntEnum
  bits the toggles set. Examples:
  - `do_autoloot` flipped `PlayerFlag.AUTOLOOT` (bit 4 = 0x10) but the
    table read bit 15 (0x00008000) → `config` always showed `autoloot OFF`.
  - `do_brief` flipped `CommFlag.BRIEF` (bit 12 = 0x1000) which collided
    with the table's "combine" hex (0x00001000) → flipping `brief` lit up
    `combine ON` in the display.
  - Module-local `COMM_AFK = 0x00000800` was 0x800 (bit 11);
    `CommFlag.AFK = 1<<25 = 0x2000000`.
- **Fix**: Replaced every hex literal in the `configs` table with
  `int(PlayerFlag.X)` / `int(CommFlag.X)`. Re-pointed the module-local
  `COMM_AFK` alias at `int(CommFlag.AFK)` (kept the name for backwards-
  compat with any other importer).
- **Test**: `tests/integration/test_do_config_flag_alignment.py` (2/2).

### `PARALLEL-005` — ✅ FIXED (`3e71334`, 2.9.56)

- **Python**: `mud/commands/obj_manipulation.py:614-625` (`_can_drop_obj`)
- **ROM C**: `src/handler.c can_drop_obj` + `src/merc.h:1111`
  `#define ITEM_NODROP (H)` where `H = 1<<7 = 0x80`
- **Gap**: Inline `ITEM_NODROP = 0x0010` aliased `ExtraFlag.EVIL` (bit 4),
  not `ExtraFlag.NODROP`. `_can_drop_obj` is the shared gate for
  `do_drop`, `do_put`, `do_give`, and `inventory.py:do_drop_all` — so
  pre-fix NODROP cursed gear could be dropped freely (defeating the
  canonical use case for the flag) and EVIL items were spuriously
  blocked. `mud/commands/shop.py:_can_drop_object` already used the
  canonical `ITEM_NODROP` import, so shops were unaffected; only the
  drop/put/give/drop_all paths were broken.
- **Fix**: Replaced inline literal with `int(ExtraFlag.NODROP)`.
- **Test**: `tests/integration/test_can_drop_obj_nodrop_bit.py` (3/3 —
  NODROP rejected, EVIL allowed, unflagged allowed).
- **Bug in test**: `test_drop_command.py::test_drop_nodrop_item_is_rejected`
  encoded `extra_flags = 0x0010` — the same wrong bit. Per AGENTS.md
  "ROM is source of truth, a test asserting behavior contradicting ROM C
  is a bug in the test", the test now uses `int(ExtraFlag.NODROP)`.

## Files Modified

### 2.9.55 (PARALLEL-001 + PARALLEL-004)
- `mud/commands/misc_player.py` — `configs` table + `COMM_AFK` alias
- `tests/integration/test_do_config_flag_alignment.py` — NEW
- `docs/parity/audits/PARALLEL_REPRESENTATIONS.md` — rows flipped: 001 → ✅ FIXED (re-classified MEDIUM active bug), 004 → ✅ FIXED (re-classified)
- `CHANGELOG.md` — 2.9.55 section
- `pyproject.toml` — 2.9.54 → 2.9.55

### 2.9.56 (PARALLEL-005)
- `mud/commands/obj_manipulation.py:614-625` — inline literal → `int(ExtraFlag.NODROP)`
- `tests/integration/test_can_drop_obj_nodrop_bit.py` — NEW
- `tests/integration/test_drop_command.py::test_drop_nodrop_item_is_rejected` — wrong hex → `int(ExtraFlag.NODROP)`
- `docs/parity/audits/PARALLEL_REPRESENTATIONS.md` — PARALLEL-005 → ✅ FIXED (re-classified MEDIUM)
- `CHANGELOG.md` — 2.9.56 section
- `pyproject.toml` — 2.9.55 → 2.9.56

## Test Status

- `tests/integration/test_do_config_flag_alignment.py` — 2/2 ✅
- `tests/integration/test_can_drop_obj_nodrop_bit.py` — 3/3 ✅
- Adjacent suites (75 tests across config/auto_flags/player_config) — green
- Drop/put/give/inv025-trigger suite (50 tests) — green
- Full integration suite not re-run (low-blast-radius targeted fixes)

## Audit re-classification

`docs/parity/audits/PARALLEL_REPRESENTATIONS.md` had its "8 ⚠️ DRIFT-RISK"
summary overturned by these fixes. **Three rows so far promoted from
⚠️ DRIFT-RISK to MEDIUM active bug**: PARALLEL-001 (`do_config` table),
PARALLEL-004 (`COMM_AFK` alias), PARALLEL-005 (`_can_drop_obj`).

Remaining rows still need inspection — pre-existing audit assertion
"no current bug" cannot be trusted on the others either. Top
suspects, in descending impact:

- **PARALLEL-003** `mud/commands/remaining_rom.py:104, 105, 211`:
  `COMM_QUIET = 0x00000004` (canonical `1<<0 = 0x1`),
  `ACT_GAIN = 0x00100000` inside `do_train` (canonical `1<<27 = 0x8000000`).
  ACT_GAIN is used to find trainer NPCs in the room — wrong bit means
  `do_train` likely never finds a trainer.
- **PARALLEL-006** `mud/commands/imm_load.py:176, 177`:
  `ACT_NOPURGE = 0x00002000` (canonical `1<<21 = 0x200000`),
  `ITEM_NOPURGE = 0x00000040` (canonical `1<<14 = 0x4000`). Affects the
  immortal `purge` room-purge protection — wrong bit means NOPURGE-flagged
  NPCs/objects may get purged anyway, OR non-NOPURGE entities get spared.
- **PARALLEL-002** `mud/commands/player_config.py:76`:
  `IMM_SUMMON = 0x00000010` (canonical `1<<0 = 0x1`). Affects
  NPC `nosummon` toggle.
- **PARALLEL-002** PLR_CANLOOT/PLR_NOSUMMON/PLR_NOFOLLOW are
  coincidentally correct (`1<<15`, `1<<16`, `1<<17`).
- **PARALLEL-003** `COMM_DEAF = 0x00000002` is coincidentally correct
  (`1<<1`).

## Next Steps

1. **Push approval** required for 2.9.52–2.9.56 (5 commits since
   origin/master). Per standing rule, no push without explicit
   per-cluster approval ("yes push v2.9.56 to origin/master" or
   similar).
2. **Continue PARALLEL hex-bit burn-down** — PARALLEL-003 (`ACT_GAIN`
   in `do_train`) is the next highest-impact target. PARALLEL-006
   (`ACT_NOPURGE` / `ITEM_NOPURGE`) follows. Each is a single gap-closer
   with a targeted regression test (`do_train` finds trainer; `do_purge`
   skips NOPURGE NPC; etc.).
3. **Then PARALLEL-008** (dead `.carrying` fallback in `consumption.py`)
   and **PARALLEL-011** (stale docstring at `handler.py:694`) — these
   really are cleanup, single mechanical commit.
4. **Then Class 1 BROADCAST_COVERAGE burn-down** (29 ❌; verify
   helper-transitivity before promoting each row to a gap-closer).
5. **Pre-existing flake** at
   `test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs` —
   filed; not addressed.
6. **GitNexus refresh**: index now 8 commits stale
   (last indexed `069f17f`). Run `npx gitnexus analyze --skip-agents-md`.
7. **Locked Class 1 worktree hygiene**:
   `.claude/worktrees/agent-a1b07201d504ce97b` still locked. Unlock +
   remove in a separate hygiene pass.
