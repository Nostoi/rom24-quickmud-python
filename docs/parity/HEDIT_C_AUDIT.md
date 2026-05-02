# HEDIT_C_AUDIT.md — `src/hedit.c` (462 lines, 9 functions)

**Status**: ✅ AUDITED — all 14 gaps closed (HEDIT-001..014); 24 integration tests green.
**Date**: 2026-05-02 (completed)
**Audited by**: claude-sonnet-4.6

---

## Phase 1 — Function Inventory

| ROM Function | Lines | Python Counterpart | File | Status |
|---|---|---|---|---|
| `get_help_area` | 40–51 | (no direct port — Python uses dict registry) | — | N/A |
| `hedit_show` | 53–67 | `_hedit_show` | `mud/commands/build.py:4164` | ⚠️ PARTIAL |
| `hedit_level` | 69–94 | `_interpret_hedit` level branch | `mud/commands/build.py:4149` | ⚠️ PARTIAL |
| `hedit_keyword` | 96–113 | `_interpret_hedit` keyword branch | `mud/commands/build.py:4135` | ⚠️ PARTIAL |
| `hedit_new` | 115–186 | `cmd_hedit` new branch | `mud/commands/build.py:4043` | ⚠️ PARTIAL |
| `hedit_text` | 188–203 | `_interpret_hedit` text branch | `mud/commands/build.py:4142` | ⚠️ PARTIAL |
| `hedit` (dispatcher) | 205–260 | `_interpret_hedit` | `mud/commands/build.py:4086` | ⚠️ PARTIAL |
| `do_hedit` | 284–333 | `cmd_hedit` | `mud/commands/build.py:4024` | ⚠️ PARTIAL |
| `hedit_delete` | 336–398 | (missing) | — | ❌ MISSING |
| `hedit_list` | 400–462 | (missing) | — | ❌ MISSING |

---

## Phase 3 — Gap Table

| Gap ID | Severity | ROM C Reference | Python Reference | Description | Status |
|---|---|---|---|---|---|
| HEDIT-001 | CRITICAL | `src/hedit.c:53-67` | `build.py:4164` | `hedit_show` format wrong. ROM: `"Keyword : [%s]\n\rLevel   : [%d]\n\rText    :\n\r%s-END-\n\r"`. Python: custom multi-line format with truncation at 100 chars. | ✅ FIXED |
| HEDIT-002 | CRITICAL | `src/hedit.c:69-94` | `build.py:4149` | `hedit_level` range check wrong. ROM: `-1` to `MAX_LEVEL` (51) inclusive, with `"HEdit : levels are between -1 and %d inclusive.\n\r"`. Python: rejects negative (`< 0`) and uses wrong error message. | ✅ FIXED |
| HEDIT-003 | CRITICAL | `src/hedit.c:96-113` | `build.py:4135` | `hedit_keyword` ROM sends `"Ok.\n\r"` on success. Python: `f"Keywords set to: ..."` — wrong message. | ✅ FIXED |
| HEDIT-004 | CRITICAL | `src/hedit.c:76,102` | `build.py:4136,4144` | `hedit_level` empty-arg check uses `"Syntax: level [-1..MAX_LEVEL]\n\r"`. `hedit_keyword` uses `"Syntax: keyword [keywords]\n\r"`. Python: different messages. | ✅ FIXED |
| HEDIT-005 | CRITICAL | `src/hedit.c:188-203` | `build.py:4142` | `hedit_text` ROM: no-arg invokes `string_append` (interactive text editor) and returns `TRUE`. Python: `"Usage: text <help text content>"` then sets text inline — completely different behavior. | ✅ FIXED |
| HEDIT-006 | CRITICAL | `src/hedit.c:228-234` | `build.py:4034` | Security check in `hedit` dispatcher (not `do_hedit`): `ch->pcdata->security < 9` → `"HEdit: Insufficient security to edit helps.\n\r"` + `edit_done`. Python: `"HEdit: Insufficient security to edit helps."` (missing `\n\r`). | ✅ FIXED |
| HEDIT-007 | CRITICAL | `src/hedit.c:236-259` | `build.py:4086` | `hedit` dispatcher: empty input → `hedit_show`. Python: empty input → `"Syntax: keywords ..."`. Wrong fallback. | ✅ FIXED |
| HEDIT-008 | CRITICAL | `src/hedit.c:242-246` | `build.py:4116` | `done` handling in ROM: `edit_done(ch)` — clears editor. Python: clears and returns `"Help entry saved. Use '@hesave' to write to disk."` — ROM returns nothing on `done`. Also ROM `done` keyword is exact, no `exit` alias. | ✅ FIXED |
| HEDIT-009 | CRITICAL | `src/hedit.c:248-256` | `build.py:4086` | `hedit` dispatcher: unknown command → `interpret(ch, arg)` (falls back to normal command table). Python: returns `f"Unknown help editor command: {cmd}"` — no fallback. | ✅ FIXED |
| HEDIT-010 | CRITICAL | `src/hedit.c:336-398` | (missing) | `hedit_delete` entirely missing from Python. Removes help from `help_first` list, all `had_list` area chains, frees help; boots all editors editing the same help; sends `"Ok.\n\r"`. | ✅ FIXED |
| HEDIT-011 | CRITICAL | `src/hedit.c:400-462` | (missing) | `hedit_list` entirely missing from Python. Two subcommands: `list all` (paginated all helps, 4-column format `%3d. %-14.14s`) and `list area` (same format but area-local helps only). Unknown arg → `"Syntax: list all\n\r        list area\n\r"`. | ✅ FIXED |
| HEDIT-012 | IMPORTANT | `src/hedit.c:115-186` | `build.py:4043` | `hedit_new`: ROM checks `had_lookup(arg)` first (area name prefix match); if no area found, uses `ch->in_room->area->helps`. Python ignores area name arg entirely. Also ROM `"HEdit : help exists.\n\r"` on duplicate; Python creates new entry silently. Also ROM sets `ch->desc->editor = ED_HELP` after `hedit_new` call in `do_hedit`. | ✅ FIXED |
| HEDIT-013 | IMPORTANT | `src/hedit.c:284-333` | `build.py:4024` | `do_hedit`: ROM does case-insensitive `is_name(argall, pHelp->keyword)` scan across all help_first list. Python does exact `help_registry.get(keyword)`. `is_name` is a prefix/word match — `hedit sword` should match entry with keywords `"SWORD SWORDS"`. | ✅ FIXED |
| HEDIT-014 | IMPORTANT | `src/hedit.c:91,111` | `build.py:4139,4158` | `hedit_level` and `hedit_keyword` both return `TRUE` on success (causing `had->changed = TRUE` in dispatcher). Python never sets any `changed` flag on the area's help-area. | ✅ FIXED |

---

## Phase 4 — Gap Closures

(In progress)

---

## Phase 5 — Completion Summary

(Pending)
