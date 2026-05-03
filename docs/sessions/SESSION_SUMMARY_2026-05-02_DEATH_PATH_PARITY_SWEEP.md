# Session Summary — 2026-05-02 — Death-path parity sweep

## Reported

User log (`~/mud-death.log`, `2026-05-02T22:07:53→22:08:11`) showed
two visible symptoms after a PC was killed by a lizard in the school
arena:

1. Prompt rendered `<0hp 100m 100mv>` for one cycle after death,
   then `<1hp ...>` after the next `look`.
2. After the `look` returned the Temple Altar room description (a
   correct respawn), the SAME "lizard scratches you / mortally
   wounded / KILLED!!" sequence rendered AGAIN with timestamps
   milliseconds apart, even though the lizard was in a far-away
   room. User read this as "I died twice and got disconnected."

## Findings (subagent triage — 4 parallel Explore agents)

The disconnect symptom in the original report was a misread. The
log proves the WS connection survived death — the `look` after
respawn worked, the prompt updated. The actual bugs were:

**Finding 1 (MAJOR) — duplicate message delivery.**
`mud/combat/engine.py:205-227` `_push_message` did BOTH:
- `asyncio.create_task(_send(character, message))` — async send.
- `mailbox.append(message)` — unconditional queue append.

`mud/net/connection.py:1756-1762` then drained `char.messages` after
every command. `messages` is initialized on every `Character` at
`mud/models/character.py:398`, so the "test fallback" docstring was
false in production. Net effect: every combat message reached the
WS client TWICE — once via the async path during the tick, once via
the read-loop drain on the next command. The 13s gap in the user
log matches: messages queued during the death tick, then drained
when the user typed `look`. The "second death" was the first death
message replayed.

ROM ref: `src/comm.c:write_to_buffer` writes once to the descriptor
output buffer. No replay channel exists.

**Finding 2 (MAJOR) — `bust_a_prompt` showed raw `hit`.**
`mud/utils/prompt.py:55-65` (default prompt) and the `%h` token
both read `int(getattr(char, "hit", 0))` directly. Death path
timing:

1. `apply_damage:591` → `update_pos(victim)` sets `position = DEAD`
   when `hit <= -11`. `hit` is still negative.
2. `apply_damage:604` checks `position == DEAD`, dispatches messages
   (which includes async `_push_message` of "You have been KILLED!!").
3. `apply_damage:612` calls `_handle_death` → `raw_kill` →
   `victim.hit = max(1, hit)` (`mud/combat/death.py:584`).

ROM `src/comm.c:1420ff` runs in a single-threaded loop where step 3
completes before any prompt fires; Python's async dispatch can
interleave a prompt render between steps 2 and 3, exposing the
negative `hit`. Fix is display-only clamp at both render sites.

**Finding 3 (MINOR) — `_handle_death` fighting-pointer ordering.**
`mud/combat/engine.py:1087-1102` clears `attacker.fighting = None`
before calling `raw_kill`, which then calls `_stop_fighting(victim,
True)` to sweep `character_registry`. The sweep no-ops on the
killing-blow attacker (already cleared), but correctly clears any
other mob in `character_registry` whose `.fighting is victim`. So
single-attacker case is correct, multi-attacker case is correct via
the sweep. Verdict: ordering is fine, but the explicit clears are
load-bearing for read clarity. Documented with parity comment
citing ROM `src/fight.c:damage`.

**Finding 4 (no-op) — phantom cross-room damage at temple altar.**
The "second death" the user saw at 22:08:06 was not a real second
combat event. `mud/game_loop.py:violence_tick:1297-1301` correctly
checks `attacker.room == victim.room` before damaging, mob's
`fighting` is correctly cleared by `_handle_death` and the sweep,
and mobs are properly registered. The "second KILL" at the temple
altar was the message replay from Finding 1.

## What landed

| Commit | Description |
|--------|-------------|
| `f586d11` | `fix(parity): bust_a_prompt clamps displayed hit to >= 0` |
| `59bebf0` | `fix(parity): single-delivery for combat messages — remove dual mailbox append` |
| (this session, version bump commit) | `chore(release): 2.7.3 + parity comment + session handoff` |

Files modified:
- `mud/utils/prompt.py` — clamp at `_bust_default_prompt` and `%h` token, with parity comments citing `src/fight.c:1718` (raw_kill clamp) and `src/comm.c:1420ff` (single-threaded prompt render).
- `mud/combat/engine.py` — `_push_message` returns immediately after async dispatch when a connection exists; `_handle_death` parity comment on the bidirectional fighting-pointer clear.
- `docs/divergences/MESSAGE_DELIVERY.md` — updated to reflect gated-append semantics, explicitly calls out the duplicate-delivery bug.
- `pyproject.toml` — 2.7.2 → 2.7.3.
- `CHANGELOG.md` — 2.7.3 section under Fixed/Added.

Tests added (8 new):
- `tests/test_prompt_clamps_hp.py` — 4 cases.
- `tests/integration/test_message_delivery_no_duplicate.py` — 2 cases.
- `tests/integration/test_pc_death_no_message_replay.py` — 1 case
  (end-to-end death-sequence + drain).
- `tests/integration/test_pc_death_keeps_connection.py` — 1 case
  (regression guard for raw_kill behavior).

## Verification

Pre-existing pytest failures in `tests/test_logging_admin.py` (8 cases,
"Huh?" dispatcher misses) verified pre-existing via `git stash`
baseline; not introduced by this session's changes.

```sh
pytest tests/test_prompt_clamps_hp.py \
       tests/integration/test_message_delivery_no_duplicate.py \
       tests/integration/test_pc_death_no_message_replay.py \
       tests/integration/test_pc_death_keeps_connection.py -v
# All pass (8 cases).
```

Live repro after the fix (manual, by user):

```sh
cd /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python
MUD_DEBUG_VIOLENCE=1 PYTHONUNBUFFERED=1 python3 -m mud websocketserver \
    2>&1 | tee ~/mud-death-after.log
```

Connect via WS client, get killed by a mob. Expect:
- Exactly ONE "You have been KILLED!!" line.
- Prompt shows `<1hp ...>` post-death (never `<0hp ...>`).
- After respawn `look` shows the Temple Altar ONCE — no replay of
  the combat sequence.

## Out of scope (carries over)

The plan's "Out of Scope" list (still open follow-ups in
`SESSION_STATUS.md`):
- `do_kill` → `multi_hit` parity (single swing today vs ROM's multi-swing)
- `is_safe()` gate inside `apply_damage` damage path
- Dual `load_character` / `save_character` consolidation
- Scavenger RNG-order flake
- Stale eddol.json save (1 HP at login)
- Resume broad-sweep: rewrite `tests/test_builder_hedit.py`
