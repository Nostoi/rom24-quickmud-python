# Session Summary — 2026-05-26 — INV-020 disconnect-cleanup leg (2.9.47)

## Scope

Continuation of the 2026-05-26 session series. INV-020's void-quit leg
landed in 2.9.46 (`c9b3937` + handoff `069f17f` pushed to origin/master).
The disconnect-cleanup leg was the last documented INV-020 hole:
`mud/net/connection.py` telnet+websocket `finally`-blocks treated socket
close as `do_quit` semantics (per INV-009) but bypassed `_nuke_pets` +
`die_follower`. Closed by extracting a `_disconnect_extract_cleanup`
helper from the anonymous `finally`-block code and routing both
disconnect paths through it.

## Outcomes

### `INV-020` disconnect leg — ✅ FIXED (`16a5d97`, 2.9.47)

- **Python**: `mud/net/connection.py:_disconnect_extract_cleanup` (new
  module-level helper) — calls `_nuke_pets(char, room=char.room) +
  char.pet = None + die_follower(char)`, mirroring ROM
  `src/handler.c:2117-2122 extract_char`. Wired into both telnet
  (line ~2020+) and websocket (line ~2294+) disconnect `finally`
  blocks before the existing `char.room.remove_character` cleanup,
  gated on `not forced_disconnect`.
- **ROM C**: `src/handler.c:2117-2122` extract_char (same chain
  enforced for the raw_kill leg of INV-020 since v2.9.x).
- **Why gated on `not forced_disconnect`**: `_disconnect_session`
  transfers the live Character to a new descriptor on a forced
  disconnect (reconnect path). The Character is not being extracted
  there — running `_nuke_pets + die_follower` would wrongly destroy
  the pet and reset followers on a reconnect. The gate matches the
  pre-existing `INV-009 REGISTRY-DISCONNECT-CLEANUP` gate.
- **Tests**: `tests/integration/test_inv020_extract_quit_cleanup.py`
  extended — 2 new tests (4/4 total):
  - `test_disconnect_nukes_pets` — master + charmed pet (`AFF_CHARM`);
    after `_disconnect_extract_cleanup(master)`, pet is removed from
    `character_registry` and `master.pet is None`.
  - `test_disconnect_calls_die_follower` — leader + grouped (leader)
    + follower (master); after `_disconnect_extract_cleanup(leader)`,
    `grouped.leader is grouped` (self-reset, NOT None) and
    `follower.master is None`.
  Helper-extraction made the contract testable without standing up a
  real socket (advisor's blocking concern from 2.9.46 — resolved).
  Full suite: **4773 passed, 4 skipped** in 464s.
- **INV-020 row** in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
  amended: pending "Disconnect-cleanup leg still open" note removed,
  point (f) added documenting the new helper. All four PC-extract
  triggers (raw_kill, void-quit, `_extract_character`, socket
  disconnect) now funnel through `_nuke_pets + die_follower`.

## Files Modified

- `mud/net/connection.py` — `_disconnect_extract_cleanup` helper +
  wired into both `finally` blocks
- `tests/integration/test_inv020_extract_quit_cleanup.py` — 2 new
  tests (4/4)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-020 amended
- `CHANGELOG.md` — 2.9.47 section
- `pyproject.toml` — 2.9.46 → 2.9.47

## Test Status

- `tests/integration/test_inv020_extract_quit_cleanup.py` — 4/4 ✅
- Connection-area suites (websocket + integration filter `connection
  or websocket or quit or extract`) — 34/34 ✅
- `ruff check mud/net/connection.py tests/...` — clean
- Full suite: **4773 passed, 4 skipped** in 464s wall-clock

## Next Steps

1. **Push approval** required for 2.9.47 (`16a5d97`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.47 to origin/master").
2. **GitNexus refresh** — index now stale at `069f17f` (2 commits
   behind: `c9b3937` 2.9.46, `16a5d97` 2.9.47). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **INV-020 is now fully enforced**. Probe-then-scope candidates
   still on the menu (INV budget 23/~20):
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     wired correctly but no INV row pins it; would be a contract-lock
     more than a bug find.
   - **Position-transition adjacency** — INV-016 / INV-019 cover
     broadcast and silent-promotion-on-heal sides; the `update_pos`
     callers (do_yell, do_emote-while-down) could surface a missing
     transition.
   - **Group-leader on logout vs persistence** — saved characters
     with `leader != self` reload with the dangling pointer
     reconstituted from save format; worth a probe.
