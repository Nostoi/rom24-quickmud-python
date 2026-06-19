# Session Summary — 2026-06-19 — INV-001 debt burndown COMPLETE (final 3 sites)

## Scope

Continued the INV-001 SINGLE-DELIVERY debt burndown from the 2026-06-18 skills
session, which had reduced `_INV001_DEBT` in
`tests/test_message_delivery_convention.py` from 10 → 3 frozen sites. This
session resolved the **final 3 frozen sites** — the trickier ones the prior
handoff flagged as "verify before migrating, not mechanical." Each was
characterized against ROM C source before acting; the verdicts diverged from a
blanket "migrate all three" (one is a genuine bug, one is a clean test-only
migration, one is intentionally mailbox-only and was reclassified, not changed).
With this, **`_INV001_DEBT` is empty** and the burndown is complete.

## Outcomes

### snoop-forward — ✅ CLOSED (genuine bug, migrated)

- **Python**: `mud/commands/dispatcher.py:process_command` (~1200)
- **ROM C**: `src/interp.c:491-496` — `write_to_buffer(ch->desc->snoop_by, …)`
  (immediate descriptor write)
- **Gap**: INV-001 SINGLE-DELIVERY wrong-channel/late (SPEC-017 class)
- **Fix**: the snooped char's logline (`% <cmd>`) was appended straight to the
  snooper's `messages` mailbox. A snooper actively watching is a *connected* PC,
  so the line sat in the mailbox until their next command. Routed through
  `push_message` (async socket xor mailbox fallback). The recipient is the
  snooping character (`ch->desc->snoop_by->character`) — confirmed correct.
- **Tests**: `tests/integration/test_interp_dispatcher.py::test_interp_002_snoop_forward_reaches_connected_snooper_on_socket`
  (connected-socket present + mailbox-empty; fail-firsted on empty socket). The
  pre-existing disconnected mailbox test stays green.
- **Commit**: `b85d4864`, v2.14.126

### "still recovering" registry line — ✅ CLOSED (test-only path, migrated for consistency)

- **Python**: `mud/skills/registry.py:SkillRegistry.use` wait-state guard (~160)
- **Gap**: INV-001 wrong-channel/late (was originally excluded per INV-001 (d))
- **Fix**: `use` appended "You are still recovering." to `caster.messages` then
  `raise`d. Never a double-delivery (the raise carries no return channel) and
  `use` has no production callers — but still wrong-channel for a connected
  caster. Migrated to `push_message` anyway (burndown goal = empty
  `_INV001_DEBT`). The disconnected/test path keeps the mailbox fallback via
  `push_message`'s loop-aware probe, so `tests/test_skills.py:225` stays green.
  Supersedes the INV-001 (d) "deliberately excluded" note (tracker + the
  still-recovering test docstring updated).
- **Discriminating check**: confirmed no `reg.use` caller exercises the
  recovering branch with a connected caster under a running loop — the two
  integration callers monkeypatch RNG into success/skill-fail paths (wait=0),
  and `test_skills.py:225` is synchronous with no connection.
- **Tests**: `tests/integration/test_skill_registry_delivery_channel.py::test_recovering_line_reaches_connected_caster_on_socket`
- **Commit**: `5074d7ac`, v2.14.127

### `_queue_personal_message` — ✅ RESOLVED AS LEGITIMATE (not a bug; reclassified)

- **Python**: `mud/commands/communication.py:_queue_personal_message` (~27)
- **ROM C**: `src/act_comm.c:50`/`83`/`93` — `add_buf(victim->pcdata->buffer, …)`
  (deferred tell-buffer, flushed on return — NOT `write_to_buffer`)
- **Verdict**: intentionally mailbox-only. It is the Python analog of ROM's
  deferred tell-buffer for **linkdead / AFK / note-writing** targets. Routing it
  through `push_message` would push to the live socket for AFK / note-writing
  players (who ARE connected), breaking ROM's deferral. Its `do_yell` caller
  reaches it only on the disconnected leg (ROM `do_yell` delivers only to
  `CON_PLAYING` descriptors).
- **Action**: moved from `_INV001_DEBT` → `_LEGITIMATE` with a why-comment (so
  the guard still catches a genuinely-buggy connected-PC use), and an INV-001
  comment added at the function. `_INV001_DEBT` is now empty.
- **Follow-up (not a bug, noted in tracker)**: `do_yell`'s hand-rolled
  `if writer: create_task(...); continue` else-mailbox XOR duplicates
  `push_message`'s logic — collapsible for tidiness, behaviorally correct today.
- **Commit**: `f4bfa17a`, v2.14.128

## Files Modified

- `mud/commands/dispatcher.py` — snoop-forward → `push_message` + import
- `mud/skills/registry.py` — wait-state line → `push_message`
- `mud/commands/communication.py` — INV-001 why-comment on `_queue_personal_message`
- `tests/integration/test_interp_dispatcher.py` — new connected-snooper test
- `tests/integration/test_skill_registry_delivery_channel.py` — new recovering test
- `tests/integration/test_still_recovering_single_delivery.py` — docstring note updated (excluded → migrated)
- `tests/test_message_delivery_convention.py` — `_INV001_DEBT` emptied; comm site moved to `_LEGITIMATE`
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 row: 3 closure notes
- `CHANGELOG.md` — Fixed (×2) + Changed (×1) entries
- `pyproject.toml` — 2.14.125 → 2.14.128

## Test Status

- Per-area: `test_interp_dispatcher.py`, `test_skill_registry_delivery_channel.py`,
  `test_message_delivery_convention.py`, `test_still_recovering_single_delivery.py`,
  `test_skills.py`, `test_inv001_comm_delivery_channel.py` — all green
- Full suite: **5831 passed, 4 skipped** (244s) — +2 new tests vs prior 5829
- `gitnexus_detect_changes` run before each commit (all low risk); reindexed after each

## Next Steps

INV-001 debt burndown is **complete** — `_INV001_DEBT` is empty, so the Layer-A
delivery scanner now forbids any new unsanctioned `*.messages.append` outright.
Open follow-ups (unchanged from prior handoff): DELETE-002 (do_delete wiznet
self-deletion broadcast), STEAL-015 (steal skill-handler missing is_safe gate),
INV-050 bool-retirement, `mud/entrypoint.py` dead code, and the `do_yell`
hand-rolled-XOR tidy-up noted above. Higher-yield enumeration-independent lever
per `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine →
diff_harness widening (Class 11 / Phase C).
