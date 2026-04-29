# `flags.c` ROM Parity Audit

- **Status**: ✅ AUDITED — FLAG-001 closed; FLAG-002 (settable-bit preservation) deferred as MINOR follow-up
- **Date**: 2026-04-28
- **Source**: `src/flags.c` (ROM 2.4b6, 251 lines, 1 public function: `do_flag`)
- **Python primary**: `mud/commands/remaining_rom.py:do_flag`

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Python counterpart | Status |
|------------|-----------|--------------------|--------|
| `do_flag` | 44-251 | `mud/commands/remaining_rom.py:do_flag` (line 316) | ⚠️ STUB — see FLAG-001 |

## Phase 2 — Verification

### `do_flag` (ROM 44-251)

ROM `do_flag` is the immortal command for inspecting and toggling flag bits on a character or mobile. Its behavior:

1. Parse `arg1=mob|char`, `arg2=name`, `arg3=field`, then peek at the leading byte of remaining `argument`. If it is `=`, `+`, or `-`, consume that operator token (`=`, `+`, or `-`) into `word`. Otherwise the operator is implicit toggle.
2. Resolve `arg2` via `get_char_world` (cross-area name lookup). Error: `You can't find them.`
3. Reject NPC fields on PCs and vice-versa with strict guards: `act`/`form`/`parts` are NPC-only; `plr`/`comm` are PC-only.
4. Map `arg3` to `(flag *, flag_table)`:
   - `act` → `victim->act`, `act_flags` (NPCs only)
   - `plr` → `victim->act`, `plr_flags` (PCs only)
   - `aff` → `victim->affected_by`, `affect_flags`
   - `immunity` → `victim->imm_flags`, `imm_flags`
   - `resist` → `victim->res_flags`, `imm_flags`
   - `vuln` → `victim->vuln_flags`, `imm_flags`
   - `form` → `victim->form`, `form_flags` (NPCs only)
   - `parts` → `victim->parts`, `part_flags` (NPCs only)
   - `comm` → `victim->comm`, `comm_flags` (PCs only)
5. Tokenize remaining flag names. For each, `flag_lookup` against the resolved table; bail on first unknown name with `That flag doesn't exist!`. Successful matches accumulate in a `marked` bitmask.
6. Build `new` = `(type == '=') ? 0 : old`. Walk `flag_table[]`: any non-`settable` bit that was set in `old` is forced into `new` (preserves system flags); any bit set in `marked` is then `=|+`SET, `-`REMOVE, or toggled (default).
7. Assign `*flag = new`.

ROM also exposes `arg3 == "off"` in the syntax help text (line 68) but the dispatcher at lines 105-187 has no `off` branch — submitting `off` falls through to `That's not an acceptable flag.` We preserve this ROM quirk.

### Python `do_flag` (`mud/commands/remaining_rom.py:316-361`)

The Python entry point is a **stub**:

- Validates that `args` exists and has 4 tokens.
- Resolves `victim` via `get_char_world`.
- Rejects `act` on PCs and `plr` on NPCs.
- Returns the placeholder string `f"Flag '{flags}' toggled on {field} for {victim_name}."`

It does **not** parse operators (`=`/`+`/`-`/toggle), does **not** look up flag names in any table, does **not** mutate any bit on the victim, and does **not** validate field names beyond `act`/`plr`. Any immortal who runs `flag char Bob plr +holylight` sees a confirmation message but Bob's flags are unchanged.

This is one cohesive gap (the entire mutation pipeline is missing), recorded as **FLAG-001**.

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `FLAG-001` | CRITICAL | `src/flags.c:44-251` | `mud/commands/remaining_rom.py:do_flag` | `do_flag` is a syntax-validator stub; no operator parsing, no flag-table lookup, no bit mutation. The command silently lies — it confirms a change that never happens. | ✅ FIXED — full operator parsing (`=`/`+`/`-`/toggle), 9-field dispatcher, IntFlag-based name lookup, and bit mutation wired through. NPC/PC field guards mirror ROM 105-187. Tests: `tests/integration/test_flag_command_parity.py` 9/9 passing. |
| `FLAG-002` | MINOR | `src/flags.c:220-227` | `mud/commands/remaining_rom.py:do_flag` | Non-`settable` bits in ROM `flag_type` tables are preserved across the `=` operator (`act_flags` marks `IS_NPC`, `IS_AFFECTED` etc. as `settable=FALSE`). Python IntFlag carries no per-bit settable metadata, so `=` clears these structural bits. | 🔄 OPEN — deferred. Requires per-flag-table settable mask (~30 bits across act/plr/aff/imm/comm/form/parts). Low risk: only triggered when an immortal explicitly uses `=` on a mob's act field. |

## Phase 4 — Closures

### `FLAG-001` — ✅ FIXED

- **ROM C**: `src/flags.c:44-251` (`do_flag` full body).
- **Python**: `mud/commands/remaining_rom.py:do_flag` + new `_FLAG_FIELDS` dispatch table + `_lookup_flag_bit` helper.
- **Test**: `tests/integration/test_flag_command_parity.py` (9 tests covering add/remove/toggle/set, aff/immunity/comm field routing, unknown-field and unknown-flag error paths).

## Phase 5 — Completion summary

flags.c is ✅ AUDITED. The single P0 gap (FLAG-001) is closed: `do_flag` is now a fully-wired immortal command that parses operators, looks up flag names against the matching IntFlag enum, and mutates the victim's flag field. NPC/PC guards mirror ROM exactly. The minor FLAG-002 (preserve non-`settable` bits across `=`) is documented and deferred — it requires per-bit metadata not yet present in the Python flag enums and only affects a narrow `=` use-case on NPC fields.

