# Session Summary — 2026-05-28 — Equipment-key canonicalization (INV-028 followup) + convention guards (2.9.87)

## Scope

Picked up from the INV-028 light-slot session (2.9.86), whose top-listed
followup was the broader `Character.equipment` key-type inconsistency: live
`int` keys vs reloaded `str` keys for *every* slot, not just LIGHT. The probe
revealed the problem was deeper than int-vs-str-of-int — `Character.equip_object`
stored arbitrary **string** slot names (`"wield"`, `"light"`, `"body"`,
`"float"`) while `do_wear` stored `int(WearLocation.X)`, and readers were split
across both conventions. ROM keys equipment by the integer wear slot
(`src/handler.c:1733 get_eq_char(ch, int iWear)` loops `obj->wear_loc == iWear`;
`merc.h` `WEAR_LIGHT 0` … `WEAR_FLOAT 18`) — there are **no** string slot names
in ROM, and AGENTS.md already mandated the IntEnum key, so this fixed drift from
an existing rule. The session converged all paths on `int(WearLocation.X)`,
then added grep-guards + pre-commit hooks so the drift cannot recur, plus
adjacent rule-doc hygiene surfaced by the same investigation.

GitNexus was unavailable all session (read-only index DB —
`Cannot execute write operations`; reindex itself fails). Impact analysis used
grep + the full test suite per the CLAUDE.md documented fallback. The full suite
caught 30 string-key test failures AND, critically, 3 production readers that
the initial grep + first-draft guard had missed (different variable name /
getattr chain) — which then drove strengthening the guard.

## Outcomes

### Equipment-key canonicalization — ✅ CLOSED (2.9.87; INV-028 followup)

- **ROM C**: `src/handler.c:1733 get_eq_char(ch, int iWear)`, `:1781 equip_char`
  set/read `obj->wear_loc` as an integer; `merc.h:1337-1356` WEAR_* are ints.
- **Python contract**: `Character.equipment` is keyed strictly by
  `int(WearLocation.X)`. New `mud.models.constants.canonical_wear_slot(slot)`
  (int/IntEnum, numeric str, or legacy name → int; `ValueError` otherwise)
  applied at every **write** site; every **reader** uses the int key.
- **Two real bugs fixed** (hidden by the inconsistency):
  - `give_school_outfit` equipped the lit war banner (vnum 3716, `item_type
    light`, `value[2]=200`) under the string `"light"`; `Room._has_lit_light_source`
    only read `int(WearLocation.LIGHT)` → every newbie's starting light was
    uncounted in room lighting.
  - A shield worn via `do_wear` (int key 11) was invisible to
    `engine._has_shield_equipped`, which read the string `"shield"`.
  - **Latent**: `commands/compare.py:_find_equipped_match` read the non-existent
    `char.equipped` attribute (AGENTS.md anti-pattern) → always `{}` → compare
    vs a worn weapon silently never matched. Fixed to `char.equipment` + int key.
- **Write sites**: `models/character.py:equip_object` + `from_orm` equipment
  restore; `db/serializers.py:_slot_to_wear_loc` (now int-tolerant).
- **Readers fixed**: `combat/engine.py` (wield + shield), `commands/inventory.py:
  give_school_outfit`, `skills/handlers.py` (floating-disc + `portal`/`nexus`
  HOLD warp-stone lookup), `combat/death.py:_is_floating_slot`,
  `commands/compare.py`.
- **Shims removed**: the INV-028 per-reader LIGHT tolerance (`room.py` str-`"0"`
  fallback, `game_loop.py` `"light"`-name match). `Character.equipment` retyped
  `dict[int, Object]`.
- **Tests**: `tests/integration/test_equip_key_canonical.py` (3 cases:
  school-light counted; do_wear shield seen by combat check; do_wear→save→load
  yields int LIGHT key not str `"0"`) — all 3 verified failing pre-fix. 15
  existing test files updated for int keys (one alias-slot test rewritten —
  `"float"`/`"floating"` deliberately collapse to one slot, matching ROM's
  single WEAR_FLOAT).

### Convention guards + rule hygiene — ✅ (2.9.87)

- `tests/test_equipment_key_convention.py` — grep-guard banning string-keyed
  equipment access in `mud/` (mirrors `test_rng_determinism.py`). Strengthened
  after the suite exposed escapes: a second pattern matches distinctive
  wear-slot names (`wield`, `hold`, `float`, `shield`, …) on **any** variable,
  catching `equipped.get("wield")` and `getattr(…,"equipment",{}).get("hold")`.
- `tests/test_attribute_convention.py` — grep-guard banning the AGENTS.md
  anti-pattern attribute names `.carrying` / `.characters` / `.equipped`.
- `.pre-commit-config.yaml` — local hooks for both guards (commit-time, not just
  CI; matches the existing `lint_test_fixtures.py` precedent).
- AGENTS.md "Equipment lookup" rule rewritten (int-key contract +
  `canonical_wear_slot` write-path); "Integer math" rule corrected to require
  `c_div`/`c_mod` only when an operand **can be negative** (the old blanket
  "never `//`/`%`" contradicted ~30 legitimate non-negative uses and is not
  grep-enforceable).
- `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` — filed `CLEANUP-001` (~41
  hardcoded hex flag literals → enum refs; per-site `merc.h` verification;
  non-blocking).
- `CLAUDE.md` — added a "META — MAINTAINING THIS DOCUMENT" section (when to add
  a rule, how to write it, when to escalate a rule to a tooling hook).

## Files Modified

- `mud/models/constants.py` — `WEAR_SLOT_BY_NAME` + `canonical_wear_slot`.
- `mud/models/character.py` — `equip_object` + `from_orm` restore canonicalize; `equipment: dict[int, Object]`.
- `mud/combat/engine.py` — wield + shield readers use int key.
- `mud/combat/death.py` — `_is_floating_slot` int slot.
- `mud/commands/inventory.py` — `give_school_outfit` int keys.
- `mud/commands/compare.py` — `char.equipped`→`char.equipment` + int keys (latent bug).
- `mud/skills/handlers.py` — floating-disc + portal/nexus HOLD readers int key.
- `mud/models/room.py`, `mud/game_loop.py` — INV-028 LIGHT shims removed.
- `mud/db/serializers.py` — `_slot_to_wear_loc` int-tolerant.
- `tests/integration/test_equip_key_canonical.py` — new (3 cases).
- `tests/test_equipment_key_convention.py`, `tests/test_attribute_convention.py` — new guards.
- 15 existing test files — int-key migration.
- `.pre-commit-config.yaml` — 2 convention hooks.
- `AGENTS.md` — equipment + integer-math rules. `CLAUDE.md` — meta-rules.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-028 followup marked CLOSED.
- `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` — CLEANUP-001.
- `CHANGELOG.md` — 2.9.87. `pyproject.toml` — 2.9.86 → 2.9.87.

## Test Status

- New: `test_equip_key_canonical.py` 3/3; `test_equipment_key_convention.py` 1/1; `test_attribute_convention.py` 1/1.
- The 12 previously-failing files re-run: 212 passed.
- **Full suite: 4894 passed, 4 skipped, 0 failed** (512s).
- `ruff check` on changed/new files clean (pre-existing B007/F841/E402/B010/I001 in serializers/death/handlers/inventory confirmed pre-existing via stash baseline).

## Next Steps

1. **Push approval** — 3 commits ahead of `origin/master` (3f3570d6 fix,
   70f0d87d chore, b1f6d791 docs), shipping 2.9.87. Not pushed. (Prior
   session's 2.9.80–2.9.86 appear already on origin — `git rev-list
   origin/master..HEAD` == 3.)
2. **`CLEANUP-001`** — migrate the ~41 hardcoded hex flag literals to enum refs
   (per-site `merc.h` verification), file-by-file.
3. **`_wear_all` light handling** (carried over from 2.9.86) — `wear all` won't
   equip a light; ROM's `wear all` → `wear_obj` → WEAR_LIGHT would.
4. **ARITH triage remaining (7 ❌ MISSING)**: ARITH-004, 017/018/019, 114,
   206/207, 208 (see prior summaries).
5. **GitNexus read-only DB** — `gitnexus_impact`/`detect_changes`/reindex
   unavailable; fix DB perms/lock outside the session.
6. **Pre-existing flake** `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
