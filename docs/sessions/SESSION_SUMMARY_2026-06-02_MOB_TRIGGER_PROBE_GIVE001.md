# Session Summary — 2026-06-02 — MOB-TRIGGER ORDERING PROBE + GIVE-001

## Scope

Cross-file invariants is the sole active pass. Continued from the ACT_COMM-003
session (same day) by probing the remaining recommended candidate: **mob trigger
(TRIG_*) dispatch ordering**. The probe verified the three highest-value
ordering contracts are faithful and surfaced one incidental delivery-channel bug
(GIVE-001) in an already-✅ row.

## Probe result — mob-trigger ordering is faithful (3 contracts verified)

Read the ROM C contract and Python equivalent for the three ordering contracts
most likely to drift; all match — a legitimate reportable conclusion, not a
failed probe:

1. **TRIG_ENTRY / TRIG_GREET / TRIG_GRALL on room entry** (`src/act_move.c:238-243`,
   `mp_greet_trigger` `src/mob_prog.c:1325-1349`): ROM fires TRIG_ENTRY only for
   **NPC** movers and TRIG_GREET/GRALL only when a **PC** moves (`!IS_NPC(ch)`),
   *after* followers have moved. Python's `mud/world/movement.py` (walk path
   :487-490, portal path :630-633) gates identically; `mobprog.py:mp_greet_trigger`
   replicates the GREET (default_pos + can_see) / GRALL exclusivity.
2. **TRIG_DEATH** (`src/fight.c:917-924`): ROM fires it from `damage()` **before**
   `raw_kill`, NPC-gated, with `position = POS_STANDING` forced first. Python
   `mud/combat/engine.py:apply_damage:752-759` fires `mp_death_trigger` before
   `_handle_death`, NPC-gated, position forced to STANDING. Coverage matches too:
   the trigger fires only from the damage path, so `do_slay`→`raw_kill` correctly
   **skips** it in both. (A cosmetic divergence — ROM leaves position STANDING
   into `raw_kill`, Python restores DEAD in a `finally` — was confirmed
   **unobservable**: `_handle_death`/`raw_kill` never branch on the incoming NPC
   position; dropped, not filed.)
3. **TRIG_GIVE** (`src/act_obj.c:830-842`): ROM transfers the object to the victim,
   emits the messages, then fires `mp_give_trigger` — so the object is in the
   mob's inventory when the give-prog runs. Python `mud/commands/give.py:78-98`
   mirrors this ordering exactly.

Not probed this pass (left for a future probe): bribe/exit/fight/kill/hpcnt
ordering. **No wholesale "mob triggers are clean" claim** — only these three.

## Outcomes

### `GIVE-001` — ✅ FIXED (do_give recipient TO_VICT wrong-channel)

- **Python**: `mud/commands/give.py:93` (object branch) + `:147` (coins branch,
  `_give_money`).
- **ROM C**: `src/act_obj.c:834` (`"$n gives you $p."`, object) + `~726` (coins) —
  both emitted via `act(..., TO_VICT)`, immediate descriptor write.
- **Gap**: both branches delivered the recipient line via raw
  `victim.messages.append(...)` — the mailbox fallback a **connected** PC only
  drains on its next prompt — so a connected recipient saw the gift line **late**.
  INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family (the ACT_COMM-003
  shape). The giver's TO_CHAR line was already correct (returned by `do_give`,
  sent by the connection loop) — only the victim leg was wrong-channel. Filed as
  a new ID in `ACT_OBJ_C_AUDIT.md` because the `do_give` row was already
  ✅ 100% (out-of-scope bug in an audited row, per AGENTS.md routing).
- **Fix**: both legs route through `push_message` (async send for connected PCs,
  mailbox fallback for disconnected/tests). `push_message` does not dispatch
  TRIG_ACT, so the object branch's `disable_mobtrigger()` contract (ROM `:832`
  MOBtrigger=FALSE) is unaffected.
- **Impact**: `gitnexus_impact({target: "do_give"})` = **LOW** (only the
  dispatcher reaches it). `gitnexus_detect_changes` = low (confined to
  `do_give`/`_give_money`, zero affected processes).
- **Tests**: `tests/integration/test_give001_victim_delivery_channel.py` (2 tests,
  connected PCs: object-give + coins-give recipient line on the async channel,
  mailbox empty). Fail-first confirmed (`sent=[]`). Existing give tests use
  disconnected chars (mailbox fallback) so they false-green against unfixed code.

## Files Modified

- `mud/commands/give.py` — both victim TO_VICT legs `messages.append` → `push_message`.
- `tests/integration/test_give001_victim_delivery_channel.py` — new, 2 tests.
- `docs/parity/ACT_OBJ_C_AUDIT.md` — added `GIVE-001` gap row (✅ FIXED) under the
  do_give section.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added `give.py` to the INV-001
  "Touched by" trail (no new INV row — wrong-channel cousin of an existing contract).
- `CHANGELOG.md` — added `GIVE-001` `Fixed` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.67 → 2.12.68.

## Test Status

- `pytest tests/integration/test_give001_victim_delivery_channel.py` — 2/2.
- Give area suite (test_give_command + inv025_give_pers_sweep) — 20/20.
- Full suite: **5336 passed, 4 skipped** (~133s parallel) — zero fallout.

## Next Steps

Cross-file invariants remains the active pass. **Tracker is at 26 enforced INV
rows — past the ~20 soft cap AGENTS.md flags; a future session should weigh
consolidation (INV-014/INV-015 precedent) before adding new rows.** The two
delivery-channel fixes this day (ACT_COMM-003, GIVE-001) both filed under
INV-001's wrong-channel trail rather than minting new rows. Remaining
mob-trigger ordering contracts **not yet probed**: bribe / exit / fight / kill /
hpcnt. Probe-then-scope: read ROM C contract → read Python equivalent → one
failing test → close as a gap or file as INV-034.

> **Push note:** this session's two commits — 2.12.67 (`a181a894`, ACT_COMM-003)
> and 2.12.68 (`a6fb9c03`, GIVE-001) — plus the two handoff-docs commits are on
> local `master` but **NOT yet pushed** to `origin/master` (which sits at
> `64f0dc1d` / 2.12.66). CHANGELOG/version reflect 2.12.68.
