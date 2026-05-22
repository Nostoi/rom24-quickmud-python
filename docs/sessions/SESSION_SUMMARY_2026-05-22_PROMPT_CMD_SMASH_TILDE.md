# Session Summary — 2026-05-22 — `do_prompt` smash_tilde parity (PROMPT-CMD-003)

## Scope

Closed the PROMPT-CMD cluster opened by 2.8.35's NANNY-SAVELOAD-002
probe. PROMPT-CMD-001/002 landed in 2.8.36; PROMPT-CMD-003 lands here.
ROM `src/act_info.c:945` runs `smash_tilde(buf)` on the custom prompt
template before storing to `ch->prompt`, replacing every `~` with `-`
so the stored string cannot corrupt the player file on save (ROM uses
`~` as the end-of-string marker on disk). Python's `do_prompt`
previously stored the raw argument including any tildes the player
typed.

## Outcomes

### `PROMPT-CMD-003` — ✅ FIXED — `smash_tilde` on custom prompt template

- **Python**: `mud/commands/auto_settings.py:do_prompt` (custom-template branch)
- **ROM C**: `src/act_info.c:945`, `src/db.c:3663-3672`
  ```c
  strcpy (buf, argument);
  smash_tilde (buf);
  ...
  ch->prompt = str_dup (buf);
  ```
- **Fix**: After the trailing-space normalization from PROMPT-CMD-001
  but before assigning to `char.prompt`, call
  `mud.utils.text.smash_tilde(arg)`. The "all" branch is unaffected
  because the constant template `"<%hhp %mm %vmv> "` contains no
  tildes.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_003_smash_tilde_on_custom_template`
  — sets `prompt T~AG>` on the live websocket, asserts the success
  reply echoes `"Prompt set to T-AG>"` (tildes replaced), and verifies
  the raw tilde does not leak through.

## Two ROM-divergence corners deferred (stable-IDed for future)

While reading the ROM block I confirmed two additional minor
divergences from `src/act_info.c:919-955`. Both are corner cases — no
behavioral impact on typical play — so they are captured for future
hardening rather than closed here (one gap = one test = one commit
discipline):

- **PROMPT-CMD-004** — 50-char truncation. ROM trims `argument` to 50
  bytes before `strcpy`/`smash_tilde`. Python stores the full string.
- **PROMPT-CMD-005** — `%c` suffix → append trailing space. ROM tests
  `str_suffix("%c", buf)` and appends `" "` so the cursor doesn't
  hug the next character. Python does not.

Both rows recorded in `docs/parity/ACT_INFO_C_AUDIT.md`.

## Files Modified

- `mud/commands/auto_settings.py` — `do_prompt` calls `smash_tilde` on the custom-template branch before storing.
- `tests/integration/test_prompt_cmd_parity.py` — added `test_prompt_cmd_003_smash_tilde_on_custom_template`.
- `docs/parity/ACT_INFO_C_AUDIT.md` — `do_prompt` row updated: PROMPT-CMD-001/002/003 all ✅ FIXED; PROMPT-CMD-004/005 stable-IDed for future.
- `CHANGELOG.md` — `[2.8.37]` section.
- `pyproject.toml` — 2.8.36 → 2.8.37.
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer.

## Test Status

- Targeted (`tests/integration/test_prompt_cmd_parity.py`): 3/3 passing.
- Full suite: **4609 passed, 4 skipped** (+1 vs prior 4608/4; zero regressions).

## Next Steps

PROMPT-CMD cluster closed. Natural next direction (per user pick
already made for this session run): **Plan Task 5 — re-audit a
high-risk command family.** Tracker recommendation: start with `say`
in `src/act_comm.c` (lowest blast radius — no targeting) and walk it
end-to-end with Mode-B transcript-parity tests for self-message and
room-broadcast wording. Probably the cleanest order:

1. Audit `do_say` against `src/act_comm.c` end-to-end (one
   `rom-parity-audit` invocation against `act_comm.c`).
2. Gap-close any divergences one ID at a time (`rom-gap-closer`
   per gap).
3. Session-handoff when done.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list. `mud/commands/dispatcher.py` is on it; this slice did not touch the dispatcher so no fallback was needed.
- PROMPT-CMD-004 / PROMPT-CMD-005 stable-IDed but not closed — corner-case hardening for a later session.
