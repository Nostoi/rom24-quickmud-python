# `src/db2.c` ROM Parity Audit

**Date started:** 2026-04-28
**Auditor:** automated (rom-parity-audit skill)
**Status:** ⚠️ Phase 3 complete — gaps catalogued; Phase 4 closures pending
**ROM file:** `src/db2.c` (958 lines)
**Python module(s):** `mud/loaders/social_loader.py`, `mud/loaders/mob_loader.py`, `mud/loaders/obj_loader.py`

---

## Phase 1 — Function inventory

| ROM function | ROM lines | Python counterpart | Status |
|---|---|---|---|
| `load_socials(FILE *fp)` | 53–180 | `mud/loaders/social_loader.py:10` `load_socials(path)` | N/A — JSON deviation |
| `load_mobiles(FILE *fp)` | 190–374 | `mud/loaders/mob_loader.py:51` `load_mobiles(tokenizer, area)` | ⚠️ PARTIAL |
| `load_objects(FILE *fp)` | 379–599 | `mud/loaders/obj_loader.py:369` `load_objects(tokenizer, area)` | ✅ AUDITED (minor only) |
| `convert_objects(void)` | 612–752 | — | N/A — no old-format areas |
| `convert_object(OBJ_INDEX_DATA *)` | 763–857 | — | N/A — no old-format areas |
| `convert_mobile(MOB_INDEX_DATA *)` | 869–958 | — | N/A — no old-format areas |

### N/A rationale

- **`load_socials`**: QuickMUD ships `data/socials.json` (already converted) and loads via `mud/loaders/social_loader.py`. The original `area/social.are` file is present in the tree but is not parsed by the engine. This is an intentional architectural deviation — the parser format differs but the in-memory `Social` registry is the parity target, not the file format.
- **`convert_objects` / `convert_object` / `convert_mobile`**: ROM's old-format converters fire only when an area uses `#MOBOLD` / `#OBJOLD` sections (legacy MERC format). No file under `area/` uses those sections (`grep -l '^#MOBOLD\|^#OBJOLD' area/*.are` is empty). Python has no `load_old_mob` / `load_old_obj` either — old-format support was dropped from the port. Marked N/A; revisit only if a legacy area is ever introduced.

---

## Phase 2 — Line-by-line verification

### `load_mobiles` (ROM 190–374 vs `mud/loaders/mob_loader.py:51`)

ROM behavior, with parity status:

| ROM step | ROM line | Python equivalent | Parity |
|---|---|---|---|
| Read vnum, area assignment, `new_format=TRUE` | 213–228 | mob_loader.py:59, 145–146 | ✅ |
| `player_name`, `short_descr`, `long_descr`, `description` | 230–233 | mob_loader.py:60–63 | ⚠️ uses `next_line().rstrip("~")` for player_name/short_descr — not multi-line `fread_string` (DB2-005, MINOR) |
| Race lookup | 234 | mob_loader.py:64 (stored as raw string) | ⚠️ no race table merge (see DB2-002) |
| `long_descr[0] = UPPER(...)`, `description[0] = UPPER(...)` | 236–237 | not present | ❌ DB2-003 |
| `act = fread_flag \| ACT_IS_NPC \| race_table[].act` | 239–240 | mob_loader.py:118 stores raw string only | ❌ DB2-001 (IS_NPC) + DB2-002 (race merge) |
| `affected_by = fread_flag \| race.aff` | 241–242 | mob_loader.py:119 raw string only | ❌ DB2-002 |
| `alignment`, `group` | 244–245 | mob_loader.py:120–121 | ✅ |
| `level`, `hitroll` | 247–248 | mob_loader.py:122–123 (named `thac0`) | ✅ |
| Hit dice / mana dice / damage dice | 251–269 | mob_loader.py:124–127 (parsed lazily by spawn) | ✅ |
| `dam_type = attack_lookup(...)` | 270 | mob_loader.py:128 raw string, parsed by spawn | ✅ |
| `ac[*] = fread_number * 10` | 273–276 | mob_loader.py:84–88 — **does not multiply by 10** | ❌ DB2-006 (CRITICAL) |
| `off_flags \| race.off`, `imm_flags \| race.imm`, `res_flags \| race.res`, `vuln_flags \| race.vuln` | 279–286 | mob_loader.py:92–95 raw strings only | ❌ DB2-002 |
| `start_pos`, `default_pos`, `sex`, `wealth` | 289–293 | mob_loader.py:99–102 | ✅ |
| `form \| race.form`, `parts \| race.parts` | 295–297 | mob_loader.py:106–107 raw strings only | ❌ DB2-002 |
| `size`, `material` | 299–301 | mob_loader.py:108–109 | ✅ |
| `F` flag-removal letter loop | 303–336 | mob_loader.py:177–184 via `_apply_flag_removal` | ✅ |
| `M` mobprog letter loop | 337–356 | mob_loader.py:154–176 | ✅ |
| `kill_table[URANGE(0, level, MAX_LEVEL-1)].number++` | 370 | not present | ⚠️ DB2-004 (MINOR — kill_table not implemented) |
| `top_vnum_mob`, `assign_area_vnum`, `top_mob_index` bookkeeping | 367–369 | not tracked (registry holds prototypes by vnum directly) | N/A — bookkeeping only |

### `load_objects` (ROM 379–599 vs `mud/loaders/obj_loader.py:369`)

| ROM step | ROM line | Python | Parity |
|---|---|---|---|
| Read vnum, area, `new_format=TRUE`, `reset_num=0` | 402–418 | obj_loader.py:377, 419 | ✅ (`reset_num` defaults to 0 in dataclass) |
| `name`, `short_descr`, `description`, `material` | 420–423 | obj_loader.py:378–381 | ⚠️ name/short_descr use `next_line` not `fread_string` (DB2-005, MINOR) |
| Item-type per-branch value parse (WEAPON/CONTAINER/DRINK_CON/FOUNTAIN/WAND/STAFF/POTION/PILL/SCROLL/default) | 425–478 | obj_loader.py:222–267 `_parse_item_values` | ✅ |
| `level`, `weight`, `cost` | 479–481 | obj_loader.py:398–400 | ✅ |
| Condition letter map (P/G/A/W/D/B/R) | 484–511 | obj_loader.py:26–34 `_CONDITION_MAP` | ✅ |
| `A` letter — affect with `where=TO_OBJECT, type=-1, level=pObjIndex->level, duration=-1` | 519–533 | obj_loader.py:432–448 | ✅ |
| `F` letter — affect with where ∈ {A,I,R,V}, parses bitvector | 536–569 | obj_loader.py:449–475 | ✅ |
| `E` letter — extra description | 571–581 | obj_loader.py:427–431 | ✅ |
| Hash bookkeeping `top_obj_index`, `top_vnum_obj`, `assign_area_vnum` | 590–595 | not tracked (registry indexed by vnum) | N/A |

### `load_socials` (ROM 53–180)

ROM parses `area/social.are` token-stream (8 fields per social: char_no_arg, others_no_arg, char_found, others_found, vict_found, char_not_found, char_auto, others_auto). Python loads `data/socials.json` (the canonical socials shipped with the port). The `Social` model and runtime semantics match; only the file format differs. Marking N/A by deviation.

If ROM-format social parsing is ever required (e.g., to load third-party `.soc` files), open a new gap (`DB2-100+`) and reference this audit.

### `convert_*` functions

Skipped — see Phase 1 N/A rationale. No old-format areas exist; no Python entry-point exists. No way to write a meaningful integration test without first introducing a synthetic legacy area.

---

## Phase 3 — Gap table

| Gap ID | Severity | ROM ref | Python ref | Description | Status |
|---|---|---|---|---|---|
| **DB2-001** | CRITICAL | `src/db2.c:239` | `mud/loaders/mob_loader.py:118`, `mud/loaders/json_loader.py:427` | `load_mobiles` does not OR `ACT_IS_NPC` into prototype `act_flags`. ROM unconditionally adds it; Python relies on the area file always including the `A` letter. Mobs missing the letter get spawned with `is_npc=False` semantics in flag tests. Both loaders now prepend `A` to the act_flags letter string when missing. | ✅ FIXED — `tests/integration/test_db2_loader_parity.py::test_load_mobiles_forces_act_is_npc_flag` and `::test_load_mobiles_from_json_forces_act_is_npc_flag` |
| **DB2-002** | CRITICAL | `src/db2.c:239–242,279–286,295–297` | `mud/loaders/mob_loader.py:merge_race_flags`, `mud/loaders/json_loader.py:_load_mobs_from_json` | `load_mobiles` did not merge `race_table[race].{act,aff,off,imm,res,vuln,form,parts}` into the prototype's flag fields. Race-derived defaults (dragon flying, troll regeneration, undead form) were silently dropped at load time. `merge_race_flags()` now ORs each race-table letter set into the prototype's act/aff/off/imm/res/vuln/form/parts fields; both .are and JSON loaders invoke it after MobIndex construction. | ✅ FIXED — `tests/integration/test_db2_loader_parity.py::test_load_mobiles_merges_race_table_flags` and `::test_load_mobiles_from_json_merges_race_table_flags` |
| **DB2-003** | IMPORTANT | `src/db2.c:236–237` | `mud/loaders/mob_loader.py:118–123`, `mud/loaders/json_loader.py:424–427` | `load_mobiles` did not uppercase the first character of `long_descr` and `description`. ROM does `pMobIndex->long_descr[0] = UPPER(...)` to defend against area-builder typos; Python preserved verbatim, so any mob with a lowercase first letter in those fields rendered that way in room/look output. Both the .are and JSON loaders now apply the same first-char uppercase normalization. | ✅ FIXED — `tests/integration/test_db2_loader_parity.py::test_load_mobiles_uppercases_first_char_of_long_descr_and_description` and `::test_load_mobiles_from_json_uppercases_first_char_of_long_descr_and_description` |
| **DB2-004** | MINOR | `src/db2.c:370` | — | `load_mobiles` does not maintain `kill_table[level].number` count. No user-visible impact in QuickMUD-Python today (no `kill_table` command surface). Track only; defer until/unless kill_table is ported. | 🔄 OPEN (deferred) |
| **DB2-005** | MINOR | `src/db2.c:230–232,420–422` | `mud/loaders/mob_loader.py:60–61`, `mud/loaders/obj_loader.py:378–379` | Single-line `next_line().rstrip("~")` used where ROM uses `fread_string` (multi-line tilde-terminated). Canonical areas never use multi-line for these fields, but third-party areas could. Theoretical only. | 🔄 OPEN (deferred) |
| **DB2-006** | CRITICAL | `src/db2.c:273–276` | `mud/loaders/mob_loader.py:84–88`, `mud/loaders/json_loader.py:438–441` | `load_mobiles` did not multiply armor-class fields by 10 on load. ROM stores `pMobIndex->ac[AC_PIERCE] = fread_number(fp) * 10;` (and bash/slash/exotic). Both the .are loader and the JSON loader now apply the `* 10` normalization on read; `convert_are_to_json.py` divides back when re-emitting JSON so the JSON files remain a faithful raw mirror of the .are upstream. | ✅ FIXED — `tests/integration/test_db2_loader_parity.py::test_load_mobiles_multiplies_armor_class_by_ten` and `::test_load_mobiles_from_json_multiplies_armor_class_by_ten` |

Severity legend: CRITICAL = visible behavior diverges (combat math, flag tests). IMPORTANT = wording/broadcast wrong. MINOR = cosmetic or not yet user-reachable.

---

## Phase 4 — Gap closures

(Use `/rom-gap-closer DB2-NNN` per gap. One gap → one failing integration test → one fix → one `feat(parity)` or `fix(parity)` commit.)

Recommended close order:
1. **DB2-006** (AC ×10) — affects every combat roll; biggest behavioral delta.
2. **DB2-001** (`ACT_IS_NPC` OR) — unblocks correctness of every `is_npc` check downstream.
3. **DB2-002** (race-table merge) — restores race-derived intrinsic flags.
4. **DB2-003** (UPPER first char) — cosmetic but trivial.
5. DB2-004, DB2-005 — deferred MINORs, decide per session.

Each closure should:
- Add an integration test under `tests/integration/test_area_loader_*.py` (or a new `test_db2_loader_parity.py`) that loads a synthetic mob with the relevant area-file fixture and asserts the loaded `MobIndex` matches ROM expectations.
- Cite ROM `src/db2.c:NNN` in a code comment on the fix line.
- Update the matching gap row above to ✅ FIXED with the test name + commit hash.

---

## Phase 5 — Closure (pending)

Will be filled in once all CRITICAL/IMPORTANT gaps are closed. At that point:

1. Flip `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` `db2.c` row from `⚠️ Partial 55%` to `✅ Audited 100%` (P1 gaps closed; MINOR deferrals documented here).
2. Update CHANGELOG.md `[Unreleased]` with one `Fixed` line per closed gap.
3. Hand off to `/rom-session-handoff` for the session summary + `SESSION_STATUS.md` refresh.
4. Bump `pyproject.toml` patch version per AGENTS.md Repo Hygiene.
