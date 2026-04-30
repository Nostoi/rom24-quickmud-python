# OLC_SAVE_C_AUDIT.md — `src/olc_save.c` (1136 lines, 17 functions)

**Status**: ⚠️ Partial — Phase 1–3 complete (audit doc + gap IDs filed); Phase 4–5 pending closures
**Date**: 2026-04-29
**Audited by**: Opus 4.7 inline (per session brief — Sonnet subagents have terminated mid-investigation in this codebase across three prior sessions)
**Sibling audits**: OLC_C_AUDIT.md (⚠️ Partial), OLC_ACT_C_AUDIT.md (⚠️ Partial — TIER A/B closed)

---

## Architectural framing — locked

ROM `olc_save.c` is the `.are` text-format writer. QuickMUD Python writes
**JSON** instead via `mud/olc/save.py` (`save_area_to_json`), keeping `.are`
as a read-only legacy input format (handled in `mud/loaders/area_loader.py`).

This is an **architectural divergence by design**, not a parity gap. The
audit treats JSON as the canonical write format and verifies:

1. **Field coverage** — does the JSON output persist every field that
   `save_area`/`save_mobile`/`save_object`/`save_rooms` writes? Anything that
   round-trips through ROM `.are` save+load must round-trip through Python
   JSON save+load.
2. **`do_asave` / `cmd_asave` subcommand parity** — the entry-point command
   surface (numeric-vnum, `world`, `changed`, `list`, `area`) must accept the
   same inputs and respect the same security gates.
3. **Section presence** — resets, shops, specials, mobprogs, helps must all
   be persisted; these are commonly missing in JSON ports.

What the audit explicitly does **NOT** treat as a gap:

- ROM `fwrite_flag` A–Za–z bit-letter encoding — N/A; JSON stores ints.
- ROM `fix_string` `\r`/`~` strip — N/A; JSON encodes natively.
- Byte-level `.are` formatting (column widths, trailing newlines, `#0` /
  `#$` markers, `S\n\n\n\n` section terminators) — N/A; JSON has its own grammar.
- ROM verbose-comment annotations on resets (`Load %s`, `loaded to %s`) — N/A;
  not consumed by the JSON loader, only debugging aids in `.are`.

---

## Summary

`src/olc_save.c` exposes 17 public functions across three layers: the per-record
serializers (`save_mobile`, `save_object`, `save_rooms`, …), the section
wrappers (`save_mobiles`, `save_objects`, …), the area-level orchestrator
(`save_area`), and the command entry point (`do_asave`). Python's
`mud/olc/save.py` (293 lines) covers ~25% of the field surface — most fields
on `save_mobile`/`save_object` are silently dropped on JSON write, which means
**round-tripping a mob/obj proto through OLC save+reload erases shop, spec_fun,
mprogs, off/imm/res/vuln flags, form, parts, size, level, item-type-specific
value layouts, and ROM-style affect chains**. The gap surface is thus broad
but mostly mechanical: each missing field is one closure.

Tier breakdown: **TIER A** (line-by-line P0/P1) — 7 functions · **TIER B**
(moderate P1) — 5 functions · **TIER C** (helpers / wrappers / N/A) — 5
functions.

**Key finding (CRITICAL)**: a saved-then-reloaded JSON area will lose mob
shop bindings, mob spec_fun bindings, mob mprog lists, mob defensive flag
sets (off/imm/res/vuln), mob form/parts/size/material, object level, object
item-type-specific value layouts, object affect chains, and helps. This is a
data-loss bug in the OLC pipeline, not just a cosmetic divergence — anyone
running `oedit … done` followed by `asave <vnum>` followed by a reboot will
find the prototype reverted to a degraded state.

---

## Phase 1 — Function Inventory

> Legend: ✅ AUDITED · ⚠️ PARTIAL · ❌ MISSING · 🔄 NEEDS DEEP AUDIT · N/A

| ROM Symbol | ROM Lines | Python Counterpart | Tier | Status |
|---|---|---|---|---|
| `fix_string` | 50–67 | — | C | N/A — JSON encodes `\r`/`~` natively |
| `save_area_list` | 76–110 | `save_area_list` (mud/olc/save.py:273) | B | ⚠️ PARTIAL — missing `social.are` prepend, missing HELP_AREA filenames; sorts by vnum (ROM uses `area_first` linked list — equivalent under dict insertion order) |
| `fwrite_flag` | 122–149 | — | C | N/A — JSON stores ints |
| `save_mobprogs` | 151–169 | — (no Python counterpart) | B | ❌ MISSING — `_serialize_mobile` does not persist mprog list |
| `save_mobile` | 176–253 | `_serialize_mobile` (mud/olc/save.py:136) | A | ⚠️ PARTIAL — many fields missing (off/imm/res/vuln flags, form, parts, size, material, mprog list, race-DIF logic) |
| `save_mobiles` | 262–277 | inline in `save_area_to_json` (mud/olc/save.py:219) | C | ✅ AUDITED — section wrapper; iterates per-area registry |
| `save_object` | 289–438 | `_serialize_object` (mud/olc/save.py:171) | A | ⚠️ PARTIAL — missing `level`, item-type-specific value layouts (DRINK_CON/CONTAINER/WEAPON/POTION/PILL/SCROLL/STAFF/WAND), structured affect serialization (TO_OBJECT vs TO_AFFECTS/IMMUNE/RESIST/VULN), structured extra_descr serialization, condition letter encoding |
| `save_objects` | 449–464 | inline in `save_area_to_json` (mud/olc/save.py:225) | C | ✅ AUDITED — section wrapper |
| `save_rooms` | 475–569 | `_serialize_room` (mud/olc/save.py:72) | A | ⚠️ PARTIAL — Python writes raw `exit_info` int; ROM derives `locks` (0..4) from EX_ISDOOR/PICKPROOF/NOPASS combinations and writes that. JSON-authoritative framing means raw int round-trips correctly, so this is a documented divergence not a behavioral gap. Missing: any ROM-reset propagation of `EX_ISDOOR` based on lock-bit bundle (ROM lines 511–522). |
| `save_specials` | 578–606 | — (no Python counterpart) | B | ❌ MISSING — `_serialize_mobile` does not persist `spec_fun` |
| `save_door_resets` | 616–658 | — (transitively via `_serialize_reset`) | C | ⚠️ PARTIAL — Python persists raw reset list; ROM emits synthetic D-resets for closed/locked exits. JSON-authoritative framing covers this if loader rehydrates door state from exit flags. |
| `save_resets` | 668–777 | `_serialize_reset` (mud/olc/save.py:62) | A | ⚠️ PARTIAL — Python emits generic command/arg1..4 dump; ROM emits per-command structured rows (M/O/P/G/E/D/R) with verbose annotations. JSON-authoritative framing accepts the dump form, but missing fields beyond arg1..arg4 (none in ROM) — verify. |
| `save_shops` | 786–824 | — (no Python counterpart) | A | ❌ MISSING — `_serialize_mobile` does not persist `MobShop` data (keeper, buy_type[5], profit_buy/sell, open_hour/close_hour) |
| `save_helps` | 826–843 | — (no Python counterpart) | B | ❌ MISSING — no help-write path; `mud/models/help.py` is read-only via loader |
| `save_other_helps` | 845–872 | — | C | ❌ MISSING — depends on `save_helps` |
| `save_area` | 879–914 | `save_area_to_json` (mud/olc/save.py:196) | A | ⚠️ PARTIAL — orchestrator-level; missing sections: specials, shops, mobprogs, helps. AREADATA section covered (name, builders, vnum range, credits, security). |
| `do_asave` | 922–1136 | `cmd_asave` (mud/commands/build.py:1370) | A | ⚠️ PARTIAL — all 5 subcommands wired (numeric vnum, world, changed, list, area), but message strings drift from ROM, `area` branch only covers `redit` (ROM covers AEDIT/REDIT/OEDIT/MEDIT/HELP), no autosave path (ROM `if (!ch) sec = 9`), no NPC/security gate matching ROM line 933 |

---

## Phase 2 — Function-by-function verification (TIER A only)

### `save_mobile` (ROM 176–253) vs `_serialize_mobile` (mud/olc/save.py:136)

ROM writes 38 fields per mob. Python persists 21. **Missing or misnamed**:

| ROM field | ROM line | Python status |
|---|---|---|
| `off_flags` | 205 | ❌ Missing |
| `imm_flags` | 206 | ❌ Missing |
| `res_flags` | 207 | ❌ Missing |
| `vuln_flags` | 208 | ❌ Missing |
| `form` | 213 | ❌ Missing |
| `parts` | 214 | ❌ Missing |
| `size` | 216 | ❌ Missing |
| `material` | 217–219 | ❌ Missing |
| `mprogs` (list of MPROG_LIST) | 245–250 | ❌ Missing — no field |
| race-DIF deltas (act/aff/off/imm/res/vuln/form/parts) | 221–243 | ❌ Missing — Python writes absolute values, no race-relative override (acceptable under JSON framing if loader applies race defaults first) |
| `hit_dice`/`mana_dice`/`damage_dice` | 194–199 | ⚠️ Stored as strings; ROM stores 3 ints/dice (DICE_NUMBER/TYPE/BONUS). Same OLC_ACT-010b sub-gap. |
| `ac` (4 columns / 10) | 201–204 | ⚠️ Stored as `"1d1+0"` string; ROM stores 4 ints. Sub-gap of OLC_ACT-010b. |

### `save_object` (ROM 289–438) vs `_serialize_object` (mud/olc/save.py:171)

| ROM field | ROM line | Python status |
|---|---|---|
| `level` | 378 | ❌ Missing — `_serialize_object` does not emit |
| item-type-specific value layout (DRINK_CON/CONTAINER/WEAPON/POTION/PILL/SCROLL/STAFF/WAND) | 311–376 | ⚠️ Python writes `values: [int]*5` raw; ROM writes liquid-name / skill-name / weapon-name / attack-name strings for human readability. Under JSON framing, raw ints round-trip correctly — N/A. |
| condition letter (P/G/A/W/D/B/R from condition int) | 382–397 | ⚠️ Python passes raw `condition` string through; ROM derives the letter from a `condition > N` ladder. JSON-authoritative framing accepts either; verify loader handles both. |
| affect chain — TO_OBJECT applies (`A\n%d %d`) vs TO_AFFECTS/IMMUNE/RESIST/VULN (`F\n[AIRV] %d %d %s`) | 399–429 | ❌ `_serialize_object` does `list(...affects, [])` — raw pass-through, no structured serialization, no `where`/`location`/`modifier`/`bitvector` tuple emit |
| extra_descr (keyword + description tilde-terminated) | 431–435 | ❌ Same — `list(...extra_descr, [])` raw pass-through; no per-extra `_serialize_extra_descr` call (helper exists, just unused here) |

### `save_rooms` (ROM 475–569) vs `_serialize_room` (mud/olc/save.py:72)

| ROM field | ROM line | Python status |
|---|---|---|
| Per-exit `locks` field (0..4 derived from ISDOOR/PICKPROOF/NOPASS) | 507–541 | ⚠️ Python emits raw `exit_info` int as `flags`. Round-trips under JSON. |
| Per-exit `EX_ISDOOR` propagation based on lock-flag bundle | 511–522 | ⚠️ Python does not run this normalization on save. Equivalent only if loader sets ISDOOR consistently. |
| `M %d H %d\n` only when mana_rate≠100 or heal_rate≠100 | 551–555 | ✅ Python conditional on lines 100–106 |
| `C %s~\n` clan only when clan>0 | 556–558 | ✅ Python conditional on line 108–110 |
| `O %s~\n` owner when non-null | 560–561 | ✅ Python conditional on line 112–114 |

### `save_resets` (ROM 668–777) vs `_serialize_reset` (mud/olc/save.py:62)

ROM writes per-reset-command structured rows with capitalized object names and
mob short-descrs as inline annotations. Python writes flat
`{command, arg1..arg4}` dicts. Under JSON framing, the loader needs only the
structured fields (which Python persists). **Missing**: `D` resets are
recorded in Python's resets list (per OLC-022 closures) but ROM
`save_door_resets` synthesizes additional D-resets from closed/locked exits
(ROM lines 616–658). If JSON loader does the synthesis, this is N/A;
otherwise gap. **Verify.**

### `save_area` (ROM 879–914) vs `save_area_to_json` (mud/olc/save.py:196)

ROM emits these sections in order: AREADATA → MOBILES → OBJECTS → ROOMS →
SPECIALS → RESETS → SHOPS → MOBPROGS → HELPS → `#$`. Python emits AREADATA
fields + rooms + mobiles + objects only. **Missing sections**: SPECIALS,
SHOPS, MOBPROGS, HELPS. RESETS are persisted inside each room (Python
`room["resets"]`) which is structurally equivalent to ROM's per-room walk
inside the RESETS section.

### `do_asave` (ROM 922–1136) vs `cmd_asave` (mud/commands/build.py:1370)

| ROM behavior | ROM line | Python status |
|---|---|---|
| Autosave path: `if (!ch) sec = 9` | 931–936 | ❌ `cmd_asave` requires `char` non-null — no autosave entry |
| `IS_NPC(ch) → sec = 0` security gate | 933 | ❌ Not modeled; `_is_builder` may handle this transitively — verify |
| Numeric vnum branch: silent on success (no message) | 982–995 | ⚠️ Python returns `f"Area {area.name} (vnum {area.vnum}) saved."` — ROM is silent |
| `world` branch: ROM "You saved the world.\n\r" | 1013 | ⚠️ Python returns `f"You saved the world. ({saved_count} areas)"` — appended count |
| `world` branch: `REMOVE_BIT(AREA_CHANGED)` per area | 1009 | ✅ `save_area_to_json` clears `area.changed = False` |
| `changed` branch: ROM "Saved zones:\n\r" header + per-area row + "None.\n\r" fallback | 1029–1064 | ⚠️ Python: "Saved zones:\n…" header ✓, per-area row ✓, but on empty list returns "No changed areas to save." instead of "None." |
| `area` branch: dispatch on editor type (AREA/ROOM/OBJECT/MOBILE/HELP) | 1094–1115 | ❌ Only `redit` editor wired; aedit/oedit/medit/hedit not covered |
| `area` branch success: ROM "Area saved.\n\r" | 1126 | ⚠️ Python `f"Area {area.name} saved."` — name appended |
| `area` branch ED_HELP: "Grabando area : " + save_other_helps | 1108–1110 | ❌ Untranslated Spanish string in ROM; no Python equivalent |

---

## Phase 3 — Gaps

| Gap ID | Severity | ROM C ref | Python ref | Description | Status |
|---|---|---|---|---|---|
| OLC_SAVE-001 | CRITICAL | src/olc_save.c:205-208 | `_serialize_mobile` (save.py:136) | Mob `off_flags`/`imm_flags`/`res_flags`/`vuln_flags` not persisted. Round-trip OLC save+reload erases mob defensive/offensive flag sets. | ✅ FIXED — `_serialize_mobile` now emits `offensive`/`immune`/`resist`/`vuln` letter-strings; round-trip locked by `tests/integration/test_olc_save_001_mob_defensive_flags.py` |
| OLC_SAVE-002 | CRITICAL | src/olc_save.c:213-219 | `_serialize_mobile` (save.py:136) | Mob `form`/`parts`/`size`/`material` not persisted. | ✅ FIXED — `_serialize_mobile` now emits all four as strings; locked by `tests/integration/test_olc_save_002_mob_form_parts_size_material.py` |
| OLC_SAVE-003 | CRITICAL | src/olc_save.c:245-250 + 151-169 | `_serialize_mobile` (save.py:136) + `save_area_to_json` | Mob `mprogs` (MPROG_LIST per mob + #MOBPROGS section per area) not persisted. Round-trip erases mob progs entirely. | ✅ FIXED — `save_area_to_json` now emits structured `mob_programs` list grouped by program vnum (one entry per program, multiple assignments allowed); locked by `tests/integration/test_olc_save_003_mob_mprogs.py` |
| OLC_SAVE-004 | CRITICAL | src/olc_save.c:786-824 | `_serialize_mobile` (save.py:136) + `save_area_to_json` | Mob `pShop` (keeper, buy_type[5], profit_buy/sell, open_hour/close_hour) not persisted. Round-trip erases shop bindings. | ✅ FIXED — `save_area_to_json` now emits a top-level `shops` list via new `_collect_shops` helper; paired loader-side `_load_shops_from_json` rehydrates `shop_registry` and re-attaches `MobIndex.pShop`. Locked by `tests/integration/test_olc_save_004_mob_shops.py` |
| OLC_SAVE-005 | CRITICAL | src/olc_save.c:578-606 | `_serialize_mobile` (save.py:136) + `save_area_to_json` | Mob `spec_fun` not persisted. Round-trip erases spec_fun bindings. | ✅ FIXED — `save_area_to_json` now emits a top-level `specials` list via new `_collect_specials` helper; loader-side `apply_specials_from_json` was already present. Locked by `tests/integration/test_olc_save_005_mob_spec_fun.py` |
| OLC_SAVE-006 | CRITICAL | src/olc_save.c:378 | `_serialize_object` (save.py:171) | Object `level` not persisted. Round-trip resets all object levels to 0/default. | ✅ FIXED — `_serialize_object` now emits `level`; paired loader change in `_load_objects_from_json` reads it back. Locked by `tests/integration/test_olc_save_006_object_level.py` |
| OLC_SAVE-007 | CRITICAL | src/olc_save.c:399-429 | `_serialize_object` (save.py:171) | Object affect chain serialized as raw `list(...affects, [])` — opaque pass-through, not structured (`where`/`location`/`modifier`/`bitvector`). On JSON reload, affects become unparseable. | ✅ FIXED — `_serialize_object` now routes affects through new `_serialize_affect` helper that normalizes dict-or-`Affect`-dataclass into json-safe dicts (preserves A-line `location`/`modifier`, F-line `where`/`bitvector`). Locked by `tests/integration/test_olc_save_007_object_affects.py` (5 cases). |
| OLC_SAVE-008 | CRITICAL | src/olc_save.c:431-435 | `_serialize_object` (save.py:171) | Object extra_descr list serialized as raw pass-through, not via `_serialize_extra_descr` helper. On JSON reload, extra-descs become unparseable. | ✅ FIXED — `_serialize_object` now routes extra-descrs through the existing `_serialize_extra_descr` helper (now dict-aware so it handles both dict and `ExtraDescr` dataclass inputs). Locked by `tests/integration/test_olc_save_008_object_extra_descr.py` (3 cases). |
| OLC_SAVE-009 | IMPORTANT | src/olc_save.c:826-872 | — | No Python help-save path. ROM `save_helps`/`save_other_helps` not ported. | 🔄 OPEN |
| OLC_SAVE-010 | IMPORTANT | src/olc_save.c:1094-1115 | `cmd_asave` "area" branch (build.py:1441) | `cmd_asave area` only handles `redit` editor; ROM dispatches on AREA/ROOM/OBJECT/MOBILE/HELP editors via `ch->desc->editor`. Aedit/oedit/medit/hedit users get a confusing error. | ✅ FIXED — dispatcher now branches on `session.editor` across aedit / redit / oedit / medit / hedit, resolving area from `editor_state["area"]` / `room.area` / `obj_proto.area` / `mob_proto.area`; hedit returns ROM-faithful "Grabando area :" prefix pending OLC_SAVE-009 help-save port. Locked by `tests/integration/test_olc_save_010_asave_area_dispatch.py` (6 cases). |
| OLC_SAVE-011 | IMPORTANT | src/olc_save.c:931-936 | `cmd_asave` (build.py:1370) | No autosave entry: ROM `if (!ch) sec = 9` allows the autosave timer to call `do_asave(NULL, "world")`; Python `cmd_asave` requires non-null `char`. Blocks future autosave wiring. | ✅ FIXED — `cmd_asave(char: Character \| None, args)` now accepts `char=None` for the autosave timer; "world" branch skips the IS_BUILDER gate when ch is None and returns silently (mirrors ROM `if (ch) send_to_char`). Other null-ch arg paths short-circuit before any char-attribute access. Locked by `tests/integration/test_olc_save_011_autosave_entry.py` (3 cases). |
| OLC_SAVE-012 | IMPORTANT | src/olc_save.c:933 | `cmd_asave` (build.py:1370) | NPC security gate (ROM `IS_NPC(ch) → sec = 0`, then `IS_BUILDER` returns FALSE) not explicitly modeled. Verify `_is_builder` enforces equivalent behavior; if not, NPCs (e.g. mob_special calling cmd_asave) bypass security. | 🔄 OPEN |
| OLC_SAVE-013 | IMPORTANT | src/olc_save.c:94-99 | `save_area_list` (save.py:273) | `save_area_list` missing `social.are` prepend and HELP_AREA filename rows. ROM emits both above the area list; Python emits area filenames only. | 🔄 OPEN |
| OLC_SAVE-014 | MINOR | src/olc_save.c:982-995 | `cmd_asave` numeric branch (build.py:1385) | ROM numeric-vnum branch is silent on success; Python returns `"Area X (vnum N) saved."`. String drift. | 🔄 OPEN |
| OLC_SAVE-015 | MINOR | src/olc_save.c:1013 | `cmd_asave` "world" branch (build.py:1403) | ROM "world" success: `"You saved the world.\n\r"`. Python: `"You saved the world. (N areas)"`. Appended count drifts from ROM. | 🔄 OPEN |
| OLC_SAVE-016 | MINOR | src/olc_save.c:1059-1064 | `cmd_asave` "changed" branch (build.py:1414) | ROM "changed" empty case: `"None.\n\r"`. Python: `"No changed areas to save."`. String drift. | 🔄 OPEN |
| OLC_SAVE-017 | MINOR | src/olc_save.c:1126 | `cmd_asave` "area" branch (build.py:1463) | ROM "area" success: `"Area saved.\n\r"`. Python: `f"Area {area.name} saved."`. Appended name drifts. | 🔄 OPEN |
| OLC_SAVE-018 | MINOR | src/olc_save.c:382-397 | `_serialize_object` (save.py:189) | Object `condition` ladder (P/G/A/W/D/B/R from int) not normalized on save. JSON-authoritative framing accepts raw int OR letter; verify loader. Documented divergence. | 🔄 OPEN |
| OLC_SAVE-019 | MINOR | src/olc_save.c:475-569 | `_serialize_room` (save.py:72) | ROM derives per-exit `locks` (0..4) from EX_ISDOOR/PICKPROOF/NOPASS combinations and propagates EX_ISDOOR back into `rs_flags` on save. Python emits raw `exit_info` int — round-trips under JSON, but if save→reboot→reload sequence depends on the ISDOOR normalization side effect, behavior diverges. Document and verify. | 🔄 OPEN |
| OLC_SAVE-020 | MINOR | src/olc_save.c:616-658 | — | ROM `save_door_resets` synthesizes D-resets from closed/locked exits at save time; Python relies on `room.resets` already containing them. Verify reset persistence path captures door states. | 🔄 OPEN |

---

## Phase 4 — Closures

None this session. See Phase 3 gap table; closures handed off to
`rom-gap-closer` per-gap.

**Recommended closure order** (by data-loss severity → cosmetic):

1. **Round-trip data loss block** (CRITICAL — close first, all together):
   OLC_SAVE-001 → OLC_SAVE-002 → OLC_SAVE-003 → OLC_SAVE-004 → OLC_SAVE-005 →
   OLC_SAVE-006 → OLC_SAVE-007 → OLC_SAVE-008. Each closure adds one missing
   field/section to JSON serialization + one round-trip integration test
   (load .are → save JSON → load JSON → assert proto equals original).
2. **Help save** (IMPORTANT): OLC_SAVE-009 — port `save_helps` to JSON.
3. **Dispatcher coverage** (IMPORTANT): OLC_SAVE-010 → OLC_SAVE-011 →
   OLC_SAVE-012 — full `cmd_asave area` editor coverage, autosave entry,
   NPC gate.
4. **`save_area_list` polish** (IMPORTANT): OLC_SAVE-013 — `social.are` +
   HELP_AREA prepend.
5. **Message string drift** (MINOR): OLC_SAVE-014..017 — one commit per
   string fix, rom-gap-closer per gap.
6. **JSON-equivalence-documented divergences** (MINOR): OLC_SAVE-018 →
   OLC_SAVE-019 → OLC_SAVE-020 — verify loader handles the documented form,
   add round-trip tests, mark as "structural divergence with locked
   equivalence test" if loader copes.

---

## Phase 5 — Completion criteria

`olc_save.c` flips ❌ Not Audited → ⚠️ Partial today (audit doc filed,
gap IDs OLC_SAVE-001..020 stable, no closures yet).

Status will flip to ✅ AUDITED only after:

- OLC_SAVE-001..008 (CRITICAL — round-trip data loss) closed with
  integration tests verifying full proto round-trip equality.
- OLC_SAVE-009..013 (IMPORTANT) closed or explicitly deferred with
  justification (e.g. autosave timer not yet ported → defer 011).
- OLC_SAVE-014..017 (MINOR — string drift) closed; these are mechanical.
- OLC_SAVE-018..020 (MINOR — JSON-equivalence-documented) verified or
  closed with locked-equivalence tests (same pattern as OLC_ACT-013/014).
- Tracker row in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` updated
  from `25%` to the closure %.

**Locked decisions for closure subagents:**

1. **JSON is the canonical write format.** Do not implement a `.are` writer.
2. **Round-trip equality is the test bar.** Each CRITICAL closure must
   include a load→save→load test that asserts the proto's field set is
   preserved.
3. **Loader-side parity is in scope when needed.** If a CRITICAL field
   serialization closure requires a corresponding `mud/loaders/json_loader.py`
   change to read it back, both sides land in the same closure commit
   (one gap = one feature = one commit, both sides included).
4. **Sub-gaps inherited from OLC_ACT-010b** (dice/AC stored as strings
   instead of 3 ints) are NOT closed in this audit — they're upstream of
   OLC_SAVE-001..002 and require a data-model change. Cross-reference but
   defer.
