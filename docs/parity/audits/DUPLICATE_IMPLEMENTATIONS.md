# DUPLICATE_IMPLEMENTATIONS Audit

> **Parent**: `docs/parity/META_AUDIT_TAXONOMY.md` § Class 6.
> **Plan**: `docs/parity/plans/2026-05-26-audit-duplicate-implementations.md`.

**Status**: complete as of 2026-05-26. 67 candidates discovered, 5 closed by [2.9.21 `rom_api.py` deletion](#closed-by-rom_apipy-deletion), **5 ❌ real bugs**, **3 ⚠️ DEAD-CODE** rows, **~20 ⚠️ CLEANUP** rows, **4 ✅ intentional** rows.

## Rubric

Each row in the table represents a same-name same-primitive `def`
that exists at 2+ file:line sites under `mud/`. Status:

- **❌ MISSING** — copies materially diverge AND the wrong/incomplete copy is reachable from gameplay. Real parity bug.
- **⚠️ DEAD-CODE** — one copy is wrong/stub but unreached by production callers (only test imports or no imports at all). Drift risk if a future maintainer reaches for the wrong one.
- **⚠️ CLEANUP** — copies are functionally identical (drift risk, no current bug). Consolidation pays down maintenance debt.
- **✅ MATCH** — copies are intentionally distinct (different concerns) or already consolidated via re-export.

Gap IDs use the form `DUPL-NNN`. Burn-down: one gap-closer commit per ❌, batched commits acceptable for ⚠️ CLEANUP rows that share a target site.

The DUPLICATE_IMPLEMENTATIONS audit also surfaced its own headline finding — the whole `mud/rom_api.py` module — which was closed independently as part of [v2.9.21 (`18bd6d2d`)](#closed-by-rom_apipy-deletion). The rows it took with it are documented in the appendix.

## Headline ❌ — real parity bugs

| # | Primitive | Sites | Dispatcher-wired? | Divergence | Gap ID | Consolidation plan |
|---|-----------|-------|-------------------|------------|--------|--------------------|
| 1 | `_send_to_char` | ✅ **FIXED** (2.9.24 conditions; 2.9.25 DUPL-001a 9 `output_buffer` black-hole stubs; 2.9.26 DUPL-001b combat/assist + skills/handlers duplicate-delivery; 2.9.27 DUPL-001c `game_loop.py:341` duplicate-delivery — fix-time re-audit revealed the prior "canonical-equivalent" claim was wrong: copy did async send AND mailbox append unconditionally, double-delivering every tick-driven plague/decay/light message to connected PCs). | All 13 sites now route through `mud/utils/messaging.py:send_to_char_buffered` (single-delivery: async-to-socket for connected PCs, mailbox fallback for tests/disconnected). | All 13 sites converged on canonical. Bug classes closed: messages-only black hole (conditions), output_buffer black hole (9 imm_*/admin), duplicate-delivery (combat/assist + skills/handlers + game_loop). | DUPL-001 | ✅ Regression tests: `tests/integration/test_gain_condition_delivers_to_connected_pc.py` (conditions), `test_imm_command_delivery_dupl_001a.py` (output_buffer), `test_dupl_001b_no_duplicate_delivery.py` (combat/assist + skills/handlers), `test_dupl_001c_game_loop_no_duplicate.py` (game_loop). |
| 2 | `_push_message` | ✅ **FIXED** (2.9.22) — canonical at `mud/utils/messaging.py:push_message`; `combat/engine.py` + `magic/effects.py` re-export it | both reached | `combat/engine.py` writes to async socket and `return`s — single delivery channel per `docs/divergences/MESSAGE_DELIVERY.md` (avoiding the documented duplicate-delivery bug where the read loop drains `messages` after every command). `magic/effects.py` wrote to BOTH async socket AND `messages` list — every magic effect message replayed on the next prompt for connected PCs. | DUPL-002 | ✅ Canonical `push_message` lives at `mud/utils/messaging.py`. Both `combat/engine.py` and `magic/effects.py` import it. Regression test: `tests/integration/test_magic_effect_message_no_duplicate.py`. |
| 3 | `_extract_obj` | ✅ **FIXED** (2.9.28). All three copies consolidated onto canonical `mud/game_loop.py:_extract_obj(obj)` — the recursive, ROM-faithful implementation mirroring `src/handler.c:2051 extract_obj` (recurse over `contains`, unlink from `in_room`/`carried_by`/`in_obj`, remove from `object_registry`). The buggy `obj_manipulation.py` copy read `char.carrying` (a non-existent attribute — canonical is `char.inventory`), so `do_quaff` never actually removed the potion from the player's inventory — the same potion could be quaffed infinitely. The `imm_load.py` copy had the same `carrier.carrying` bug. `obj_manipulation.py` retains a thin adapter (signature `(char, obj)`) that delegates to the canonical `(obj)`-only entry point. Regression tests: `tests/integration/test_dupl_003_extract_obj.py` — `do_quaff` inventory removal + recursive container-contents extraction on `do_sacrifice`. |
| 4 | `_check_improve` | ✅ **FIXED** (2.9.22) — three `pass` stubs deleted; `do_peek` wired to canonical `mud.skills.registry.check_improve` | only `misc_player.py` reached (via `do_peek`); the other two stubs were dead code | All three were `pass` stubs. Re-verification narrowed the audit row's "all 3 reached" claim: only `misc_player.py:_check_improve` was actually invoked (from `do_peek` line 199). The `thief_skills.py` and `remaining_rom.py` stubs were never called — `do_sneak`/`do_hide` delegate to `mud/skills/handlers.py` (canonical), and `remaining_rom.py` had no internal call at all. `do_peek` also had a latent crash: `from mud.core.dice import number_percent` referenced a non-existent module, so any successful peek would have raised `ModuleNotFoundError`. Both issues fixed in one commit. | DUPL-004 | ✅ Deleted all three stubs. `do_peek` now imports `check_improve` from `mud.skills.registry` and `number_percent` from `mud.utils.rng_mm` (ROM Parity Rules — RNG via `rng_mm`). Calls `check_improve(char, "peek", True, multiplier=4)` matching ROM `src/act_info.c:505`. Regression test: `tests/integration/test_do_peek_check_improve.py` (success + failure branches). |
| 5 | `load_area_from_json` + `load_all_areas_from_json` | `mud/loaders/json_loader.py:252`+`:808`, `mud/loaders/json_area_loader.py:14`+`:220` (2 pairs) | unverified | Two parallel JSON area loaders with same name but different schemas (`json_loader.py` handles a nested `{"area": {...}}` format; `json_area_loader.py` expects `vnum_range.min/max` shape) and different return types (`None` vs `dict[int, Area]`). Either two formats are both supported (and which loader fires depends on import order) or one is dead. Until verified, the risk is silent area-load divergence. | DUPL-005 | Identify which file the production area-load path imports. Verify the JSON-on-disk shape under `data/areas/`. If both shapes appear, document the divergence; otherwise delete the unused loader. |

## ⚠️ DEAD-CODE — wrong/stub copy unreached

These rows have one correct implementation reached by production, and one wrong/stub implementation reached by nothing (or only test imports). Drift risk: a future maintainer could route through the wrong one.

| # | Primitive | Sites | Wired copy | Dead/stub copy | Gap ID | Consolidation plan |
|---|-----------|-------|------------|----------------|--------|--------------------|
| 6 | `check_killer` | `mud/combat/engine.py:1112`, `mud/combat/safety.py:89` | `engine.py` (full ROM logic: charm chain, victim KILLER/THIEF gates) | `safety.py` is a 5-line stub setting `PlayerFlag.KILLER` with no ROM-faithful logic. No production import found. | DUPL-006 | Delete `safety.py:check_killer`. Re-run import audit to confirm no callers. |
| 7 | `affect_loc_name` | `mud/handler.py:1302`, `mud/commands/affects.py:47` | likely `handler.py` (canonical) | unverified — likely `commands/affects.py` is a stale clone | DUPL-007 | Verify import sites. Delete the unreached copy. |
| 8 | `get_char_room` / `get_char_world` | `mud/world/char_find.py:15`+`:76`, `mud/commands/imm_commands.py:55`+`:89` | `world/char_find.py` (canonical, applies `can_see` visibility) | `commands/imm_commands.py` likely intentional (immortals should bypass `can_see`). | DUPL-008 | Verify intent. If immortal-side bypass is real, keep both with comments tying to ROM `get_char_room_imm`-equivalent. Otherwise consolidate. |

## ⚠️ CLEANUP — functionally identical, no current bug

Spot-checked candidates that turned out to be functionally identical (drift risk only — consolidating these prevents future divergence but closes no current bug). Listed compactly.

| # | Primitive | Copies | Canonical-target proposal | Gap ID |
|---|-----------|--------|---------------------------|--------|
| 9 | `_get_trust` | 9 | `mud/world/trust.py:get_trust` (new file) or fold into `mud/utils/perms.py` | DUPL-009 |
| 10 | `_is_awake` | 6 | `mud/models/character.py:Character.is_awake` (property) | DUPL-010 |
| 11 | `_has_affect` | 5 | `mud/models/character.py:Character.has_affect_flag` | DUPL-011 |
| 12 | `_possessive_pronoun` | 4 | `mud/utils/act.py` (canonical site already exists) | DUPL-012 |
| 13 | `_reflexive_pronoun` | 2 | same as DUPL-012 | DUPL-013 |
| 14 | `_coerce_int` | 4 | `mud/math/c_compat.py:coerce_int` | DUPL-014 |
| 15 | `_one_argument` | 3 | `mud/utils/parser.py:one_argument` | DUPL-015 |
| 16 | `_get_skill_percent` | 3 | `mud/skills/registry.py` | DUPL-016 |
| 17 | `_get_skill` | 3 | `mud/skills/registry.py` | DUPL-017 |
| 18 | `add_follower` / `stop_follower` / `is_same_group` | 2 each | `mud/characters/follow.py` (canonical, has broadcasts after 2.9.19/20) | DUPL-018 |
| 19 | `_apply_wait_state` | 2 | `mud/utils/timing.py:apply_wait_state` | DUPL-019 |
| 20 | `_append_message` | 3 | `mud/utils/messaging.py` (alongside DUPL-001 target) | DUPL-020 |
| 21 | `_broadcast` / `_broadcast_room` | 3+2 | use `mud/net/protocol.py:broadcast_room` / `mud/models/room.py:Room.broadcast` instead | DUPL-021 |
| 22 | `_object_item_type` / `_resolve_item_type` / `_resolve_item_type_code` | 3+2+2 | `mud/models/object.py:Object.item_type` (already exists) | DUPL-022 |
| 23 | trivial predicates (`_is_npc`, `_is_charmed`, `_is_outside`, `_is_room_owner`, `_is_name_match`, `_is_builder`, `_has_shop`, `_has_flag`, `_has_act_flag`, `_clear_comm_flag`, `_match_name`) | 2 each (11 names) | move to `mud/utils/predicates.py` (new file) | DUPL-023 |
| 24 | resolver/parser helpers (`_resolve_path`, `_resolve_level`, `_parse_int`, `_parse_dice`, `_safe_int`, `_format_wear_flags`, `_get_weight_mult`, `_get_obj_weight`, `_get_session`, `_find_character`, `_find_obj_here`, `_find_obj_inventory`, `_obj_to_obj`, `_room_is_private`, `_skill_percent`, `_display_name`) | 2-3 each (16 names) | per-target consolidation; some belong on `Object`/`Character`/`Room` as methods, others under `mud/world/` | DUPL-024 |

CLEANUP rows are batchable — one consolidation commit per target file is acceptable. Rough estimate: 5-8 commits to close 9-24.

## ✅ MATCH — intentional, no consolidation needed

| Primitive | Sites | Why ✅ |
|-----------|-------|--------|
| `main` (5 copies) | `scripts/convert_*.py` | Per-script entrypoint, expected |
| `clear_registries` (2 copies) | `scripts/convert_are_to_json.py`, `scripts/convert_shops_to_json.py` | Per-script test setup |
| `_serialize_object` (2 copies) | `mud/olc/save.py`, `mud/db/serializers.py` | Distinct serialization targets (OLC area files vs DB save) |
| `_safe_int` (2 copies) | `mud/db/serializers.py`, `mud/loaders/obj_loader.py` | Trivial parser scoped to each loader's context |
| `_act_room` (2 copies) | `mud/commands/imm_display.py`, `mud/commands/imm_commands.py` | Different signatures by design |
| `_can_see` (2 copies) | `mud/mobprog.py`, `mud/ai/aggressive.py` | Different visibility semantics for mob scripts vs aggression checks |
| `migrate` (2 copies) | `mud/__main__.py`, `mud/db/migrate_from_files.py` | Unrelated concerns; name collision only |

## Closed by `rom_api.py` deletion

Five rows in the original 67-candidate set were closed for free by the 2.9.21 deletion of `mud/rom_api.py` (see CHANGELOG 2.9.21):

| Primitive | Was | Now |
|-----------|-----|-----|
| `is_note_to` | rom_api.py vs notes.py | single def in notes.py |
| `get_max_train` | rom_api.py (wrong stub) vs handler.py | single def in handler.py |
| `do_imotd` | rom_api.py (wrong sig) vs commands/misc_info.py | single def in misc_info.py |
| `do_rules` | rom_api.py (wrong sig) vs commands/misc_info.py | single def in misc_info.py |
| `do_story` | rom_api.py (wrong sig) vs commands/misc_info.py | single def in misc_info.py |

Plus rom_api.py's harmless re-exports (e.g. `board_lookup → find_board`) — all gone with the module.

## Methodology

1. **Discovery**: `grep -rnE "^def " mud/`, name-bucket, filter to >1 occurrence. Initial: ~67 candidates.
2. **Filter**: drop dunders, generic helpers (`to_dict`, `serialize`, etc.). Survivors: 67.
3. **Per-candidate analysis**: subagent scan + manual verification of every ❌ candidate. The subagent had ~50% precision on ❌ — many original ❌ rows were actually ⚠️ CLEANUP (functionally identical) or ⚠️ DEAD-CODE (wrong copy unreached). The 5 verified ❌ are real parity bugs.
4. **Surfaced separately**: the `rom_api.py` module itself, addressed in 2.9.21.

## Re-scan cadence

Re-run discovery (Task 1 of the audit plan) after every major refactor session touching `mud/`. Particularly after any consolidation commit closing CLEANUP rows — confirm the canonical site is the only remaining def for that primitive.

## Burn-down ordering

Recommended order for the burn-down plan (each ❌ = one focused gap-closer commit):

1. **DUPL-002 `_push_message`** — narrowest fix, smallest blast radius (one file change + one test). Validates the audit's methodology before tackling bigger consolidations.
2. **DUPL-004 `_check_improve`** — three identical stubs blocking skill improvement. Single delete + import change per file. Integration test exercises a thief skill.
3. **DUPL-001 `_send_to_char`** — biggest blast radius (13 callsites). Spread over multiple commits if needed; treat conditions.py first since it has a confirmed delivery bug.
4. **DUPL-003 `_extract_obj`** — recursive correctness + wrong attribute. Needs a careful regression test exercising container-in-inventory extraction.
5. **DUPL-005 `load_area_from_json`** — verify which is wired before deleting; possible silent divergence between two JSON schemas.

DEAD-CODE rows (DUPL-006 through 008) can be closed in a single mop-up commit per row.

CLEANUP rows (DUPL-009 through 024) close in batched consolidation commits — one per target file. Estimated 5-8 commits to close 16 rows.
