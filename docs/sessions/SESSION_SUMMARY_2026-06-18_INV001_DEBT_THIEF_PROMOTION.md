# Session Summary — 2026-06-18 — INV-001 debt burndown: THIEF promotion line

## Scope

Continued the cross-file / divergence-class sweep (per-file audit tracker
exhausted). Picked up the top actionable follow-up from
`SESSION_STATUS.md` Next Intended Task #1 — **INV-001 debt burndown** —
migrating the 13 frozen `_INV001_DEBT` mailbox-bypass sites in
`tests/test_message_delivery_convention.py` onto the `push_message`
single-delivery chokepoint, one ROM-confirmed TDD fix per site. This session
closed the first and simplest of them: the THIEF promotion line in
`thief_skills.py`.

## Outcomes

### `INV-001` debt — THIEF promotion line — ✅ CLOSED (2.14.120)

- **Python**: `mud/commands/thief_skills.py:_steal_failure` (line ~252)
- **ROM C**: `src/act_obj.c:2256-2261` (`do_steal` PC-on-PC failure → `SET_BIT(ch->act, PLR_THIEF)` + `send_to_char("*** You are now a THIEF!! ***\n\r", ch)`)
- **Gap**: first frozen `_INV001_DEBT` site — `char.messages.append("*** You are now a THIEF!! ***\n")`
- **Fix**: the line was appended straight to the `char.messages` mailbox, which
  the connection read loop only drains after the player's *next* command — a
  connected thief saw the promotion late (INV-001 SINGLE-DELIVERY wrong-channel
  class, same shape as SPEC-017). Routed through the file's existing
  `_send_to_char_sync` → `push_message` chokepoint (async socket for connected
  PCs, mailbox fallback for tests/disconnected), exactly mirroring ROM's
  `send_to_char`. The file already had `_send_to_char_sync` (used by the
  steal-yell loop), so the change is a one-line substitution + a parity comment.
- **Tests**: `tests/integration/test_steal_thief_flag_delivery.py` — 2 new
  (connected-PC socket-once + mailbox-empty; disconnected mailbox fallback).
  Fail-first verified: before the fix the promotion landed in the mailbox while
  the (already-migrated) yell reached the socket. The mailbox-vs-socket split is
  only observable for a connected PC under a running event loop — a disconnected
  char collapses both paths (why this needs a live-loop integration test, not the
  static guard alone).
- Debt allowlist line deleted in `test_message_delivery_convention.py`
  (13 → 12 frozen `_INV001_DEBT` sites). The guard's orphan check enforces the
  deletion.

## Files Modified

- `mud/commands/thief_skills.py` — THIEF promotion line → `_send_to_char_sync`
- `tests/integration/test_steal_thief_flag_delivery.py` — new (2 tests)
- `tests/test_message_delivery_convention.py` — removed THIEF debt allowlist entry
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 row: THIEF announce
  marked ✅ CLOSED (2.14.120); debt site list trimmed
- `CHANGELOG.md` — `Fixed` entry
- `pyproject.toml` — 2.14.119 → 2.14.120

## Test Status

- `pytest tests/integration/test_steal_thief_flag_delivery.py tests/test_message_delivery_convention.py tests/test_skill_steal_rom_parity.py tests/integration/test_inv025_steal_act_trigger_dispatch.py -n0` — 19/19 passing
- `ruff check .` — clean
- `gitnexus_detect_changes` — low risk, only `_steal_failure` touched in production
- Full suite not re-run this session (single-line delivery-channel change, area
  suites green); baseline remains 5812 passing (v2.14.115).

## Next Steps

INV-001 debt burndown continues (Next Intended Task #1 — now 12 frozen sites
left). Remaining candidates, roughly easiest-first:

1. `mud/net/connection.py:766`/`787` — login enter-game broadcast (ROM
   `src/nanny.c:804`/`810-815` `act` TO_ROOM).
2. `mud/commands/dispatcher.py:1201` — snoop forward (ROM `src/comm.c:1393-1398`
   `write_to_buffer(d->snoop_by)`).
3. `mud/commands/communication.py:29` — `_queue_personal_message`.
4. `mud/commands/magic_items.py:319` — wand TO_VICT.
5. `mud/skills/handlers.py` (4 sites) + `mud/skills/registry.py` cluster — the
   `_deliver_message`+`messages.append` dual-channel (`_deliver_message` is a
   third local copy of the chokepoint, DUPL-style — likely a small refactor that
   closes several at once).

Each is one clean ROM-confirmed TDD fix per site, deleting its allowlist line.
Other open follow-ups unchanged from the prior status: DELETE-002, STEAL-015,
INV-050 bool-retirement, `mud/entrypoint.py` dead code. The higher-yield
enumeration-independent lever remains the Hypothesis state-machine →
diff_harness widening (`DIVERGENCE_CLASS_ROSTER.md` Class 11 / Phase C).
