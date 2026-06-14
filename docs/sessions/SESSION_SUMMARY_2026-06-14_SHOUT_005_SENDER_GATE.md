# Session Summary — 2026-06-14 — `do_shout` sender-gate parity (SHOUT-005)

## Scope

Continuation of the cross-file / broadcast-surface parity loop. SESSION_STATUS.md
named the **act_comm.c broadcast inventory** as the next intended task ("verify the
full inventory" of `do_say`/`do_yell`/`do_shout`/channels now that the act()-lens
vein is exhausted). Swept the three core broadcast verbs against ROM C:

- **`do_say`** (communication.py:181-234) — verified correct: per-listener PERS via
  `pers(char, listener)`, `push_message` (INV-001 XOR), TRIG_ACT gate, SPEECH
  trigger loop all match ROM `act_comm.c:768-791`. No gap.
- **`do_yell`** (communication.py:764-813) — verified correct: no WAIT_STATE (ROM
  `do_yell` has none), same-area `descriptor_list` filter, PERS wording. No gap.
- **`do_shout`** (communication.py:309-353) — **GAP FOUND**: sender-gate sequence
  diverged from ROM on three branches. Closed as SHOUT-005.

One gap closed via failing-test-first → fix → green → audit-row flip → CHANGELOG →
version bump → commit → reindex. Suite 5782 → 5783 passing; version 2.14.94 → 2.14.95.

## Outcomes

### `SHOUT-005` — ✅ FIXED

- **Python**: `mud/commands/communication.py:319-326` (do_shout sender gates)
- **ROM C**: `src/act_comm.c:814-820`
- **Gap**: `do_shout`'s sender-gate sequence borrowed preconditions that belong to
  the `talk_channel` family (gossip/grats, `act_comm.c:297-303`), not to shout.
  ROM `do_shout` gates the sender **only** on `COMM_NOSHOUT`, then unconditionally
  `REMOVE_BIT(ch->comm, COMM_SHOUTSOFF)` and proceeds. Python wrongly added three
  blocking early-returns:
  - (a) `COMM_NOCHANNELS` → "The gods have revoked your channel privileges." —
    spurious; a god-silenced player can still shout in ROM.
  - (b) `COMM_QUIET` → "You must turn off quiet mode first." — spurious; a quieted
    player can still shout in ROM (QUIET only gates *listeners*).
  - (c) `COMM_SHOUTSOFF` → "You must turn shouts back on first." — **inverted**;
    ROM auto-clears the shouter's own shouts-off (`REMOVE_BIT`, silently) and
    delivers the shout, rather than blocking.
- **Fix**: deleted the NOCHANNELS and QUIET sender gates; replaced the
  SHOUTSOFF-block branch with `_clear_comm_flag(char, CommFlag.SHOUTSOFF)`. Only
  the NOSHOUT gate remains before the clear, matching ROM exactly. `banned_channels`
  (a QuickMUD extension, not in ROM) left untouched.
- **Tests**: `tests/integration/test_shout_yell_parity.py::test_shout_005_sender_gate_matches_rom`
  (3 facets: NOCHANNELS-can-shout, QUIET-can-shout, SHOUTSOFF-auto-cleared+delivered).
  Two legacy assertions in `tests/test_communication.py::test_shout_and_tell_respect_comm_flags`
  updated (they encoded the divergent block/quiet-gate behavior). 25/25 green in the
  shout+communication slice; full suite 5783 passed / 4 skipped.

## Files Modified

- `mud/commands/communication.py` — do_shout: removed 2 spurious sender gates,
  inverted SHOUTSOFF branch → auto-clear (ROM REMOVE_BIT).
- `tests/integration/test_shout_yell_parity.py` — added `test_shout_005_sender_gate_matches_rom`.
- `tests/test_communication.py` — updated 2 legacy assertions in
  `test_shout_and_tell_respect_comm_flags` to ROM-correct behavior.
- `docs/parity/ACT_COMM_C_AUDIT.md` — added SHOUT-005 row (✅ FIXED); corrected the
  do_shout "ROM C Behavior" note (it had wrongly claimed a sender QUIET check
  "handled by caller" — ROM do_shout has no sender QUIET/NOCHANNELS gate at all).
- `CHANGELOG.md` — added 2.14.95 `Fixed` entry.
- `pyproject.toml` — 2.14.94 → 2.14.95.

## Test Status

- `pytest tests/integration/test_shout_yell_parity.py tests/test_communication.py` — 25/25 passing.
- `pytest tests/integration/test_inv001_comm_delivery_channel.py` — 4/4 passing (INV-001 SINGLE-DELIVERY unaffected).
- Full suite: **5783 passed, 4 skipped** (233s).
- `ruff check .` clean; `gitnexus_detect_changes` scope = do_shout + audit doc + 2 test files (low risk, 0 affected processes).

## Next Steps

act_comm.c broadcast inventory: the **three core verbs (`do_say`/`do_yell`/`do_shout`)
are now verified clean**. Remaining act_comm.c broadcast sites not yet swept under
this lens: the `talk_channel` family (`do_gossip`/`do_grats`/`do_quote`/`do_question`/
`do_answer` — confirm each gates sender on QUIET+NOCHANNELS per `act_comm.c:297-303`
and renders `$n` per-listener PERS), `do_pmote`/`do_emote` (EMOTE-005 prior — verify
pmote), and `do_tell`/`do_reply` (TELL-series prior). A 5-minute probe per verb:
read the ROM C gate sequence → diff the Python early-returns → one failing test if
they diverge. If all clean, the act_comm.c broadcast surface is fully swept and the
next move is a different divergence class from `DIVERGENCE_CLASS_ROSTER.md` (run
`/rom-divergence-sweep`) or the next cross-file INV candidate.
