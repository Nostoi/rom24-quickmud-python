# Session Status — 2026-06-02 — ACT_COMM-003 STOP_FOLLOWER DELIVERY CHANNEL CLOSED (2.12.67)

## Current State

- **Active mode**: cross-file invariants (sole active pass — no per-file audit
  gaps remain). This session probed the recommended **group/follower-chain**
  candidate and closed one wrong-channel divergence.
- **This session — one commit (local on `master`, NOT yet pushed):**
  - **2.12.67 — ACT_COMM-003 (stop_follower wrong-channel)**: ROM
    `stop_follower` (`src/act_comm.c:1626-1627`) emits both the TO_VICT
    `"$n stops following you."` and TO_CHAR `"You stop following $N."` lines via
    `act()` — immediate, single-channel delivery to the descriptor. Python used
    raw `char.messages.append(...)` for both, the mailbox fallback a **connected**
    PC only drains on its next prompt; the sibling primitive `add_follower` was
    already on `push_message`, so `stop_follower` was the leftover asymmetric
    cousin (INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family). Observable
    off the command path — `die_follower` iterating the registry on a leader's
    extract/death, or charm wearing off mid-tick. Both lines now route through
    `push_message`, matching `add_follower`; the `can_see`/`in_room` gate
    (FOLLOW-002) and unconditional detach state are unchanged. `gitnexus_impact`
    rated `stop_follower` CRITICAL (27 impacted, 5 direct callers), but
    `push_message` is byte-identical to the old append for any char without a
    `.connection`, so disconnected chars and all existing tests are unaffected —
    only connected PCs change. Full suite **5334 passed, 4 skipped** — zero
    fallout. New `tests/integration/test_act_comm003_stop_follower_delivery_channel.py`
    (1 connected-PC test; the existing disconnected-char follow tests false-green
    against unfixed code).

- **Open gaps**: **none** (per-file). All per-file audit rows ✅; cross-file
  invariants is the active probe-then-scope pass.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md](SESSION_SUMMARY_2026-06-02_ACT_COMM003_STOP_FOLLOWER_CHANNEL.md)
  (prior: [INV033_FURNITURE_ON_POINTER](SESSION_SUMMARY_2026-06-02_INV033_FURNITURE_ON_POINTER.md)).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.67 |
| Tests | **full suite green: 5334 passed, 4 skipped** (`pytest`, ~125s parallel); ACT_COMM-003 (`stop_follower`, CRITICAL blast radius) caused zero fallout |
| ROM C files audited | 43 / 43 (per-file pass complete; cross-file invariants active) |
| Cross-file invariants | **26 enforced** (ACT_COMM-003 filed under INV-001's wrong-channel family — no new INV row; tracker past the ~20 soft cap, consolidation due) |
| Open gaps | **none** — ACT_COMM-003 CLOSED this session (2.12.67) |

## Next Intended Task

Cross-file invariants is the sole active pass. Tracker is at 26 INV rows — past
the ~20 soft cap AGENTS.md flags; a future session should weigh **consolidation**
(INV-014/INV-015 precedent) before adding more rows. The group/follower chain is
now well-covered (INV-020 membership/extract, INV-031 PC-death-preserves-group,
ACT_COMM-003 channel symmetry between `add_follower`/`stop_follower`). Remaining
uncovered cross-file candidate:

1. **Mob trigger ordering** — TRIG_* dispatch sequence vs ROM.

Method: probe-then-scope (read ROM C contract → read Python equivalent → one
failing test → close as a gap or file as next free INV-034).

> **Push note:** 2.12.67 (`a181a894`) is committed locally on `master` but
> **NOT yet pushed** to `origin/master` (which sits at `64f0dc1d` / 2.12.66).
> Push when ready; CHANGELOG/version reflect 2.12.67.
