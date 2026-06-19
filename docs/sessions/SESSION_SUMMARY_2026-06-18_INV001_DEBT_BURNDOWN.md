# Session Summary — 2026-06-18 — INV-001 debt burndown (3 sites)

## Scope

Continued the cross-file / divergence-class sweep (per-file audit tracker
exhausted), working the top actionable follow-up from `SESSION_STATUS.md` —
**INV-001 debt burndown**: migrating the frozen `_INV001_DEBT` mailbox-bypass
sites listed in `tests/test_message_delivery_convention.py` onto the
`push_message` single-delivery chokepoint, one ROM-confirmed TDD fix per site,
deleting each allowlist line as it closes. This session closed **three** sites
(13 → 10 frozen), each a separate failing-test-first commit.

Every site is the same INV-001 SINGLE-DELIVERY wrong-channel class: a line
appended straight to `<entity>.messages` (the mailbox) which the connection read
loop only drains after the player's *next* command, so an idle **connected** PC
sees the line late. The fix routes it through `push_message` (async socket for
connected PCs under the live loop, mailbox fallback for tests/disconnected). The
divergence is only observable for a connected PC under a running event loop — a
disconnected char collapses both paths — so each test is a live-loop integration
test, not a static-guard assertion.

## Outcomes

### `INV-001` debt — THIEF promotion line — ✅ CLOSED (2.14.120, commit 8ef44cda)

- **Python**: `mud/commands/thief_skills.py:_steal_failure`
- **ROM C**: `src/act_obj.c:2256-2261` (`SET_BIT(PLR_THIEF)` + `send_to_char("*** You are now a THIEF!! ***")`)
- **Fix**: the "*** You are now a THIEF!! ***" line (PC caught stealing from a
  PC) → routed through the file's existing `_send_to_char_sync` → `push_message`.
- **Test**: `tests/integration/test_steal_thief_flag_delivery.py` (2 tests).

### `INV-001` debt — login enter-game broadcast — ✅ CLOSED (2.14.121, commit 22865df8)

- **Python**: `mud/net/connection.py:broadcast_entry_to_room`
- **ROM C**: `src/nanny.c:804`, `813-814` (`act("$n has entered the game.", TO_ROOM)`, char + pet)
- **Fix**: both per-recipient `act_format` legs (char arrival + pet arrival) →
  `push_message`. The per-occupant loop is **kept** — ROM's `act` TO_ROOM masks
  `$n` per recipient via `can_see`, which a single pre-formatted `Room.broadcast`
  would lose. Added `from mud.utils.messaging import push_message`.
- **Test**: `tests/integration/test_nanny_login_parity.py::test_login_entry_reaches_connected_onlooker_on_socket`.
  The two pre-existing disconnected-mailbox assertions stay green (fallback).

### `INV-001` debt — wand zap TO_VICT — ✅ CLOSED (2.14.122, commit 53226411)

- **Python**: `mud/commands/magic_items.py:do_zap`
- **ROM C**: `src/act_obj.c:2125` (`act("$n zaps you with $p.", TO_VICT)`)
- **Fix**: the "$n zaps you with $p." victim line → `push_message` (sibling
  TO_ROOM/TO_NOTVICT legs already used the correct `_broadcast`→`act_to_room`
  chokepoint). The line fires *before* the wand's success/failure roll, so
  delivery is deterministic. Added the messaging import.
- **Test**: `tests/integration/test_consumables.py::test_zap_victim_message_reaches_connected_victim_on_socket`.

## Files Modified

- `mud/commands/thief_skills.py`, `mud/net/connection.py`,
  `mud/commands/magic_items.py` — the three delivery migrations
- `tests/integration/test_steal_thief_flag_delivery.py` — new
- `tests/integration/test_nanny_login_parity.py` — +1 connected-socket test
- `tests/integration/test_consumables.py` — +1 connected-socket test
- `tests/test_message_delivery_convention.py` — 3 debt allowlist lines deleted
  (the orphan check enforces each deletion)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 row: three closure notes
- `CHANGELOG.md` — three `Fixed` entries
- `pyproject.toml` — 2.14.119 → 2.14.122

## Test Status

- Touched-area sweep (consumables / nanny-login / steal / message-delivery guard
  / room-broadcast / spec017): 98/98 passing
- `ruff check .` — clean (ruff-format hook reformatted `test_consumables.py`
  once; re-staged)
- `gitnexus_detect_changes` — low risk on all three commits; only the target
  function touched in production each time
- Full suite not re-run end-to-end (three single-line delivery-channel changes,
  all area suites green); baseline remains 5812 passing (v2.14.115).

## Next Steps

INV-001 debt burndown continues — **10 frozen `_INV001_DEBT` sites remain**.
Remaining candidates (see the INV-001 row's grep-guard paragraph for the live
list), roughly easiest-first:

1. `mud/commands/dispatcher.py:1201` — snoop forward (ROM `src/comm.c:1393-1398`
   `write_to_buffer(d->snoop_by)`). Note snoop targets the *snooper's*
   descriptor, not the snooped char — verify the recipient before migrating.
2. `mud/commands/communication.py:29` — `_queue_personal_message` (a deferred
   mailbox path — confirm it isn't intentionally mailbox-only before changing).
3. `mud/skills/handlers.py` (4 sites: 2248/2271/2310/2483) +
   `mud/skills/registry.py` (4 sites: 161/197/345/353) — the
   `_deliver_message`+`messages.append` dual-channel. `_deliver_message` is a
   third local copy of the chokepoint (DUPL-style); migrating it likely closes
   several sites at once via one refactor — the highest-yield remaining target.

Each is one clean ROM-confirmed TDD fix per site, deleting its allowlist line.
Other open follow-ups unchanged: DELETE-002, STEAL-015, INV-050 bool-retirement,
`mud/entrypoint.py` dead code. Higher-yield enumeration-independent lever per
`docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine → diff_harness
widening (Class 11 / Phase C).
