# Session Summary — 2026-05-23 — TELL-006 + PROMPT-CMD-004/005 hygiene pass

## Scope

Short hygiene pass immediately after the act_comm.c channel re-audit
arc shipped to origin (`886d560`). Closed the three remaining
warm-ups on the act_comm.c / act_info.c shelf so the next session
can open against a fresh audit target.

## Outcomes

### `TELL-006` — ✅ ANALYZED-INERT (2.8.53 / `bd21cba`)

- **ROM C**: `src/act_comm.c:893,926,937`
- **Python**: `mud/commands/communication.py:_handle_buffered_tell` (no change)
- **Analysis**: ROM does `buf[0] = UPPER(buf[0])` on the buffered
  tell string. The formatted string always begins with `'{'` (the
  colour code `{k`), and `UPPER('{') == '{'` since `{` is not
  lowercase. The transformation is provably a no-op in ROM C itself
  — not "masked by Python code path" like TELL-004; structurally
  unreachable.
- **Close**: doc-only. `docs/parity/ACT_COMM_C_AUDIT.md` row flipped
  from 🔄 OPEN to ✅ ANALYZED. No test (a tautology test would assert
  identity transformation). With this, the do_tell gap row
  (TELL-001..006) is fully closed.

### `PROMPT-CMD-004` — ✅ FIXED — 50-char truncation (2.8.54 / `e9f026c`)

- **Python**: `mud/commands/auto_settings.py:do_prompt`
- **ROM C**: `src/act_info.c:943-944`
- **Fix**: `if len(arg) > 50: arg = arg[:50]` before `smash_tilde`,
  matching ROM's `if (strlen(argument) > 50) argument[50] = '\0';`.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_004_truncates_template_to_50_chars`.

### `PROMPT-CMD-005` — ✅ FIXED — trailing space unless `%c` suffix (2.8.54 / `e9f026c`)

- **Python**: `mud/commands/auto_settings.py:do_prompt`
- **ROM C**: `src/act_info.c:946-947`, `src/db.c:3784` (`str_suffix`)
- **Fix**: `if not arg.endswith("%c"): arg = arg + " "` after
  `smash_tilde` and the 50-char truncation. ROM's `str_suffix`
  returns TRUE when the suffix is *not* a match, so the strcat
  fires for every template that doesn't already end with the
  colour-code escape.
- **Test**: `tests/integration/test_prompt_cmd_parity.py::test_prompt_cmd_005_appends_trailing_space_unless_pct_c_suffix`.
- **Legacy test updates**: `tests/test_player_prompt.py` (×4) and
  `tests/integration/test_prompt_rom_parity.py` (×1) flipped from
  pre-fix expectations to ROM-exact stored values (per AGENTS.md
  "ROM is the source of truth" rule).

## Committed jointly (004 + 005)

PROMPT-CMD-004 and PROMPT-CMD-005 share the same 4-line ROM block
(`src/act_info.c:943-947`) and the legacy test assertions in
`tests/test_player_prompt.py` couple both fixes; splitting would
require asserting transient half-states (e.g. `"a"*100 + " "` in a
commit that has 005 but not 004). Committed jointly with both gap
IDs explicit in the message.

## Files Modified

- `mud/commands/auto_settings.py` — `do_prompt`: added truncation + trailing-space normalization.
- `tests/integration/test_prompt_cmd_parity.py` — two new tests (004, 005).
- `tests/test_player_prompt.py` — 4 legacy assertions updated to ROM-true stored values.
- `tests/integration/test_prompt_rom_parity.py` — 1 legacy assertion updated.
- `docs/parity/ACT_COMM_C_AUDIT.md` — TELL-006 row flipped to ✅ ANALYZED.
- `docs/parity/ACT_INFO_C_AUDIT.md` — `do_prompt` notes column lists PROMPT-CMD-001..005 all ✅ FIXED.
- `CHANGELOG.md` — `[2.8.53]` and `[2.8.54]` sections.
- `pyproject.toml` — 2.8.52 → 2.8.53 → 2.8.54.

## Test Status

- Targeted (prompt suites): 22/22 passing.
- Full suite at 2.8.54: **4631 passed, 4 skipped** (+2 vs 2.8.52; zero regressions).

## Commits this session

| Hash | Version | Subject |
|------|---------|---------|
| `bd21cba` | 2.8.53 | docs(parity): TELL-006 closed as analyzed-inert (no-op UPPER on '{') |
| `e9f026c` | 2.8.54 | fix(parity): do_prompt 50-char truncation + trailing space append |

Plus this handoff commit.

## Next Steps

Channel-message arc complete, do_prompt shelf complete, TELL-006
closed. Remaining shelf items:

1. **PMOTE-001** — `do_pmote` greenfield port. ROM ~50 lines of C
   with per-recipient second-person name substitution +
   apostrophe/possessive handling. Larger; deserves its own session.
2. **New audit target outside act_comm.c / act_info.c**. Highest-value
   candidates now that `pers()` is broadly used:
   - **Combat death messaging** (`mud/combat/engine.py`,
     `mud/handler.py:extract_obj/raw_kill`) — likely contains
     analogous PERS gaps for `$n killed $N`-style act() lines.
   - **Healer / shop / train / practice** transactional commands
     (`act_obj.c` / `act_wiz.c`) per tracker priority.

Recommendation: **combat death messaging** — same PERS gap pattern
the channel arc just normalized; helper is warm; integration test
fixtures (`movable_char_factory`, `_make_online`) are already
in-hand.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifting on every test
  run. Repo hygiene commit (`git rm --cached log/orphaned_helps.txt`
  + `.gitignore` entry) is overdue.
- GitNexus index stale (last indexed at `de1893f`). Re-run
  `npx gitnexus analyze --skip-agents-md` before the next session
  that needs `gitnexus_impact`.
- Local commits `bd21cba` and `e9f026c` (+ this handoff) not pushed
  yet — waiting on explicit user push approval.
