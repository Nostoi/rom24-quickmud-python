# Session Summary — 2026-05-29 — WIZ-045 (do_goto wizinvis bamf-announce gate) + INV-027 correction

## Scope

Continued from the SHOP-PET-002 / INV-001 (e) handoff. The per-file audit
tracker is exhausted, so cross-file invariants is the standing pass;
`SESSION_STATUS.md` named the **INV-027 candidate** (ACT-INVIS-TRUST-GATE, on the
invariants watch list) as a concrete next probe. Ran the probe-then-scope method
against primary ROM source — and the probe **disproved the documented
candidate's stated ROM mechanism**, which re-routed the session into closing a
real per-command gap (`WIZ-045`) instead of promoting the (mis-scoped) invariant.

## Outcomes

### `WIZ-045` — ✅ FIXED (2.11.30, `1705628d`)

- **Python**: `mud/commands/imm_commands.py:do_goto` + new
  `mud/commands/imm_commands.py:_act_room_invis_gated`
- **ROM C**: `src/act_wiz.c:969-994` (`do_goto` bamfout/bamfin per-recipient loops)
- **Gap**: ROM `do_goto` does **not** broadcast the bamfout/bamfin (or default
  swirling-mist) line with a plain `act(..., TO_ROOM)`. It loops
  `ch->in_room->people` and sends each line via `act(..., rch, TO_VICT)` **only**
  to occupants where `get_trust(rch) >= ch->invis_level`, so a wiz-invis
  immortal's departure/arrival is **suppressed entirely** for sub-trust witnesses
  (gated on `invis_level` only, not full `can_see`). The Python `do_goto` routed
  both bamf broadcasts through `_act_room` (`mud/commands/imm_commands.py:473`),
  which substitutes `$n`→`char.name` once and sends the same string to **every**
  room occupant — no `invis_level` gate. A wiz-invis immortal's swirling-mist (or
  custom bamf) line therefore leaked to all witnesses, exposing the immortal's
  identity and presence.
- **Fix**: new `_act_room_invis_gated(room, char, message)` helper applies the
  per-recipient `get_trust(person) >= char.invis_level` gate (mirroring
  `act_wiz.c:969-994`; self-excluded like ROM's `TO_VICT` skip of `to == ch`).
  `do_goto`'s four bamf calls (departure default + custom, arrival default +
  custom) now use it. With `invis_level == 0` (normal immortal) the gate is always
  true, so the announce reaches everyone exactly as before. The **shared
  `_act_room` was deliberately left untouched** — it is also used by `do_transfer`,
  whose ROM path (`act_wiz.c:1072,1075`) is a plain `act(TO_ROOM)` with actor =
  the *transferred victim* and PERS name-masking, **no** `invis_level` gate;
  always-gating the shared helper would have silently broken `do_transfer` parity.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py` (2) —
  `test_goto_suppresses_bamf_for_subtrust_witnesses_when_wizinvis` (wiz-invis at
  `invis_level=60`: high-trust witness sees the swirling-mist line, sub-trust
  witness sees **nothing** — ROM suppresses, it is not merely name-masked) and
  `test_goto_bamf_visible_to_all_when_not_wizinvis` (regression guard:
  `invis_level=0` → every witness still sees it). Fail-first verified
  (`assert not True` — the sub-trust witness received "swirling mist" pre-fix).

### `INV-027` candidate — ROM mechanism CORRECTED + re-scoped (`077aae18`)

- **What was wrong**: the INV-027 watch-list entry (ACT-INVIS-TRUST-GATE) claimed
  ROM `act()` **suppresses the whole broadcast line** for sub-trust witnesses via
  a per-recipient `get_trust(rch) >= ch->invis_level` filter *inside* `act()`, and
  proposed routing `broadcast_room` through a `_can_witness` suppress helper with a
  test asserting "trust=10 witness sees nothing".
- **Why it's wrong** (primary source): `act_new` (`src/comm.c:2230-2244`) delivers
  the line to **every** eligible recipient — there is no `invis_level` filter in
  the recipient loop. Visibility is the `$n`/`$N` **name substitution**:
  `PERS(ch, to)` (`src/merc.h:2145`) → `can_see(to, ch)` (`src/handler.c:2618-2625`,
  FALSE when `get_trust(to) < ch->invis_level`), so a sub-trust witness gets the
  line with the actor rendered as **"someone"**, not nothing. Implementing the
  original proposal would have made the port **diverge** from ROM for generic
  `act(TO_ROOM)` broadcasts. Also: `broadcast_room` (`mud/net/protocol.py:58`)
  receives a **pre-formatted string** with no per-recipient `$n` rendering, so it
  is the wrong enforcement point regardless.
- **Re-scoped** as **ACT-PERS-NAME-MASKING**: the real cross-file contract is that
  every `act()` `$n`/`$N` must route through `can_see`-aware `pers()`. Concrete
  violation recorded: `mud/utils/act.py:act_format._pers` (lines 56-73) returns the
  name unconditionally — no `can_see` — and is used by `spec_funs`, `wiznet`,
  `connection`, `movement`, `music`; only `mud/combat/*` is faithful (uses
  `vision.pers()`). `mud/world/movement.py:107` even *documents* the masking intent
  the helper fails to deliver (latent bug). Left as an **open watch-list candidate**
  (wide blast radius; needs its own probe to separate per-recipient callers from
  `recipient=None` broadcast-once callers — the MESSAGE_DELIVERY.md divergence).
- The genuine line-suppression behavior is **per-command** in `do_goto`/`do_violate`
  (`act_wiz.c:969-994,1026-1057`), now tracked as `WIZ-045`/`WIZ-046` in
  `ACT_WIZ_C_AUDIT.md` — not as an `act()`-level invariant. The original framing is
  retained struck-through in the tracker for the audit trail.

## Files Modified

- `mud/commands/imm_commands.py` — new `_act_room_invis_gated` helper;
  `do_goto`'s four bamf broadcasts routed through it (WIZ-045). `_act_room`
  untouched.
- `tests/integration/test_act_wiz_command_parity.py` — 2 new tests (WIZ-045).
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-045 row (✅ FIXED) + WIZ-046 row
  (⚠️ OPEN) added; Phase 2 narrative subsection; header + footer updated.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027 watch-list entry
  corrected and re-scoped (ACT-PERS-NAME-MASKING); original framing retained
  struck-through.
- `CHANGELOG.md` — `[2.11.30]` Fixed (WIZ-045).
- `pyproject.toml` — 2.11.29 → 2.11.30.

Commits: `077aae18` (INV-027 doc correction), `1705628d` (WIZ-045 fix). Both on
`master`. The pre-existing uncommitted `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`
tweak (carried across sessions, unrelated to parity) was left uncommitted.

## Test Status

- `tests/integration/test_act_wiz_command_parity.py` — 114 passed (+2 WIZ-045).
- goto-referencing suites (`test_act_wiz_command_parity` + `test_command_parity`
  + `test_admin_commands`) — 131 passed.
- **Full suite**: **4982 passed, 4 skipped** (100.45s; +2 vs prior 4980 = the two
  new WIZ-045 tests). No regressions.
- `ruff check` on touched code: `mud/commands/imm_commands.py` clean; the 4
  errors in `test_act_wiz_command_parity.py` are all **pre-existing** (lines
  ≤1538, verified byte-identical to HEAD); new test additions clean. **0 new.**
- `gitnexus_detect_changes`: LOW risk, 0 affected processes; changed scope =
  `do_goto` + locals + doc sections (`_act_room` correctly absent). Reindexed
  after commit (exit 0; only the known C-header scope-extraction warnings).

## Outstanding

- **`WIZ-046` — `do_violate` shares the identical wizinvis bamf-announce gap**
  (same `_act_room` root cause as WIZ-045; ROM `src/act_wiz.c:1026-1057`). Filed
  ⚠️ OPEN in `ACT_WIZ_C_AUDIT.md`; the `_act_room_invis_gated` helper is ready to
  reuse. Scoped to a follow-up commit (one gap = one test = one commit).
- **INV-027 (ACT-PERS-NAME-MASKING)** — open watch-list candidate. The concrete
  violation is `mud/utils/act.py:act_format._pers` lacking `can_see`; promoting it
  needs a probe to separate per-recipient `act_format` callers (where PERS masking
  applies) from `recipient=None` broadcast-once callers fed to `broadcast_room`.
- Carried from prior sessions: pet-shop haggle/"now follows you" wrong-channel
  (INV-001 family, mailbox-only); `Character.pet` stale type annotation;
  `do_cast` object-targeting legs; converter hardening; the
  `test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.

## Next Steps

Per-file audit tracker remains exhausted; **cross-file invariants is the standing
pass**. Concrete next candidates, in rough priority:

1. **`WIZ-046`** — close `do_violate`'s wizinvis bamf gate by reusing
   `_act_room_invis_gated` (smallest, well-defined, ready helper). One test, one
   commit.
2. **INV-027 (ACT-PERS-NAME-MASKING) probe** — verify which `act_format` callers
   are per-recipient vs broadcast-once, then route `act_format._pers` through
   `vision.pers()` and reconcile the two `_act_room` helpers. Promote to ENFORCED
   if the per-recipient surface is tractable.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).
