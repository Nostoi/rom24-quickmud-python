# Session Summary — 2026-05-29 — VISION-001 prerequisite + INV-027 (ACT-PERS-NAME-MASKING) ENFORCED

## Scope

Continuation of the WIZ-046 / INV-027-probe session, picking up **Next Task #1**
from `SESSION_STATUS.md` (and the durable `HANDOFF_2026-05-29_INV027_PREREQ_can_see_roomless.md`
written when the prior session's tool-output channel began buffering): the
`can_see_character` room-None reconciliation that blocked INV-027 enforcement.
The output channel was reliable this session, so the prerequisite was closed
**and** INV-027 enforcement was carried through to ENFORCED. One INV-027-class
sibling leak surfaced during the advisor review and was filed durably as an OPEN
gap rather than waved past.

Three commits landed (one cross-file prerequisite, one enforcement, one
honesty/doc follow-up).

## Outcomes

### `VISION-001` — ✅ FIXED (2.11.33, `8270c544`)

- **Python**: `mud/world/vision.py:can_see_character` (the `target_room is None` bail).
- **ROM C**: `src/handler.c:2618-2664` (`can_see` — never NULL-checks nor
  dereferences `victim->in_room`; only the looker's room matters).
- **Gap**: VISION-001 — `can_see_character` returned `False` whenever the
  **target** was roomless, over-masking the legitimate roomless-subject case
  (the new player passed to `wiznet("Newbie alert! $N sighted.", ...)` at
  `src/nanny.c:547`, whose `in_room` is NULL at `CON_GET_NEW_CLASS`).
- **Fix**: drop the `target_room is None` bail; keep `observer_room is None →
  False` (defensive — ROM's looker always has a room and the dark gate
  dereferences `ch->in_room`).
- **Safety**: `gitnexus_impact` = CRITICAL (124 impacted, 28 direct callers). A
  full caller census confirmed no descriptor/registry/`room.people` iterator can
  observe a roomless target except the intentional synthetic wiznet subjects:
  `do_who` iterates `SESSIONS` (roomed by construction — room set at
  `connection.py:1879` before `SESSIONS` registration at `:1903`); `do_where`
  (`info.py:314`) and `do_whois` (`info_extended.py:235`, `CON_PLAYING` filter)
  carry their own guards; room transitions are synchronous (no `await` between
  `room=None` and re-placement/extract — `room.py:176`, `game_loop.py:546`).
- **Tests**: `tests/test_vision_roomless_target.py` (3) — roomed observer in a
  LIT room sees a roomless non-invisible target; still masks an invisible
  roomless target without detect-invis; roomless observer still cannot see.
- **Deferred sibling**: VISION-002 (the dark gate's non-ROM `observer_room is
  target_room` same-room guard, `vision.py` vs `handler.c:2638`) filed OPEN in
  `HANDLER_C_AUDIT.md`. Does **not** block INV-027 (tests place the observer in
  a lit room).

### `INV-027` (ACT-PERS-NAME-MASKING) — ✅ ENFORCED, per-recipient `act_format` subset (2.11.34, `e1829bdf`)

- **Python**: `mud/utils/act.py:_pers` now routes `$n`/`$N` through
  `mud/world/vision.py:can_see_character` when `viewer is not None and target is
  not viewer`, returning `"someone"` on failure. The `recipient=None`
  broadcast-once path keeps the name (no viewer to gate against — the
  `MESSAGE_DELIVERY.md` divergence; pinned by a boundary test).
- **ROM C**: `src/merc.h:2145` (`PERS`) → `src/handler.c:2618-2664` (`can_see`);
  wiznet uses the same masking (`src/act_wiz.c:188` passes the actor as `vch`).
- **Production enrichment**: `announce_wiznet_new_player`
  (`mud/net/connection.py`) now builds a **real roomless `Character`** as the
  newbie-alert subject instead of a bare `SimpleNamespace`, so `$N` renders the
  real name via VISION-001 (ROM `nanny.c:547` passes the real roomless `ch`) and
  the `has_affect`/`invis_level` reads don't raise. (`Character()` does not
  self-register into `character_registry` — verified, no phantom leak.)
- **Test-mock enrichment** (the 15 predicted regressions: `test_wiznet` ×7,
  `test_account_auth` ×4, `test_spec_funs` ×4): mock recipients were roomless
  real `Character`s (→ masked) or bare `SimpleNamespace` without `has_affect`
  (→ AttributeError once VISION-001 removed the early bail). Fixed by rooming
  the listeners in lit rooms (`_connected_character` helper, `_give_lit_room`)
  and adding a no-affect `has_affect` stub (`_no_affect`) — matching production
  (real roomed immortals). **Expected strings unchanged** (real names); the
  dedicated INV-027 test (real `Character`s) locks the masking contract.
- **Tests**: `tests/integration/test_inv027_act_pers_name_masking.py` — the
  `xfail` marker removed; `test_act_pers_masks_invisible_actor_name_for_nonseeing_recipient`
  now passes alongside the `recipient=None` boundary guard.

### `WIZ-047` — ❌ FILED OPEN (2.11.34 doc, `1089dd13`)

- **Python**: `mud/commands/imm_commands.py:_act_room` (line 475) does
  `message.replace("$n", char_name)` **unconditionally** — no PERS masking.
- **ROM C**: `src/act_wiz.c` `do_transfer` (`act("$n ...", TO_ROOM)`, PERS-masked).
- **Why filed, not fixed**: same INV-027 PERS contract on a different
  enforcement point (an invisible/wiz-invis transferred immortal leaks its real
  name to non-seeing witnesses). The original INV-027 writeup listed
  "reconcile the two `_act_room` helpers" as in-scope; the 2.11.34 enforcement
  deliberately scoped its code fix to `act_format._pers` only. Surfaced by the
  advisor reviewing the enforcement for completeness — filed durably as a MEDIUM
  OPEN gap in `ACT_WIZ_C_AUDIT.md` (Phase 3) and cross-referenced from the
  INV-027 row, rather than buried under the "ENFORCED" checkmark. Distinct from
  WIZ-045/046 (whole-bamf-line `invis_level` suppression on `do_goto`/`do_violate`).

## Files Modified

- `mud/world/vision.py` — dropped the `target_room is None` bail (VISION-001).
- `mud/utils/act.py` — `_pers` routes `$n`/`$N` through `can_see_character` (INV-027).
- `mud/net/connection.py` — newbie-alert subject is now a real roomless `Character`.
- `tests/test_vision_roomless_target.py` — new, VISION-001 (3 tests).
- `tests/integration/test_inv027_act_pers_name_masking.py` — `xfail` removed.
- `tests/test_wiznet.py` — `_connected_character` places each mock in a lit room.
- `tests/test_account_auth.py` — `_give_lit_room` helper; roomed 4 wiznet-listener tests.
- `tests/test_spec_funs.py` — `_no_affect` `has_affect` stub on 4 spec-fun tests' char mocks.
- `docs/parity/HANDLER_C_AUDIT.md` — added VISION-001 (FIXED) + VISION-002 (OPEN) stable-ID rows.
- `docs/parity/ACT_WIZ_C_AUDIT.md` — added WIZ-047 (OPEN) gap row.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-027 → ENFORCED (subset) + Remaining (OPEN) WIZ-047.
- `CHANGELOG.md` — added 2.11.33 (VISION-001) + 2.11.34 (INV-027) sections.
- `README.md` — version 2.11.32 → 2.11.34; test suite 4985/1-xfailed → 4989/0-xfailed.
- `pyproject.toml` — 2.11.32 → 2.11.33 → 2.11.34.

## Test Status

- `tests/test_vision_roomless_target.py` — 3/3 passing.
- `tests/integration/test_inv027_act_pers_name_masking.py` — 2/2 passing (xfail removed).
- 15-test regression oracle (`test_wiznet` + `test_account_auth` + `test_spec_funs` + `test_spec_funs_extra`) — green.
- **Full suite**: 4989 passed, 4 skipped, 0 xfailed (~96s parallel).
- `ruff check` on changed production files (`vision.py`, `act.py`, `connection.py`) — clean. (Pre-existing test-file lint/format drift untouched — out of scope.)

## Next Steps

Cross-file invariants remains the standing pass (per-file audit tracker has no
⚠️ Partial / ❌ Not Audited rows). Concrete next options:

1. **`WIZ-047`** (`imm_commands._act_room` `$n` leak) — the remaining half of the
   INV-027 PERS contract. `rom-gap-closer`-able: write the failing per-recipient
   test (invisible transferred char → non-seeing witness sees "someone", seeing
   witness sees the name), then route `_act_room`'s `$n` through
   `vision.pers(char, person)` per-recipient. One gap = one test = one commit.
2. **`VISION-002`** — the dark-gate same-room divergence (`vision.py` vs
   `handler.c:2638`). Larger scope (could shift cross-room/scan visibility);
   file a failing test first.
3. Fresh cross-file probe in an area not yet covered by an INV row (affect ticks,
   position transitions, mob script triggers, group/follower chain).

Carried-open (unchanged): pet-shop haggle/"now follows you" wrong-channel
(INV-001 family, mailbox-only); `Character.pet` stale type annotation; `do_cast`
object-targeting legs; converter hardening; the
`test_backstab_uses_position_and_weapon` / `test_combat_death.py` xdist flakes.
