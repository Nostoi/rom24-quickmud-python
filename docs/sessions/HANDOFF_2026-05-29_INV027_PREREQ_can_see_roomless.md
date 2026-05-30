# Handoff — 2026-05-29 — INV-027 prerequisite: `can_see_character` roomless-target policy

Continuation of the WIZ-046 / INV-027-probe session. Picks up **Next Task #1**
from `SESSION_STATUS.md`: the `can_see_character` room-None reconciliation that
blocks INV-027 (ACT-PERS-NAME-MASKING) enforcement.

This handoff exists because the session's tool-output channel began **buffering /
delaying results** mid-stream (Bash/Read returning empty `result` blocks, then
flushing a batch several calls later). A CRITICAL-blast-radius change (43
`act_format` callers + combat via `pers`) cannot be driven safely through a
TDD loop without a reliable read of `pytest`/`grep` output, so the analysis was
captured here durably before any code was written. **No code was changed this
session.** Re-attempt when the harness output channel is reliable.

## Confirmed ROM ground truth (primary source, read this session)

1. **`can_see(ch, victim)`** — `src/handler.c:2618-2664`. The function only ever
   dereferences the **looker's** room: `room_is_dark(ch->in_room)` and the incog
   comparison `ch->in_room != victim->in_room`. It **never NULL-checks nor
   dereferences `victim->in_room`**. Ordering: `ch==victim` → trust<invis_level →
   incog → holylight/imm → blind → dark(ch->in_room) → invisible → sneak → hide →
   TRUE.
2. **ROM `wiznet`** — `src/act_wiz.c:171-194`. Per recipient `d`, calls
   `act_new(string, d->character, obj, ch, TO_CHAR, POS_DEAD)`. So in the
   recipient's render: `$n` actor = `d->character` (recipient), `$N` (vch) = the
   wiznet `ch` argument (the subject/sender). `$N` name-masking =
   `PERS(ch, d->character)` = `can_see(d->character /*recipient*/, ch /*subject*/)`.
3. **ROM newbie alert** — `src/nanny.c:547`:
   `wiznet("Newbie alert!  $N sighted.", ch, NULL, WIZ_NEWBIE, 0, 0)` passes the
   **real** new-player `ch`, whose `in_room` is **NULL** at `CON_GET_NEW_CLASS`
   (char_to_room happens later). `$N` still renders the real name because
   `can_see(recipient, newplayer)` only touches the recipient's room.

## The actual decision (per advisor — NOT a ROM mandate)

ROM never has a roomless char inside `can_see` at all, so there is **no ROM
ground truth** for how Python should treat a roomless *target*. The
`target_room is None → False` bail at `mud/world/vision.py:163` is a **Python
policy** guarding a **Python-only state** (chars mid-teleport/mid-extract, and the
synthetic wiznet subjects). It is currently *over-broad*: it also masks the
legitimate wiznet case where the subject is intentionally roomless. The fix is a
deliberate policy choice; document it as such in the gap doc + commit, do **not**
claim "ROM requires removing the bail."

### Biggest regression risk (gate the whole thing on this)

Removing the `target_room is None` bail makes a roomed observer able to "see" a
roomless target. In combat that never happens (targets have rooms). The danger is
`look` / `scan` / `who` / `where` / auto-exit / room-listing code that iterates
`room.people` or the registry and could encounter a target with `room=None`
mid-teleport/mid-extract — today they silently mask it; after the change they'd
surface a "roomless ghost," a behavior ROM never exhibits (ROM extracts
atomically). **Run the caller census and read every such site before writing the
vision change.** If any path can pass `room=None` targets, guard at the call site
(or keep masking there) rather than loosening `can_see_character` globally.

Census commands to run (were blocked by the buffering issue this session):
```
grep -rn "can_see_character" mud/
grep -rn "\bpers(" mud/ | grep -v "def pers\|def _pers\|describe_character"
grep -rln "can_see_character" tests/
```
Then open each `look`/`scan`/`who`/`where`/exit-listing caller.

## Recommended decomposition (three commits, ordered; gates between)

**Commit 0 (lowest risk, do first) — enrich the synthetic wiznet placeholders.**
`mud/net/connection.py` has `SimpleNamespace` actors that lack `has_affect`,
`invis_level`, `room`, etc.:
- `:207` `announce_wiznet_new_player` → `SimpleNamespace(name, sex)` (newbie alert `$N`).
- `:417` reconnect "$N groks the fullness of $S link." path (`_broadcast_reconnect_notifications`).
- (`:249`, `:281`, `:1222`, `:1340`, `:1642` are other SimpleNamespace uses — audit which feed `act_format`/`wiznet`; the helper ones at 1222/1340 already carry `room=None`.)
ROM passes a **real `ch`**, so make these real `Character(name=…, sex=…,
is_npc=False)` with `room=None` (a real Character has `has_affect`, `invis_level=0`).
Re-run the 15 originally-regressing tests (`test_wiznet` ×7, `test_account_auth`
×4, `test_spec_funs` ×4) — this commit alone should leave them green and removes
the AttributeError surface before the scary change. NOTE: a real
`Character(room=None)` still hits the `target_room is None` bail, so enrichment
alone does NOT fix the newbie name — it just de-risks. The vision change is still
required.

**Commit 1 (VISION-00x) — `can_see_character` roomless-target policy.**
After the caller census clears: stop returning False solely because
`target_room is None`; keep `observer_room is None → False` (defensive — the
looker always has a room in ROM, and the dark check needs it). Corner to decide
explicitly: the dark gate at `vision.py:181` is `observer_room is target_room and
room_is_dark(observer_room)`; with `target_room=None` that is False, so a roomless
subject is visible **even from a dark observer room** — which diverges from ROM
(ROM's looker-dark-room WOULD mask). Decide whether to care; if yes, change the
dark gate to key off `observer_room` darkness regardless of same-room (separate,
larger scope — probably defer and note it).
Failing test asserting the exact corner:
- roomed observer **sees** roomless non-invisible target → True
- roomed observer **still masks** an *invisible* roomless target (no detect-invis) → False
- observer with `room=None` → still False
Run `gitnexus_impact` on **both** `can_see_character` and `pers` (expect
CRITICAL). Give it a `VISION-00x` row in the relevant audit doc so it's
`rom-gap-closer`-able.

**Commit 2 (INV-027 enforcement) — route `_pers` through the gate.**
`mud/utils/act.py:_pers` → call `can_see_character(viewer, target)` when
`viewer is not None and target is not viewer` (the recipient-not-None scope the
existing test already encodes); return `"someone"` when it fails. Remove the
`xfail` in `tests/integration/test_inv027_act_pers_name_masking.py`. Upgrade any
remaining `SimpleNamespace` mock actors in `test_wiznet`/`test_spec_funs` to
room-bearing / `has_affect`-bearing objects. Promote INV-027 to **ENFORCED**
(per-recipient subset only; the broadcast-once `recipient=None` path stays the
documented MESSAGE_DELIVERY.md divergence — the boundary test already pins it).

## Pre-flight before re-attempting
- Confirm the output channel is reliable (run `pytest -n0 <one test>` and verify
  you can actually read pass/fail).
- Re-run the 15 previously-regressing tests on current `master` to capture the
  exact list + current green state as your regression oracle.
- `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` has a pre-existing uncommitted
  tweak carried across sessions (unrelated to parity) — leave it or commit
  separately, do not fold into parity commits.

## Key file:line references
- `mud/world/vision.py:153-202` `can_see_character`; `:163` the bail; `:181` dark gate; `:294` `pers`.
- `mud/utils/act.py:56` `_pers`; `:107` `act_format`; `:139/:141` `$n`/`$N` → `_pers`.
- `mud/wiznet.py:233-254` `_wiznet_deliver` → `act_format(recipient=ch, actor=sender or ch, arg2=sender)`.
- `mud/net/connection.py:207`, `:417` synthetic wiznet actors.
- ROM: `src/handler.c:2618` `can_see`; `src/act_wiz.c:171` `wiznet`; `src/nanny.c:547` newbie alert.
- Test: `tests/integration/test_inv027_act_pers_name_masking.py` (xfail to remove).
