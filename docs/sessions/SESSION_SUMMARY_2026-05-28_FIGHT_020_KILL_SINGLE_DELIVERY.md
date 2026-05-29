# Session Summary — 2026-05-28 — FIGHT-020 `kill` single-delivery (FINDING-008 sub-issue 3, re-triaged)

## Scope

Picked up from `SESSION_SUMMARY_2026-05-28_FIGHT_019_THAC0_HIT_MODEL.md`. That
session closed FINDING-008 sub-issue 1 (the THAC0 hit model) and recorded
sub-issue 3 (combat line emitted twice at step 4 `kill drunk`) as a **"harness
capture artifact, NOT a SINGLE-DELIVERY violation."** This session re-triaged
sub-issue 3 from the engine code + ROM C, found that conclusion **wrong**, and
closed the real bug (FIGHT-020) on `master`.

## Outcomes

### `FIGHT-020` — ✅ FIXED (master, 2.11.5, commit `d1e60112`)

- **Python**: `mud/commands/combat.py::do_kill`
- **ROM C**: `src/fight.c:2771-2817` (`do_kill` → `multi_hit`, void — no return channel); `src/fight.c:859-862` (death branch sends the killer nothing)
- **Gap**: `do_kill` returned `multi_hit(...)[0]` — the attacker's TO_CHAR combat
  line that `apply_damage` had **already** delivered via `_push_message`. The
  connection read loop (`mud/net/connection.py:1980-2000`) sends a command's
  return value **and** drains the push, so a connected PC received every
  `kill`-initiated combat line **twice** (async `_push_message` send +
  `send_to_char(char, response)`). A real SINGLE-DELIVERY (INV-001) violation —
  the same class as the previously-fixed WS death-path double-message bug.
- **Fix**: `do_kill` now runs `multi_hit(char, victim)` and `return ""`, like
  ROM's void `do_kill` and like every combat-tick caller. Combat output flows
  solely through `_push_message`. The non-ROM `"You kill X."` line (returned by
  `_handle_death`, surfaced only on the `kill` first strike) is no longer
  delivered — ROM sends the killer nothing on death; the killing-blow dam_message
  (pushed before the death branch) is the killer's last line.
- **Empirical proof (the discriminator that the prior static-only triage lacked)**:
  a mock-connection PC driven through the real connection-loop delivery receives
  `['{2You miss drunk.{x', '{2You miss drunk.{x']` before the fix, **one** line
  after. Death case: killing dam_message once, no `"You kill"` line.
- **Tests**: `tests/integration/test_kill_command_single_delivery.py` (2 new —
  non-fatal + fatal). 11 combat-content-return assertions across
  `tests/test_combat.py`, `tests/test_combat_thac0_engine.py`,
  `tests/test_combat_defenses_prob.py` re-baselined to read the pushed line from
  `char.messages` (via a `deliver_kill` helper); `test_fight_c_do_kill_parity`
  asserts `do_kill` returns `""` and pins the multi_hit sequence.

### Re-triage correction (honesty thread)

The FIGHT-019 session's "sub-issue 3 = harness capture artifact" was wrong. The
prior triage checked only that `multi_hit` returns one line, without tracing the
**connected-PC** path where `_push_message` delivers (async) **on top of** the
returned value the connection loop sends. Confirmed empirically here. The
master-side records (`FIGHT_C_AUDIT.md`, this summary, `SESSION_STATUS.md`,
CHANGELOG) are reconciled. **`tools/diff_harness/FINDINGS.md` (on `diff-harness`)
still says "harness capture artifact" and MUST be corrected during the
diff-harness phase — it is unreachable from `master`.**

## Files Modified

- `mud/commands/combat.py` — `do_kill` returns `""` (delivers via `_push_message`).
- `tests/integration/test_kill_command_single_delivery.py` — new (2 tests).
- `tests/test_combat.py`, `tests/test_combat_thac0_engine.py`, `tests/test_combat_defenses_prob.py` — 11 assertions re-baselined via `deliver_kill`.
- `tests/integration/test_fight_c_do_kill_parity.py` — asserts `do_kill` returns `""`.
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-020 row + reclassified FIGHT-019 tail.
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — broadened INV-001 + filed two follow-ups.
- `CHANGELOG.md` — 2.11.5 entries; `pyproject.toml` — 2.11.4 → 2.11.5.

## Test Status

- `tests/integration/test_kill_command_single_delivery.py` — 2/2 passing.
- Full suite (parallel, `-n auto`): **4930 passed, 4 skipped, 0 failed** (108s).
- `gitnexus_detect_changes`: 31 symbols / 6 files, **LOW** risk, 0 affected
  processes (caveat: `combat.py` caller `dispatcher.py` is in the documented 32KB
  gitnexus gap — verified instead via the full suite + the empirical tests).
- `ruff check`: touched files clean; one **pre-existing** F541 in `do_flee`
  (`combat.py:695`, not this work) remains in the CI-tolerated lint debt.

## Outstanding

- **`master` is 1 commit ahead of `origin/master` (UNPUSHED)** at 2.11.5
  (`d1e60112`). Not pushed — awaiting explicit go-ahead.
- **INV-001 follow-ups filed (not fixed), same SINGLE-DELIVERY contract:**
  - **(a) `broadcast_room`/`broadcast_global`** (`mud/net/protocol.py`) append to
    BOTH the async `send_to_char` task and `char.messages` → every room broadcast
    (death/position-change/says routed through it) reaches a connected PC twice.
    Surfaced by the FIGHT-020 death-path test (`{RVictim is DEAD!!{x` ×2,
    `hits the ground … DEAD.` ×2). Needs its own failing-test-first fix (mirror
    `push_message`'s connection-XOR-mailbox).
  - **(b) `do_surrender`** (`mud/commands/combat.py`, NPC-ignores-surrender
    branch) returns `multi_hit(opponent, char)` output → the surrendering PC gets
    the TO_VICT push **and** a returned attacker-perspective (`"You hit …"`)
    line: the same return-value double-send as `do_kill`, plus a wrong-perspective
    leak. Discard the return like `do_kill`.
- **`FINDINGS.md` correction (REQUIRED, diff-harness phase):** flip sub-issue 3
  from "harness capture artifact" to "real engine bug, FIGHT-020."
- **FINDING-008 sub-issue 2 (color normalization)** — still genuine harness work
  on `diff-harness`: strip ROM `{`-color codes in `compare._normalize_output`
  (reuse `mud.net.ansi.strip_ansi`). `_normalize_output` currently strips ANSI
  escapes (`\x1b[…m`) but not raw ROM `{2…{x` tokens.

## Next Steps

1. **Merge `master` → `diff-harness`** to bring FIGHT-019 (sub-issue 1) **and**
   FIGHT-020 (sub-issue 3) onto the harness branch.
2. **Fix sub-issue 2** (color-norm) on `diff-harness` and **correct `FINDINGS.md`**.
3. **Re-run the `combat_melee_rounds` differential.** The drunk has 31 HP and does
   **not** die at step 4, so the `broadcast_room` death-path duplicate will not
   touch this scenario. Expect step 4 to clear but the first divergence may
   **advance to step 5** rather than the differential going fully clean — re-run,
   do not declare. Once green, merge `diff-harness` → `master`.
4. **Close INV-001 follow-ups (a) broadcast_room and (b) do_surrender** as separate
   gap-closer commits (each: failing test → fix → re-baseline).

## Continuation — INV-001 follow-up (a) broadcast_room — ✅ FIXED (master, 2.11.6, commit `6a4034f0`)

Closed the higher-impact follow-up in the same session.

- **Python**: `mud/net/protocol.py::broadcast_room`, `broadcast_global`
- **ROM C**: `src/comm.c:write_to_buffer` (one delivery channel per message)
- **Gap**: both functions appended each message to BOTH the fire-and-forget
  `asyncio.create_task(send_to_char(...))` send AND `char.messages`. For a
  connected PC the async send delivers immediately and the connection read loop
  drains `char.messages` after the next command → every room/global broadcast
  (deaths, position changes, arrivals, channels routed through these helpers)
  replayed once more on the next prompt. SINGLE-DELIVERY violation, same class
  as FIGHT-020 and the WS death-path bug.
- **Fix**: connection-XOR-mailbox per recipient (async send for connected PCs,
  `char.messages` fallback for disconnected chars / tests), mirroring
  `push_message`. The ~195 call sites are unchanged; connection-less recipients
  (the vast majority in tests) still queue to the mailbox.
- **Tests**: `tests/integration/test_broadcast_room_single_delivery.py` (3 —
  room + global single delivery to a connected PC; mailbox fallback preserved).
  Full suite: **4933 passed, 4 skipped, 0 failed**.
- **Still open**: INV-001 follow-up (b) `do_surrender` (NPC-ignores branch
  returns `multi_hit` output — return-value double-send + wrong-perspective
  leak).

## Continuation — INV-001 follow-up (b) do_surrender — ✅ FIXED (master, 2.11.7, commit `4d829d49`)

Closed the last open INV-001 instance — INV-001 SINGLE-DELIVERY is now fully
enforced (`do_kill` + `broadcast_room`/`broadcast_global` + `do_surrender`).

- **Python**: `mud/commands/combat.py::do_surrender`
- **ROM C**: `src/fight.c:3239-3240` (`multi_hit(mob, ch, TYPE_UNDEFINED)` — void)
- **Gap**: the NPC-ignores-surrender branch did
  `attack_messages = multi_hit(opponent, char); messages.extend(attack_messages)`
  and returned them, so the surrendering PC received the NPC counterattack twice:
  the correct TO_VICT push (`{4the brute hits you{x`) AND the returned
  attacker-perspective line (`{2You hit …{x`) — return-value double-send +
  wrong-perspective leak.
- **Fix**: discard `multi_hit`'s return like `do_kill`; output reaches the PC via
  the TO_VICT push and the room via TO_NOTVICT.
- **Tests**: `tests/integration/test_surrender_single_delivery.py` (connected PC
  surrenders → receives the `{4` TO_VICT line once, no `{2` attacker-perspective
  leak). Targeted serial verification (surrender + kill + broadcast + thac0 +
  defense suites): 14/14 green.

### Combat-test brittleness surfaced (now the top remaining task)

A clean parallel full-suite run flaked `test_one_hit_uses_equipped_weapon` — one
of ~8 unseeded hit-dependent tests in `tests/test_combat.py` that resolve the
FIGHT-019 THAC0 roll without pinning `number_bits`, so they pass/fail on RNG
stream position (xdist worker grouping). Pinned that one (`number_bits = 19`);
the other 7 remain and should be hardened next (see SESSION_STATUS task 5). This
is RNG-neutral to the do_surrender change (verified: the flaky test does not
involve surrender and passes in isolation).

## Continuation — combat-test brittleness hardening — ✅ DONE (master, 2.11.8, commit `cdb1946f`)

Closed the brittleness pass surfaced above.

- **Gap**: after FIGHT-019 made THAC0 the only hit model, the unseeded
  outcome-asserting tests in `tests/test_combat.py` resolved hits via the
  unseeded `number_bits(5)` stream — passing only by RNG-stream position and
  flaking on the nat-0/nat-19 edge under different xdist worker groupings.
- **Fix**: pinned `number_bits` per test — `lambda *_: 19` (nat-19, always hits)
  for hit/damage/kill assertions, `lambda *_: 0` (nat-0, always misses) for
  `test_attack_misses_target`. 8 tests hardened (plus the 2 already pinned).
  Tests whose only assertion is `assert_attack_message` (true for both hit and
  miss) or that count attacks rather than hits were left unpinned — not
  outcome-brittle. No production behavior change.
- **Verification**: `test_combat.py` 32/32 across 3 serial runs; full parallel
  suite **4934 passed, 4 skipped, 0 failed**.

## Session net result

INV-001 SINGLE-DELIVERY fully enforced (FIGHT-020 `do_kill` + `broadcast_room`/
`broadcast_global` + `do_surrender`) and the combat-test suite is now
deterministic. Master is **7 commits ahead of `origin` at 2.11.8, unpushed**.
Remaining: push (with go-ahead), then the harness thread (merge master→
`diff-harness`, sub-issue 2 color-norm, correct `FINDINGS.md`, re-run the
`combat_melee_rounds` differential).
