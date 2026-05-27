# Session Summary — 2026-05-26 — `do_slay` TO_VICT/TO_NOTVICT broadcasts (2.9.50)

## Scope

Continuation of the 2026-05-26 session series. PURGE-001 (2.9.49)
closed the last `_extract_char` stub leak. The deferred SLAY-002 gap
from the SLAY-001 (2.9.48) summary — `do_slay` missing TO_VICT and
TO_NOTVICT room broadcasts (ROM `src/fight.c:3282-3284`) — was the
next adjacent gap. This session closes it.

## Outcomes

### `SLAY-002` — ✅ FIXED (`e61eda5`, 2.9.50)

- **Python**: `mud/commands/imm_load.py:do_slay` — added two broadcasts
  before the `raw_kill(victim)` call: TO_VICT via `_send_to_char` to
  the victim, TO_NOTVICT via a loop over `room.people` (excluding
  both the attacker and the victim) calling `_send_to_char` on each
  bystander.
- **ROM C**: `src/fight.c:3282-3284` — three `act()` calls fire in
  CHAR/VICT/NOTVICT order before `raw_kill`:

      act ("{1You slay $M in cold blood!{x", ch, NULL, victim, TO_CHAR);
      act ("{1$n slays you in cold blood!{x", ch, NULL, victim, TO_VICT);
      act ("{1$n slays $N in cold blood!{x", ch, NULL, victim, TO_NOTVICT);

- **Gap (pre-fix)**: Python returned only the TO_CHAR string. The
  victim and any bystanders saw nothing — pure divergence from ROM
  with no shared infrastructure reason.
- **Ordering note**: broadcasts must fire pre-kill because `raw_kill`
  removes the victim from `room.people`; a post-kill TO_NOTVICT loop
  would still hit bystanders but TO_VICT to a freshly-extracted
  Character would not deliver.
- **Tests**: `tests/integration/test_slay_broadcasts.py` — 1/1:
  - `test_slay_sends_to_vict_and_notvict` — asserts victim receives
    "slays you in cold blood" and a bystander receives "slays $N in
    cold blood" with third-person pronoun.
  Full suite: **4772 passed, 4 skipped** in 1242s.
- **No new INV row** — single-function intra-module fix.

### Deferred (next gap-closer candidates)

- **Position-transition adjacency** — `update_pos` callers
  (do_yell, do_emote-while-down) probe.
- **Group-leader on logout vs persistence** — saved characters with
  `leader != self` reload with dangling pointer reconstituted from
  save format.

## Files Modified

- `mud/commands/imm_load.py` — `do_slay` adds TO_VICT + TO_NOTVICT
  broadcasts before raw_kill
- `tests/integration/test_slay_broadcasts.py` — NEW (1 test)
- `CHANGELOG.md` — 2.9.50 section
- `pyproject.toml` — 2.9.49 → 2.9.50

## Test Status

- `tests/integration/test_slay_broadcasts.py` — 1/1 ✅
- Adjacent suites (`test_slay_routes_through_raw_kill.py`,
  `test_purge_routes_through_extract_character.py`) — 2/2 ✅
- Full suite: **4772 passed, 4 skipped** in 1242s wall-clock

## Next Steps

1. **GitNexus refresh** — index stale (multiple commits behind). Run
   `npx gitnexus analyze --skip-agents-md` before next probe.
2. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers.
   - **Group-leader on logout vs persistence** — dangling pointer
     reconstituted from save format.
