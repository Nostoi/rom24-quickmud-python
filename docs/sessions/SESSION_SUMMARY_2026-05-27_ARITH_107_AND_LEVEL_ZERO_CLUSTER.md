# Session Summary — 2026-05-27 — ARITH-107 fix + level-0 spell/skill dice cluster reclass

## Scope

Continued the META Class 2 ARITHMETIC_BOUNDARY close-out begun in
2.9.64. Picked up directly from `SESSION_STATUS.md` 2.9.74 "Next
Intended Task" list: closed **ARITH-107** (item #2, `area.nplayer`
floor in `Room.remove_character`) and triaged the **level-0
spell/skill dice cluster** (item #3, ARITH-020/021/022/023). Probe
of ROM source confirmed all four cluster candidates are dead
defensive code — reclassified to ⛔ N/A with ROM-cite comments.

## Outcomes

### `ARITH-107` — ✅ FIXED (2.9.75)

- **Python**: `mud/models/room.py:171` (`Room.remove_character`)
- **ROM C**: `src/handler.c:1501-1502` (`char_from_room`)
- **Gap**: ARITH-107 — `max(0, current - 1)` floor on `area.nplayer`
- **Fix**: Floor removed. `area.nplayer = int(area.nplayer) - 1`
  matches ROM's bare `--ch->in_room->area->nplayer`. The existing
  `if char in self.people:` guard prevents a bare
  `remove_character(non-present-char)` from decrementing, so the
  only path that fires a negative value is genuine desync (e.g. a
  prior bypass of the canonical helpers — see INV-023). Negative
  `nplayer` now surfaces desync bugs via repop / area-age divergence
  in `src/db.c:1617-1630` instead of silently masking them.
- **Tests**: `tests/integration/test_arith_107_nplayer_no_floor.py`
  (3/3) — negative-on-desync, NPC-skip, balanced-add-remove.
  Full integration suite: **2340 passed, 3 skipped** in 84.95s.

### `ARITH-020` / `ARITH-021` / `ARITH-022` / `ARITH-023` — ⛔ N/A (2.9.76)

Reclassified the entire level-0 spell/skill dice cluster as dead
defensive code after ROM-source probe (delegated to Sonnet
subagent for token efficiency; results verified against
`src/magic.c`, `src/fight.c`, `src/db.c`).

- **ARITH-020** — `mud/skills/handlers.py:3744`
  `rng_mm.dice(1, max(1, level))` in `spell_energy_drain`. ROM
  `src/magic.c:2727` does `dice(1, level)` raw. Unreachable:
  `do_cast` level/class gate forbids level-0 casters; mob casters
  always have level ≥ 1 by area data. ROM `dice(1, 0) = 0` via the
  `size == 0` short-circuit in `src/db.c` — divergence exists but
  the input cannot fire.

- **ARITH-021** — `mud/skills/handlers.py:4127`
  `max(0, level - 2)` in `spell_fire_breath`. ROM `src/magic.c:4701`
  passes `level - 2` raw to `saves_spell`. Unreachable: dispatched
  only via `spec_breath_fire` spec_fun, attached exclusively to
  high-level dragon mobs. `saves_spell(-1, ...)` is arithmetically
  valid in ROM (no crash), but the input cannot fire.

- **ARITH-022** — `mud/skills/handlers.py:4517`
  `max(0, level - 2)` in `spell_frost_breath`. ROM `src/magic.c:4759`.
  Same reasoning as ARITH-021 — `spec_breath_frost` on dragon mobs
  only.

- **ARITH-023** — `mud/skills/handlers.py:5518`
  `max(1, int(...level))` in `do_kick`. ROM `src/fight.c:3129` does
  `number_range(1, ch->level)` raw. Unreachable: `do_kick` requires
  `ch->fighting != NULL` plus a successful `gsn_kick` skill check;
  level-0 characters cannot fight or have skills. Additionally,
  ROM `number_range(1, 0)` returns `from = 1` via the `to < from`
  swap branch in `src/db.c` — identical to the Python floor even
  if reached.

  ROM-cite comments added at all four sites documenting
  unreachability per site. No production behavior change.

## Files Modified

- `mud/models/room.py` — ARITH-107 floor removal at line 171.
- `mud/skills/handlers.py` — ROM-cite comments added at four sites
  (3744, 4127, 4517, 5518) for ARITH-020/021/022/023 N/A reclass.
- `tests/integration/test_arith_107_nplayer_no_floor.py` — new file,
  3 regression cases.
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — flipped rows:
  ARITH-107 → ✅ FIXED, ARITH-020/021/022/023 → ⛔ N/A.
- `CHANGELOG.md` — added 2.9.75 (Fixed) and 2.9.76 (Changed)
  sections.
- `pyproject.toml` — `2.9.74` → `2.9.76`.

## Test Status

- `pytest tests/integration/test_arith_107_nplayer_no_floor.py` — 3/3 passing.
- `pytest tests/integration/test_inv023_area_nplayer_coherence.py` — 2/2 passing (cross-file invariant still green after floor removal).
- Full integration suite: **2340 passed, 3 skipped** in 84.95s.
- `ruff check mud/models/room.py tests/integration/test_arith_107_nplayer_no_floor.py` — clean.
- Pre-existing lint in `mud/skills/handlers.py` (B007/F841 at lines 672/1734/3469/3616/6249) untouched.

## Next Steps

1. **Push approval needed** — 9 commits ahead of `origin/master`
   spanning 2.9.70–2.9.76 (verify with
   `git log origin/master..HEAD`). The carry-counter, ARITH-107,
   and level-0 cluster work all needs to ship together to avoid
   half-applied parity state.
2. **ARITH-111** — held-back item-shop haggle floor at
   `mud/commands/shop.py:822`. Needs the `deduct_cost`-with-negative-
   cost analysis described in the audit doc row 26. Reachable when
   `profit_buy < 50` (custom area shops); ROM allows `cost` to go
   negative while Python clamps to 0. Lower priority than freshly-
   open items but still in scope for closing ARITHMETIC_BOUNDARY.
3. **ARITH-114** — PC ceiling divergence on `get_curr_stat`
   (Python flat 25 vs ROM per-race/class `max_stat` for PCs at
   `src/handler.c:861-869`). Only matters above stat-22; can wait.
4. **Remaining ARITH triage open**: 14 ❌ MISSING. With this
   session: cumulative **15 FIXED / 17 N/A / 14 MISSING**. The
   remaining MISSING entries are mostly higher-context (need
   downstream effect analysis, not single-line floor removals).
5. **Pre-existing lint** still parked in `mud/skills/handlers.py`
   (B007/F841 at 5 sites), `mud/handler.py:566-567,960`,
   `tests/integration/test_do_practice_command.py:255`,
   `mud/commands/combat.py:685`, `mud/commands/consumption.py:11,164-166`.
6. **GitNexus FTS read-only warnings** still firing each session
   (documented upstream issue); node/edge graph remains current.
   Stop-and-reindex fired after each commit and was honored — graph
   is fresh as of session end.
7. **Pre-existing flake** at
   `tests/test_combat_death.py::test_auto_flags_trigger_and_wiznet_logs`.
8. **Worktree hygiene** — locked worktrees still present in
   `.claude/worktrees/`.
