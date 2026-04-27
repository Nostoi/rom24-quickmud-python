# mob_prog.c — ROM 2.4b6 Parity Audit

**Status**: 🔄 IN PROGRESS — Phase 3 (gap identification complete)
**Started**: 2026-04-27
**ROM source**: `src/mob_prog.c` (1362 lines)
**Python target**: `mud/mobprog.py` (1685 lines)
**Tracker entry**: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` row "mob_prog.c" (was ⚠️ Partial 75%)

`mob_prog.c` implements the MOBprogram interpreter: trigger dispatch, the `if/or/and/else/endif` control flow, the `cmd_eval` predicate evaluator, `expand_arg` ($-code substitution), and the seven trigger-handler entry points used by the rest of the engine.

---

## Phase 1 — Function inventory

| ROM function                  | ROM lines  | Python counterpart                        | Status      |
|-------------------------------|------------|-------------------------------------------|-------------|
| `keyword_lookup`              | 199–206    | `mobprog.keyword_lookup` (1584)           | ✅ AUDITED  |
| `num_eval`                    | 212–232    | `mobprog._compare_numbers` (663)          | ✅ AUDITED  |
| `get_random_char`             | 243–257    | `mobprog._get_random_char` (217)          | ✅ AUDITED  |
| `count_people_room`           | 263–279    | `mobprog._count_people_room` (347)        | ✅ AUDITED  |
| `get_order`                   | 286–301    | `mobprog._get_order` (381)                | ✅ AUDITED  |
| `has_item`                    | 309–318    | `mobprog.has_item` (1611)                 | ✅ AUDITED  |
| `get_mob_vnum_room`           | 323–330    | `mobprog.get_mob_vnum_room` (1638)        | ✅ AUDITED  |
| `get_obj_vnum_room`           | 335–342    | `mobprog.get_obj_vnum_room` (1665)        | ✅ AUDITED  |
| `cmd_eval`                    | 356–702    | `mobprog._cmd_eval` (679)                 | ⚠️ PARTIAL  |
| `expand_arg`                  | 711–921    | `mobprog._expand_arg` (488)               | ⚠️ PARTIAL  |
| `program_flow`                | 939–1170   | `mobprog._program_flow` (1136)            | ⚠️ PARTIAL  |
| `mp_act_trigger`              | 1183–1201  | `mobprog.mp_act_trigger` (1301)           | ✅ AUDITED  |
| `mp_percent_trigger`          | 1207–1222  | `mobprog.mp_percent_trigger` (1321)       | ✅ AUDITED  |
| `mp_bribe_trigger`            | 1224–1242  | `mobprog.mp_bribe_trigger` (1358)         | ✅ AUDITED  |
| `mp_exit_trigger`             | 1244–1281  | `mobprog.mp_exit_trigger` (1425)          | ✅ AUDITED  |
| `mp_give_trigger`             | 1283–1323  | `mobprog.mp_give_trigger` (1388)          | ✅ AUDITED  |
| `mp_greet_trigger`            | 1325–1349  | `mobprog.mp_greet_trigger` (1469)         | ⚠️ PARTIAL  |
| `mp_hprct_trigger`            | 1351–1362  | `mobprog.mp_hprct_trigger` (1488)         | ✅ AUDITED  |

Trigger bit values verified against `src/merc.h:1971-1986` (A=1<<0 ACT, B=1<<1 BRIBE, …, P=1<<15 SURR) — Python `Trigger` enum agrees.

---

## Phase 2 — Verified parity (no gap)

- **`num_eval` operators** (`==`/`>=`/`<=`/`>`/`<`/`!=`) — exhaustive switch matches `_compare_numbers` (`mob_prog.c:212-232`).
- **`cmd_eval` Case 1 numeric checks** (`rand`, `mobhere`, `objhere`, `mobexists`) — match ROM 1:1 except `objexists` (see MOBPROG-001).
- **`cmd_eval` Case 2 room counts** (`people`, `players`, `mobs`, `clones`, `order`, `hour`) — `_count_people_room` flag semantics match ROM 263–279 including the `same group` flag-4 path via `is_same_group` ⇄ leader/master test.
- **`cmd_eval` Case 3** (`ispc`/`isnpc`/`isgood`/`isevil`/`isneutral`/`isimmort`/`ischarm`/`isfollow`/`isactive`/`isdelay`/`isvisible`/`hastarget`/`istarget`/`exists`) — all paths match ROM 496–537.
- **`cmd_eval` Case 4** (`affected`/`act`/`off`/`imm`/`carries`/`wears`/`has`/`uses`/`name`/`pos`/`objtype`) — flag lookups, name token matching, and item-type lookups parity-correct.
- **`cmd_eval` Case 5** (`vnum`/`hpcnt`/`room`/`sex`/`level`/`align`/`money`/`objval0..4`/`grpsize`) — formulas match ROM 631–700, including the `gold + silver*100` money roll-up and `(hit*100)/max_hit` hp-percent.
- **`expand_arg`** — all $-codes (`i I n N t T r R q Q j e E J X k m M K Y l s S L Z o O p P`) covered. Sex-index clamping `URANGE(0, sex, 2)` is mirrored.
- **`program_flow` control flow** — `if`/`and`/`or`/`endif`/`break`/`end` semantics match ROM 1019–1147 with the same `MAX_NESTED_LEVEL=12` and `MAX_CALL_LEVEL=5` guards.
- **`mp_act_trigger`** — first-match break, substring `strstr` ↔ `in` check, NPC-only guard.
- **`mp_percent_trigger`** — strict `<` random-percent comparison via `rng_mm.number_percent()`.
- **`mp_bribe_trigger`** — `amount >= atoi(prg->trig_phrase)` threshold, first match wins.
- **`mp_exit_trigger`** — direction filter, EXIT-vs-EXALL position/visibility gating, first match wins (`mob_prog.c:1244-1281`).
- **`mp_give_trigger`** — vnum fast path + name-token loop + literal `"all"` synonym.
- **`mp_hprct_trigger`** — `(100 * hit) / max_hit < phrase` uses Python `//` (no signs involved → identical to ROM `c_div`).
- **`get_random_char`** — Python uses `highest = -1` while ROM uses `highest = 0`, but `rng_mm.number_percent()` returns `1..100` (no zero), so the starting value never wins; behavior is identical.

---

## Phase 3 — Gaps

| Gap ID         | Severity   | ROM ref                  | Python ref                | Status   |
|----------------|------------|--------------------------|---------------------------|----------|
| MOBPROG-001    | CRITICAL   | `mob_prog.c:399`         | `mobprog.py:727-755`      | ✅ FIXED — `tests/integration/test_mobprog_predicates.py` |
| MOBPROG-002    | CRITICAL   | `mob_prog.c:1340-1346`   | `mobprog.py:1469-1485`    | ✅ FIXED — `tests/integration/test_mobprog_greet_trigger.py` |
| MOBPROG-003    | IMPORTANT  | `mob_prog.c:631-648`     | `mobprog.py:1012-1024`    | ✅ FIXED — `tests/integration/test_mobprog_predicates.py` |
| MOBPROG-004    | IMPORTANT  | `mob_prog.c:601-609`     | `mobprog.py:967-992`      | 🔄 OPEN  |
| MOBPROG-005    | IMPORTANT  | `mob_prog.c:1127-1140`   | `mobprog.py:1189-1194`    | 🔄 OPEN  |
| MOBPROG-006    | IMPORTANT  | `mob_prog.c:795-799`     | `mobprog.py:540-545`      | 🔄 OPEN  |
| MOBPROG-007    | MINOR      | `mob_prog.c:1051-1109`   | `mobprog.py:1170-1188`    | 🔄 OPEN  |

### MOBPROG-001 — `objexists` is room-only; ROM searches the world (CRITICAL)

ROM `cmd_eval` `CHK_OBJEXISTS` (`mob_prog.c:399`) returns `(get_obj_world (mob, buf) != NULL)` — a world-wide search through every loaded object on every char/room. Python (`mobprog.py:727-755`) only checks `_obj_here(mob, …)` (current room contents), then objects carried by people in the same room, then `arg1`/`arg2`. Programs that do `if objexists artifact` to detect a globally-placed item return false in Python where ROM returns true. **Visible behavior divergence in any prog that tracks world objects.**

### MOBPROG-002 — `mp_greet_trigger` fires GRALL after a failed GREET roll; ROM doesn't (CRITICAL)

ROM (`mob_prog.c:1340-1345`):
```c
if (HAS_TRIGGER (mob, TRIG_GREET) && position == default_pos && can_see ...)
    mp_percent_trigger (mob, ch, NULL, NULL, TRIG_GREET);
else if (HAS_TRIGGER (mob, TRIG_GRALL))
    mp_percent_trigger (mob, ch, NULL, NULL, TRIG_GRALL);
```

The `else` is exclusive: a mob with both GREET and GRALL programs that is awake and can see the player only gets a GREET attempt; GRALL is reserved for the busy/blind case. Python (`mobprog.py:1480-1485`) uses `if mp_percent_trigger(...): continue` — meaning when the GREET random-percent roll *fails*, control falls through to the GRALL block and a GRALL program also fires. This double-fires triggers any time a mob carries both flags and the GREET probability check rolls badly.

### MOBPROG-003 — `if vnum $n …` against a PC returns False; ROM compares against 0 (IMPORTANT)

ROM `CHK_VNUM` (`mob_prog.c:631-648`) for `$n/$t/$r/$q/$i`:
```c
if (lval_char != NULL && IS_NPC (lval_char))
    lval = lval_char->pIndexData->vnum;
```
If the actor is a PC, `lval` stays at its initialized `0`, then `num_eval(0, oper, rval)` runs — `if vnum $n == 0` is TRUE for PCs, `if vnum $n != 0` is FALSE, etc. Python (`mobprog.py:1012-1024`) early-returns `False` whenever `target_char` isn't an NPC, so the comparison always evaluates to False regardless of operator. Programs that gate logic on `if vnum $n == 0` to detect PCs lose that branch.

### MOBPROG-004 — `clan`/`race`/`class` use int/string fallback; ROM uses name→int lookup tables (IMPORTANT)

ROM (`mob_prog.c:601-609`) calls `clan_lookup(buf)` / `race_lookup(buf)` / `class_lookup(buf)` to convert the keyword (e.g. `mage`, `dragon`, `arctic`) into its registered integer index, then compares to `lval_char->clan/race/class`. Python (`mobprog.py:967-992`) tries `int(value_token)` first; on `ValueError` it falls back to a lowercase string compare against `str(value)`. Since `Character.race` / `ch_class` / `clan` are stored as integer indices (not name strings), the string fallback compares e.g. `"3"` to `"mage"` and always returns False. Result: every `if race $n dragon` / `if class $n mage` / `if clan $n thieves` predicate returns False in Python, blocking class/race-gated mob behavior.

### MOBPROG-005 — `else` doesn't reset `state[level]` to `IN_BLOCK`; ROM does (IMPORTANT)

ROM (`mob_prog.c:1138-1139`):
```c
state[level] = IN_BLOCK;
cond[level]  = (cond[level] == TRUE) ? FALSE : TRUE;
```
Python (`mobprog.py:1189-1194`) only toggles `cond[level]`; `state[level]` stays at `END_BLOCK` from the matching `if`. The state machine flag is consulted by the `or`/`and`/`endif`/`else` control words to detect "misplaced if" / "or without if" errors. Within the `else` body, ROM treats new `if`s with `state[level] == IN_BLOCK` (the legal case); Python leaves `END_BLOCK` set, so a nested `if` inside an `else` block hits the `state[level] == BEGIN_BLOCK`-style check inconsistently and can return early on legal programs.

### MOBPROG-006 — `$R` $-code uses `rch` data; ROM uses `ch` (replicate-the-bug parity) (IMPORTANT)

ROM (`mob_prog.c:798-799`) — note the `IS_NPC (ch)` and `ch->short_descr/ch->name`:
```c
i = (rch != NULL && can_see (mob, rch))
    ? (IS_NPC (ch) ? ch->short_descr : ch->name) : someone;
```
This is a long-standing ROM bug (`rch` was intended; `ch` slipped in) that produces the original actor's name when expanding `$R`. Python (`mobprog.py:540-545`) uses `pick.short_descr or pick.name` where `pick = rch`, i.e. it produces the *random* char's short_descr — the "correct" behavior. Per `AGENTS.md` ROM Parity Rules ("when ROM C behavior is 'wrong' or quirky, we replicate it exactly"), Python must reproduce the ROM bug.

### MOBPROG-007 — Invalid if-check keyword silently returns False; ROM bugs out and aborts the prog (MINOR)

ROM (`mob_prog.c:1049-1056, 1076-1083, 1103-1109`) on an unknown `if`/`and`/`or` keyword logs `"Mobprog: invalid if_check (…), mob %d prog %d"` via `bug()` and **returns from `program_flow`**, aborting the rest of the program. Python (`mobprog.py:1170-1188`) calls `_cmd_eval(check_name.lower(), …)` which silently returns False for unknown keywords; the program continues executing. Effect: typos in mob progs are louder and more debuggable in ROM than in Python, and a typo'd `or` clause stops the whole prog in ROM where Python keeps running. Cosmetic for live behavior; matters for area-builder feedback.

---

## Phase 4 — Closure plan

Hand off each gap to `/rom-gap-closer` in this order (CRITICAL → IMPORTANT → MINOR), one TDD cycle per gap, one `fix(parity)`/`feat(parity)` commit per gap:

1. **MOBPROG-001** — fix `objexists` to walk `mud.models.character.character_registry` + each char's inventory + every room's contents (mirroring `db.c:get_obj_world`). Test in `tests/integration/test_mobprog_predicates.py` (new) — run a prog with `if objexists 9999` against an obj loaded into a remote room.
2. **MOBPROG-002** — drop the `continue` after a failing GREET attempt in `mp_greet_trigger`; restructure as `if HAS_TRIGGER GREET … else if HAS_TRIGGER GRALL …`. Test by seeding `rng_mm` so GREET roll fails on a mob with both flags and asserting GRALL prog did NOT fire.
3. **MOBPROG-003** — in `_cmd_eval` `vnum` branch, when target is a PC keep `lval = 0` and fall through to `_compare_numbers` instead of returning False. Test: prog with `if vnum $n == 0` against a PC fires, against an NPC does not.
4. **MOBPROG-004** — wire `clan_lookup`/`race_lookup`/`class_lookup` style helpers (likely already in `mud.models.constants` / `mud.skills.registry`) into the three checks; preserve the int-direct fast path. Test: prog with `if class $n mage` fires for a mage PC.
5. **MOBPROG-005** — set `state[level] = IN_BLOCK` in the `else` branch of `_program_flow`. Test: nested `if/else { if/else }` program executes the inner else branch correctly.
6. **MOBPROG-006** — change `_expand_arg` `R` branch to read `ch.short_descr or ch.name` (i.e. the original actor) per the ROM bug. Cite `mob_prog.c:798-799` in a comment. Test: an `$R` expansion with a PC actor and NPC random-victim renders the *PC* short_descr, not the random victim's.
7. **MOBPROG-007** — emit a structured warning / log on unknown if-check keyword and abort the program (parity with `bug()`+return). Test: a prog with `if foozle $n` halts and does not execute subsequent commands.

After all CRITICAL+IMPORTANT closures: rerun `pytest tests/test_mobprog*.py tests/integration/test_mobprog_*.py` and bump the tracker row to ✅ AUDITED. MINOR gap MOBPROG-007 may be closed in the same session or deferred (per `docs/ROM_PARITY_VERIFICATION_GUIDE.md`).

---

## Phase 5 — Closure (pending)

Will be filled in by `/rom-session-handoff` once all CRITICAL + IMPORTANT gaps are closed:

- Tracker row flip in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.
- `CHANGELOG.md` `[Unreleased]` entries (one bullet per closed gap).
- `pyproject.toml` 2.6.4 → 2.6.5.
- `docs/sessions/SESSION_SUMMARY_<date>_MOB_PROG_C_AUDIT.md` and refreshed `SESSION_STATUS.md`.
