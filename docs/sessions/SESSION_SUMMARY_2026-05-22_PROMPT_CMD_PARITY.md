# Session Summary — 2026-05-22 — `do_prompt` command-side parity (PROMPT-CMD-001/002)

## Scope

Followed up the 2.8.35 NANNY-SAVELOAD-002 probe finding — the
persistence layer for the prompt template was clean, but the
`do_prompt` command path itself diverged from ROM `src/act_info.c:919-955`
in two ways: the dispatcher stripped trailing whitespace from every
command's args before the handler saw them (so `prompt MYTAG> ` lost
the trailing space the player typed), and the success reply was
truncated to `"Prompt set."` instead of ROM's
`"Prompt set to <template>\n\r"`.

## Outcomes

### `PROMPT-CMD-002` — ✅ FIXED — success reply echoes stored template

- **Python**: `mud/commands/auto_settings.py:do_prompt`
- **ROM C**: `src/act_info.c:953-954`
  ```c
  sprintf (buf, "Prompt set to %s\n\r", ch->prompt);
  send_to_char (buf, ch);
  ```
- **Fix**: both the `"all"` branch and the custom-template branch now return `f"Prompt set to {char.prompt}"` instead of the truncated `"Prompt set."` Existing helper tests in `tests/test_player_prompt.py` and the live-websocket round-trip in `tests/integration/test_nanny_saveload_runtime_path.py` updated to the ROM-exact wording.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_002_success_reply_echoes_stored_template`.

### `PROMPT-CMD-001` — ✅ FIXED — trailing whitespace preserved in custom templates

- **Python**: `mud/commands/dispatcher.py:process_command` + `mud/commands/auto_settings.py:do_prompt`
- **ROM C**: `src/act_info.c:944`, `src/interp.c:interpret` — `interpret()` only strips line-ending whitespace from incoming input; `do_prompt` uses the raw `argument` string (after the head's separator-skip), so trailing visible whitespace is preserved into `ch->prompt`.
- **Fix A (dispatcher)**: `core = trimmed.rstrip()` → `core = trimmed.rstrip("\r\n")`. To keep the existing Python log convention (the per-command log line includes the trailing whitespace the player actually typed, even after alias expansion — see `tests/test_logging_admin.py::test_logging_logs_alias_expansion`), the log-line composition now derives `trailing_ws` from `trimmed.rstrip()` rather than from `core` directly. This keeps log behavior identical while letting `core`/`arg_str` carry the trailing visible whitespace through to handlers like `do_prompt` that need it.
- **Fix B (handler)**: `arg = (args or "").strip()` → `arg = args or ""`. Dispatcher already provides args with leading whitespace removed via `_one_argument`; ROM's `do_prompt` doesn't strip its argument; matching that here completes the round-trip.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_001_preserves_trailing_whitespace_on_template` — set `prompt BOB> ` on the live websocket, send `look` to force a fresh prompt render, assert `BOB> ` (with the trailing space) appears in the rendered prompt.

### Investigation discipline

The dispatcher change was a global one (every command now sees trailing
whitespace its args used to be stripped of). Probe approach:

1. Wrote failing tests for both gaps first.
2. Made the smaller PROMPT-CMD-002 fix in isolation, ran targeted suite,
   committed mentally before touching the dispatcher.
3. Made the dispatcher change; one full-suite failure surfaced
   (`test_logging_logs_alias_expansion`, which relied on the previous
   stripped-then-side-channel log composition).
4. Reproduced the breakage, traced it to the log-line side channel,
   and fixed it by re-computing the log-only trailing whitespace via
   `trimmed.rstrip()`. This kept the public log behavior identical
   while letting the handler-side arg flow through unstripped.
5. Re-ran full suite green.

The advisor-style "probe before commit" pattern (used successfully in
2.8.34's INV-009 work) caught this here too: it's a tiny refactor with
large surface area, and a failing test for the suspected behavior
revealed an additional convention that needed preserving.

## Files Modified

- `mud/commands/dispatcher.py` — preserve trailing visible whitespace in `core`; recover log trailing from `trimmed.rstrip()`.
- `mud/commands/auto_settings.py` — `do_prompt` uses raw arg (no `.strip()`); success reply echoes stored template.
- `tests/integration/test_prompt_cmd_parity.py` — new enforcement file (2 tests).
- `tests/test_player_prompt.py` — updated `Prompt set.` → `Prompt set to <template>` assertion.
- `tests/integration/test_nanny_saveload_runtime_path.py` — same update.
- `CHANGELOG.md` — `[2.8.36]` section.
- `pyproject.toml` — 2.8.35 → 2.8.36.
- `docs/sessions/SESSION_STATUS.md` — refreshed pointer.

## Test Status

- Targeted (`tests/integration/test_prompt_cmd_parity.py`): 2/2 passing.
- Adjacent (`tests/test_logging_admin.py`, `tests/test_player_prompt.py`, `tests/integration/test_nanny_saveload_runtime_path.py`): all green after assertion updates.
- Full suite: **4608 passed, 4 skipped** (+2 vs prior baseline 4606/4; zero regressions).

## Next Steps

The 2.8.33 → 2.8.36 arc completes a clean trust-rebuild loop on
`nanny.c` + `save.c` reconnect / save-reload surfaces (NANNY-RECONNECT-001..003,
INV-009, NANNY-SAVELOAD-001..003, PROMPT-CMD-001..002). Two natural
next directions:

1. **Plan Task 5 — re-audit a high-risk command family.** Tracker calls
   out healer / shop / train / practice → communication (`say` /
   `tell` / `emote` / `pose` / `pmote`) → notes / boards → combat
   death messaging. Start with `say` (lowest blast radius — no
   targeting) and audit `src/act_comm.c` end-to-end with Mode-B
   transcript-parity tests for self-message + room-broadcast wording.

2. **smash_tilde on `do_prompt` arg.** ROM `src/act_info.c:945` calls
   `smash_tilde(buf)` before storing to `ch->prompt`. Python's
   `do_prompt` doesn't. Low priority — only matters if the template
   contains `~`, which the player file format treats as a delimiter —
   but cheap to add and is the natural next PROMPT-CMD-003 slice if
   you want one more contained warm-up.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list; `mud/commands/dispatcher.py` is on it. Verified this slice via grep + full suite.
