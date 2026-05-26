# Session Summary — 2026-05-26 — INV-020 void-quit cleanup-chain (2.9.46)

## Scope

Continuation of the 2026-05-26 session that closed `affect_check`
prototype fallback (2.9.45, pushed). Per SESSION_STATUS, next move was
the PC-quit follower/pet cleanup probe against INV-020. Read ROM
`src/handler.c:2103-2180 extract_char` (the canonical PC-removal
chokepoint), then traced every Python PC-extract trigger to see which
ones funnel through the helper that already does the cleanup and which
ones bypass it. Result: the void-quit path
(`mud/game_loop.py:_auto_quit_character`) bypassed both `_nuke_pets`
and `die_follower`. Closed for the void-quit leg; disconnect-cleanup
leg (`mud/net/connection.py` finally-blocks) split into a follow-up.

## Outcomes

### `INV-020` expansion: RAW-KILL-CLEANUP-CHAIN → EXTRACT-CHAR-CLEANUP-CHAIN — ✅ FIXED (`c9b3937`, 2.9.46)

- **Python**: `mud/game_loop.py:_auto_quit_character` (line 512 area) —
  inserted `_nuke_pets(character) + character.pet = None + die_follower(character)`
  between `save_character` and the existing room/registry cleanup,
  citing ROM `src/handler.c:2117-2122` in a code comment.
- **ROM C**: `src/handler.c:2117-2122` — `nuke_pets(ch); ch->pet =
  NULL; if (fPull) die_follower(ch); stop_fighting(ch, TRUE);`. Every
  PC-extract trigger (`do_quit`, `do_pull`, `raw_kill` for PCs) funnels
  through `extract_char` and therefore through this 4-step cleanup.
- **Gap (pre-fix)**: void-quit leaked both cleanups — charmed pets
  stayed in the world with dangling `master` pointers (still
  `AFF_CHARM`'d, with no living master), and group followers kept
  dangling `leader` pointers at the extracted Character.
  `is_same_group` then false-positives matches via the stale leader
  pointer, the same dangling-pointer hazard INV-020 closed at the
  raw_kill leg.
- **Tests**: `tests/integration/test_inv020_extract_quit_cleanup.py`
  — 2/2:
  - `test_void_quit_nukes_pets` — master + charmed pet (`AFF_CHARM`);
    after `_auto_quit_character(master)`, pet is removed from
    `character_registry` and `master.pet is None`.
  - `test_void_quit_calls_die_follower` — leader + grouped (leader)
    + follower (master); after `_auto_quit_character(leader)`,
    `grouped.leader is grouped` (self-reset, NOT None — `is_same_group`
    would false-positive via dangling pointer otherwise) and
    `follower.master is None`.
  Full suite: **4771 passed, 4 skipped** in 542s.
- **INV-020 row** in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
  renamed `EXTRACT-CHAR-CLEANUP-CHAIN`. Contract rewritten to cover
  all extract triggers (raw_kill + do_quit + void-quit + future
  paths). Added the void-quit enforcement point and listed the
  disconnect-cleanup leg as a deferred follow-up.
- **No new INV row**: per advisor consult, expanded INV-020 in place
  rather than file INV-027. Same ROM mechanism, different triggers —
  keeps invariant budget at 23/~20.

## Files Modified

- `mud/game_loop.py` — `_auto_quit_character` calls `_nuke_pets +
  die_follower`
- `tests/integration/test_inv020_extract_quit_cleanup.py` — NEW (2 tests)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-020 expanded
- `CHANGELOG.md` — 2.9.46 section
- `pyproject.toml` — 2.9.45 → 2.9.46

## Test Status

- `tests/integration/test_inv020_extract_quit_cleanup.py` — 2/2 ✅
- Existing INV-020 raw_kill suite — 4/4 ✅
- Full suite: **4771 passed, 4 skipped** in 542s wall-clock

## Deferred (next gap-closer)

**Disconnect-cleanup leg.** `mud/net/connection.py` telnet+websocket
disconnect `finally`-blocks (lines 1989+, 2263+) also extract the PC
without going through `_nuke_pets + die_follower`. Same gap, different
trigger. Needs a small refactor first — extract a
`_disconnect_cleanup(char)` helper from the anonymous `finally` blocks
so it's testable, then route through the cleanup chain. Tracked in the
INV-020 row "Disconnect-cleanup leg still open" note.

## Next Steps

1. **Push approval** required for 2.9.46 (`c9b3937`).
   Per standing rule: do NOT push without explicit per-cluster
   approval ("yes push v2.9.46 to origin/master").
2. **GitNexus refresh** — index now stale at `5d3ce9d` (three commits
   behind: `cf126f0` 2.9.44, `1ffc06f` 2.9.45, `c9b3937` 2.9.46). Run
   `npx gitnexus analyze --skip-agents-md` before the next probe.
3. **Follow-up gap-closer**: disconnect-cleanup leg (above). Single
   gap, separate commit per one-gap-one-test-one-commit rule.
4. **Probe-then-scope candidates** still on the menu after disconnect-
   leg closes (INV budget 23/~20):
   - **TRIG_KILL / TRIG_DEATH dispatch** — engine.py audit notes
     they're correctly wired but no INV row pins it; would be a
     contract-lock more than a bug find.
   - **Position-transition adjacency** — INV-016 / INV-019 cover
     broadcast and silent-promotion-on-heal sides; the
     `update_pos` callers (do_yell, do_emote-while-down, etc.)
     could surface a missing transition.
