# Session Summary — 2026-06-19 — ARITH-208 (mob-hp source floor ⇄ UB-divisor coupling)

## Scope

Picked up from the DB-003 handoff (`HANDOFF_2026-06-19_DB-003_RESET_O_AUDIT.md` →
"Companion item to fold in: ARITH-208"). ARITH-208 was the last entangled
reset/spawn arithmetic item: the `max(0, dice+bonus)` source floor on mob
hp/mana rolls. The handoff flagged it as **audit-sized**, not a gap-closer
single commit, because removing the source floor in isolation would unmask the
policy-mandated UB-divisor floors as a NEW sign divergence. This session closed
it as a **coordinated source + divisor** change with the divisor floors narrowed
to a zero-only guard.

## Outcomes

### `ARITH-208` — ✅ FIXED

- **ROM C**: `create_mobile` `src/db.c:2074-2077` stores
  `max_hit = dice(number, size) + bonus` **raw** (can be negative; `dice()` at
  `src/db.c:3628` returns `0` for size 0, `number` for size 1) and sets
  `mob->hit = mob->max_hit`. The `100 * hit / max_hit` divisors
  (`src/fight.c:2310` do_berserk, `src/fight.c:865-867` injury thresholds,
  `src/mob_cmds.c` hpcnt/HPCT) divide raw — ROM's `neg/neg = positive`.
- **Root cause (coupling)**: Python floored BOTH sides — source at 0
  (`templates._roll_dice`) and every divisor at 1 (`max(1, max_hit)`). The two
  floors masked each other. Removing only the source would yield
  `100 * neg / 1` (large negative) instead of ROM's `neg / neg` (positive).
- **Fix**:
  - **Source** — `mud/spawning/templates.py` `_roll_dice`: removed the
    `max(0, …)` floor and the divergent `if number<=0 or size<=0: return
    max(0,bonus)` short-circuit. `rng_mm.dice` already mirrors ROM `dice()`
    exactly, so the body is now `return rng_mm.dice(number, size) + bonus`.
  - **Divisors** — narrowed `max(1, x)` → **zero-only guard** `x or 1` so a
    negative `max_hit` flows through to a ROM-faithful `c_div`, and only the
    exact-zero divisor diverges (the `UB_DIVISORS.md` crash policy is preserved,
    not removed):
    - `mud/commands/combat.py` do_berserk — divisor zero-guarded; the
      `UMIN(ch->hit + 2*level, ch->max_hit)` heal cap now uses the **raw**
      `max_hit` (ROM `src/fight.c`), not the guarded divisor.
    - `mud/combat/messages.py` dam_message — zero-guard (already `c_div`).
    - `mud/mobprog.py` hpcnt + HPCT — zero-guard **and** bare `//` → `c_div`
      (latent floor-vs-truncation bug: a negative `current`/`max_hit` floored
      toward −∞ instead of C truncating toward zero).
    - `mud/combat/engine.py` `max_hit / 4` injury thresholds (`src/fight.c:865-867`)
      — `//` → `c_div` (now reachable with a negative `max_hit`).
- **Tests**: `tests/test_arith_208_dice_no_floor.py` — 5 new, pinning
  (a) source floor gone (`_roll_dice((1,1,-4)) == -3`, `((0,0,-5)) == -5`),
  (b) spawn propagates negative `max_hit` raw (`mob.hit == mob.max_hit == -3`),
  (c) divisor zero-guard preserved (no `ZeroDivisionError` at `max_hit == 0`),
  (d) divisor neg/neg = positive (hpcnt `$n > 50` flips True at hit==max_hit==-50).
  Existing `tests/test_arith_max_hit_floor.py` (ARITH-011/012 zero-guard) stays
  green — the zero case is unchanged.

## Files Modified

- `mud/spawning/templates.py` — `_roll_dice` source floor removed (raw dice+bonus)
- `mud/commands/combat.py` — do_berserk divisor zero-guard + raw `max_hit` heal cap
- `mud/combat/messages.py` — dam_message divisor zero-guard
- `mud/mobprog.py` — hpcnt/HPCT zero-guard + `//`→`c_div` (+ `c_div` import)
- `mud/combat/engine.py` — injury-threshold `max_hit/4` `//`→`c_div`
- `tests/test_arith_208_dice_no_floor.py` — new, 5 tests
- `docs/divergences/UB_DIVISORS.md` — policy narrowed: "keep the floor" →
  "zero-only guard (`x or 1`), negatives are now ROM-faithful"; ARITH-208 row added
- `docs/parity/audits/ARITHMETIC_BOUNDARY.md` — rows 42/43 ❌→✅; summary count
  `Effective open MISSING: 2 → 1`; narrative line flipped
- `CHANGELOG.md` — Fixed entry
- `pyproject.toml` — 2.14.172 → 2.14.173

## Test Status

- `tests/test_arith_208_dice_no_floor.py` + `tests/test_arith_max_hit_floor.py` — 7/7
- Targeted: spawning / combat / mobprog / mob_damage / `mud/` doctests — 125/125
- Differential: `test_differential_smoke.py` + `test_diff_harness_unit.py` — 68/68
- `ruff check` (touched files) — clean
- `gitnexus_detect_changes` — low risk, scope confined to the 6 expected symbols + docs
- Full suite: **5894 passed, 4 skipped** (0:07:58)

### `ARITH-211` — ✅ FIXED (same session, surfaced by ARITH-208)

- **ROM C**: `show_char_to_char` `src/act_info.c:456-459` —
  `percent = max_hit > 0 ? 100*hit/max_hit : -1` (the `-1` buckets to the worst
  health tier "is bleeding to death").
- **Root cause**: `mud/world/look.py` `_look_char` used `else 100`, rendering "in
  excellent condition" for a non-positive `max_hit`. Latent for `max_hit == 0`
  (masked by `getattr(...,100) or 100`) but ARITH-208 made it reachable for a
  **negative** `max_hit`.
- **Fix**: `else 100` → `else -1`; `//` → `c_div`.
- **Tests**: `tests/test_arith_211_look_condition_negative_max_hit.py` (1 new).

## Outstanding (filed durably this session)

- **ARITH-210** ❌ MISSING — `mud/spawning/templates.py` `from_prototype` sets
  `current_hp = max_hit if max_hit else max(proto.hit[1]+proto.hit[2], 1)`. ROM
  `mob->hit = mob->max_hit` raw (`src/db.c:2077`) → a `max_hit == 0` proto should
  give `hit == 0`, but Python floors to ≥ 1. Negative already propagates (truthy);
  only the **zero** case diverges. Same defensive-floor class as ARITH-205/207/209.
  Needs a reachability probe (does a 0-hp spawn → immediate mortal-wound on first
  `update_pos`?) before removing the floor — small coordinated change, not a blind
  delete. Filed in `docs/parity/audits/ARITHMETIC_BOUNDARY.md`.

## Next Steps

The reset/spawn divergence surface is now **fully drained** (DB-003 + ARITH-208
both closed). ARITH backlog: only the **ARITH-114** follow-on remains open
(get_curr_stat per-race/class ceiling).

Cross-file / divergence-class sweep is the active pass. Fresh candidates with no
INV row yet: **affect ticks**, **position transitions**, **mob script triggers**,
**group/follower chain**. Use the probe-then-scope method (read ROM C contract →
read Python equivalent → one failing contract test → close as gap or file as
INV-NNN). Feature-sized alternatives: BOARD-001 (default board seeding), OLC save
paths. Run `/rom-divergence-sweep` for the completeness lens (which verification
layer each class needs).
