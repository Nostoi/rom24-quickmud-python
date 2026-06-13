# Session Summary — 2026-06-12 — WIZ-051 + cross-file invariants probe (continuation)

## Scope

Continuation session picking up from the INV-046 PHANTOM-REGISTRY closure (v2.14.21). The
per-file audit tracker is now effectively exhausted — the only remaining `🔄 OPEN` rows are the two
deferred track-only DB2 gaps (DB2-004 `kill_table` count, DB2-005 multi-line `fread_string` for
mob/obj fields; both "theoretical only, no user-visible impact in QuickMUD-Python") and a stale
EMOTE-002 status-header at `ACT_COMM_C_AUDIT.md:1007` whose actual gap row (line 1012) is already
✅ FIXED. So this session closed the last live per-file gap (WIZ-051) and moved into the cross-file
invariants pass.

---

## Outcomes

### `WIZ-051` — `find_location` missing object fallback — ✅ FIXED (2.14.22)

- **Python**: `mud/commands/imm_commands.py:37-65` (`find_location`)
- **ROM C**: `src/act_wiz.c:780-795`
- **Gap**: ROM `find_location` resolves a target in three steps — numeric vnum via
  `get_room_index`, a character via `get_char_world` (→ `victim->in_room`), then an **object** via
  `get_obj_world` (→ `obj->in_room`). The Python port stopped after the character lookup, so
  `at <object>` / `goto <object>` / `transfer <player> <object>` answered "No such location."
  instead of targeting the room the object lies in.
- **Fix**: Appended ROM's third fallback — `get_obj_world(char, arg)` (already implemented in
  `mud/world/obj_find.py`) → `obj.in_room`. Purely additive: the new branch only fires where the
  prior code already returned `None`, so no existing behavior changes.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py::test_goto_object_resolves_to_room_object_lies_in`
  (1 new). Full `test_act_wiz_command_parity.py` suite: 121/121 passing.

## Files Modified

- `mud/commands/imm_commands.py` — `find_location` object fallback
- `tests/integration/test_act_wiz_command_parity.py` — 1 new test
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-051 row flipped 🔄 OPEN → ✅ FIXED
- `CHANGELOG.md` — `[2.14.22]` Fixed entry
- `pyproject.toml` — 2.14.21 → 2.14.22

## Test Status

- `pytest tests/integration/test_act_wiz_command_parity.py` — **121/121 passing**
- WIZ-051 test verified failing-before / passing-after (TDD)
- `ruff check` on changed files — clean
- GitNexus MCP was disconnected mid-session (the background reindex cycled the server); blast radius
  for `find_location` was taken from the PreToolUse hook (callers: `do_at`, `do_goto`,
  `do_transfer`) and the additive nature of the change. Per AGENTS.md, the green area suite is the
  regression check when GitNexus is unavailable.

## Outstanding

- **Two xdist flakes** — `test_ac_clamping_for_negative_values`,
  `test_hpcnt_fires_exactly_once_per_violence_tick`; flaked under `-n auto` in an earlier session,
  not yet diagnosed (did not recur in the WIZ-051 area run).
- **DB2-004 / DB2-005** — deferred track-only gaps; no action unless `kill_table` is ported or a
  third-party area uses multi-line `fread_string` for mob/obj single-line fields.
- **Stale doc-header** — `ACT_COMM_C_AUDIT.md:1007` still says "EMOTE-002 🔄 OPEN" though its row is
  ✅ FIXED; cosmetic, fold into a future doc-hygiene pass.

## Next Steps

Cross-file invariants is the active pass (per-file tracker exhausted). Candidate probes (read ROM C
contract → read Python equivalent → one failing test → close as gap or file as next free INV-NNN):

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK and the hunt/track loop vs Python AI.
2. **`weather_update` message fan-out order** — ROM broadcast ordering across the descriptor walk.
3. **`update_handler` pulse cadence** — ROM pulse counters (PULSE_VIOLENCE, PULSE_MOBILE, etc.) vs
   the Python tick scheduler.
4. **Diagnose the two xdist flakes** — isolate with `-n0`, reproduce with `-n auto`.
