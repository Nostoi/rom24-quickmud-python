# Session Status — 2026-05-28 — INV-001 SINGLE-DELIVERY fully closed (FIGHT-020 `kill` + broadcast_room + do_surrender; FINDING-008 #3 re-triaged)

## Current State

- **Active mode**: differential-harness-driven parity verification. This session
  re-triaged FINDING-008 sub-issue 3 (combat line emitted twice at `kill drunk`),
  which the prior session had recorded as a "harness capture artifact." It is a
  **real engine bug** — closed as FIGHT-020 on `master`.
- **Last completed**:
  - **`FIGHT-020`** ✅ FIXED (master 2.11.5, `d1e60112`) — `do_kill` returned
    `multi_hit(...)[0]`, the attacker combat line `apply_damage` had already
    pushed via `_push_message`; the connection loop sends the return value AND
    drains the push, so connected PCs received every `kill`-initiated combat line
    **twice** (SINGLE-DELIVERY / INV-001 violation). `do_kill` now returns `""`
    (ROM's void `do_kill`); combat output flows solely through `_push_message`.
    Also retired a non-ROM `"You kill X."` line. Proven end-to-end with a
    mock-connection delivery harness; 11 combat tests re-baselined.
  - **INV-001 follow-up (a) `broadcast_room`/`broadcast_global`** ✅ FIXED
    (master 2.11.6, `6a4034f0`) — both appended to BOTH the async `send_to_char`
    task AND `char.messages`, double-delivering every room/global broadcast
    (deaths, position changes, arrivals, channels) to connected PCs. Now
    connection-XOR-mailbox like `push_message`. Regression:
    `tests/integration/test_broadcast_room_single_delivery.py`.
  - **INV-001 follow-up (b) `do_surrender`** ✅ FIXED (master 2.11.7,
    `4d829d49`) — the NPC-ignores-surrender branch returned `multi_hit`'s output,
    so the surrendering PC got the NPC counterattack twice (TO_VICT push + the
    returned attacker-perspective line — double-send + wrong-perspective leak).
    Return now discarded like `do_kill`. **INV-001 is now fully enforced.**
    Regression: `tests/integration/test_surrender_single_delivery.py`. Also pinned
    `number_bits` in `test_one_hit_uses_equipped_weapon` (a parallel-suite flake).
  - **Re-triage correction**: the FIGHT-019 session's "harness capture artifact"
    triage of sub-issue 3 was **wrong** (it traced only `multi_hit`'s return, not
    the connected-PC push+return double-channel). Master-side docs reconciled;
    `FINDINGS.md` on `diff-harness` still needs the correction.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_FIGHT_020_KILL_SINGLE_DELIVERY.md](SESSION_SUMMARY_2026-05-28_FIGHT_020_KILL_SINGLE_DELIVERY.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md](SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | **2.11.7** (5 commits ahead of `origin/master` — `4d829d49`, **UNPUSHED**). `diff-harness` separate, unmerged. |
| Tests (master) | **4933 passed, 4 skipped** (clean parallel run, post-do_surrender). ⚠️ ~8 unseeded combat tests in `tests/test_combat.py` are RNG-stream-position fragile under xdist (one, `test_one_hit_uses_equipped_weapon`, pinned this session); a full hardening pass is the top remaining task — see below. |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `fight.c` row: FIGHT-019 (hit model) + FIGHT-020 (`do_kill` single-delivery) closed. |
| Differential harness | **Sound.** Surfaced FINDING-001→008. FINDING-008 sub-issue 1 (FIGHT-019) + sub-issue 3 (FIGHT-020) now resolved on `master`; sub-issue 2 (color norm) remains harness-side. `combat_melee_rounds` xfail stays red until `diff-harness` picks up master + sub-issue 2. v1 on `diff-harness`, unmerged. |
| INV-001 SINGLE-DELIVERY | ✅ **FULLY ENFORCED**: `do_kill` (FIGHT-020, 2.11.5) + `broadcast_room`/`broadcast_global` (2.11.6) + `do_surrender` (2.11.7). All three return-value/dual-channel double-sends closed; no open follow-ups. |

## Next Intended Task

1. **Merge `master` → `diff-harness`** — brings FIGHT-019 + FIGHT-020 onto the
   harness branch (resolves FINDING-008 sub-issues 1 + 3 there).
2. **On `diff-harness`: fix sub-issue 2** (color normalization — strip ROM `{`
   tokens in `compare._normalize_output`, reuse `mud.net.ansi.strip_ansi`) and
   **correct `tools/diff_harness/FINDINGS.md`** (sub-issue 3 → "real engine bug,
   FIGHT-020", not "capture artifact").
3. **Re-run `combat_melee_rounds`** — the drunk (31 HP) does not die at step 4, so
   the `broadcast_room` death duplicate won't affect it; expect step 4 to clear,
   but the first divergence may **advance to step 5**. Re-run, don't declare. Then
   merge `diff-harness` → `master`.
4. ✅ DONE — INV-001 follow-up (b) `do_surrender` closed (2.11.7).
   ((a) `broadcast_room` closed in 2.11.6.)
5. **Combat-test brittleness hardening (now the top remaining task — the parallel
   suite is no longer reliably green).** ~8 unseeded hit-dependent tests in
   `tests/test_combat.py` resolve the FIGHT-019 THAC0 roll without pinning
   `number_bits`, so they pass/fail on RNG-stream position (xdist worker
   grouping) — a clean parallel run flaked `test_one_hit_uses_equipped_weapon`
   this session (now pinned). Remaining: `test_attack_damages_but_not_kill`,
   `test_attack_kills_target`, `test_attack_misses_target`,
   `test_shield_block_requires_shield`, `test_multi_hit_single_attack`,
   `test_multi_hit_second_attack`, `test_visibility_and_position_modifiers`,
   `test_riv_scaling_applies_before_side_effects`. Pin `number_bits` per test —
   `lambda *_: 19` (nat-19, always hits) for hit-asserting tests; a miss-yielding
   value for the miss-asserting ones (e.g. `test_attack_misses_target`). See
   `FIGHT_C_AUDIT.md` Notes.
