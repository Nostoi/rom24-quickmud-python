# Session Status — 2026-06-14 — SHOUT-005 (do_shout sender-gate parity); act_comm.c core broadcast verbs swept clean

## Current State

- **Active focus**: Cross-file / broadcast-surface parity pass (per-file audit
  tracker exhausted — only deferred track-only DB2 rows remain). Sweeping the
  `act_comm.c` broadcast-verb inventory under the act()/sender-gate lens.
- **Last completed**: **SHOUT-005** — `do_shout` (`mud/commands/communication.py:319-326`)
  sender-gate sequence now matches ROM. ROM `do_shout` (`src/act_comm.c:814-820`)
  gates the sender **only** on `COMM_NOSHOUT`, then unconditionally
  `REMOVE_BIT(ch->comm, COMM_SHOUTSOFF)` and proceeds. Python had borrowed three
  blocking gates that belong to the `talk_channel` family (gossip/grats,
  `act_comm.c:297-303`), not to shout: a `NOCHANNELS` player was blocked ("The gods
  have revoked your channel privileges."), a `QUIET` player was blocked ("You must
  turn off quiet mode first."), and a `SHOUTSOFF` player was blocked ("You must turn
  shouts back on first.") instead of having their own shouts-off silently
  auto-cleared and the shout delivered. Removed the two spurious gates and inverted
  the SHOUTSOFF branch to `_clear_comm_flag` (ROM `REMOVE_BIT`). `banned_channels`
  (a QuickMUD extension) untouched. Test:
  `tests/integration/test_shout_yell_parity.py::test_shout_005_sender_gate_matches_rom`
  (3 facets); 2 legacy assertions in `tests/test_communication.py` corrected.
  Found by the act_comm.c broadcast-inventory sweep that SESSION_STATUS named as the
  next task — **`do_say` and `do_yell` verified clean** in the same pass (no gap).
  (v2.14.95).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_SHOUT_005_SENDER_GATE.md](SESSION_SUMMARY_2026-06-14_SHOUT_005_SENDER_GATE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.95 |
| Tests | 5783 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | act_comm.c broadcast inventory (core verbs clean; channel family next) |

## Next Intended Task

Continue the **act_comm.c broadcast-verb sweep**. The three core verbs
(`do_say`/`do_yell`/`do_shout`) are now verified clean. Remaining sites:

1. **`talk_channel` family** — `do_gossip`/`do_grats`/`do_quote`/`do_question`/
   `do_answer`. Confirm each gates the **sender** on `COMM_QUIET` + `COMM_NOCHANNELS`
   per ROM `act_comm.c:297-303` (the gates `do_shout` correctly lacks), and renders
   `$n` per-listener PERS. GOSSIP-001/002 prior — verify the siblings.
2. **`do_pmote`** — verify against ROM (EMOTE-005 closed `do_emote`).
3. **`do_tell`/`do_reply`** — TELL-series prior; spot-check the gate sequence.

Method per verb: read the ROM C gate sequence → diff the Python early-returns →
one failing test if they diverge (one gap = one test = one commit via
`/rom-gap-closer`). If all clean, the act_comm.c broadcast surface is fully swept;
next move is a fresh divergence class from
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` (`/rom-divergence-sweep`) or the next
cross-file INV candidate.
