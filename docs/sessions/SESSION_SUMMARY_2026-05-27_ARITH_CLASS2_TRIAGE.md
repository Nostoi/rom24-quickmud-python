# Session Summary — 2026-05-27 — META Class 2 ARITHMETIC_BOUNDARY triage (2.9.64)

## Scope

Picked up immediately after the 2.9.63 handoff with Class 1 BROADCAST_COVERAGE
complete and SESSION_STATUS listing Class 2 ARITHMETIC_BOUNDARY as the most
attractive next META class ("likely smallest follow-up — survey THAC0, damage
caps, weight/carry rollover sites"). Goal this session was a pure triage pass:
enumerate every defensive floor/cap in `mud/`, classify each against ROM C,
and file stable gap IDs. No code changes intended — close-out is per-gap and
deferred to subsequent sessions via `/rom-gap-closer`.

## Outcomes

### META Class 2 ARITHMETIC_BOUNDARY — ✅ TRIAGED

- **New audit doc**: `docs/parity/audits/ARITHMETIC_BOUNDARY.md`
- **ROM reference**: `src/` (read-only) — `handler.c`, `fight.c`, `magic.c`,
  `update.c`, `act_obj.c`, `act_move.c`, `act_wiz.c`, `act_comm.c`, `db.c`,
  `skills.c`, `mob_cmds.c`.
- **Method**: `grep -rn -E "max\(1,|max\(0,|max\(-1,|min\([0-9]+,"` against
  `mud/**/*.py` excluding test_/web/net/account/json_io/imc — 215 hits.
  Split into 3 batches and dispatched parallel sonnet subagents. Each hit
  classified as ✅ MATCH (ROM has `UMAX`/`UMIN`/`URANGE`/explicit guard at
  same point), ❌ MISSING (Python guards a game-mechanic value ROM does not),
  or N/A (stdlib bounds, UI clamps, parser indices, persistence safety, RNG
  internals).
- **Tally**: 56 ✅ MATCH / 45 ❌ MISSING / 114 N/A.
- **Gap IDs filed (45 total)**:
  - **Batch A (combat / skills / groups / advancement / mob progs, 134
    sites)**: ARITH-001..ARITH-023 — 23 gaps.
  - **Batch B (handler / world / models / equipment / shop / consumption,
    31 sites)**: ARITH-101..ARITH-113 — 13 gaps.
  - **Batch C (game_loop / loaders / spawning / db / config / imm_set / rng,
    50 sites)**: ARITH-201..ARITH-209 — 9 gaps.

### High-impact gap highlights (gameplay-visible in normal play)

| Gap ID | Site | Divergence |
|--------|------|------------|
| ARITH-010 | `mud/commands/advancement.py:174` | `do_practice` floors `int_app[int].learn / rating` to 1. ROM gives **0** when result rounds to zero (low-INT, high-rating skill). Skill-training balance. |
| ARITH-013 | `mud/commands/combat.py:779` | Mana-cost divisor `(2 + ch->level - required_level)` floored to 1. ROM divides raw, then `UMAX(min_mana, ...)` clamps the negative/huge cost to `min_mana`. Python caps cost at 100. |
| ARITH-015 | `mud/skills/handlers.py:1445` | Berserk `number_fuzzy(level/8)` base floored to 1. ROM gives 0-duration berserk (no affect applied) for levels 1–7. |
| ARITH-016 | `mud/skills/handlers.py:2121` | Charm-person `number_fuzzy(level/4)` floored to 1. ROM gives 0-duration charm (wears off instantly) for levels 1–3. |
| ARITH-009 | `mud/groups/xp.py:257` | `xp_compute` return floored to 0. ROM can return negative XP from alignment edge math; Python swallows. |
| ARITH-105 | `mud/models/character.py:478` | `get_curr_stat` floored to **0** in Python. ROM `URANGE(3, perm+mod, max)` — stats never go below 3. Flows into every stat-dependent calc (hit/dam/AC/carry/wield/sneak). |
| ARITH-101/102/103 | `mud/handler.py:995/1003/1011` | `create_money` weight: ROM raw `gold/5` / `silver/20` produces weight 0 for small stacks; Python inflates to 1. Carry-weight accounting. |

### Notable lower-priority clusters

- **UB-protection (div-by-zero shields)**: ARITH-001/002/003/005/006/007/008/011/012/014 — Python silently produces a reasonable value; ROM would invoke UB (SIGFPE / wraparound) on the same input. Both wrong; closure probably means `assert` + `divergences/` doc rather than direct replication.
- **Carry-accounting underflow floors**: ARITH-106/107/108/109/112/113/201/205 — ROM intentionally lets `carry_number`, `carry_weight`, `area.nplayer` go negative as sentinel for double-extraction; Python's `max(0, ...)` masks corruption.
- **Plague tick floors**: ARITH-203/204 — ROM drives `mana`/`move` negative on plague drain; Python clamps to 0.
- **Possibly invented guarantee**: ARITH-209 (`json_loader.py:357`) — comment claims ROM has `max(1, arg4)` but `db.c` reset uses arg4 directly; floor may be removable rather than fixable.

## Files Modified

- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — new, full 215-row triage with header + 3-batch table + prioritised gap list + next-steps section.
- `CHANGELOG.md` — new `[2.9.64]` section: Added (Class 2 triage entry).
- `pyproject.toml` — 2.9.63 → 2.9.64.
- `docs/sessions/SESSION_SUMMARY_2026-05-27_ARITH_CLASS2_TRIAGE.md` — this file.
- `docs/sessions/SESSION_STATUS.md` — overwritten with 2.9.64 state.

No `mud/` or `tests/` changes this session — pure triage.

## Test Status

No test changes. Did not re-run the full suite (no code changed; the 2.9.63
baseline was 2302/2302 + 3 documented skips in 84s, full `pytest -q` still
hangs past 15min on this machine — pre-existing). The audit's enforcement
tests will be written per-gap during close-out via `/rom-gap-closer`.

## GitNexus

GitNexus FTS database remained read-only throughout the session (same warning
as 2.9.63 SESSION_STATUS). Did not run `gitnexus_impact` or
`gitnexus_detect_changes` because (a) no code touched, (b) FTS broken. The
grep-scan strategy from `META_AUDIT_TAXONOMY.md` Class 2 was the explicit
substitute for graph-based detection here, so the missing index is not a
blocker for this pass.

## Next Steps

1. **Push approval needed.** Local `master` is 2.9.64 with **2 commits** ahead of
   `origin/master` (this session's audit-doc commit + handoff commit; 2.9.63
   was already pushed).
2. **Close high-impact ARITH gaps via `/rom-gap-closer`**, starting with the
   table above (ARITH-010, ARITH-013, ARITH-015, ARITH-016, ARITH-009,
   ARITH-105, ARITH-101–103). One gap = one test = one commit.
3. **Decide policy on UB-protection gaps** before closing the cluster —
   they cannot be directly replicated without ROM-style crashes. Likely
   resolution: `assert` at the divergence site + a `docs/divergences/` note.
4. **ARITH-209 spot-check**: re-read `db.c` reset code to confirm the
   `json_loader.py:357` floor is invented; if so it's a removal rather than
   a parity fix.
5. **Decide whether to do another META class first** before per-gap close-out.
   Candidates: Class 3 GATE_CONSISTENCY, Class 4 TRIGGER_CALL_SITE_MIGRATION,
   Class 5 LIFECYCLE_STAGING. Class 6 is the smallest unaudited remainder
   (per taxonomy doc).
6. **GitNexus reindex** still needed. Run
   `npx gitnexus analyze --skip-agents-md` before any probe-heavy next
   session.
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`
   remains unaddressed.
