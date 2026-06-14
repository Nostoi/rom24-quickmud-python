# Session Summary — 2026-06-14 — act_comm.c broadcast-verb sweep COMPLETE (TELL-009 + GOSSIP-003)

## Scope

Continued the `act_comm.c` broadcast-verb sweep handed off from the SHOUT-005
session. The remaining verbs to reconcile against ROM were the `talk_channel`
family (gossip/grats/quote/question/answer/music/auction), `do_pmote`, and
`do_tell`/`do_reply`. Method per verb: read the ROM C gate sequence → diff the
Python early-returns → one failing test if they diverge (one gap = one test =
one commit). Two real divergences surfaced and were closed; `do_pmote` and
`do_reply` were verified parity-clean with no code change. The act_comm.c
broadcast surface is now **fully swept**.

Both divergences were the same epistemic failure the AGENTS.md re-verify mandate
warns about: a stale audit note ("acceptable addition / acceptable enhancement")
asserting a known-divergent behavior was ROM-correct. Reading ROM C — not the
doc — caught both. This is the third such catch in the act_comm.c sweep after
SHOUT-005.

## Outcomes

### `TELL-009` — ✅ FIXED (v2.14.96)

- **Python**: `mud/commands/communication.py:do_tell` (removed the NOCHANNELS gate at the former line 246-247)
- **ROM C**: `src/act_comm.c:850-866`
- **Gap**: spurious `COMM_NOCHANNELS` sender gate. ROM `do_tell` gates the
  sender **only** on `NOTELL||DEAF` → "Your message didn't get through.", then
  `QUIET` → "You must turn off quiet mode first." (then a dead `DEAF` branch).
  There is **no** NOCHANNELS gate — NOCHANNELS revokes the *public* channels
  (the `talk_channel` family, act_comm.c:297-303), not the private `tell`. A
  god-silenced player can still send tells in ROM; Python blocked them with
  "The gods have revoked your channel privileges." Same category error as
  SHOUT-005 (channel-family gate wrongly borrowed onto a hand-written verb).
- **Fix**: deleted the NOCHANNELS gate; left a ROM-citing comment. `banned_channels`
  (a QuickMUD extension) untouched. Corrected the stale "acceptable enhancement"
  note in the audit doc.
- **Tests**: `tests/integration/test_tell_parity.py::test_tell_009_nochannels_sender_can_still_tell` (1, green); full tell-parity suite 7/7.

### `GOSSIP-003` — ✅ FIXED (v2.14.97)

- **Python**: `mud/commands/communication.py:_check_channel_blockers` (:366) + `do_clantalk` (:631)
- **ROM C**: `src/act_comm.c:306/363/420/477/535/592/649/704`, `src/act_wiz.c:342/351`
- **Gap**: the NOCHANNELS channel-revocation line used corrected English
  "privileges" instead of ROM's **misspelled** "priviliges". ROM emits
  `"The gods have revoked your channel priviliges.\n\r"` verbatim at all 8
  talk_channel sites + the imm revoke/restore. A faithful port replicates the
  typo. The shared `_check_channel_blockers` gate (covers
  gossip/grats/quote/question/answer/music/auction) and `do_clantalk`'s own
  inline gate both diverged; `mud/commands/imm_punish.py:41/48` already matched ROM.
- **Fix**: corrected both production strings to "priviliges". Inverted 7
  contra-ROM assertions in `tests/test_communication.py` (a test asserting
  contra-ROM behavior is a bug in the test, per AGENTS.md).
- **Tests**: `tests/test_communication.py::test_gossip003_nochannels_message_matches_rom_misspelling` (1, green; exercises both the shared-helper path via `gossip` and `do_clantalk`'s inline path with a clan-member speaker); full `test_communication.py` 21/21.

### `do_pmote` — ✅ VERIFIED CLEAN (no change)

- **Python**: `mud/commands/imm_emote.py:do_pmote` + `_pmote_substitute`
- **ROM C**: `src/act_comm.c:1098-1192`
- NOEMOTE gate (NPC-exempt), empty→"Emote what?", the `',{'` "Moron!" guard,
  self-line `$n $t`, per-viewer `$N $t` routed through `pers(char, viewer)`, the
  `desc==NULL`/self skip, and the letter-by-letter name→"you"/"r" substitution
  loop (mirroring lines 1131-1175) all match ROM. 7 existing pmote tests pass.

### `do_reply` — ✅ VERIFIED CLEAN (no change)

- **Python**: `mud/commands/communication.py:do_reply` (:298)
- **ROM C**: `src/act_comm.c:954+`
- Gates only on `COMM_NOTELL` (no NOCHANNELS), then routes through `do_tell` —
  matches ROM. (Benefits from the TELL-009 fix transitively.)

## Files Modified

- `mud/commands/communication.py` — removed TELL-009 NOCHANNELS gate; GOSSIP-003 spelling fix at `_check_channel_blockers` + `do_clantalk`
- `tests/integration/test_tell_parity.py` — added `test_tell_009_...`
- `tests/test_communication.py` — added `test_gossip003_...`; inverted 7 contra-ROM "privileges" assertions
- `docs/parity/ACT_COMM_C_AUDIT.md` — added TELL-009 + GOSSIP-003 rows; corrected two stale "acceptable" notes; updated do_tell snippet + parity-check bullets
- `CHANGELOG.md` — added 2.14.96 (TELL-009) and 2.14.97 (GOSSIP-003) sections
- `pyproject.toml` — 2.14.95 → 2.14.96 → 2.14.97

## Test Status

- `tests/test_communication.py` — 21/21
- `tests/integration/test_tell_parity.py` — 7/7
- Communication regression set (`test_communication` + tell/shout-yell parity + act_comm_gaps + inv001 delivery) — 66/66
- `-k pmote` — 7/7
- `ruff check` (changed files) — clean

## Next Steps

The act_comm.c broadcast-verb surface is fully swept (do_say/do_yell/do_shout,
the talk_channel family, do_tell/do_reply, do_pmote, do_clantalk/do_immtalk all
reconciled). The per-file audit tracker has no ⚠️ Partial / ❌ Not Audited rows,
so the active pass is **cross-file invariants / divergence-class sweep**. Next
move: pick a fresh divergence class from `docs/parity/DIVERGENCE_CLASS_ROSTER.md`
(`/rom-divergence-sweep`) or the next cross-file INV candidate (affect ticks,
position transitions, mob script triggers, group/follower chain). The
"category-error" pattern (channel-family gate wrongly borrowed onto a
hand-written verb) was the recurring shape in act_comm.c — worth a targeted
probe in any other command file that mixes generic helpers with per-command
gates (act_move.c, act_obj.c entry gates).
