# Session Summary — 2026-06-18 — INV-001 debt burndown (skills handlers/registry, 3 sites)

## Scope

Continued the INV-001 SINGLE-DELIVERY debt burndown from the prior session
(which closed THIEF promotion / login broadcast / wand zap, leaving 10 frozen
`_INV001_DEBT` sites in `tests/test_message_delivery_convention.py`). This
session took the handoff's "highest-yield" target — the `mud/skills/` cluster —
and closed **7 of the 10** frozen sites across three failing-test-first commits.
All were the same INV-001 wrong-channel class: a caster-facing line appended to
`<caster>.messages` (the mailbox the connection read loop only drains after the
player's *next* command) instead of routed through the single-delivery
`push_message` chokepoint (async socket *xor* mailbox).

## Outcomes

### `registry.py` `_deliver_message` consolidation — ✅ CLOSED (v2.14.123)

- **Python**: `mud/skills/registry.py:SkillRegistry.use` (failed-cast failure
  line) + `_check_improve` ("You have become better…" / "You learn from your
  mistakes…")
- **ROM C**: `src/magic.c:551` (`send_to_char` failure), `src/skills.c:951-967`
  (`send_to_char(buf, ch)` improve lines)
- **Gap**: dual delivery — a local `_deliver_message` copy (socket-only, no
  mailbox fallback) fired *and* a paired `caster.messages.append(...)`, so a
  connected PC got the line on the async socket once, then again from the
  mailbox replay on the next prompt.
- **Fix**: all three route through `push_message`; the divergent
  `_deliver_message` helper (DUPL-style third copy of the chokepoint, exactly 3
  callers, all migrated) is **deleted**. One root-cause refactor → three debt
  lines closed (10 → 7 frozen).
- **Tests**: `tests/integration/test_skill_registry_delivery_channel.py` (2 —
  failure + improve, connected-socket-once + mailbox-empty). Disconnected-char
  `tests/test_skills.py` mailbox assertions stay green via `push_message`'s
  loop-aware fallback.

### `charm_person` caster lines — ✅ CLOSED (v2.14.124)

- **Python**: `mud/skills/handlers.py:charm_person` (3 caster lines)
- **ROM C**: `src/magic.c:1358` (self-charm), `:1371` (ROOM_LAW), `:1390`
  (`act(..., TO_CHAR)` adoring-eyes)
- **Gap**: all three mailbox-only → late for an idle connected caster at cast
  time (SPEC-017 shape).
- **Fix**: all three route through `_send_to_char`. Three debt lines closed
  (7 → 4 frozen).
- **Tests**: `tests/integration/test_charm_person_delivery_channel.py` (3 —
  self-charm + ROOM_LAW + adoring-eyes, connected-socket-present +
  mailbox-empty).

### `colour_spray` caster line — ✅ CLOSED (v2.14.125)

- **Python**: `mud/skills/handlers.py:colour_spray`
- **ROM C**: `src/magic.c:1437` (spray flavor flows through `damage()`, a
  descriptor write — never a deferred mailbox queue)
- **Gap**: caster spray line appended to `caster.messages` while its target/room
  legs already used `_send_to_char` (migrated 2.12.72) — mailbox-only/late.
- **Fix**: caster leg routes through `_send_to_char` too. `colour_spray` returns
  the `int` damage, not the line, so no return-channel double. Last
  skills-handler debt line closed (4 → 3 frozen).
- **Tests**: `tests/integration/test_colour_spray_delivery_channel.py` (1).

## Files Modified

- `mud/skills/registry.py` — 3 lines → `push_message`; `_deliver_message` helper
  + unused `asyncio` import removed; `push_message` import added.
- `mud/skills/handlers.py` — 4 caster lines (charm ×3 + colour_spray ×1) →
  `_send_to_char`.
- `tests/integration/test_skill_registry_delivery_channel.py` — new (2 tests).
- `tests/integration/test_charm_person_delivery_channel.py` — new (3 tests).
- `tests/integration/test_colour_spray_delivery_channel.py` — new (1 test).
- `tests/test_message_delivery_convention.py` — 7 `_INV001_DEBT` allowlist lines
  deleted (orphan check enforces).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 row: 3 closure notes
  appended (10 → 7 → 4 → 3 frozen).
- `CHANGELOG.md` — 3 `Fixed` entries.
- `pyproject.toml` — 2.14.122 → 2.14.125.

## Test Status

- New delivery-channel tests: 6/6 passing (each fail-firsts on the bypass).
- Full suite: **5829 passed, 4 skipped** (444s, parallel) — +6 over the prior
  5823.
- `ruff check` clean on touched files.

## Next Steps

**3 `_INV001_DEBT` sites remain** — the trickier ones the handoff flagged for
care (verify before migrating, not mechanical):

1. `mud/commands/dispatcher.py:1201` — snoop-forward
   (`snooper_messages = getattr(snooper, "messages", None)`). ROM
   `src/comm.c:1393-1398` `write_to_buffer(d->snoop_by)` targets the **snooper's**
   descriptor, not the snooped char — confirm the recipient before migrating.
2. `mud/commands/communication.py:29` — `_queue_personal_message`
   (`target.messages.append(message)`). Confirm it isn't *intentionally*
   mailbox-only (deferred personal-message/note path) before changing.
3. `mud/skills/registry.py:161` — "You are still recovering." getattr+append.
   **Deliberately excluded** per INV-001 (d): it appends then `raise`s (no return
   channel), has no production callers (test-only `SkillRegistry.use`), and
   `tests/test_skills.py` asserts the mailbox delivery. Likely stays frozen —
   re-confirm before touching.

Other open follow-ups (unchanged): DELETE-002 (do_delete wiznet self-deletion
broadcast), STEAL-015 (steal skill-handler has no is_safe gate), INV-050
bool-retirement, `mud/entrypoint.py` dead code. Higher-yield
enumeration-independent lever per `docs/parity/DIVERGENCE_CLASS_ROSTER.md`:
Hypothesis state-machine → diff_harness widening (Class 11 / Phase C).
