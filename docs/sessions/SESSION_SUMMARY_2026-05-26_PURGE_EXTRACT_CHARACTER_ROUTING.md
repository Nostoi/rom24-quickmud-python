# Session Summary — 2026-05-26 — `do_purge` routes through `_extract_character` (2.9.49)

## Scope

Continuation of the 2026-05-26 session series. SLAY-001 closed the
`do_slay` half of the local stripped `_extract_char` stub leak in
`mud/commands/imm_load.py`. The adjacent `do_purge` leg — 3 call sites
to the same stub — was filed as the next gap-closer. This session
closes it.

## Outcomes

### `PURGE-001` — ✅ FIXED (`f71c422`, 2.9.49)

- **Python**: `mud/commands/imm_load.py:do_purge` — three call sites
  (room-purge loop line 187, named-player line 216, named-NPC line
  220) now call `mud.mob_cmds._extract_character(victim)`. The local
  stripped `_extract_char` stub was removed entirely.
- **ROM C**: `src/act_wiz.c:2595, 2638, 2646` — all three sites call
  `extract_char(victim, TRUE)`. `extract_char` in ROM
  (`src/handler.c:2103-2180`) runs `nuke_pets` → `die_follower` →
  `stop_fighting` → inventory extraction → unlink from room → remove
  from char_list.
- **Gap (pre-fix)**: the local stub only stopped fighting, unlinked
  from `room.people`, and removed from `registry.char_list`. No pet
  cleanup, no follower cleanup, no inventory extraction. An immortal
  purging a charmed pet's master left the pet in the world with a
  dangling `master` pointer and `AFF_CHARM` still set — the same
  dangling-pointer hazard INV-020 was created to close.
- **Tests**: `tests/integration/test_purge_routes_through_extract_character.py`
  — 1/1:
  - `test_purge_room_nukes_pets` — pins the pet-cleanup leg.
    Follower leg is already covered by INV-020's chain test grid via
    the shared `_extract_character` helper.
  Full suite: **4771 passed, 4 skipped** in 487s.
- **No new INV row** — same INV-020 contract, additional caller routed
  through the canonical chokepoint.

### Deferred (next gap-closer candidates)

- **`do_slay` missing TO_VICT / TO_NOTVICT broadcasts** — ROM
  `src/fight.c:3282-3284` calls three `act` messages before
  `raw_kill`. Python only returns the TO_CHAR message. One-line fix.
- **Position-transition adjacency** — `update_pos` callers
  (do_yell, do_emote-while-down) probe — potential missed transitions
  beyond INV-016 / INV-019.
- **Group-leader on logout vs persistence** — saved characters with
  `leader != self` reload with dangling pointer reconstituted from
  save format.

## Files Modified

- `mud/commands/imm_load.py` — three `_extract_char(victim)` calls →
  `_extract_character(victim)`; removed local stub; added
  `from mud.mob_cmds import _extract_character` import
- `tests/integration/test_purge_routes_through_extract_character.py` — NEW (1 test)
- `CHANGELOG.md` — 2.9.49 section
- `pyproject.toml` — 2.9.48 → 2.9.49

## Test Status

- `tests/integration/test_purge_routes_through_extract_character.py` — 1/1 ✅
- `tests/integration/test_act_wiz_command_parity.py` purge tests — 4/4 ✅
- Adjacent suites (slay/INV-020 chain) — 6/6 ✅
- Full suite: **4771 passed, 4 skipped** in 487s wall-clock

## Next Steps

1. **Push approval** required for 2.9.49 (`f71c422`). Per standing
   rule: do NOT push without explicit per-cluster approval
   ("yes push v2.9.49 to origin/master").
2. **GitNexus refresh** — index stale at `069f17f` (5 commits behind).
   Run `npx gitnexus analyze --skip-agents-md` before next probe.
3. **`do_slay` broadcast gap** — TO_VICT/TO_NOTVICT act messages.
4. **Probe-then-scope candidates remaining**:
   - **Position-transition adjacency** — `update_pos` callers.
   - **Group-leader on logout vs persistence** — dangling pointer
     reconstituted from save format.
