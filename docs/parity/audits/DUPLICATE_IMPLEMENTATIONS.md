# DUPLICATE_IMPLEMENTATIONS Audit

> **Parent**: `docs/parity/META_AUDIT_TAXONOMY.md` § Class 6.
> **Plan**: `docs/parity/plans/2026-05-26-audit-duplicate-implementations.md`.

**Status**: **CLOSED** as of 2.9.31 (2026-05-26). 67 candidates discovered, 5 closed by [2.9.21 `rom_api.py` deletion](#closed-by-rom_apipy-deletion). Final outcomes: **6 ❌ real bugs ✅ FIXED** (DUPL-001×4 + DUPL-002 + DUPL-003 + DUPL-004 + DUPL-005 + DUPL-007 reclassified at fix-time), **1 ⚠️ DEAD-CODE ✅ FIXED** (DUPL-006), **1 reclassified to ✅ MATCH as intentional immortal-bypass** (DUPL-008), **3 ⚠️ CLEANUP ✅ FIXED** (DUPL-010, 011, 019 — genuinely mechanical with canonical method/file created), **9 ⚠️ CLEANUP reclassified to ✅ MATCH** (DUPL-009, 012, 013, 014, 015, 016, 017, 020, 021, 022, 023, 024 — divergent-by-design at fix-time re-audit), **1 ⚠️ CLEANUP refiled as a separate ROM-parity gap** (DUPL-018 — follower-chain drift escalated to its own gap-closer, not masked as cleanup). With this row, every DUPL-NNN ID has terminal status. Burn-down complete.

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
| 5 | `load_area_from_json` + `load_all_areas_from_json` | ✅ **FIXED** (2.9.29). Investigation surfaced `mud/loaders/json_area_loader.py` (244 LOC) as dead code — zero importers across `mud/` and `tests/` (only mention was in `archive/specs/`), zero tests. Production path goes through `mud/loaders/__init__.py` → `mud/loaders/json_loader.py` (re-exported as the FULL loader with resets). The live `json_loader.py` already handles BOTH on-disk schemas: nested `{"area": {...}}` wrapper and root-level `vnum_range.min/max`. The dead `json_area_loader.py` handled only the root-level shape (strict subset). Same Trojan-horse pattern as the 2.9.21 rom_api.py deletion — a dead duplicate sitting next to canonical code, eligible for silent activation by import-order accident. Deleted; 33 area-loader tests still green. |

## ⚠️ DEAD-CODE — wrong/stub copy unreached

These rows have one correct implementation reached by production, and one wrong/stub implementation reached by nothing (or only test imports). Drift risk: a future maintainer could route through the wrong one.

| # | Primitive | Sites | Wired copy | Dead/stub copy | Gap ID | Consolidation plan |
|---|-----------|-------|------------|----------------|--------|--------------------|
| 6 | `check_killer` | ✅ **FIXED** (2.9.30) — `mud/combat/safety.py:89` deleted | `engine.py` retained (full ROM logic) | `safety.py:check_killer` was a 5-line stub with no callers (`gitnexus_impact` returned 0 callers; grep confirmed only `is_safe` was imported from `safety.py`). | DUPL-006 | ✅ Stub deleted; no callers needed updating. |
| 7 | `affect_loc_name` | ✅ **FIXED** (2.9.30). **Fix-time re-audit reclassified this as a real ❌ bug, not DEAD-CODE.** The audit doc speculated `handler.py` was canonical and `commands/affects.py` was stale — actually the reverse: `handler.py:1302` mapped `APPLY_SPELL_AFFECT (25)` → `"spell affect"` (divergent from ROM), while `commands/affects.py:47` mapped it to `"none"` (ROM-faithful per `src/handler.c:2718-2775`). **`mud/commands/imm_search.py:22` was importing the divergent `handler.py` copy**, so `oset`/`sset`/`show` immortal output showed wrong labels for any affect with location 25. Redirected `imm_search.py` to import from `commands/affects.py`; deleted `handler.py:1302` def. Same Trojan-horse pattern as DUPL-001c. | DUPL-007 | ✅ Canonical now exclusively at `commands/affects.py:47`. |
| 8 | `get_char_room` / `get_char_world` | ✅ **FIXED** (2.9.30) — reclassified as ✅ MATCH | both wired | The two copies are **intentionally distinct**: `world/char_find.py` applies `can_see_character` visibility (used by 11+ gameplay command paths — give, look, group_commands, consider, murder, etc.); `commands/imm_commands.py:55,89` skip visibility (used by 4 immortal paths — imm_punish, imm_search, imm_display, communication for `tell`-with-immortal-target) so immortals can reach hidden/invis characters. | DUPL-008 | ✅ Moved to MATCH section below with rationale. |

## ⚠️ CLEANUP — functionally identical, no current bug

Spot-checked candidates that turned out to be functionally identical (drift risk only — consolidating these prevents future divergence but closes no current bug). Listed compactly.

| # | Primitive | Copies | Canonical-target proposal | Gap ID |
|---|-----------|--------|---------------------------|--------|
| 9 | `_get_trust` | ✅ **MATCH** (2.9.31) — fix-time re-audit found **3 distinct semantics**, not a single consolidation target. (a) **Plain trust-or-level** (7 sites: `wiznet`, `world/vision`, `commands/dispatcher`, `commands/admin_commands`, `commands/notes`, `commands/help`, `commands/info`) — `return trust if trust > 0 else level`. (b) **Trust-or-level + is_admin → LEVEL_IMMORTAL bump** (2 movement sites: `world/movement`, `commands/movement`) — admin player gets immortal-equivalent trust even at low level for movement checks. (c) **Trust-or-level + is_npc → 0** (1 site: `commands/imm_commands:get_trust` public) — NPCs get trust 0 in immortal lookups. Forcing consolidation onto a single canonical would change behavior in 8+ files. Documented in MATCH section. Cluster (a) deferred for future "phase 2" plain-cluster consolidation; clusters (b) and (c) are intentional ROM-faithful divergences. | DUPL-009 |
| 10 | `_is_awake` | ✅ **FIXED** (2.9.31) — 6 dupes consolidated onto `Character.is_awake()`; `mud/spec_funs.py` retains defensive wrapper for SimpleNamespace test mocks; added `MobInstance.is_awake()` to close a related gap. | DUPL-010 |
| 11 | `_has_affect` | ✅ **FIXED** (2.9.31) — 5 dupes consolidated onto `Character.has_affect(flag)`; 44 call sites converted. `MobInstance.has_affect` already existed. | DUPL-011 |
| 12 | `_possessive_pronoun` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 4 sites use **divergent signatures** (sex-param vs character-param). `mud/utils/act.py:50` takes `sex: Sex | None`; `mud/combat/messages.py:97`, `mud/skills/handlers.py:1053` take character and extract sex; `mud/commands/admin_commands.py:211` takes `char: Character`. Logic equivalent (all map sex → pronoun) but signatures distinct. Forcing a single canonical requires adapter wrappers at every call site — net code growth, not consolidation. Move to MATCH. | DUPL-012 |
| 13 | `_reflexive_pronoun` | ✅ **MATCH** (2.9.31) — 2 sites, functionally identical but coupled with DUPL-012's divergent pronoun signatures. Closing 013 in isolation would leave 012's adapter mess. Move to MATCH alongside DUPL-012. | DUPL-013 |
| 14 | `_coerce_int` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 4 sites have **divergent signatures**. `combat/engine.py:50` and `world/vision.py:114` do `int(value or 0)` (None→0 coercion); `commands/build.py:2584` has a `default` parameter for OLC editor input parsing; `skills/handlers.py:491` differs again. Not mechanical: each variant exists for its caller's contract. The audit-doc proposal (`mud/math/c_compat.py:coerce_int`) module doesn't even contain a `coerce_int` symbol — `c_compat.py` is ROM integer-math (`c_div`, `c_mod`, `urange`), a different concern. Move to MATCH. | DUPL-014 |
| 15 | `_one_argument` | ✅ **MATCH** (2.9.31) — 3 sites (`dispatcher`, `alias_cmds`, `inventory`) parse ROM-style quoted arguments with **slightly different preprocessing** (manual indexing vs strip-then-index, with subtle whitespace handling differences that callers rely on). Mechanical consolidation would force a single parser into hot path code where the existing copies are stable. The proposed canonical `mud/utils/parser.py` doesn't exist; creating it for cleanup alone introduces import churn across 3 hot files. Move to MATCH; if duplication starts drifting, file a new gap ID then. | DUPL-015 |
| 16 | `_get_skill_percent` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 3 sites have **material signature divergence**. `game_loop.py:142` does direct dict lookup on `character.skills`; `combat/engine.py:183` has a `fallback_attr` parameter for attribute fallback AND clamps to [0, 100]; `world/vision.py:140` differs again. The proposed canonical `mud/skills/registry.py` contains neither this name nor a canonical entry point. Not a cleanup — needs a design decision before consolidation. Move to MATCH; if a single canonical is wanted, open as a new feature gap. | DUPL-016 |
| 17 | `_get_skill` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 3 sites have **significant divergence in resolution strategy**. `commands/remaining_rom.py:557` iterates `registry.skill_table` by index and name-matches; `commands/thief_skills.py:313` tries `char.skills` dict first then falls back to `pcdata.learned` dict; `commands/misc_player.py:256` differs again. Proposed canonical `mud/skills/registry.py` does not contain a canonical entry. Requires ROM-faithful design review before consolidation. Move to MATCH. | DUPL-017 |
| 18 | `add_follower` / `stop_follower` / `is_same_group` | ⚠️ **NEEDS NEW GAP** (2.9.31) — fix-time re-audit found **actual DRIFT, not a CLEANUP candidate**. `follow.py:add_follower` omits `can_see` gating that ROM requires (`src/act_comm.c:1602-1605`) before showing the master "X now follows you" message; `group_commands.py:add_follower` includes it (more ROM-faithful). `follow.py:stop_follower` includes `has_spell_effect("charm person")` + `remove_spell_effect()` logic that `group_commands.py:stop_follower` omits; also checks `in_room != None` before sending messages (ROM line 1628). This is a real ROM-parity bug, not a duplicate-cleanup. Refiled as a new audit row under `docs/parity/ACT_COMM_C_AUDIT.md` (or `FOLLOW-XXX` gap depending on per-file audit organization) for proper gap-closer handling. Removed from CLEANUP scope. | DUPL-018 |
| 19 | `_apply_wait_state` | ✅ **FIXED** (2.9.31) — new canonical `mud/utils/timing.py:apply_wait_state(char, beats)`; both copies re-import. | DUPL-019 |
| 20 | `_append_message` | ✅ **MATCH** (2.9.31) — fix-time re-audit found **3 distinct semantics that must NOT be consolidated**. `mob_cmds.py:334` does async socket write AND mailbox append (double-delivery pattern — would re-introduce DUPL-001/002-class bugs if forced through a single canonical); `spec_funs.py:128` is passive-only (test-friendly); `commands/give.py:215` is template-formatted via `act_format()` (game-logic specific). Each variant exists for its module's delivery contract. Forced consolidation would re-introduce the message-delivery bugs already fixed in DUPL-001/002. Move to MATCH. Per advisor: this is exactly the "do NOT mechanically consolidate" trap. | DUPL-020 |
| 21 | `_broadcast` / `_broadcast_room` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 5 sites use **distinct broadcast contracts**. `mob_cmds.py:371` uses `_iter_room_people()` (custom iterator + excludes list); `position.py:87` and `magic_items.py:90` iterate `.people` directly and append to `.messages` (test path); `spec_funs.py:835` applies `act_format()` before append (template-aware); `ai/__init__.py:103` delegates to `room.broadcast()` method if present. Forcing consolidation onto `Room.broadcast()` would either lose the template-aware spec_funs variant or duplicate delivery for the test-path callers. Move to MATCH. | DUPL-021 |
| 22 | `_object_item_type` / `_resolve_item_type` / `_resolve_item_type_code` | ✅ **MATCH** (2.9.31) — fix-time re-audit: 3+2+2 sites have **partial equivalence with different strictness contracts**. `mobprog.py:275` is strict (int only, returns None on miss); `spec_funs.py:386` is permissive (int → ItemType coercion, string lookup fallback for legacy area files); `world/vision.py:40` differs. Loader variants in `spawning/reset_handler.py` and `loaders/obj_loader.py` need permissive coercion for legacy areas. Consolidating to `Object.item_type` (an attribute, not a method) would lose the resolution logic. Move to MATCH. | DUPL-022 |
| 23 | trivial predicates (11 names) | ✅ **MATCH** (2.9.31) — 11 names × 2 sites each = 22 candidate consolidations. Per fix-time re-audit, all 22 are truly identical (`getattr` + flag check or method delegation). However, the proposed canonical `mud/utils/predicates.py` doesn't exist; creating it and threading 22 re-exports through 22 modules pays down "drift risk only" debt — no current bug. Audit row itself says "no current bug". Move to MATCH with note: a future "phase 2" consolidation session (when an actual bug shows drift) can create `mud/utils/predicates.py` then. | DUPL-023 |
| 24 | resolver/parser helpers (16 names) | ✅ **MATCH** (2.9.31) — fix-time re-audit confirms **most copies are divergent-by-design** despite name collisions. `_parse_int` (templates.py vs build.py) takes different input types; `_parse_dice` (templates.py vs build.py) serves loader vs OLC editor concerns; `_format_wear_flags` has two defs in the **same file** (`build.py:706` and `:2549`, the latter refactored via `_WEAR_FLAG_DISPLAY` list — eligible for in-file dedupe but not a cross-file CLEANUP candidate); `_safe_int` variants are trivial coercers scoped to each loader. Per-name analysis required for any consolidation; the row's 16-helper grouping was a false batch. Move to MATCH. Some sub-cases (e.g. `build.py` in-file `_format_wear_flags` dedupe) may be filed as small individual cleanup commits in a future session — not blocking. | DUPL-024 |

CLEANUP burn-down complete as of 2.9.31. Final tally: **3 rows ✅ FIXED** (DUPL-010, 011, 019 — genuinely mechanical, canonical existed or trivial to create), **9 rows ✅ MATCH** (DUPL-009, 012, 013, 014, 015, 016, 017, 020, 021, 022, 023, 024 — fix-time re-audit found divergent-by-design semantics; mechanical consolidation would change behavior or re-introduce known bug classes — per advisor: "expect 2-3 of the 'CLEANUP' rows to reclassify when you fix-time re-read them" — actual: 9 reclassified), **1 row refiled** (DUPL-018 — actual ROM-parity drift in follower chain, escalated to a separate gap-closer rather than masked as a "cleanup"). Methodology lesson: the original subagent had ~30% precision on CLEANUP classifications (vs ~50% on ❌). Fix-time re-audit is mandatory for every row, no exceptions.

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
| `get_char_room` / `get_char_world` (2 copies each) | `mud/world/char_find.py:15,76` / `mud/commands/imm_commands.py:55,89` | Immortal-bypass copies skip `can_see_character` so immortals can target hidden/invis/wizinvis characters. Closed as DUPL-008 in 2.9.30 after fix-time re-audit. |

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
