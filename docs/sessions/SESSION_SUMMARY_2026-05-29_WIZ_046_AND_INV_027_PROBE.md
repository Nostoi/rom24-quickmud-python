# Session Summary — 2026-05-29 — WIZ-046 (do_violate wizinvis bamf gate) + INV-027 probe

## Scope

Continued from the WIZ-045 / INV-027-correction handoff. The per-file audit
tracker is exhausted, so cross-file invariants is the standing pass.
`SESSION_STATUS.md` named **WIZ-046** as the ready #1 task (the `do_violate`
sibling of the WIZ-045 gate, helper already in place). Closed WIZ-046, then —
at the user's direction — ran the **INV-027 (ACT-PERS-NAME-MASKING) probe**, the
named #2 candidate. The probe confirmed the violation, attempted the enforcement,
**reverted it on the empirical evidence** (15 regressions including real
production wiznet paths), and pinned the blocker — the honest probe-then-scope
outcome rather than a forced promotion.

## Outcomes

### `WIZ-046` — ✅ FIXED (2.11.31, `dfbb17f5`)

- **Python**: `mud/commands/imm_server.py:163` (`do_violate`)
- **ROM C**: `src/act_wiz.c:1026-1051` (`do_violate` bamfout/bamfin per-recipient loops)
- **Gap**: `do_violate` is structurally identical to `do_goto` — it loops
  `ch->in_room->people` and sends each bamfout/bamfin (or default swirling-mist)
  line via `act(..., rch, TO_VICT)` **only** to occupants where
  `get_trust(rch) >= ch->invis_level`, so a wiz-invis immortal's
  departure/arrival is **suppressed entirely** for sub-trust witnesses. The
  Python `do_violate` routed its four bamf broadcasts through the ungated
  `_act_room` (the WIZ-045 root cause), leaking the line — and thus the
  immortal's presence — to every witness.
- **Fix**: `do_violate`'s four bamf calls now reuse the `_act_room_invis_gated`
  helper introduced for WIZ-045 (per-recipient `get_trust(person) >=
  char.invis_level` gate); the `_act_room` import was swapped for it. With
  `invis_level == 0` (normal immortal) the gate is always true, so the announce
  reaches everyone exactly as before.
- **Tests**: `tests/integration/test_act_wiz_command_parity.py` (2) —
  `test_violate_suppresses_bamf_for_subtrust_witnesses_when_wizinvis` (asserts
  **both** legs: source-room departure witnesses see "leaves…", destination
  private-room arrival witnesses see "appears…", sub-trust witnesses see nothing
  on either) + `test_violate_bamf_visible_to_all_when_not_wizinvis` (regression
  guard, `invis_level == 0`). Fail-first verified (`assert not True` — the
  sub-trust witness received "swirling mist" pre-fix).

### `INV-027` (ACT-PERS-NAME-MASKING) — PROBED: violation CONFIRMED, enforcement REVERTED, blocker PINNED (2.11.32, `47449114`)

- **ROM contract (confirmed against primary source)**: `act_new` `$n`/`$N` →
  `PERS(ch, looker)` (`src/merc.h:2145`) → `can_see(looker, ch)`
  (`src/handler.c:2618-2664`), masking an unseen actor's name to "someone" while
  the line is still delivered. True for both generic `act(TO_ROOM)` **and**
  wiznet (`src/act_wiz.c:188` passes the actor as `vch`, so `$N` is PERS-masked
  per listener).
- **Violation**: `mud/utils/act.py:act_format._pers` returns the name
  unconditionally — no `can_see`. Only the combat path (`mud/world/vision.py:pers`)
  is faithful. Caller census separated the two classes the deferral note asked
  for: per-recipient callers (`spec_funs`, `connection` enter-game, `movement`
  follow, `give`/`position`/`magic_items` victim legs — masking applies) vs
  `recipient=None` broadcast-once callers (the MESSAGE_DELIVERY divergence —
  per-recipient PERS unreproducible).
- **Enforcement attempted + reverted**: routing `_pers` through
  `can_see_character` (gated on `viewer is not None`) regressed **15 tests**
  (`test_wiznet` ×7, `test_account_auth` ×4, `test_spec_funs` ×4). Root cause
  **pinned**: Python's wiznet path passes **roomless synthetic actors** —
  `announce_wiznet_new_player` (`mud/net/connection.py:207`) builds a
  `SimpleNamespace(name=…, sex=…)` placeholder with no room — and
  `can_see_character` (`mud/world/vision.py:161-164`) bails `room is None →
  False`. ROM `can_see` has **no `victim->in_room` check** and only dereferences
  `ch->in_room` for the dark check, after the trust/incog/holylight gates — ROM
  actors always have rooms, so the branch handles a state ROM never reaches.
  Result of the naive fix: **"Newbie alert! someone sighted."** / **"someone
  groks the fullness of his link."** in production — a real user-facing
  regression, not a test artifact. The change was reverted; `_pers` is unchanged
  except an INV-027 NOTE.
- **Blocker / prerequisite**: enforcement is blocked on reconciling
  `can_see_character`'s room-None handling with ROM `can_see` ordering (and/or
  having wiznet pass real-room actors). That helper has 43 `act_format` callers
  plus combat depending on it, so its room-None semantics (no ROM ground truth)
  need their own gap ID, failing test, and `gitnexus_impact` pass — explicitly
  NOT bundled here.
- **Contract locked**: `tests/integration/test_inv027_act_pers_name_masking.py`
  holds the same-room masking assertion as a **strict `xfail`** (reason names the
  blocker; remove the marker when the prerequisite lands) plus a passing
  `recipient=None` boundary guard. Tracker records the full probe outcome.
  **INV-027 stays OPEN.**

## Files Modified

- `mud/commands/imm_server.py` — `do_violate` four bamf calls → `_act_room_invis_gated`; import swapped (WIZ-046).
- `mud/utils/act.py` — `_pers` INV-027 NOTE only (no behavior change; enforcement reverted).
- `tests/integration/test_act_wiz_command_parity.py` — 2 new tests (WIZ-046).
- `tests/integration/test_inv027_act_pers_name_masking.py` — new file: strict-`xfail` masking contract + passing `recipient=None` boundary (INV-027).
- `docs/parity/ACT_WIZ_C_AUDIT.md` — WIZ-046 row ✅ FIXED; narrative/header/footer updated.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027 "Probe outcome (2026-05-29)" subsection + header status.
- `CHANGELOG.md` — `[2.11.31]` Fixed (WIZ-046); `[2.11.32]` Changed (INV-027 probe).
- `pyproject.toml` — 2.11.30 → 2.11.31 → 2.11.32.

Commits: `dfbb17f5` (WIZ-046), `47449114` (INV-027 probe). Both on `master`. The
pre-existing uncommitted `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` tweak
(carried across sessions, unrelated to parity) was left uncommitted.

## Test Status

- `tests/integration/test_act_wiz_command_parity.py` — 116 passed (+2 WIZ-046).
- INV-027 file — 1 passed (boundary), 1 xfailed (locked masking contract).
- wiznet/spec_funs/account_auth suites (post-revert) — 119 passed.
- **Full suite**: **4985 passed, 4 skipped, 1 xfailed** (123s; +1 passed +1
  xfailed vs the WIZ-046 baseline of 4984 = the two INV-027 tests). No regressions.
- `ruff check` on touched code: clean (the 4 errors in
  `test_act_wiz_command_parity.py` are pre-existing, lines ≤1538; 0 new).
- `gitnexus_impact`: WIZ-046 LOW (0 callers — leaf command); `act_format`
  upstream **CRITICAL** (43 direct callers) — warned, drove the empirical
  measure-then-revert. `gitnexus_detect_changes`: both commits LOW, 0 affected
  processes, scope exactly as expected. Reindexed after each commit.

## Outstanding

- **`can_see_character` room-None reconciliation** (INV-027 prerequisite, NEW) —
  `mud/world/vision.py:161-164` bails `room is None → False`; ROM `can_see`
  (`src/handler.c:2618-2664`) has no `victim->in_room` check and checks
  trust/incog/holylight before the dark gate. Blocks INV-027 enforcement; needs
  its own failing test + impact pass (43 `act_format` callers + combat). Filed in
  the INV-027 tracker bullet; not yet its own gap ID.
- **INV-027 enforcement** — once the prerequisite lands, remove the `xfail`
  marker and upgrade the `SimpleNamespace` mocks in `test_wiznet`/`test_spec_funs`
  to room-bearing / `has_affect`-bearing objects.
- Carried from prior sessions: pet-shop haggle/"now follows you" wrong-channel
  (INV-001 family, mailbox-only); `Character.pet` stale type annotation;
  `do_cast` object-targeting legs; converter hardening; the
  `test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.

## Next Steps

Per-file audit tracker remains exhausted; **cross-file invariants is the standing
pass**. Concrete next candidates, in rough priority:

1. **INV-027 prerequisite — roomless-actor visibility** (verify ordering first,
   then choose). The decision is **three-way**, not "just reorder
   `can_see_character`": (a) reorder `can_see_character` to ROM ordering
   (trust/incog/holylight before the dark gate; no `victim->in_room` bail);
   (b) move room-placement before the wiznet announce; (c) bake the name for the
   synthetic newbie/login cases. **Confirm the announce/placement ordering first**
   — `announce_wiznet_new_player` (`mud/net/connection.py:190`) takes `name: str`
   and builds its placeholder internally, firing at `connection.py:1698` *before*
   `char.room` is set at `:1879`, so "pass the real char" doesn't cleanly work and
   fixing `can_see_character` alone leaves the newbie alert still saying "someone."
   `can_see_character`'s room-None branch guards a state ROM never reaches, so the
   reconciliation is a design choice, not strictly a bug fix. Give the chosen fix a
   gap ID (consider a `VISION-00x` row so it's `rom-gap-closer`-able), write the
   ROM-contract failing test, run `gitnexus_impact` (expect CRITICAL). Unblocks INV-027.
2. **INV-027 enforcement** — after #1: route `_pers` through the reconciled
   visibility check, remove the `xfail`, realign the mock-based tests. Promote the
   per-recipient subset to ENFORCED (broadcast-once stays MESSAGE_DELIVERY-divergent).
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).
