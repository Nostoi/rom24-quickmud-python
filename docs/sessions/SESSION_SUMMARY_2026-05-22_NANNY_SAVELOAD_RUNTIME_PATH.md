# Session Summary — 2026-05-22 — `nanny.c` / `save.c` save → reload → retained state (runtime path)

## Scope

Closed the final open bullet of Plan Task 4
(`docs/superpowers/plans/2026-05-21-parity-trust-rebuild-reaudit.md`):
save → reload → retained state on real server paths. Three Mode-B
round-trip tests on the live websocket path — wimpy, custom prompt
template, per-character aliases — locking in the persistence layer
against drift. Pattern follows the NANNY-RECONNECT trio in 2.8.33.

## Outcomes

### `NANNY-SAVELOAD-001` — ✅ VERIFIED — wimpy round-trip

- **Python**: `mud/commands/remaining_rom.py:do_wimpy` → `mud/account/account_manager.py:save_character_to_db` (writes `db_char.wimpy`) → `mud/models/character.py:from_orm` (reads `db_char.wimpy`).
- **ROM C**: `src/act_info.c:2800-2830` (do_wimpy), `src/save.c:fwrite_char/fread_char`, `src/act_info.c:1548-1549` (score read-back).
- **Test**: `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_001_wimpy_round_trips_through_reconnect` — set `wimpy 30`, disconnect, reconnect, `score` shows `"Wimpy set to 30 hit points."` No drift.

### `NANNY-SAVELOAD-002` — ✅ VERIFIED — custom prompt template round-trip

- **Python**: `mud/commands/auto_settings.py:do_prompt` → `mud/account/account_manager.py:save_character_to_db` (writes `db_char.prompt`) → `mud/models/character.py:from_orm` (restores `char.prompt`) → `mud/utils/prompt.py:bust_a_prompt` (renders the saved template).
- **ROM C**: `src/act_info.c:919-955` (do_prompt), `src/comm.c:1420-1595` (bust_a_prompt).
- **Test**: `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_002_prompt_template_round_trips_through_reconnect` — set `prompt ROMSAVELOADPROMPT>`, disconnect, reconnect; assert the first post-MOTD prompt contains the saved template (no ROM-default `<Nhp Nm Nmv>` fallback). Persistence layer is clean.
- **Probe-only finding (NOT this gap's scope)**: the do_prompt command path has two parity gaps unrelated to save→reload —
  1. The dispatcher strips trailing whitespace from `prompt <template>` arguments before `do_prompt` sees them, so `prompt MYTAG> ` loses the trailing space. ROM `src/act_info.c:944` uses the raw `argument` string and preserves it.
  2. The success reply is `"Prompt set."` (truncated). ROM emits `"Prompt set to %s\n\r"` (`src/act_info.c:953-954`) which echoes the stored template back to the player.
  Both captured as follow-ups in `docs/sessions/SESSION_STATUS.md`. Worth a future PROMPT-CMD-001 / PROMPT-CMD-002 slice.

### `NANNY-SAVELOAD-003` — ✅ VERIFIED — per-character alias round-trip

- **Python**: `mud/commands/alias_cmds.py:do_alias` (writes `char.aliases`) → `mud/account/account_manager.py:save_character_to_db:256-257` (writes `db_char.aliases` as JSON) → `mud/models/character.py:from_orm:1149-1153` (restores via dict update).
- **ROM C**: `src/alias.c:102-220` (do_alias), `src/save.c:fwrite_char/fread_char`, `src/alias.c:165-175` (alias listing).
- **Test**: `tests/integration/test_nanny_saveload_runtime_path.py::test_nanny_saveload_003_alias_round_trips_through_reconnect` — set `alias k kill`, disconnect, reconnect, send `alias`, assert listing contains the ROM-format `"    k:  kill"`. Exercises the DB JSON column round-trip end-to-end. No drift.

## Files Modified

- `tests/integration/test_nanny_saveload_runtime_path.py` — new test file, three Mode-B round-trip tests.
- `docs/parity/NANNY_C_AUDIT.md` — added NANNY-SAVELOAD-001..003 rows (all ✅ VERIFIED).
- `CHANGELOG.md` — `[2.8.35]` section.
- `pyproject.toml` — 2.8.34 → 2.8.35.
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer + follow-up backlog.

## Test Status

- Targeted (`tests/integration/test_nanny_saveload_runtime_path.py`): 3/3 passing.
- Full suite (`./venv/bin/python -m pytest -q --timeout=60`): **4606 passed, 4 skipped** (+3 vs prior baseline 4603/4; zero regressions).

## Next Steps

Plan Task 4 is done. Two natural next slices:

1. **Plan Task 5 — re-audit a high-risk user-visible command family.** The tracker calls out healer/shop/train/practice, communication (`say/tell/emote/pose/pmote`), and notes/boards as "player notices drift immediately" surfaces. Pick one and convert weak smoke tests to Mode-B transcript-parity assertions.

2. **PROMPT-CMD parity slice** (surfaced by NANNY-SAVELOAD-002 probe):
   - **PROMPT-CMD-001** — preserve trailing whitespace on `prompt <template>` (dispatcher trim vs. ROM raw-argument behavior).
   - **PROMPT-CMD-002** — `do_prompt` success reply should echo the stored template (`"Prompt set to %s"`), not the truncated `"Prompt set."`.
   Small, contained, one-test-each. Good warm-up for the next session.

Repo hygiene reminder: `log/orphaned_helps.txt` is still tracked and keeps drifting on test runs. Consider `git rm --cached` + `.gitignore` entry in a small future commit.
