# Session Summary — 2026-05-23 — `fight.c` PERS sweep on `_position_change_message` (FIGHT-004..008)

## Scope

Opened the previously-95%-stuck `fight.c` audit on its
position-change broadcast surface to clear the same PERS pattern
the channel-arc work normalized. Five gaps closed end-to-end in
five TDD commits, plus one hygiene mop-up commit for two
PROMPT-CMD-005 legacy assertions surfaced by the full-suite
verification.

## Outcomes

### `FIGHT-004` — ✅ FIXED — POS_MORTAL TO_ROOM PERS (2.8.55 / `40c0879`)

- **ROM C**: `src/fight.c:837-838`
- **Python**: `mud/combat/engine.py:_position_change_message` MORTAL branch
- **Fix**: New `_broadcast_pos_change` helper iterates `room.people`, calls `mud.world.vision.pers(victim, listener)` per recipient, and dispatches through the same fire-and-forget websocket path as `broadcast_room`. Helper now powers FIGHT-005..007 too.
- **Test**: `tests/integration/test_invisibility_combat.py::TestPositionChangeBroadcastPers::test_fight_004_pos_mortal_broadcast_uses_pers_for_invisible_victim`.

### `FIGHT-005` — ✅ FIXED — POS_INCAP TO_ROOM PERS (2.8.56 / `172360a`)

- **ROM C**: `src/fight.c:845-846`
- **Python**: same function, INCAP branch
- **Fix**: One-line swap to `_broadcast_pos_change(victim, "{name} is incapacitated and will slowly die, if not aided.")`.
- **Test**: `::test_fight_005_pos_incap_broadcast_uses_pers_for_invisible_victim`.

### `FIGHT-006` — ✅ FIXED — POS_STUNNED TO_ROOM PERS (2.8.57 / `2e6020c`)

- **ROM C**: `src/fight.c:853-854`
- **Python**: same function, STUNNED branch
- **Fix**: One-line swap to `_broadcast_pos_change`.
- **Test**: `::test_fight_006_pos_stunned_broadcast_uses_pers_for_invisible_victim`.

### `FIGHT-007` — ✅ FIXED — POS_DEAD TO_ROOM (PERS + `{R{x` + two-bang wording) (2.8.58 / `b9b4a8a`)

- **ROM C**: `src/fight.c:860`
- **Python**: same function, DEAD broadcast
- **Fix**: Three sub-divergences in one CRITICAL gap — (a) PERS substitution; (b) ROM red colour wrap `{R...{x`; (c) `"DEAD!!!"`→`"DEAD!!"` wording typo. Template `"{{R{name} is DEAD!!{{x"` (braces escaped for `str.format`). Legacy assertion in `tests/test_combat.py` updated to ROM-exact form.
- **Test**: `::test_fight_007_pos_dead_broadcast_uses_pers_and_red_colour_and_two_bangs`.

### `FIGHT-008` — ✅ FIXED — POS_DEAD TO_CHAR self-message (`{R{x` + blank-line) (2.8.59 / `120482c`)

- **ROM C**: `src/fight.c:861`
- **Python**: same function, DEAD branch return value
- **Fix**: Return `"{RYou have been KILLED!!{x\n"`. The protocol layer in `mud/net/protocol.py:send_to_char` auto-appends one `\r\n` to every message, so the embedded trailing `\n` plus the auto-append produces the same visual blank-line spacing ROM gets from its two `\n\r` pairs.
- **Test**: `::test_fight_008_pos_dead_self_message_wraps_red_and_appends_blank_line`.

### `PROMPT-CMD-005` legacy-test mop-up (2.8.60 / `895c6d8`)

- Full-suite verification after FIGHT-008 surfaced two pre-existing legacy assertions still expecting the pre-PROMPT-CMD-005 stored value (no trailing space): `tests/integration/test_config_commands.py::test_prompt_custom` and `tests/test_player_auto_settings.py::TestPrompt::test_prompt_set_custom`. Updated both to ROM-true stored values. No production code change.

## Files Modified

- `mud/combat/engine.py` — added `_broadcast_pos_change` helper (39 LOC); refactored all four position-change-message branches to use it; DEAD self-message return updated for colour + blank-line.
- `tests/integration/test_invisibility_combat.py` — new `TestPositionChangeBroadcastPers` class with 5 tests (FIGHT-004..008).
- `tests/test_combat.py` — 1 legacy assertion updated for FIGHT-007.
- `tests/integration/test_config_commands.py` — 1 legacy assertion mopped up for PROMPT-CMD-005.
- `tests/test_player_auto_settings.py` — 1 legacy assertion mopped up for PROMPT-CMD-005.
- `docs/parity/FIGHT_C_AUDIT.md` — status flipped from 95% (stuck) to active sweep; FIGHT-004..008 rows added then closed; FIGHT-009..013 reserved for weapon-proc follow-up.
- `CHANGELOG.md` — `[2.8.55]` through `[2.8.60]` sections.
- `pyproject.toml` — 2.8.54 → 2.8.60.

## Test Status

- Targeted (`tests/integration/test_invisibility_combat.py`): **9/9 passing** (5 new + 4 pre-existing).
- Death-related suites: 44/44 (`test_pc_death_no_message_replay.py`, `test_pc_death_keeps_connection.py`, `test_combat.py`).
- Full suite at 2.8.60: **4632 passed, 4 skipped** (+1 vs 2.8.54; zero regressions).

## Commits this session

| Hash | Version | Subject |
|------|---------|---------|
| `40c0879` | 2.8.55 | fix(parity): fight.c FIGHT-004 — POS_MORTAL broadcast routes through PERS |
| `172360a` | 2.8.56 | fix(parity): fight.c FIGHT-005 — POS_INCAP broadcast routes through PERS |
| `2e6020c` | 2.8.57 | fix(parity): fight.c FIGHT-006 — POS_STUNNED broadcast routes through PERS |
| `b9b4a8a` | 2.8.58 | fix(parity): fight.c FIGHT-007 — POS_DEAD broadcast PERS + red colour + two-bang wording |
| `120482c` | 2.8.59 | fix(parity): fight.c FIGHT-008 — POS_DEAD self-message red colour + blank-line |
| `895c6d8` | 2.8.60 | test(parity): PROMPT-CMD-005 — mop up two missed legacy assertions |

Plus this handoff commit.

## Next Steps

Position-change broadcast surface in `fight.c` is fully cleaned up.
Three reasonable continuations:

1. **FIGHT-009..013 weapon-proc PERS sweep** (recommended — same
   pattern, same helper, same fixtures). `mud/combat/engine.py`
   lines 1496 (poison), 1510 (vampiric), 1531 (flaming), 1541
   (frost), 1551 (shocking). Some also have wording divergences vs
   ROM `src/fight.c:614-675` (e.g. ROM `"$p freezes $n"` rendered
   by Python as `"X is frozen by Y"`).
2. **`dam_message`** — ROM `src/fight.c:2035-2233` is the
   per-hit damage broadcast surface (hundreds of damage-tier
   messages, each with `act()` lines that need PERS). Larger
   surface, but the highest-volume PERS leak in combat by far.
3. **PMOTE-001** — `do_pmote` greenfield port. Still on the
   `act_comm.c` shelf, ~50 lines of C with per-recipient
   second-person substitution.

Recommendation: **FIGHT-009..013** as the natural continuation —
same helper, same test class, hands-off pattern. Then either
`dam_message` or PMOTE-001 for a fresh session.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + drifting on every test run. Repo hygiene commit overdue.
- GitNexus index stale (last indexed `de1893f`). Re-run `npx gitnexus analyze --skip-agents-md` before the next session that needs `gitnexus_impact`.
- Local commits `40c0879..895c6d8` (6 fixes) plus this handoff not pushed yet — waiting on explicit user push approval.
