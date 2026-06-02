# Session Status — 2026-06-02 — MOB-TRIGGER ORDERING PROBE + GIVE-001 CLOSED (2.12.68)

## Current State

- **Active mode**: cross-file invariants (sole active pass — no per-file audit
  gaps remain). This day ran two probes: group/follower chain (→ ACT_COMM-003)
  and mob-trigger ordering (→ GIVE-001).
- **This session — two parity commits (local on `master`, NOT yet pushed):**
  - **2.12.68 — GIVE-001 (do_give recipient wrong-channel)**: ROM `do_give`
    emits the recipient TO_VICT line (`"$n gives you $p."` object branch,
    `src/act_obj.c:834`; `"$n gives you N coins."` coins branch, `~726`) via
    `act()` — immediate descriptor write. Python delivered both via raw
    `victim.messages.append(...)`, the mailbox a **connected** PC only drains on
    its next prompt → late gift line. Both legs now route through `push_message`;
    the giver's TO_CHAR leg was already correct (returned). `push_message` does
    not dispatch TRIG_ACT so the object branch's `disable_mobtrigger()` contract
    is unaffected. INV-001 / MAGIC-003 wrong-channel family. `gitnexus_impact`
    LOW. Surfaced while probing **mob-trigger ordering** — which verified faithful
    for the 3 highest-value contracts (entry/greet IS_NPC gating + post-follower
    order; TRIG_DEATH fires from `damage()` before `raw_kill`, NPC-gated, and
    `do_slay`→`raw_kill` correctly skips it; TRIG_GIVE obj-in-inventory-before-prog).
    New `tests/integration/test_give001_victim_delivery_channel.py` (2 tests).
  - **2.12.67 — ACT_COMM-003 (stop_follower wrong-channel)**: `stop_follower`'s
    TO_VICT/TO_CHAR lines moved off raw `char.messages.append` onto
    `push_message`, matching the already-migrated `add_follower`. See
    [SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md](SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md).

- **Open gaps**: **none** (per-file). All per-file audit rows ✅; cross-file
  invariants is the active probe-then-scope pass.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_MOB_TRIGGER_PROBE_GIVE001.md](SESSION_SUMMARY_2026-06-02_MOB_TRIGGER_PROBE_GIVE001.md)
  (prior this day: [ACT_COMM003_STOP_FOLLOWER_CHANNEL](SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md),
  [INV033_FURNITURE_ON_POINTER](SESSION_SUMMARY_2026-06-02_INV033_FURNITURE_ON_POINTER.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.68 |
| Tests | **full suite green: 5336 passed, 4 skipped** (`pytest`, ~133s parallel); GIVE-001 (`do_give`, LOW) caused zero fallout |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | **26 enforced** (ACT_COMM-003 + GIVE-001 both filed under INV-001's wrong-channel trail — no new rows; tracker past the ~20 soft cap, consolidation due) |
| Open gaps | **none** — ACT_COMM-003 (2.12.67) + GIVE-001 (2.12.68) CLOSED this day |

## Next Intended Task

Cross-file invariants is the sole active pass. **Tracker is at 26 INV rows —
past the ~20 soft cap AGENTS.md flags; a future session should weigh
consolidation (INV-014/INV-015 precedent) before adding new rows.** Mob-trigger
ordering verified faithful for entry/greet/death/give; the remaining unprobed
contracts are **bribe / exit / fight / kill / hpcnt** ordering. Other uncovered
areas: a wider INV-001 wrong-channel grep sweep (every command-layer
`victim.messages.append` / cross-character TO_VICT line is a candidate — two
turned up this day).

Method: probe-then-scope (read ROM C contract → read Python equivalent → one
failing test → close as a gap or file as next free INV-034).

> **Push note:** 2.12.67 (`a181a894`) and 2.12.68 (`a6fb9c03`) + handoff-docs
> commits are on local `master` but **NOT yet pushed** to `origin/master`
> (which sits at `64f0dc1d` / 2.12.66). Push when ready; CHANGELOG/version
> reflect 2.12.68.
