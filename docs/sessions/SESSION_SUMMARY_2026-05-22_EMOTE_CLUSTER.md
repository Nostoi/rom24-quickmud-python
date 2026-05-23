# Session Summary — 2026-05-22 — `do_emote` re-audit (EMOTE-001/002 + PMOTE-001 stub)

## Scope

Third slice of the 2026-05-22 act_comm.c re-audit arc. Applied the
same audit lens to `do_emote` that just closed `do_say` (SAY-001..004).
The reusable `pers()` helper added in 2.8.41 made EMOTE-001 trivial
to close — proving the "this helper unblocks the channel-message
cluster" hypothesis from the SAY-002 summary. Also surfaced
PMOTE-001 as a missing-function gap (`do_pmote` not implemented in
Python at all); stable-IDed for a future session.

## Outcomes

### `EMOTE-001` — ✅ FIXED — `do_emote` per-listener PERS substitution (2.8.42)

- **Python**: `mud/commands/communication.py:do_emote`
- **ROM C**: `src/act_comm.c:1091`, `src/handler.c:2618-2664 can_see`
- **Fix**: Refactored TO_ROOM delivery from one `broadcast_room`
  call with `f"{char.name} {args}"` to a per-listener loop using
  `mud.world.vision.pers(char, listener)`. Invisible emoter now
  renders as `"someone"` to listeners without `DETECT_INVIS`.
- **Tests**:
  - `tests/integration/test_emote_parity.py::test_emote_001_invisible_emoter_renders_as_someone_to_unaided_listener`
  - `tests/integration/test_emote_parity.py::test_emote_001_visible_emoter_renders_real_name_to_listener` (control)
- **Commit**: `4c61270`.

### `EMOTE-002` — ✅ FIXED — `do_emote` TO_CHAR renders "You" (2.8.43)

- **Python**: `mud/commands/communication.py:do_emote`
- **ROM C**: `src/act_comm.c:1092`
- **Fix**: Return `f"You {args}"` instead of `f"{char.name} {args}"`. ROM's `act()` on the TO_CHAR branch substitutes `$n` to "You" — the actor reads `"You smiles happily"`, not `"Alice smiles happily"`.
- **Test**: `tests/integration/test_emote_parity.py::test_emote_002_self_message_renders_you_not_actor_name`.
- **Legacy fix**: `tests/integration/test_communication_enhancement.py::TestEmoteCommand::test_emote_broadcasts_custom_action` updated to ROM-exact form.
- **Commit**: `e10aa0f`.

### `PMOTE-001` — ❌ MISSING (stable-IDed, not closed)

- **ROM C**: `src/act_comm.c:1098-1198`
- **Python**: not implemented.
- ROM `do_pmote` is a personalized-emote that substitutes second-person ("you") for matched player names per-recipient — far more complex than `do_emote` (string-matching loop with quote/possessive handling). Filed in `ACT_COMM_C_AUDIT.md` for a future session — not a one-commit fix.

## Files Modified

- `mud/commands/communication.py` — `do_emote` refactored to per-listener PERS substitution + TO_CHAR "You" return.
- `tests/integration/test_emote_parity.py` — **new file** — three tests (EMOTE-001 invis, EMOTE-001 visible control, EMOTE-002 self).
- `tests/integration/test_communication_enhancement.py` — updated `test_emote_broadcasts_custom_action` to ROM-exact form.
- `docs/parity/ACT_COMM_C_AUDIT.md` — `do_emote` row flipped from PARTIAL ⚠️ to active gap table; EMOTE-001/002 ✅ FIXED, PMOTE-001 ❌ MISSING.
- `CHANGELOG.md` — `[2.8.42]`, `[2.8.43]` sections.
- `pyproject.toml` — 2.8.41 → 2.8.43.

## Test Status

- Targeted (`tests/integration/test_emote_parity.py`): 3/3 passing.
- Full suite: **4619 passed, 4 skipped** (+3 vs 2.8.41 baseline 4616/4; zero regressions).

## Next Steps

The "channel-message cluster" continues to fall fast now that
`pers()` exists. Natural next direction:

1. **`do_tell` re-audit** — high-traffic; the recipient receives by
   direct lookup so the PERS impact may be limited, but worth
   verifying broadcast wording (the `"$N tells you '$t'"` line uses
   `$N` = the speaker → does pass through PERS for the recipient).
2. **`do_shout` / `do_yell` channels** — global broadcasts; per-listener
   PERS cost is higher but ROM does it. Also worth verifying INV-001
   single-delivery (likely OK since `broadcast_global` is one
   function call, but check whether anything else echoes).
3. **PMOTE-001** — `do_pmote` greenfield port. Larger lift (~50 lines
   of C string matching) but well-bounded. Worth doing in its own
   session.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked + still drifting. Repo hygiene commit pending.
- GitNexus 32 KB scope-extractor failures persist on the documented file list; this slice did not touch any listed file.
- Local commits `4c61270` + `e10aa0f` not pushed yet — waiting on explicit user push approval.
