# Session Status — 2026-06-20 — INV-052 + CAST-013 + INTERP-028 (table/contract sweep)

## Current State

- **Active focus**: Systematic ROM↔Python static-table diffs + cross-file
  invariants (the per-file audit tracker is drained).
- **Last completed** (3 gaps + 1 sweep this session):
  - **INV-052** (ACT-EMPTY-DISCARD) — ROM `act_new` discards NULL/empty messages
    before delivery + TRIG_ACT; Python delivered ROM-NULL social slots (`""`) as
    blank lines. Guard added at `act_to_room` + `socials._act_to_char`.
    `social_table` (244×8) verified byte-clean.
  - **CAST-013** — `do_cast` now gates on each spell's own `minimum_position`
    (const.c-derived) instead of a flat `POS_FIGHTING`; fighting chars can no
    longer cast `POS_STANDING` utility spells. (Closed the prior #2 candidate.)
  - **INTERP-028** — removed the `bs`/`backstab` dual registration; `bs` is now a
    single hidden row → `do_backstab`, matching ROM's two cmd_table rows. Dead
    `do_bs` wrapper deleted.
  - **INV-052 follow-up sweep** — 43 direct single-recipient push sites outside
    socials audited; clean negative (all pass constant non-empty templates, or
    already guard, or route through the now-guarded `act_to_room`).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md](SESSION_SUMMARY_2026-06-20_SOCIAL_TABLE_ACT_EMPTY_DISCARD.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.200 |
| Tests | 6002 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Systematic table-diff gap-closing / cross-file invariants |

## Clean negatives this session (verified parity, no gap)

- `social_table` (`area/social.are` ⇄ `data/socials.json`) — full 244×8 faithful
  join, zero content diffs (only NULL-vs-`""`, neutralized by INV-052).
- Direct single-recipient push/send sites outside socials (43) — INV-052 follow-up
  sweep, all non-empty by construction.

## Next Intended Task

**START HERE → expand the differential harness (`tools/diff_harness/`).** The
per-file audit is fully drained (P0/P1/P2 100%, P3 75% + 3 N/A; 0 Partial / 0 Not
Audited) and the cross-INV / per-file passes are now enumeration-*dependent* — they
only confirm contracts someone already named. Per `DIVERGENCE_CLASS_ROSTER.md`
guardrail #3, the ONLY enumeration-independent check (the one that finds divergences
nobody predicted) is differential execution against the ROM C oracle.

**Harness maturity (verified 2026-06-20):** there are **41 committed scenarios, all
41 converge** (`pytest tests/test_differential_smoke.py` → 41 passed;
`KNOWN_DIVERGENCES` empty). They already cover movement/get-drop, melee + spell
combat, **shops (buy/sell/insufficient-funds/keeper-broke)**, the **full mob-trigger
set** (act/bribe/death/delay/fight/give/hpcnt/kill/random/speech/surr/movement),
**char_update regen** (15 variants), affects (armor/expiry/charm/light), money,
aggression onset, drink/eat conditions. (The stale "4 scenarios" note in
`test_differential_smoke.py` predates this growth — ignore it.) So leverage is in
NEW scenarios on the surfaces still absent.

**Genuinely un-exercised surfaces (grep-verified — 0 scenarios touch these verbs):**
- **Doors**: `open`/`close`/`lock`/`unlock`/`pick` — entirely absent.
- **Containers**: `put` / get-from-container / nesting — absent (only floor get/drop + money covered).
- **Character advancement**: `practice`/`train`/`gain` — absent.
- **Death lifecycle**: `corpse` generation → auto-loot/auto-gold → `sacrifice` — absent (mob_death_trigger fires the trigger, not the corpse/loot mechanics).
- **Equipment cycle**: `wield`/`wear all`/`remove` — minimal (`wear all` already surfaced a FINDING; only `light_hold` + one `remove`).
- **Group/follow**: `follow`/`group` — absent.
- **Cast position gate**: a scenario casting a `POS_STANDING` spell while fighting (→ "You can't concentrate enough.") would lock this session's **CAST-013** fix differentially.

Concrete first steps for the next agent:

1. **Build the instrumented C shim (one-time):** `cd src && make -f
   Makefile.diffshim diffshim` (additive — ROM `src/*.c` stay byte-for-byte
   unchanged). Then `python3 -m tools.diff_harness.capture --all` regenerates
   goldens, `--check` diffs vs committed. Read `tools/diff_harness/README.md` first.
2. **Author 2–3 new scenarios** from the un-exercised list above
   (`tools/diff_harness/scenarios/<name>.json`: name/seed/start_room/char/watch/
   steps). Capture goldens, then `pytest tests/test_differential_smoke.py`.
3. **A divergence is a FINDING, not a golden to overwrite** — triage it, record in
   `tools/diff_harness/FINDINGS.md`, route to `/rom-gap-closer` (local) or a new
   INV-NNN (cross-file), fix Python/data, never edit the golden to pass.
4. **Also triage the existing open `FINDINGS.md` items** — a handful of LOW/cosmetic
   output-format divergences (`look`/`examine`/`wear all`) already surfaced but not
   closed.

Secondary / housekeeping (do NOT lead with these):
- **GitNexus MCP disconnected** late this session — reconnect it (or run `npx
  gitnexus analyze --skip-agents-md`) at session start so `gitnexus_impact` /
  `detect_changes` work. The CLI graph is current as of this session's push.
- **`test_all_commands.py` `tap` false-positive** — probe reports `tap` "Not
  registered" though it resolves to `sacrifice`; harness artifact, not a parity
  bug. Make the probe alias-aware if revisited.
- **Cross-file INV probe / signed-math (class 7)** — still valid but diminishing
  returns; fall back here only if the harness work stalls.
- **Risk posture**: HIGH-blast-radius behavioral logic changes → file, don't fix.
  Exception (proven 3× now — INV-052, CAST-013, INTERP-034): a change mirroring one
  ROM function/value exactly is strictly parity-correcting and safe.
