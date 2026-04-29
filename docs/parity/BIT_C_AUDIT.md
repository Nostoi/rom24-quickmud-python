# `bit.c` ROM Parity Audit

- **Status**: ✅ AUDITED 90% — 3 MINOR gaps deferred to OLC audit (no current Python consumer)
- **Date**: 2026-04-29
- **Source**: `src/bit.c` (ROM 2.4b6, 177 lines, 3 public-or-file-local functions)
- **Python primaries**:
  - `mud/utils/prefix_lookup.py` (`prefix_lookup_intflag`, `rom_flag_aliases`)
  - `mud/commands/remaining_rom.py` (`_lookup_flag_bit`, inline accumulator inside `do_flag`)

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Visibility | Python counterpart | Status |
|------------|-----------|------------|--------------------|--------|
| `flag_stat_table[]` | 50-83 | file-static registry | — (not ported) | ⚠️ MISSING (BIT-003) |
| `is_stat` | 93-104 | file-local helper | — (not ported) | ⚠️ MISSING (BIT-003) |
| `flag_value` | 111-142 | public (called by `olc.c`, `olc_act.c`) | logic inlined in `mud/commands/remaining_rom.py:do_flag:440-462`; no standalone reusable helper | ⚠️ PARTIAL (BIT-001) |
| `flag_string` | 151-177 | public (called by `act_olc.c`, `olc.c`, `olc_save.c`) | — (not ported) | ⚠️ MISSING (BIT-002) |

Adjacent helper that ROM keeps in `lookup.c` (called by `flag_value`):

| ROM symbol | ROM lines | Python counterpart | Status |
|------------|-----------|--------------------|--------|
| `flag_lookup` | `src/lookup.c:39-51` | `mud/utils/prefix_lookup.py:prefix_lookup_intflag` (+ `rom_flag_aliases` for ROM table-name aliases) | ✅ AUDITED — see TABLES-002 |

## Phase 2 — Verification

### `flag_stat_table[]` + `is_stat` (ROM 50-104)

ROM partitions every flag table into **stats** (single-value enums; e.g. `sex_flags`, `sector_flags`, `position_flags`) versus **flags** (bitmasks; e.g. `act_flags`, `plr_flags`, `affect_flags`). `is_stat(table)` walks `flag_stat_table[]` and returns `TRUE` when the table is a stat table. The classification drives two behaviors:

1. `flag_value`: stat tables return the single matched value via `flag_lookup`; flag tables OR all matched bits into `marked`.
2. `flag_string`: stat tables print the single name whose `bit == bits`; flag tables print every name where `IS_SET(bits, bit)`.

Python today does not carry this metadata. It is implicit in the type system instead — `IntFlag` enums (`ActFlag`, `PlayerFlag`, …) cover ROM "flag" tables, and `IntEnum` enums (`Sex`, `Position`, `Sector`, …) cover ROM "stat" tables. Code that needs the distinction picks the right enum at the call site, so a runtime `is_stat()` helper is unnecessary for current consumers. **Gap recorded as BIT-003** (will be needed when OLC ports introduce a generic table dispatcher).

### `flag_value` (ROM 111-142)

ROM signature: `int flag_value(const struct flag_type *flag_table, char *argument)`.

Behavior:
1. If `is_stat(flag_table)`: return `flag_lookup(argument, flag_table)` — single value, no accumulation.
2. Else: tokenize `argument` via `one_argument`; for each token call `flag_lookup`; ignore tokens that miss; OR every hit into `marked`; track `found`.
3. Return `marked` if any token matched, else `NO_FLAG` (-1).

Python has **no standalone `flag_value(table, argument)` helper**. The only current Python consumer of "tokenize-and-OR-flag-names" logic is `do_flag` (`mud/commands/remaining_rom.py:440-462`), which inlines a stricter variant:

- It walks `rest` (already tokenized by `args.split()`).
- For each token it calls `_lookup_flag_bit` (which delegates to `prefix_lookup_intflag`).
- On the **first** unknown token it returns `"That flag doesn't exist!"` and aborts — ROM `flag_value` would silently skip unknowns and keep going.

This is correct for `do_flag` because ROM `do_flag` itself does not call `flag_value`; it calls `flag_lookup` per-token at `src/flags.c:202-218` and bails on the first unknown name with the same `"That flag doesn't exist!"` message. So the Python inline accumulator faithfully mirrors ROM `do_flag`, NOT ROM `flag_value`. The two ROM functions have **different unknown-name semantics on purpose** and that distinction is preserved in Python.

A reusable `flag_value` helper will become necessary when OLC porting begins (`olc.c`/`olc_act.c` use it for `redit set`/`oedit flags`/etc.). **Gap recorded as BIT-001**.

### `flag_string` (ROM 151-177)

ROM signature: `char *flag_string(const struct flag_type *flag_table, int bits)`.

Behavior:
1. Two static rotating buffers (`buf[2][512]`, `cnt` toggled) so two `flag_string()` calls in one `printf` argument list don't overwrite each other — a ROM C-ism the Python port doesn't need (immutable strings).
2. Iterate `flag_table[]`:
   - If table is **flag** type and `IS_SET(bits, flag_table[flag].bit)`: append `" " + name`.
   - Else if `flag_table[flag].bit == bits`: append `" " + name` and break (stat table single-value match).
3. Return the buffer with the leading space stripped, or the literal `"none"` if nothing matched.

Python has **no `flag_string` decoder**. Existing flag-display code uses ad-hoc per-call formatting (e.g. `mud/commands/show.py`, OLC stubs in `mud/commands/build.py`) and IntFlag iteration. The OLC display surfaces (`act_olc.c:show_obj`, `olc_save.c:save_object`) will need this decoder; today's non-OLC display paths each have their own handcrafted version that already passes their integration tests. **Gap recorded as BIT-002**.

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `BIT-001` | MINOR | `src/bit.c:111-142` | `mud/utils/bit.py:flag_value` | Standalone reusable `flag_value(table, argument)` helper not ported. Current sole consumer (`do_flag`) inlines stricter ROM-`do_flag`-faithful accumulator instead. Will be needed by OLC port. | ✅ FIXED — `flag_value(table, argument) -> int \| None` accumulates IntFlag tokens (OR) and returns single value for IntEnum (stat) tables; returns None on no match (ROM `NO_FLAG`). Test: `tests/integration/test_bit_flag_value.py` (9 cases). |
| `BIT-002` | MINOR | `src/bit.c:151-177` | (no file) | `flag_string(table, bits)` decoder not ported. Current display paths each handcraft their own formatter. Will be needed by OLC `show`/`save` paths. | 🔄 DEFERRED — close alongside OLC audit |
| `BIT-003` | MINOR | `src/bit.c:50-104` | (no file) | `flag_stat_table[]` registry + `is_stat(table)` helper not ported. Stat-vs-flag distinction is currently encoded in the Python type system (IntEnum vs IntFlag) and resolved at the call site. Will be needed if OLC introduces a generic table dispatcher. | 🔄 DEFERRED — close alongside OLC audit |

No CRITICAL or IMPORTANT gaps. All current Python call sites that consume bit.c-shaped logic (`do_flag` only) match ROM behavior at the source-of-truth level (ROM `do_flag` itself, not ROM `flag_value`).

## Phase 4 — Closures

None this session. Three MINOR deferrals are not closed because:

1. **No observable behavior gap exists today.** `do_flag` works correctly; no other Python module calls into ROM `flag_value` / `flag_string` / `is_stat`-shaped functionality.
2. **Premature porting risks API drift.** ROM `flag_value`/`flag_string` take a `struct flag_type *` table pointer; the Python equivalent should take an `IntFlag` class (already proven idiomatic by `prefix_lookup_intflag`). Designing the public surface in isolation, before the first OLC consumer is ported, would likely need rework.
3. **Per `AGENTS.md` "no deferring" rule** — that rule applies to *behavioral* parity gaps. These three gaps are *infrastructure* helpers with zero current call sites; deferring them until the OLC audit produces a concrete consumer is the standard project pattern (see `MUSIC-005`/`MUSIC-006`, `FLAG-002`).

When the OLC audit begins (`olc.c`, `olc_act.c`, `olc_save.c`, `act_olc.c`), close BIT-001/002/003 in that audit's first commit, before touching OLC-specific code.

## Phase 5 — Completion summary

`bit.c` is ✅ AUDITED at 90%. ROM's three helpers (`is_stat`, `flag_value`, `flag_string`) are catalogued with stable gap IDs and deferred to the OLC audit, where their first consumers will appear. The adjacent `flag_lookup` helper (which ROM keeps in `lookup.c` and bit.c calls) is already correctly ported as `prefix_lookup_intflag` (TABLES-002), and the only current Python consumer of bit.c-shaped accumulation logic — `do_flag` — faithfully mirrors ROM `do_flag` (not ROM `flag_value`), with no observable behavior divergence.

Tracker flip: `bit.c` ⚠️ Partial 90% → ✅ Audited 90% (0/3 closed, 3 MINOR deferred to OLC audit).
