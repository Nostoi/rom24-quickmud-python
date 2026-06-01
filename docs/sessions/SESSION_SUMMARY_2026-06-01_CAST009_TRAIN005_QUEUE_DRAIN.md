# Session Summary — 2026-06-01 — CAST-009 + TRAIN-005 (open-gap queue drain)

## Scope

Picked up from `SESSION_STATUS.md` (2.12.40), which listed two remaining open
correctness gaps after the INV-025/027 PERS-masking structural queue was
drained: **CAST-009** (`MAGIC_C_AUDIT.md`) and **TRAIN-005**
(`ACT_MOVE_C_AUDIT.md`). Both were surfaced 2026-05-31 by advisor review while
closing CAST-008 / TRAIN-003 respectively, and both had been parked as 🔄 OPEN.
This session closed both via the standard single-gap TDD flow (one failing test
→ fix → audit row flip → CHANGELOG → one commit each). With these two closed,
the documented open-gap queue is empty — the next session opens a fresh
cross-file-invariants candidate area.

## Outcomes

### `CAST-009` — ✅ FIXED (commit `3cc79497`, 2.12.41)

- **Python**: `mud/commands/combat.py` `do_cast` (concentration-lost branch)
- **ROM C**: `src/magic.c:551-554`
- **Gap**: A failed cast never trained the spell skill. ROM calls
  `check_improve(ch, sn, FALSE, 1)` inside the failure branch (`:553`) — failing
  a spell is a valid path to improving it (core progression). Python returned
  `"You lost your concentration."` before ever reaching `_check_improve`; the
  lone `_check_improve(...)` call only ran on the success path.
- **Fix**: Added `skill_registry._check_improve(char, skill, skill.name, False)`
  to the failure branch, ahead of the `c_div(mana_cost, 2)` half-mana deduction,
  matching ROM order.
- **Message ordering verified**: `_deliver_message`
  (`mud/skills/registry.py:390`) is `asyncio.create_task(send_to_char(...))`
  fire-and-forget, so the deferred "You learn from your mistakes…" improve line
  lands *after* the synchronous `"You lost your concentration."` return value —
  matching ROM's send order (concentration line first, improve line second).
  (Advisor-flagged check; confirmed async-deferred.)
- **Tests**: 1 new —
  `tests/integration/test_cast_009_failed_cast_improves_skill.py` (spies on
  `_check_improve`, forces a deterministic failed cast at skill=5/seed=1, asserts
  exactly one `success=False` call). Failed before fix, passes after. Magic/skills
  area suite (63 tests) green.

### `TRAIN-005` — ✅ FIXED (commit `b99a71ef`, 2.12.42)

- **Python**: `mud/commands/advancement.py` `do_train` (no-arg branch)
- **ROM C**: `src/act_move.c:1658-1663`
- **Gap**: Bare `train` (no argument) in ROM prints
  `"You have %d training sessions."` then sets `argument = "foo"` and **falls
  through**; "foo" matches no stat/hp/mana, so control reaches the listing branch
  (`:1713`) and the player also sees `"You can train: str int wis dex con hp mana"`.
  Python early-returned just the session count, omitting the list.
- **Fix**: The no-arg branch now emits the session count as a `session_prefix`
  (`"You have N training sessions.\n"`), sets `args = "foo"` so control falls
  through to the listing branch, and prepends `session_prefix` to all four
  listing-branch returns (the three Jordan easter-egg lines + the listing line).
  `\n` is the house convention (`mud/net/protocol.py:17` normalizes, `:53`
  re-adds `\r\n`).
- **Tests**: 1 new —
  `tests/integration/test_recall_train_commands.py::test_train_no_arg_falls_through_to_listing`
  (asserts both `"5 training sessions"` and `"You can train:"` + `"hp mana"`
  appear). Failed before fix, passes after. The existing
  `test_train_shows_sessions_count` still passes (its assertions — "5" present,
  "train" present — survive the added listing). Recall/train + advancement area
  suites (59 tests) green.

## Files Modified

- `mud/commands/combat.py` — CAST-009 failure-branch `_check_improve(…, False)`.
- `mud/commands/advancement.py` — TRAIN-005 no-arg fall-through + `session_prefix`.
- `tests/integration/test_cast_009_failed_cast_improves_skill.py` — new (CAST-009).
- `tests/integration/test_recall_train_commands.py` — added TRAIN-005 test.
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-009 row → ✅ FIXED.
- `docs/parity/ACT_MOVE_C_AUDIT.md` — TRAIN-005 row → ✅ FIXED.
- `CHANGELOG.md` — added two `Fixed` entries (CAST-009, TRAIN-005).
- `pyproject.toml` — 2.12.40 → 2.12.42.
- `README.md` — version badge/Version → 2.12.42, test count 5225→5242,
  Cross-file Invariants 24→25 (catching README up from a stale 2.12.35 state).

## Test Status

- `pytest tests/integration/test_cast_009_failed_cast_improves_skill.py` — 1/1 ✅
- Magic/skills area (`test_do_cast_pk_gates`, `test_finding_013…`,
  `test_do_cast_object_target`, `test_magic_002_bless_message`,
  `test_skills.py`) + CAST-009 — 63/63 ✅
- Recall/train + advancement area
  (`test_recall_train_commands.py`, `test_advancement.py`,
  `test_character_advancement.py`) — 59/59 ✅
- **CAST-009 RNG-sequence-shift verification** (advisor-flagged): CAST-009 adds
  a `number_range(1,1000)` draw to the `do_cast` *failure* path, shifting the
  global RNG sequence for any downstream RNG-dependent assertion after a failed
  cast under the autouse `seed_mm(12345)`. Ran the cast/skill-adjacent units
  `-n0` (`test_differential_smoke.py`, `test_combat.py`,
  `test_skill_combat_rom_parity.py`, `test_skills_buffs.py`,
  `test_skills_debuffs.py`, `test_skills_mass.py`,
  `test_skills_spells_cast_listing.py`) — **202/202 passed**, exit 0. No
  downstream test broke and no `differential_smoke` `KNOWN_DIVERGENCES` xfail
  flipped to xpass. Hazard cleared; no re-baseline needed.
- `ruff check mud/commands/combat.py mud/commands/advancement.py` — clean (the
  pre-existing F541 in `do_flee` and the unused-var warnings in unrelated recall
  tests are untouched by this session).
- **Full suite: NOT completed this session.** The machine was under extreme load
  (load average ~136 from concurrent unrelated workloads — a Next.js
  `next-server`, multiple chorequest node processes, several other `claude`
  sessions). Under that load the default `-n auto` (pytest-xdist) run **hung at
  worker startup** (master process idle at ~0% CPU, zero worker processes
  spawned — `fork` timing out under load), and a serial `-n0` run progressed but
  projected to multiple hours. This is purely environmental, not a regression:
  both changes are isolated 2-line logic additions with `gitnexus_impact`
  reporting LOW risk / 0 upstream callers, and their dedicated + area suites pass.
  **A full-suite run must be done on a quiet machine before pushing.**

## Next Steps

- **Push gate**: commits `3cc79497` (CAST-009) and `b99a71ef` (TRAIN-005) plus
  this handoff commit are **local on `master`, not pushed**. Before pushing, run
  the full suite on an unloaded machine (`pytest`, or `pytest -n0` if xdist still
  hangs) and confirm green — expected `5242 passed, 4 skipped`. Only then push.
- **Open-gap queue is drained.** With CAST-009 and TRAIN-005 closed, no
  documented 🔄 OPEN correctness gaps remain. The next session should open a
  fresh **cross-file-invariants** candidate area per the AGENTS.md probe-then-
  scope method: affect ticks, position transitions, mob script triggers, or the
  group/follower chain. Pick one, run a 5-minute probe (read ROM C contract →
  read Python equivalent → one failing test), then close as a gap or file the
  next free INV-NNN.
- **Re-verify before relying on audit rows**: the prior session noted 3 of 5
  closed rows had materially wrong ROM line numbers; continue to check any
  ⚠️/❌ row against `src/` before trusting it.
