# Session Summary — 2026-06-02 — ACT_COMM-003 STOP_FOLLOWER DELIVERY CHANNEL

## Scope

Cross-file invariants is the sole active pass (no per-file audit gaps remain).
Picked up from the prior session's recommended probe — the **group/follower
chain** (`add_follower`/`stop_follower`/`die_follower`, `src/act_comm.c`). The
chain's membership/pointer coherence is already locked by INV-020 (NPC-death
dissolves group, the `nuke_pets`→`die_follower` extract chain) and INV-031
(PC-death preserves group). The probe instead surfaced a **message-delivery
channel** divergence: `stop_follower` was the leftover asymmetric cousin in the
INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family — `add_follower` had
been migrated to `push_message`, but `stop_follower` still used the raw mailbox.

## Outcomes

### `ACT_COMM-003` — ✅ FIXED (stop_follower wrong-channel)

- **Python**: `mud/characters/follow.py:64-70` (`stop_follower`).
- **ROM C**: `src/act_comm.c:1626-1627` — both lines emitted via `act()`
  (TO_VICT `"$n stops following you."`, TO_CHAR `"You stop following $N."`),
  which writes straight to the descriptor — immediate, single-channel.
- **Gap**: `ACT_COMM-003` — `stop_follower` used raw `char.messages.append(...)`
  for both lines, the mailbox fallback a **connected** PC only drains on its
  next prompt. The sibling primitive `add_follower` (lines 41/44) already used
  `push_message` (async send for connected PCs). The asymmetry is observable
  **off the command path** — `die_follower` iterating the registry on a leader's
  extract/death, or charm wearing off mid-tick — where the connection loop does
  not drain the mailbox right after the call.
- **Fix**: both lines now route through `push_message` (async send for connected
  PCs, mailbox fallback for disconnected chars / tests), matching `add_follower`.
  The `can_see`/`in_room` gate (FOLLOW-002) and the unconditional detach state
  (`master = None`, `leader = None`, `master.pet` clear) are unchanged.
- **Impact**: `gitnexus_impact({target: "stop_follower"})` = **CRITICAL** (27
  impacted, 5 direct callers: `add_follower`, `die_follower`, `_nuke_pets`,
  `check_killer`, `charm_person` — reaching death/extract/charm/shop/quit).
  Reported to the user. The risk is bounded: `push_message` is byte-identical to
  the old append for any char **without** a `.connection`, so disconnected chars
  and every existing test are unaffected — only connected PCs change behaviour.
  `gitnexus_detect_changes` rated the actual change **low** (scope confined to
  `stop_follower`, zero affected processes).
- **Tests**: `tests/integration/test_act_comm003_stop_follower_delivery_channel.py`
  (1 test, connected PCs: both lines on the async connection channel, mailboxes
  empty). The existing follow tests use **disconnected** chars (mailbox fallback)
  so they false-green against unfixed code — the connected-PC harness (borrowed
  from `test_rescue_single_delivery.py`) is the only way to exercise the fix.
  Fail-first confirmed (lines stranded in mailbox, `sent=[]`).

## Files Modified

- `mud/characters/follow.py` — `stop_follower` two `messages.append` → `push_message`.
- `tests/integration/test_act_comm003_stop_follower_delivery_channel.py` — new, 1 test.
- `docs/parity/ACT_COMM_C_AUDIT.md` — added `ACT_COMM-003` row (✅ FIXED) in the
  add_follower/stop_follower helper gap table.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — added `stop_follower` to the
  INV-001 "Touched by" trail (no new INV row — tracker is at 26, over the ~20
  soft cap; this is a wrong-channel cousin of an existing contract).
- `CHANGELOG.md` — added `ACT_COMM-003` `Fixed` entry under `[Unreleased]`.
- `pyproject.toml` — 2.12.66 → 2.12.67.

## Test Status

- `pytest tests/integration/test_act_comm003_stop_follower_delivery_channel.py` — 1/1.
- Follow/comm/delivery area suite (act_comm001/002, can_see gating, inv020,
  nukepet001, rescue) — 15/15.
- Full suite: **5334 passed, 4 skipped** (~125s parallel) — zero fallout from the
  CRITICAL-blast-radius `stop_follower` change.

## Next Steps

Cross-file invariants remains the active pass. The group/follower chain's
membership/pointer coherence (INV-020, INV-031) and now its `stop_follower`
delivery channel (ACT_COMM-003) are all locked; `add_follower` and
`stop_follower` are channel-symmetric. The tracker is at **26 enforced** INV
rows — past the ~20 soft cap AGENTS.md flags; a future session should weigh
**consolidation** (the INV-014/INV-015 precedent merged paired rows) before
adding more. Remaining uncovered cross-file candidate: **mob trigger ordering**
(TRIG_* dispatch sequence vs ROM). Probe-then-scope: read ROM C contract → read
Python equivalent → one failing test → close as a gap or file as INV-034.

> **Push note:** 2.12.67 (`a181a894`) is committed locally on `master` but
> **NOT yet pushed** to `origin/master` (which sits at `64f0dc1d` / 2.12.66).
> Push when ready; CHANGELOG/version reflect 2.12.67.
