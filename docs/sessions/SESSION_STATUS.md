# Session Status — 2026-06-14 — act_comm.c broadcast-verb sweep COMPLETE (TELL-009 + GOSSIP-003)

## Current State

- **Active focus**: Cross-file / broadcast-surface parity pass (per-file audit
  tracker exhausted). The `act_comm.c` broadcast-verb inventory is now **fully
  swept** under the act()/sender-gate lens — every verb reconciled with ROM.
- **Last completed**:
  - **TELL-009** — removed a spurious `COMM_NOCHANNELS` sender gate from
    `do_tell` (`mud/commands/communication.py:do_tell`). ROM `do_tell`
    (`src/act_comm.c:850-866`) gates the sender only on `NOTELL||DEAF` then
    `QUIET`; NOCHANNELS revokes the *public* talk_channel family, not the
    private `tell`. A god-silenced player can still tell in ROM. Same
    category error as SHOUT-005. (v2.14.96)
  - **GOSSIP-003** — the NOCHANNELS channel-revocation line now uses ROM's
    **misspelled** "priviliges" (not corrected "privileges") at both Python
    sites: the shared `_check_channel_blockers` gate (gossip/grats/quote/
    question/answer/music/auction) and `do_clantalk`'s inline gate. ROM emits
    "priviliges" verbatim at all 8 talk_channel sites + the imm revoke/restore
    (`src/act_wiz.c:342/351`); `imm_punish.py` already matched. 7 contra-ROM
    test assertions inverted. (v2.14.97)
  - **do_pmote** and **do_reply** verified parity-clean (no code change).
  - Both gaps were stale-audit-note catches (the "acceptable addition /
    enhancement" notes asserted the divergent behavior was ROM-correct);
    re-verified false against ROM source per the AGENTS.md re-verify mandate.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-14_ACT_COMM_TELL009_GOSSIP003.md](SESSION_SUMMARY_2026-06-14_ACT_COMM_TELL009_GOSSIP003.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.97 |
| Tests | 5785 passed / 4 skipped |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | act_comm.c broadcast surface fully swept; cross-file / divergence-class pass next |

## Next Intended Task

The act_comm.c broadcast-verb sweep is **done** — do_say/do_yell/do_shout,
the talk_channel family, do_tell/do_reply, do_pmote, do_clantalk/do_immtalk are
all reconciled with ROM. The per-file audit tracker has no ⚠️ Partial /
❌ Not Audited rows, so the active pass is **cross-file invariants /
divergence-class sweep**. Pick a fresh divergence class from
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` (`/rom-divergence-sweep`) or the next
cross-file INV candidate (affect ticks, position transitions, mob script
triggers, group/follower chain).

**Targeted lead worth a probe**: the recurring shape in act_comm.c was the
"category error" — a channel-family precondition (QUIET/NOCHANNELS) wrongly
borrowed onto a hand-written verb (SHOUT-005, TELL-009). Any command file that
mixes a generic gate helper with per-command gates (act_move.c, act_obj.c entry
gates) is a candidate for the same class of bug.
