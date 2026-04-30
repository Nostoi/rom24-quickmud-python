# Session Status — 2026-04-30 — `olc_save.c` IMPORTANT block: 4/5 closed

## Current State

- **Active audit**: `olc_save.c` (Phase 4 in flight — CRITICAL block
  **8/8 closed** (OLC_SAVE-001..008); IMPORTANT block **4/5 closed**
  (OLC_SAVE-010..013); only OLC_SAVE-009 (help-save port) remains in
  IMPORTANT; MINOR block OLC_SAVE-014..020 still open)
- **Last completed**: OLC_SAVE-013 (`save_area_list` social.are prepend,
  Haiku subagent). Preceded this session by OLC_SAVE-010 (asave area
  dispatcher), OLC_SAVE-011 (autosave entry char=None), OLC_SAVE-012
  (NPC security gate on `_is_builder`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-04-30_OLC_SAVE_010_TO_013_IMPORTANT_BLOCK.md](SESSION_SUMMARY_2026-04-30_OLC_SAVE_010_TO_013_IMPORTANT_BLOCK.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.99 |
| OLC_SAVE integration tests | 40/40 passing (12 closures × ~3 cases each) |
| Full integration suite | 1779 passing / 10 skipped / 0 new failures |
| ROM C files audited | ~22 / 43 (`olc_save.c` ⚠️ Partial — 12/20 gaps closed: 8 CRITICAL + 4 IMPORTANT) |
| Active focus | `olc_save.c` — OLC_SAVE-009 (help-save port) recommended next |

## Next Intended Task

Begin **OLC_SAVE-009** — port of ROM `save_helps` / `save_other_helps`
(`src/olc_save.c:826-872`). This is the only remaining IMPORTANT-block
gap and the larger standalone effort. Three preconditions to settle
before writing tests:

1. **JSON shape decision** for help entries — per-help-file (one JSON
   per `<topic>.are` source) or area-grouped (helps embedded in the
   owning area's JSON, with a top-level `helps` section). Recommend
   area-grouped for symmetry with mobs/objects/rooms; the loader side
   (`mud/loaders/json_loader.py`) already reads helps from a top-level
   `helps` array on area JSON.
2. **Write path** on `mud/models/help.py` — currently read-only via
   loader; needs a `_serialize_help` helper that emits the canonical
   `{level, keywords, text}` shape and is picked up by
   `save_area_to_json`.
3. **Dispatcher tightening** — once help-save lands, the OLC_SAVE-010
   hedit branch should be flipped from its "Grabando area : help save
   not yet implemented" placeholder to call the real save path, and
   OLC_SAVE-013 can grow the HAD/HELP_AREA filename rows on top of the
   `social.are` prepend.

After OLC_SAVE-009, tackle the **MINOR block** (OLC_SAVE-014..020):
four message-string drifts plus three JSON-equivalence-documented
divergences (condition letter, exit lock-flag, door-reset synthesis).
All mechanical, all Haiku-suitable per this session's OLC_SAVE-013
precedent.

### Subagent reliability note (carried forward)

OLC_SAVE-013 is the first IMPORTANT-block closure successfully
completed by a Haiku subagent in this codebase — single-line string
emit fits Haiku's "trivial single-keyword fix" bar. Sonnet subagents
continue to terminate mid-investigation (five sessions reproduced).
Continue running structural / multi-file closures (OLC_SAVE-009 is
one) inline; delegate mechanical string drifts (OLC_SAVE-014..017) to
Haiku.

### Fixture sweep precedent

OLC_SAVE-012 forced `is_npc=False` onto 10 existing OLC test fixtures
(test_olc_act_001..006, test_olc_builders, test_olc_save_010,
test_olc_save_011, test_olc_do_resets_subcommands). Future PC
fixtures elsewhere in the suite may carry the same latent bug — flag
and fix on encounter.

### GitNexus

Index stale at 6899cc7. The 32 KB-cap caveat in CLAUDE.md still
applies for `mud/commands/build.py`. All four closures this session
were verified via `pytest` rather than `gitnexus_impact`. Re-run
`npx gitnexus analyze` at the next major checkpoint.
