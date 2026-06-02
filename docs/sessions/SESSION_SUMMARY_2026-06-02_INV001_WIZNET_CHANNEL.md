# Session Summary — 2026-06-02 — INV-001 WIZNET DELIVERY CHANNEL (sweep complete)

## Scope

Cross-file invariants is the sole active pass (no per-file audit gaps remain).
Picked up from the prior session's single explicitly-deferred item: the last
open site of the INV-001 wrong-channel sweep — `mud/wiznet.py:_wiznet_deliver`.
Every other `*.messages.append` site in `mud/` had already been migrated to the
async-XOR-mailbox `push_message` chokepoint across 2.12.67–2.12.72; wiznet was
left mailbox-only because a naive migration tripped `asyncio.create_task`'s "no
running event loop" — the previous author's NOTE flagged its reconnect-announce
callers as running "synchronously outside an event loop." This session traced
that claim, found the resolution, and closed the site, completing the sweep.

## Outcomes

### `INV-001` (wiznet site) — ✅ CLOSED (wrong-channel, sweep complete)

- **Python**: `mud/wiznet.py:_wiznet_deliver` (~252-260);
  `mud/utils/messaging.py:push_message` (made loop-aware).
- **ROM C**: `src/act_wiz.c:171-194` (`wiznet`) — each line written straight to
  the descriptor via `send_to_char` (immediate, single-channel).
- **Gap**: `_wiznet_deliver` appended unconditionally to `ch.messages`, so a
  **connected** immortal received its wiznet lines late (drained on the next
  prompt) rather than immediately — the INV-001 SINGLE-DELIVERY / MAGIC-003
  wrong-channel family. It was the one tricky site: a direct `push_message` swap
  raised "no running event loop" for the reconnect-announce callers.
- **Root-cause trace (Gate 1)**: the reconnect/login helpers
  (`_announce_login_or_reconnect`, `_broadcast_reconnect_notifications`,
  `announce_wiznet_login/logout/new_player`) are plain `def`s, **but every
  production call site is inside an `async def` coroutine** — `handle_connection`,
  `handle_connection_with_stream`, `_run_character_creation_flow` — so there *is*
  a running event loop when they fire. The prior NOTE's "sync reconnect path"
  meant the function isn't a coroutine, not that the loop is absent. The only
  genuinely loop-less callers are the **tests**, which call
  `_broadcast_reconnect_notifications(...)` directly outside `asyncio.run`.
- **Fix**: made `push_message` (`mud/utils/messaging.py`) **loop-aware** — it now
  probes `asyncio.get_running_loop()` and, when no loop is running, falls back to
  the `messages` mailbox instead of raising. Then routed `_wiznet_deliver`
  through `push_message`. A connected immortal under the live server loop gets
  the immediate async send; the sync reconnect callers + tests fall back to the
  mailbox exactly as before, so the 4 mailbox-asserting reconnect tests stay
  green. Aligns with DUPL-001/DUPL-002 delivery consolidation (no new divergent
  local copy). The change to `push_message` is **purely additive**: the no-loop
  + connection case went crash → mailbox; every in-loop caller is byte-identical.
- **Impact**: `gitnexus_impact({target: "push_message"})` = **CRITICAL** (41
  direct callers, 319 impacted — it is the INV-001 chokepoint). Reported to the
  user. Risk bounded by the additive nature of the change; the full green suite
  confirmed zero fallout. `gitnexus_detect_changes` rated the actual diff
  **medium**, scope confined to `push_message`/`send_to_char_buffered`/
  `_wiznet_deliver` + the two doc sections.
- **Tests**: `tests/integration/test_inv001_wiznet_delivery_channel.py` (1 test,
  **async / in-loop**: a connected immortal under a running loop receives the
  line once on the async channel with `messages == []`). Gate 2 satisfied — the
  test runs inside `asyncio.run`, so it actually distinguishes fixed from
  unfixed (a sync test would hit the fallback and false-green). Fail-first
  confirmed ("wiznet delivered 0x on async channel; sent=[]").

## Files Modified

- `mud/utils/messaging.py` — `push_message` made loop-aware (`get_running_loop`
  probe, mailbox fallback when no loop).
- `mud/wiznet.py` — `_wiznet_deliver` `messages.append` → `push_message`; the
  stale "NOT migrated" NOTE replaced with the INV-001 single-delivery rationale.
- `tests/integration/test_inv001_wiznet_delivery_channel.py` — new, 1 test.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 "Still OPEN (needs
  care)" passage flipped to "wiznet — ✅ CLOSED (2.12.73), SWEEP COMPLETE" (no
  new INV row — wrong-channel cousin of the existing INV-001 contract).
- `CHANGELOG.md` — added the INV-001 wiznet `Fixed` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.72 → 2.12.73.
- `docs/sessions/SESSION_STATUS.md` — refreshed to "sweep fully complete".

## Test Status

- `pytest tests/integration/test_inv001_wiznet_delivery_channel.py` — 1/1.
- Targeted regression set (new test + `test_wiznet.py` + `test_account_auth.py` +
  `test_logging_admin.py` + `test_inv001_inline_delivery_channel.py`) — 107/107,
  including the 4 mailbox-asserting reconnect tests.
- `ruff check` on touched files — clean.
- Full suite: **5355 passed, 4 skipped** (~166s parallel) — zero fallout despite
  the CRITICAL blast radius on `push_message`.

## Next Steps

The INV-001 wrong-channel sweep is **fully closed** — no remaining sweep work.
Cross-file invariants remains the active pass. The tracker is at **26 enforced**
INV rows, past the ~20 soft cap AGENTS.md flags; next session should weigh
**consolidation** (the INV-014/INV-015/INV-010 precedent merged paired rows) —
candidate duals are INV-016/INV-019 (position-transition broadcast / silent
promotion-on-heal) and INV-006/INV-009 (fighting-pointer coherence / registry
disconnect cleanup). The leading uncovered cross-file candidate remains **mob
trigger ordering** (TRIG_* dispatch sequence vs ROM — bribe/exit/fight/kill/
hpcnt); probe-then-scope: read ROM C contract → read Python equivalent → one
failing test → close as a gap or file as INV-034.

> **Push note:** 2.12.73 (`611381de` fix + `1e21000a` docs) is committed **and
> pushed** to `origin/master` (now at `1e21000a`). CHANGELOG/version reflect
> 2.12.73. This handoff summary lands as a follow-up docs commit.
