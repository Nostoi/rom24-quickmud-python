# Session Summary — 2026-05-02 — combat-bug triage (player stops attacking)

## Reported

User session log showed:
- (a) Mobs (snail, boar) present in school's "A Safe Room" (vnum 3760).
- (b) After `kill snail` produced 3 "You scratch the snail." messages, the
  player never attacked again. The snail kept attacking on a 3-second
  cadence (PULSE_VIOLENCE). `kill snail` retried later returned
  "You do the best you can!" — i.e. the player was still in fighting state
  but no swings reached the WS client.

## Findings

### (a) Safe-room with mobs — **not a bug, ROM-faithful**

Room 3760 in `area/school.are` is named "A Safe Room" in narrative text but
its room flags are `CD` = `ROOM_NO_MOB` | `ROOM_INDOORS`. The actual
`ROOM_SAFE` flag (letter `K`) is **not set** in the .are source. ROM stock
data behaves identically — mobs can wander in. Closing this as
expected behavior, not a bug.

### (b) Player stops attacking — **not reproducible in deterministic test**

Two repros (one with `create_test_character`, one with the real
`load_character` path + an attached `connection`-like object) both show
combat working correctly:

```
tick 0: char.fighting=True pos=FIGHTING snail.hit=99 | you_msgs=1 snail_msgs=1
tick 1: char.fighting=True pos=FIGHTING snail.hit=98 | you_msgs=1 snail_msgs=1
tick 2: char.fighting=True pos=FIGHTING snail.hit=97 | you_msgs=1 snail_msgs=1
...
```

So the engine logic is sound. Whatever's broken is **specific to the live
WebSocket session** — likely either (1) two PC instances in
`character_registry` (real one with connection vs. a stale one without
`fighting` set), (2) a swallowed exception inside `multi_hit` for the PC
that `mud/game_loop.py:async_game_loop`'s catch-all silently traps, or
(3) message-dispatch routing that skips PC attacker messages while still
delivering victim messages from the snail.

### Live-session diagnostic added (uncommitted)

Added an env-gated debug print to `mud/game_loop.py:violence_tick`. With
`MUD_DEBUG_VIOLENCE=1` set, the loop prints per-pulse PC state and catches
per-character `multi_hit` exceptions instead of letting them bubble to the
async-loop catch-all.

To capture the bug:

```sh
MUD_DEBUG_VIOLENCE=1 python3 -m uvicorn mud.network.websocket_server:app
# (or however the server normally starts)
```

Then connect via the WS client, repro the empty-arena fight, and watch
stdout. Look for either:

- **No `[VIOL] pc=Eddol …` lines while combat tick is firing for the snail**
  → registry mismatch (PC isn't in `character_registry`, or fighting is
  None on the registry copy).
- **`[VIOL] pc=Eddol fighting=…` followed by `[VIOL] multi_hit raised …`**
  → an exception inside the PC's `multi_hit` is the proximate cause.
  Stack trace will tell us the line.
- **`[VIOL] pc=Eddol fighting=… same_room=False`** → room-identity
  mismatch (two `Room` instances for the same vnum).

### Parity gaps surfaced (separate FIGHT-XXX entries — do NOT bundle)

Two real ROM divergences became visible while reading the code, but neither
explains bug (b):

1. **`do_kill` calls `attack_round` (one swing); ROM calls `multi_hit`
   (multi-swing).** `mud/commands/combat.py:125`. ROM `src/fight.c:2817`
   does `multi_hit (ch, victim, TYPE_UNDEFINED)`. Worth a FIGHT-XXX entry
   in the audit tracker.
2. **`is_safe()` is implemented but not gated inside the damage path.**
   `mud/combat/safety.py:is_safe` exists and is called from `consider`,
   `murder`, `dirt`/`trip`/`disarm`, and assist logic. ROM
   (`src/fight.c:731`, `src/fight.c:2405-2928`) calls `is_safe(ch, victim)`
   inside `damage()` and inside every special-attack handler — meaning
   once two combatants drag into a safe room mid-fight, ROM stops the
   damage exchange. Python keeps swinging. Worth a second FIGHT-XXX entry.

The `_kill_safety_message` in `mud/commands/combat.py:27` only runs at
`do_kill` entry, so it doesn't cover this case either.

## What landed in this session

- `mud/game_loop.py:violence_tick` — env-gated debug instrumentation
  (`MUD_DEBUG_VIOLENCE=1`). No behavior change when the env var is unset.
  Combat suite (`tests/test_fighting_state.py`, 16 tests) still green.
- This summary document.

## What did NOT land (intentionally)

- `do_kill` → `multi_hit` parity fix.
- `is_safe` gate inside `apply_damage`/damage path.
- Message-duplication investigation (3-paths theory: `_push_message`'s
  mailbox append + `send_to_char`'s mailbox append + dispatcher's response
  send).

These are separate audit items. Shipping them as part of a "fix combat
bug" commit before reproducing the live failure would muddy the bisect
record if the bug recurs.

## Next step

User reproduces with `MUD_DEBUG_VIOLENCE=1` and captures server stdout.
Without that signal, further debugging is blind. After we have the print
trace, the actual fix becomes a one- or two-line patch and we ship it
with a focused commit message.

## Pointer refresh

`SESSION_STATUS.md` next: point at this summary and reset "next intended
task" to either (a) await user's diagnostic capture, or (b) resume the
hedit rewrite (still the broad-sweep blocker) if user redirects.
