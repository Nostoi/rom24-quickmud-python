# Session Summary — 2026-05-26 — DUPL DEAD-CODE + CLEANUP burn-down + FOLLOW-018 close (2.9.30 → 2.9.33)

## Scope

Continuation of the DUPLICATE_IMPLEMENTATIONS burn-down begun earlier
the same day (2.9.22 → 2.9.29 closed the 5 ❌ real-bug rows; see
`SESSION_SUMMARY_2026-05-26_DUPLICATE_IMPLEMENTATIONS_BURNDOWN.md`).
This session burned down the remaining ⚠️ DEAD-CODE and ⚠️ CLEANUP
rows, then closed the one CLEANUP row that fix-time re-audit
escalated into a real ROM-parity gap.

## Outcomes

### `DUPL-006` — ✅ DEAD-CODE FIXED (2.9.30)

- **Python**: `mud/combat/safety.py:89-106` (deleted 5-line `check_killer` stub).
- **Verification**: `gitnexus_impact` + grep confirmed 0 callers.
- **Fix**: Deleted.

### `DUPL-007` — ✅ FIXED (2.9.30) — fix-time-reclassified from CLEANUP to real bug

- **Python**: `mud/handler.py:1302` (deleted divergent `affect_loc_name`); `mud/commands/imm_search.py:19-33` (re-routed import to ROM-faithful copy in `mud/commands/affects`).
- **ROM C**: `src/handler.c:affect_loc_name`.
- **Trojan-horse pattern**: the handler.py copy was wired through a multi-line tuple import in `imm_search.py` that a single-line grep missed (same trap as DUPL-001c).
- **Fix**: Deleted divergent copy, redirected the one caller.

### `DUPL-008` — ✅ MATCH (2.9.30) — divergent-by-design

- Intentional immortal-bypass in `act_obj.c` parity site; not a duplicate to consolidate. Documented in audit doc.

### `DUPL-010` — ✅ CLEANUP FIXED (2.9.31)

- **Canonical**: `Character.is_awake()` at `mud/models/character.py:452` (`return self.position > Position.SLEEPING`).
- **Deletions**: 6 duplicate `_is_awake` helpers in `mud/combat/assist.py`, `mud/math/stat_apps.py`, `mud/ai/aggressive.py`, `mud/commands/advancement.py`, `mud/commands/thief_skills.py`, `mud/spec_funs.py` (latter kept a defensive wrapper — see below).
- **MobInstance gap closed**: `MobInstance` was not a `Character` subclass, so call sites like `mob.is_awake()` failed against the new bound method. Added `MobInstance.is_awake()` at `mud/spawning/templates.py:248+` alongside the existing `MobInstance.has_affect()`.
- **Defensive wrapper retained**: `mud/spec_funs.py:_is_awake` kept as a thin `getattr` fallback because spec-fun unit tests pass `SimpleNamespace` mocks that don't bind methods.

### `DUPL-011` — ✅ CLEANUP FIXED (2.9.31)

- **Canonical**: `Character.has_affect(flag)` at `mud/models/character.py:625` (`return bool(self.affected_by & flag)`).
- **Deletions**: 5 duplicate `_has_affect` helpers across `mud/game_loop.py`, `mud/spec_funs.py`, `mud/world/vision.py`, `mud/ai/aggressive.py`, `mud/commands/shop.py`. 44 call sites converted to `entity.has_affect(flag)`.

### `DUPL-019` — ✅ CLEANUP FIXED (2.9.31)

- **Canonical**: new `mud/utils/timing.py:apply_wait_state(char, beats)` mirroring ROM `WAIT_STATE` (`ch->wait = max(ch->wait, beats)`).
- **Deletions**: 2 duplicate `_apply_wait_state` helpers in `mud/commands/thief_skills.py`, `mud/commands/healer.py` re-import the canonical.

### `DUPL-009, 012-017, 020-024` — ✅ MATCH (2.9.32) — 9 rows reclassified

Fix-time re-audit found divergent-by-design semantics for every CLEANUP row in this group; mechanical consolidation would change behavior or re-introduce already-fixed bug classes. Documented per-row in `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` CLEANUP section. Examples:

- **DUPL-009** (`_get_trust`): 3 distinct semantics — plain trust, is_admin-bump, is_npc→0 short-circuit. Not consolidable.
- **DUPL-020** (`_append_message`): 3 semantics including async-write-AND-mailbox-append; forcing a single canonical would re-introduce DUPL-001/002-class double-delivery.

### `DUPL-018` — ✅ FIXED (2.9.33) via refile-then-close path

- **Refiled** at 2.9.31 from CLEANUP into a real ROM-parity gap (the only row that didn't fit either bucket).
- **Closed** in this session via `FOLLOW-001` + `FOLLOW-002` gap-closer.
- **Python**: `mud/characters/follow.py:add_follower` + `:stop_follower`.
- **ROM C**: `src/act_comm.c:1602-1603` (add_follower TO_VICT `can_see` gate); `:1625-1629` (stop_follower both messages gated on `can_see && in_room != NULL`).
- **Fix**: imported `can_see_character` from `mud.world.vision`, wrapped the master-side messages.
- **Tests**: `tests/integration/test_follow_can_see_gating.py` — 3 cases (add_follower invisibility leak; stop_follower invisibility leak; stop_follower null-room leak).
- **Audit**: new `#### 17b` row in `docs/parity/ACT_COMM_C_AUDIT.md`.

## Methodology lessons (reinforced from prior session)

- **Fix-time re-audit invalidated subagent classifications on 9 of 13 CLEANUP rows** — original subagent had ~30% precision on CLEANUP (vs ~50% on ❌ rows). Per-row fix-time re-read is mandatory; mechanical batching loses too much fidelity.
- **Refile-then-close** is the right path for a row that fits neither bucket cleanly (DUPL-018). It preserves audit-row provenance while routing the fix through the right gap-closer methodology.
- **Trojan-horse imports** (DUPL-007, mirroring DUPL-001c): a single-line grep over `from mud.X import Y` misses multi-line tuple imports. Always grep the bare symbol name as well.
- **Subclassing gaps surface during consolidation** (DUPL-010): `MobInstance` is not a `Character` subclass; introducing `Character.is_awake()` as the bound-method canonical required adding `MobInstance.is_awake()` alongside the existing `MobInstance.has_affect()`. Worth audit-tracking which Character methods MobInstance must mirror.

## Files Modified (this session, 2.9.30 → 2.9.33)

- `mud/combat/safety.py` — DUPL-006 dead `check_killer` deleted.
- `mud/handler.py` — DUPL-007 divergent `affect_loc_name` deleted.
- `mud/commands/imm_search.py` — DUPL-007 import re-routed.
- `mud/spawning/templates.py` — DUPL-010 `MobInstance.is_awake()` added.
- `mud/spec_funs.py` — DUPL-010 + DUPL-011 cleanups + defensive `_is_awake` wrapper retained.
- `mud/combat/assist.py`, `mud/math/stat_apps.py`, `mud/ai/aggressive.py`, `mud/commands/advancement.py`, `mud/commands/thief_skills.py` — DUPL-010 deletions + call-site conversions.
- `mud/game_loop.py`, `mud/world/vision.py`, `mud/commands/shop.py` — DUPL-011 deletions + call-site conversions.
- `mud/utils/timing.py` (new) — DUPL-019 canonical.
- `mud/commands/healer.py` — DUPL-019 re-import.
- `mud/characters/follow.py` — DUPL-018 / FOLLOW-001 / FOLLOW-002 `can_see` gating.
- `tests/integration/test_follow_can_see_gating.py` (new, 3 tests).
- `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` — every row flipped to terminal status.
- `docs/parity/ACT_COMM_C_AUDIT.md` — new `#### 17b add_follower/stop_follower helpers` row.
- `CHANGELOG.md` — 2.9.30 / 2.9.31 / 2.9.32 / 2.9.33 sections.
- `pyproject.toml` — 2.9.29 → 2.9.33.
- `.gitignore` — added `.lanes/`; untracked 4 `.lanes/*.json` FleetView config files.

## Test Status

- `tests/integration/test_follow_can_see_gating.py` — 3/3 pass.
- Targeted suite (`integration/ + test_combat_death.py + test_shops.py + test_skill_combat_rom_parity.py`) — 2355 passed, 3 skipped, 2 ordering-flake failures in `test_combat_death.py` that pass in isolation (pre-existing test-isolation issue unrelated to this session's changes; full-suite pre-session run was 4726/4 green).
- Full suite has not been re-run on 2.9.33 yet — recommended next session.

## Next Steps

DUPLICATE_IMPLEMENTATIONS audit is fully closed. Next active surface is **cross-file invariants** (`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) — 19 of ~20 budget already ENFORCED. Candidate areas the tracker has not yet covered: affect ticks, position transitions, mob script triggers, group/follower chain (now partially exercised by FOLLOW-001/002). Probe-then-scope pattern (5-minute ROM-vs-Python read + one failing test) is the active method.

Alternative: dispatch a meta-audit of the next class in `docs/parity/META_AUDIT_TAXONOMY.md` (DUPLICATE_IMPLEMENTATIONS was class 6 of 8).
