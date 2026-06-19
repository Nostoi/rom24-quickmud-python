# Session Summary — 2026-06-19 — /loop gap-closer COMPLETE (5/5): + SCORE-001, HANDLER-007

## Scope

Continuation of the `/loop` gap-closer session (target: 5 gaps). The first half
(WEAR-012, LOOK-008, LOOK-009) is documented in
`SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_WEAR012_LOOK008_LOOK009.md`, where the
loop was paused at 3/5 (genuine divergences on the look/examine/wear surfaces
were closing out). The user **relaunched** `/loop`, so the hunt resumed on fresh,
unexamined command surfaces — and a single `score` probe against the live ROM C
oracle surfaced BOTH remaining gaps (4 and 5), completing the loop at **5/5**.

## Outcomes (gaps 4–5; gaps 1–3 in the prior summary)

### `SCORE-001` — ✅ FIXED (gap 4)

- **ROM C**: `src/act_info.c:1477-1690` (`do_score`)
- **Python**: `mud/commands/session.py` (`do_score`)
- **Gap**: `do_score` emitted lines in the wrong order vs ROM — carrying / Wimpy /
  conditions / position / alignment were grouped at the END — and gated the Wimpy
  line on `wimpy > 0`, so a char with `wimpy == 0` dropped "Wimpy set to 0 hit
  points." entirely (ROM line 1548 prints it unconditionally).
- **Fix**: reordered to ROM's exact emission order (… practices → carrying → Str
  → exp → need-exp → Wimpy → conditions → position → AC/defenseless → immortal →
  hitroll → alignment-last) and made the Wimpy line unconditional. The per-line
  content audit had marked do_score "100% complete"; the harness caught the
  ordering it missed.
- **Tests**: `test_score_rom_line_order_and_wimpy_always_shown`
  (`tests/test_player_info_commands.py`). Commit `14e7211a`, v2.14.142.

### `HANDLER-007` — ✅ FIXED (gap 5)

- **ROM C**: `src/handler.c:907` (`can_carry_n`)
- **Python**: `mud/world/movement.py` (`can_carry_n`)
- **Gap**: `can_carry_n` read `perm_stat` index **1 (STAT_INT)** instead of index
  **3 (STAT_DEX)** under a mislabeled `# STAT_DEX` comment, so the carry-item cap
  was `MAX_WEAR + 2*INT + level` instead of ROM's `MAX_WEAR + 2*DEX + level`. Wrong
  for any char whose INT ≠ DEX (most PCs); visible on `score` and on get/pickup
  item-count limits.
- **Fix**: `_get_curr_stat(ch, int(Stat.DEX))` (per the flag-enum rule). Also
  corrected `test_stat_based_carry_caps_monotonic`, which had encoded the same
  "index 1 = DEX" error.
- **Tests**: `test_can_carry_n_uses_dex_not_int` (`tests/test_encumbrance.py`).
  Commit `bd88bb38`, v2.14.143.
- **Discovery note**: both gaps 4 and 5 fell out of ONE `score` line-by-line probe
  vs the C oracle. The carry-max diff (0/56 vs 0/50) was the HANDLER-007 tell; the
  rest was the SCORE-001 ordering. Two stale audit ✅s were corrected in the same
  pass (do_score "100% complete", can_carry_n "2*DEX VERIFIED Jan 3").

## Verification discipline correction (carried from gap 3)

The gap-2 full-suite check had used `pytest -q | tail`, whose pipeline exit code
is `tail`'s, not pytest's — masking a real failure. From gap 3 onward every
full-suite run captured pytest's exit directly (`pytest > f 2>&1; echo $?`).
Gaps 4 and 5 each verified green this way: **5854 passed, 4 skipped,
PYTEST_EXIT=0**.

## Files Modified (gaps 4–5)

- `mud/commands/session.py` — `do_score` reordered + unconditional Wimpy (SCORE-001)
- `mud/world/movement.py` — `can_carry_n` STAT_DEX (HANDLER-007)
- `tests/test_player_info_commands.py` — score order test
- `tests/test_encumbrance.py` — can_carry_n DEX test + corrected monotonic test
- `docs/parity/ACT_INFO_C_AUDIT.md` — SCORE-001 row (+ stale-✅ caveat on do_score)
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-007 entry (+ corrected can_carry_n row)
- `CHANGELOG.md`, `pyproject.toml` — 2.14.141 → 2.14.143

## Test Status

- Full suite (exit captured directly): **5854 passed, 4 skipped, PYTEST_EXIT=0**.
- ruff clean. `gitnexus detect_changes` LOW risk, 0 affected processes per commit.

## Loop summary (5/5 complete)

| # | Gap | ROM C | Commit | Version |
|---|-----|-------|--------|---------|
| 1 | WEAR-012 — `wear all` equips lights/weapons/hold | act_obj.c | 25e1829c | 2.14.139 |
| 2 | LOOK-008 — look/examine extra-descr keyword-gated | act_info.c | f748a821 | 2.14.140 |
| 3 | LOOK-009 — look-at-char objective pronoun | act_info.c | 10327a59 | 2.14.141 |
| 4 | SCORE-001 — do_score line order + Wimpy | act_info.c | 14e7211a | 2.14.142 |
| 5 | HANDLER-007 — can_carry_n uses DEX | handler.c | bd88bb38 | 2.14.143 |

All 5 found by the differential harness (`tools/diff_harness/`) vs the live ROM C
oracle; all C-oracle verified; FINDING-034/035/036 RESOLVED. **Not pushed.**

## Next Steps

Loop target met (5/5). The differential harness remains the productive
enumeration-independent finder — every gap this loop came from a probe, not the
per-file audit (which had two stale ✅s). To continue, probe more fresh surfaces
(combat/death output [RNG — bracket with `__seed`], group/follow messaging,
`give`/`put`-to-mob, weather/time, OLC) with throwaway C-oracle-vs-pyreplay
probes; close real divergences via `/rom-gap-closer`. **8 commits v2.14.139-143 on
master since the prior handoff, NOT pushed** — `git push` if sharing
(versions/CHANGELOG current). Guardrail 3: a clean sweep means "this known surface
is locked," never "close to ROM parity."
