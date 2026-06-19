# Session Summary — 2026-06-19 — do_yell → push_message chokepoint refactor

## Scope

Continuation of the same session that closed DELETE-002. Picked up the named
follow-up from `SESSION_STATUS.md`: the `do_yell` hand-rolled-XOR tidy-up.
Investigation confirmed `do_yell`'s ROM logic is otherwise faithful (gates on
`COMM_NOSHOUT`, listener check is `COMM_QUIET`-only with no `COMM_DEAF` gate, per
`src/act_comm.c:1033-1064`), so this is a behavior-preserving refactor, not a gap
fix.

## Outcomes

### `do_yell` delivery → canonical `push_message` (refactor, not a bug)

- **Python**: `mud/commands/communication.py:do_yell`
- **ROM C**: `src/act_comm.c:1033-1064` (logic confirmed faithful — no parity
  change)
- **Change**: the per-listener loop hand-rolled the async-socket-XOR-mailbox
  delivery (`if writer: asyncio.create_task(send_to_char(...)) else
  _queue_personal_message(...)`). Collapsed onto `mud.utils.messaging.push_message`
  — behaviorally identical (connected listener → immediate async send;
  disconnected → mailbox via `_queue_personal_message`'s equivalent
  `messages.append`), but `push_message` is loop-aware (falls back to the mailbox
  instead of raising `RuntimeError` when no event loop runs).
- **Why it matters**: `docs/parity/DIVERGENCE_CLASS_ROSTER.md` Class 4 (async
  message delivery) cited `do_yell`'s hand-rolled `create_task(send_to_char)` XOR
  as the canonical example of a legitimate site that defeats a *blanket* Layer-A
  static delivery guard. Collapsing it removes that blocker (the allowlist-based
  Layer-A guard `tests/test_message_delivery_convention.py` already exists since
  2.14.116; this shrinks the set of hand-rolled exceptions it must tolerate).
- **Tests**: added `test_yell_single_delivers_to_connected_listener` to
  `tests/integration/test_inv001_comm_delivery_channel.py` — a characterization
  lock (socket once, mailbox empty) that passed both before and after the refactor.
- **Cleanup**: removed the now-dead `asyncio` and `send_to_char` imports from
  `communication.py`.
- **Commit**: `8460a368`, v2.14.131

## Files Modified

- `mud/commands/communication.py` — `do_yell` routes through `push_message`;
  dropped dead `asyncio` / `send_to_char` imports.
- `tests/integration/test_inv001_comm_delivery_channel.py` — new yell
  characterization test (+ `Area` import).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — Class-4 row + to-do #1 updated to
  reflect the collapse and the 2.14.116 allowlist-guard reclaim.
- `CHANGELOG.md` — Changed entry.
- `pyproject.toml` — 2.14.130 → 2.14.131.

## Test Status

- `pytest -n0 tests/integration/test_inv001_comm_delivery_channel.py
  tests/integration/test_shout_yell_parity.py tests/integration/test_fight048_murder_yell.py
  tests/integration/test_communication_enhancement.py tests/test_skill_steal_rom_parity.py
  tests/test_message_delivery_convention.py` — **47 passing**.
- `pytest -n0 tests/integration/test_say_parity.py tests/integration/test_tell_parity.py
  tests/test_communication.py tests/integration/test_inv001_delivery_helpers_channel.py`
  — **44 passing**.
- `ruff check` — clean.
- GitNexus `detect_changes` unavailable this turn (MCP server disconnected); used
  the AGENTS.md documented fallback (grep blast-radius + area integration suites).
  `do_yell` callers: dispatcher registration + `murder.py` FIGHT-048 (covered by
  the passing `test_fight048_murder_yell.py`).

## Next Steps

- **INV-050 bool-retirement** — still GATED on the `is_safe_spell`-vs-ROM
  standalone audit (`src/fight.c:1126-1218`).
- `mud/entrypoint.py` dead code.
- Higher-yield enumeration-independent lever per
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine →
  diff_harness widening (Class 11 / Phase C).
