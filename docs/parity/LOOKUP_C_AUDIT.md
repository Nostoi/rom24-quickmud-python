# `lookup.c` ROM Parity Audit

- **Status**: Phase 3 — gap identification complete; LOOKUP-001 closure landing this session
- **Date**: 2026-04-28
- **Source**: `src/lookup.c` (ROM 2.4b6, 184 lines, 10 public functions)
- **Python primary**: scattered across `mud/models/races.py`, `mud/models/clans.py`, `mud/loaders/obj_loader.py`, `mud/commands/remaining_rom.py`

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Python counterpart | Status |
|------------|-----------|--------------------|--------|
| `flag_lookup` | 39-51 | `mud/commands/remaining_rom.py:_lookup_flag_bit` | ⚠️ PARTIAL — exact-match instead of `str_prefix`. See LOOKUP-002. |
| `clan_lookup` | 53-65 | `mud/models/clans.py:lookup_clan_id` (or similar) | ⚠️ PARTIAL — exact-match. See LOOKUP-003 (deferred). |
| `position_lookup` | 67-79 | none found | ❌ MISSING — no Python equivalent. See LOOKUP-004 (deferred). |
| `sex_lookup` | 81-93 | none found | ❌ MISSING. See LOOKUP-005 (deferred). |
| `size_lookup` | 95-107 | none found | ❌ MISSING. See LOOKUP-006 (deferred). |
| `race_lookup` | 110-122 | `mud/models/races.py:get_race` (closest, but exact-match). `mud/persistence.py:614` imports a non-existent `race_lookup`. | ❌ BROKEN — see LOOKUP-001 (this session). |
| `item_lookup` | 124-136 | none found (item-type names parsed inline in loaders) | ❌ MISSING. See LOOKUP-007 (deferred). |
| `liq_lookup` | 138-150 | `mud/loaders/obj_loader.py:_liq_lookup` (private) | ⚠️ PARTIAL — see LOOKUP-008 (deferred). |
| `help_lookup` | 152-172 | `mud/help.py` (lookup likely exists) | ❓ UNVERIFIED — out of scope for this session. |
| `had_lookup` | 174-184 | help-area lookup, see help system | ❓ UNVERIFIED — out of scope for this session. |

## Phase 2 — Verification

### Common pattern across `flag_lookup` / `clan_lookup` / `position_lookup` / `sex_lookup` / `size_lookup` / `race_lookup` / `item_lookup` / `liq_lookup`

ROM 39-150 share an identical loop pattern:

```c
for (i = 0; <table>[i].name != NULL; i++) {
    if (LOWER(name[0]) == LOWER(<table>[i].name[0])
        && !str_prefix(name, <table>[i].name))
        return <result>;
}
return <not-found>;
```

`str_prefix(short, full)` returns 0 when `short` is a (case-insensitive) prefix of `full`. So `race_lookup("hu")` matches `"human"`, `class_lookup("war")` matches `"warrior"`, and so on. This abbreviation-tolerant matching is pervasive throughout ROM — character creation prompts, OLC commands, mob_prog conditions, and the `flag` immortal command all rely on it.

QuickMUD's Python equivalents (where they exist) use **exact-match dict lookups** (`_RACES_BY_NAME.get(name.lower())`), which silently rejects abbreviations. ROM users expecting to type `class war` to match `warrior` get an error message instead.

### `race_lookup` specifically (ROM 110-122)

ROM returns an `int` race index, defaulting to `0` (= "human") on no-match. The Python `get_race(name)` returns `RaceType | None` via exact-match dict.

**Critical**: `mud/persistence.py:614` does `from mud.models.races import race_lookup` and calls `race_lookup(snapshot.race)` to restore a pet's race on load. The function name **does not exist** in `mud/models/races.py` — the import is broken. This is a latent runtime `ImportError` that would fire any time pet persistence loads a non-None race snapshot.

The path is reachable via the pet save/load flow (added recently per `save.c:do_save` parity). Anyone with a pet that has a race set will trip this on next login. Severity: CRITICAL (visible breakage on a normal user flow).

### `_lookup_flag_bit` (FLAGS_C_AUDIT.md FLAG-001 from earlier this session)

The freshly-shipped `mud/commands/remaining_rom.py:_lookup_flag_bit` uses exact-match (`member.name.upper() == upper`) instead of ROM's `str_prefix`. This means `flag char Bob plr +holy` fails to match `HOLYLIGHT`. ROM accepts the abbreviation. Recorded as LOOKUP-002 (deferred).

## Phase 3 — Gaps

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| `LOOKUP-001` | CRITICAL | `src/lookup.c:110-122` | `mud/models/races.py:race_lookup` (new), called by `mud/persistence.py:614` | Pet load crashes with `ImportError` on any pet whose snapshot has a non-None race. ROM `race_lookup(name)` returns the int race index (prefix-match, default 0). | ✅ FIXED — added `race_lookup(name: str | None) -> int` to `mud/models/races.py` with ROM-faithful case-insensitive prefix-match and fall-through `return 0`. Test: `tests/integration/test_lookup_parity.py` (6 tests). |
| `LOOKUP-002` | IMPORTANT | `src/lookup.c:39-51` | `mud/commands/remaining_rom.py:_lookup_flag_bit` | `_lookup_flag_bit` uses exact-match instead of ROM `str_prefix` (prefix-match). `flag char Bob plr +holy` rejects the abbreviation that ROM accepts. | ✅ FIXED — `_lookup_flag_bit` now delegates to new `mud/utils/prefix_lookup.py:prefix_lookup_intflag`. Test: `tests/integration/test_flag_command_parity.py::test_flag_prefix_match_accepts_abbreviation`. |
| `LOOKUP-003` | IMPORTANT | `src/lookup.c:53-65` | `mud/models/clans.py:lookup_clan_id` | Clan name lookup uses exact-match instead of prefix-match. | ✅ FIXED — `lookup_clan_id` now uses `startswith` against `CLAN_TABLE` names mirroring ROM `str_prefix`. Test: `tests/integration/test_lookup_parity.py::test_clan_lookup_prefix_match`. |
| `LOOKUP-004` | IMPORTANT | `src/lookup.c:67-79` | none | No `position_lookup` equivalent. Used by OLC for setting position by name. | 🔄 OPEN — deferred. |
| `LOOKUP-005` | IMPORTANT | `src/lookup.c:81-93` | none | No `sex_lookup` equivalent. Used by character creation and OLC. | 🔄 OPEN — deferred. |
| `LOOKUP-006` | IMPORTANT | `src/lookup.c:95-107` | none | No `size_lookup` equivalent. Used by OLC. | 🔄 OPEN — deferred. |
| `LOOKUP-007` | IMPORTANT | `src/lookup.c:124-136` | none | No `item_lookup` equivalent. Used by OLC for setting item type by name. | 🔄 OPEN — deferred. |
| `LOOKUP-008` | MINOR | `src/lookup.c:138-150` | `mud/loaders/obj_loader.py:_liq_lookup` | Private liquid lookup uses exact-match instead of prefix-match. | 🔄 OPEN — deferred. |

## Phase 4 — Closures

### `LOOKUP-001` — ✅ FIXED

- **ROM C**: `src/lookup.c:110-122` (`race_lookup`).
- **Python**: new `mud/models/races.py:race_lookup`. Called by `mud/persistence.py:614` in the pet-restore path.
- **Test**: `tests/integration/test_lookup_parity.py` — 6 tests covering symbol existence, exact-name match, prefix-match abbreviation, case-insensitivity, unknown-name fall-through to 0, and the persistence-import smoke test.

## Phase 5 — Completion summary

(Filled in once all OPEN gaps closed.)

## Notes for future sessions

- LOOKUP-002..008 are all variations of the same problem (ROM `str_prefix` not honored). A future session can land them as one cohesive change by introducing a shared `prefix_lookup(name, table)` helper and migrating each callsite.
- `help_lookup` and `had_lookup` (ROM 152-184) work on the help system data structures. Their audit belongs with a `help.c` / help-data audit, not here.
