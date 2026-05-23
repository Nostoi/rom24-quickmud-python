# Session Summary — 2026-05-23 — `do_shout` + `do_yell` re-audit (SHOUT-001..003, YELL-001)

## Scope

Fifth (and final-for-the-arc) slice of the 2026-05-22 → 2026-05-23
`act_comm.c` channel re-audit. Closed three `do_shout` gaps and one
`do_yell` gap in four TDD commits. With this slice the entire
five-command channel-message arc (`do_say` / `do_emote` / `do_tell`
/ `do_shout` / `do_yell`) is re-audited and ROM-faithful: every `$n`
substitution routes through `pers()`, every wording matches
ROM-exact, every channel that uses ROM colour codes wraps them.

## Outcomes

### `SHOUT-001` — ✅ FIXED — `do_shout` TO_CHAR drops comma (2.8.49 / `21f1b80`)

- **Python**: `mud/commands/communication.py:do_shout` return
- **ROM C**: `src/act_comm.c:824`
- **Fix**: `"You shout, '..'"` → `"You shout '..'"`. Legacy assertions in `tests/test_communication.py` (×2) updated.
- **Test**: `tests/integration/test_shout_yell_parity.py::test_shout_001_to_char_wording_drops_comma`.

### `SHOUT-002` — ✅ FIXED — `do_shout` TO_VICT drops comma (2.8.50 / `9e55e1a`)

- **Python**: `mud/commands/communication.py:do_shout` broadcast message
- **ROM C**: `src/act_comm.c:836`
- **Fix**: `"{n} shouts, '..'"` → `"{n} shouts '..'"`. Legacy assertions in `tests/test_communication.py` (×2) updated.
- **Test**: `tests/integration/test_shout_yell_parity.py::test_shout_002_to_vict_wording_drops_comma`.

### `SHOUT-003` — ✅ FIXED — `do_shout` PERS substitution for invisible shouter (2.8.51 / `78ad2cb`)

- **Python**: `mud/commands/communication.py:do_shout`
- **ROM C**: `src/act_comm.c:836`, `src/handler.c:2618`
- **Fix**: Replaced `broadcast_global(message, channel="shout", exclude=char, should_send=_should_receive)` (single fixed message) with a per-listener loop over `character_registry` mirroring ROM's `descriptor_list` iteration. Filters by `SHOUTSOFF` / `QUIET` / muted_channels and renders `pers(char, victim)` per recipient.
- **Test**: `tests/integration/test_shout_yell_parity.py::test_shout_003_invisible_shouter_renders_as_someone_to_listener`.

### `YELL-001` — ✅ FIXED — `do_yell` PERS substitution for invisible yeller (2.8.52 / `5e9e7fc`)

- **Python**: `mud/commands/communication.py:do_yell`
- **ROM C**: `src/act_comm.c:1059`, `src/handler.c:2618`
- **Fix**: One-line swap inside the existing area-wide per-listener loop — `f"{char.name} yells '{args}'"` → `f"{pers(char, victim)} yells '{args}'"`.
- **Test**: `tests/integration/test_shout_yell_parity.py::test_yell_001_invisible_yeller_renders_as_someone_to_listener`.

## Arc-level summary (entire 2026-05-22 → 23 channel re-audit)

| Command | Gaps closed | Releases | Helper used |
|---------|------------|----------|------|
| `do_say` | SAY-001/002/003/004 | 2.8.38–2.8.41 | `pers()` (added 2.8.41) |
| `do_emote` | EMOTE-001/002 | 2.8.42–2.8.43 | `pers()` |
| `do_tell` | TELL-001/002/003/004/005 (006 deferred) | 2.8.44–2.8.48 | `pers()` |
| `do_shout` | SHOUT-001/002/003 | 2.8.49–2.8.51 | `pers()` |
| `do_yell` | YELL-001 | 2.8.52 | `pers()` |

**`pers()` helper now used by all 5 channel commands.** The
audit-doc inflation pattern that hit `do_say` / `do_emote` /
`do_tell` / `do_shout` (all four claimed "100% VERIFIED" but each
had multiple CRITICAL gaps) is now cleaned up across the entire
channel surface.

## Files Modified (this slice)

- `mud/commands/communication.py` — `do_shout` and `do_yell` for all four fixes.
- `tests/integration/test_shout_yell_parity.py` — **new file** — 4 tests (SHOUT-001/002/003, YELL-001).
- `tests/test_communication.py` — updated 4 legacy `shouts, '` / `shout, '` assertions.
- `docs/parity/ACT_COMM_C_AUDIT.md` — `do_shout` and `do_yell` rows demoted from "VERIFIED ✅" to active gap tables; all 4 rows ✅ FIXED.
- `CHANGELOG.md` — `[2.8.49]` → `[2.8.52]` sections.
- `pyproject.toml` — 2.8.48 → 2.8.52.

## Test Status

- Targeted (`tests/integration/test_shout_yell_parity.py`): 4/4 passing.
- Full suite: **4629 passed, 4 skipped** (+4 vs 2.8.48 baseline 4625/4; zero regressions across all four releases).

## Next Steps

The channel-message re-audit arc is **complete**. Remaining items
on the shelf:

1. **PMOTE-001** — `do_pmote` greenfield port. ROM ~50 lines of C
   per-recipient second-person name substitution with apostrophe /
   possessive handling. Larger; its own session.
2. **TELL-006** — uppercase first char of buffered tells. MINOR
   cosmetic; ~5 min warm-up.
3. **PROMPT-CMD-004 / PROMPT-CMD-005** — corner-case `do_prompt`
   warm-ups (50-char truncation, `%c`-suffix → append trailing
   space).
4. **New audit target** — outside `act_comm.c`. Tracker priorities:
   healer / shop / train / practice; combat death messaging
   (likely contains analogous PERS gaps now that the helper is
   broadly used).

Recommendation: take a beat and **push the 4 commits**, then either
start a fresh session on a new audit target, or close the small
warm-ups (TELL-006 + PROMPT-CMD-004/005) as a short hygiene pass.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit overdue.
- GitNexus 32 KB scope-extractor failures persist on the documented file list; this slice did not touch any listed file.
- Local commits `21f1b80..5e9e7fc` (4 fixes) not pushed yet — waiting on explicit user push approval.
