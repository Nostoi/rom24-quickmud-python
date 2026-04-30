# Session Summary — 2026-04-30 — `olc_save.c` IMPORTANT block: dispatcher trio + area-list prepend

## Scope

Continuation of the prior 2026-04-30 session that closed the
`olc_save.c` CRITICAL round-trip data-loss block (OLC_SAVE-001..008).
This session moved into the IMPORTANT block, closing four of the
remaining five gaps inline (`010`/`011`/`012`) plus one delegated
mechanical closure (`013` via Haiku subagent). All four sit on the
`cmd_asave` / `_is_builder` / `save_area_list` axis. Only OLC_SAVE-009
(help-save port — larger standalone) remains in the IMPORTANT block.

## Outcomes

### `OLC_SAVE-010` — ✅ FIXED

- **Python**: `mud/commands/build.py` (`cmd_asave` "area" branch)
- **ROM C**: `src/olc_save.c:1080-1128`
- **Gap**: `cmd_asave area` only handled `redit`; ROM dispatches across ED_AREA / ED_ROOM / ED_OBJECT / ED_MOBILE / ED_HELP.
- **Fix**: Branch on `session.editor` and resolve area from `editor_state["area"]` (aedit), `room.area` (redit), `obj_proto.area` (oedit), `mob_proto.area` (medit). Hedit returns ROM-faithful "Grabando area :" prefix pending OLC_SAVE-009. Default fall-through mirrors ROM's `pArea = ch->in_room->area`.
- **Tests**: `tests/integration/test_olc_save_010_asave_area_dispatch.py` — 6/6 passing.
- **Commit**: `43aa337`

### `OLC_SAVE-011` — ✅ FIXED

- **Python**: `mud/commands/build.py` (`cmd_asave` entry + "world" branch)
- **ROM C**: `src/olc_save.c:931-936`, `:1000-1018`
- **Gap**: Python required non-null `char`; `_is_builder(None, area)` returned False, blocking the autosave-timer entry path `do_asave(NULL, "world")`.
- **Fix**: `cmd_asave(char: Character | None, args)` accepts `char=None`. The "world" branch skips the `_is_builder` gate when ch is None and returns silently (mirrors ROM `if (ch) send_to_char`). Other null-ch arg paths short-circuit before any char-attribute access.
- **Tests**: `tests/integration/test_olc_save_011_autosave_entry.py` — 3/3 passing.
- **Commit**: `06fb42d`

### `OLC_SAVE-012` — ✅ FIXED

- **Python**: `mud/commands/build.py:_is_builder` (line 199)
- **ROM C**: `src/merc.h` IS_BUILDER macro; `src/olc_save.c:933` (`IS_NPC(ch) → sec = 0`)
- **Gap**: `_is_builder` did not gate on `is_npc`. An NPC whose name appeared in an area's `builders` list (or one carrying a stub `pcdata.security`) would have passed the builder check.
- **Fix**: Short-circuit on `getattr(char, "is_npc", False)` before consulting `pcdata.security` / `area.builders`. Updated 10 existing OLC test fixtures to set `is_npc=False` on PCs (they were silently relying on the missing gate).
- **Tests**: `tests/integration/test_olc_save_012_npc_security_gate.py` — 3/3 passing.
- **Commit**: `bc3b656`

### `OLC_SAVE-013` — ✅ FIXED (Haiku subagent)

- **Python**: `mud/olc/save.py:save_area_list` (line 469)
- **ROM C**: `src/olc_save.c:94`
- **Gap**: `save_area_list` did not emit `social.are` as the first row of `area.lst` (ROM OLC convention).
- **Fix**: Prepend `f.write("social.are\n")` immediately after file open with a ROM-cite comment. HAD/HELP_AREA standalone-help rows remain N/A pending OLC_SAVE-009 (Python has no `help_area` / HAD structure yet).
- **Tests**: `tests/integration/test_olc_save_013_area_list_social_prepend.py` — 2/2 passing.
- **Commit**: `d2df0cc`
- **Subagent reliability note**: This is the first IMPORTANT-block closure successfully completed by a Haiku subagent in this codebase. The gap was a pure string-emit (one-line addition), which fits the "trivial single-keyword fix" reliability bar. Sonnet subagents remain unreliable mid-investigation — five sessions reproduced.

## Files Modified

- `mud/commands/build.py` — `cmd_asave` "area" dispatcher (010), `cmd_asave` null-ch entry + world branch (011), `_is_builder` IS_NPC short-circuit (012).
- `mud/olc/save.py` — `save_area_list` social.are prepend (013).
- `tests/integration/test_olc_save_010_asave_area_dispatch.py` — new, 6 cases.
- `tests/integration/test_olc_save_011_autosave_entry.py` — new, 3 cases.
- `tests/integration/test_olc_save_012_npc_security_gate.py` — new, 3 cases.
- `tests/integration/test_olc_save_013_area_list_social_prepend.py` — new, 2 cases.
- 10 existing OLC test fixtures (test_olc_act_*, test_olc_builders, test_olc_do_resets_subcommands, test_olc_save_010, test_olc_save_011) updated to set `is_npc=False` on PC builders — sweeping consequence of the OLC_SAVE-012 gate.
- `docs/parity/OLC_SAVE_C_AUDIT.md` — flipped rows: OLC_SAVE-010, OLC_SAVE-011, OLC_SAVE-012, OLC_SAVE-013 (all ✅ FIXED).
- `CHANGELOG.md` — four `Fixed` entries.
- `pyproject.toml` — 2.6.95 → 2.6.99 (four patch bumps).

## Test Status

- Per-gap suites — 14/14 passing (010: 6, 011: 3, 012: 3, 013: 2).
- All OLC integration suites (`test_olc_act_*` + `test_olc_builders` + `test_olc_save_*` + `test_olc_do_resets_subcommands`) — 113/113 passing after the IS_NPC fixture sweep.
- Full integration suite — 1779 passing, 10 skipped, 0 new failures (re-verified after OLC_SAVE-012 and OLC_SAVE-013).
- Pre-existing baseline: the documented `tests/test_olc_save.py` failures and the order-dependent `test_kill_mob_grants_xp_integration` flake remain; neither was caused by this session's changes.

## Next Steps

`olc_save.c` IMPORTANT block is **4/5 closed**. The remaining gap is:

- **OLC_SAVE-009** — port of ROM `save_helps`/`save_other_helps` (`src/olc_save.c:826-872`). This is the larger standalone effort: it needs a JSON shape decision for help entries (per-help-file or area-grouped), a write path on `mud/models/help.py` (currently read-only via loader), and integration with `cmd_asave` `area` for the hedit branch (so the dispatcher can replace its "Grabando area : help save not yet implemented" placeholder with a real save). Once 009 lands, the 010 hedit branch and 013 HAD prepend can both be tightened to full ROM parity.

After OLC_SAVE-009, the **MINOR block** (OLC_SAVE-014..020) covers four
message-string drifts plus three JSON-equivalence-documented divergences
(condition letter, exit lock-flag, door-reset synthesis). All
mechanical, all Haiku-suitable.

### Carried-forward notes

- **Subagent reliability**: Haiku is now confirmed reliable for one-line / single-keyword closures (OLC_SAVE-013 success). Sonnet remains unreliable mid-investigation across five sessions. Inline execution is still the default for any closure touching multi-file logic (e.g. OLC_SAVE-009's loader+serializer paired change).
- **GitNexus index** is stale (last analyzed at 6899cc7). The 32 KB-cap caveat in CLAUDE.md still applies for `mud/commands/build.py` if a future closure touches the asave dispatcher path. All four closures this session were verified via `pytest` rather than `gitnexus_impact`.
- **Fixture sweep precedent**: OLC_SAVE-012 forced `is_npc=False` onto 10 existing OLC test fixtures. Future PC fixtures elsewhere in the suite may carry the same latent bug — flag and fix on encounter.
