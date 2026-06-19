# UB-Divisor Floors — Python vs ROM C

## ROM C Behavior

ROM 2.4b6 frequently divides by a character/object field without guarding
against zero — e.g. `src/fight.c:2310` (`hp_percent = 100 * ch->hit /
ch->max_hit`) and `src/act_move.c` do_flee's hp_percent. If the divisor
field is somehow zero at the call site, ROM raises `SIGFPE` and the
game process dies.

In normal ROM play these divisions are "safe": PCs are initialized
with non-zero `max_hit`/`max_mana`, NPCs are rolled from area data the
designer ensured is sane, and corruption is rare. The C source treats
the divisor's positivity as an invariant the rest of the engine
enforces, not as something the consumer must defensively check.

## Python Architecture

The Python port cannot tolerate a `ZeroDivisionError` mid-combat the
way ROM tolerates a SIGFPE — Python would propagate the exception up
through the command dispatcher and the connection layer in ways that
break the game loop for *all* connected players, not just the
offender. The cost of replicating ROM's UB exactly is asymmetric:
ROM crashes one process, Python crashes the whole MUD.

The port therefore applies a **zero-only guard** (`divisor or 1`) on
these specific divisions. The result is a deliberate, documented
divergence at *exactly one* input: when the divisor would have been 0,
Python returns a sane value (typically `100` for `hp_percent`) instead
of crashing.

> **Zero-only guard, NOT `max(1, divisor)`.** The earlier form
> `max(1, divisor)` *also* clamped negative divisors to 1, which was a
> second, undocumented divergence: ROM divides by a negative `max_hit`
> raw (e.g. a mob spawned with `dice()+bonus < 0`, ARITH-208), so
> `100 * neg_hit / neg_max_hit = positive`, whereas `max(1, …)` produced
> `100 * neg_hit / 1 = large negative`. The guard was narrowed to
> `divisor or 1` (ARITH-208, 2026-06-19): negative divisors now flow
> through to a ROM-faithful `c_div`, and only the exact-zero case
> diverges. Pair the guard with `c_div` (never bare `//`) so the C
> truncation-toward-zero sign is preserved for negative operands.

## Policy

For each ROM raw-division where the divisor depends on character or
object state:

1. **Verify reachability.** Probe initialization paths to confirm
   whether the divisor can actually be 0 at the call site (e.g.
   degenerate area data, save corruption, equipment-affect math
   ordering). Cite the init paths (`mud/spawning/templates.py`,
   `mud/models/character.py`, `mud/handler.py`) in the audit row.

2. **Keep a zero-only guard (`divisor or 1`), not `max(1, divisor)`.**
   Do not remove the guard entirely to replicate ROM's SIGFPE — the
   cost is asymmetric (see above). But do NOT clamp negatives: a
   negative divisor must flow through to `c_div` so ROM's `neg/neg =
   positive` (and `pos/neg = negative`) is reproduced. Only the exact
   `0` divisor diverges.

3. **Add a ROM-cite comment** at the call site referencing both
   the ROM line and this divergence doc, so a future reader can
   tell the floor apart from incidental defensive code.

4. **Reclassify the audit row to `⛔ N/A`** with rationale
   "Python intentionally floors divisor to prevent crash on
   degenerate state ROM would crash on. See
   `docs/divergences/UB_DIVISORS.md`." The audit-tally counts
   shift one ❌ MISSING → one ⛔ N/A per closure.

5. **Add a regression test** confirming the floor saves the
   call from `ZeroDivisionError`. The test pins the divergence
   so a future "ROM-strict" refactor cannot quietly remove the
   floor and break live play.

## Gaps Covered by This Policy

All these divisor sites use the **zero-only guard** (`divisor or 1`) +
`c_div` as of ARITH-208 (2026-06-19) — negatives are ROM-faithful, only
the exact-zero divisor diverges.

| Gap ID | Site | Divisor | Reachable in Python? |
|--------|------|---------|----------------------|
| ARITH-011 | `mud/commands/combat.py` do_berserk hp_percent | `max_hit` | PC-only path; PC `max_hit` initializes to ≥ 20 (`mud/models/character.py:951-976`). Unreachable in steady-state PC play, but kept consistent with ARITH-012. The `UMIN(ch->hit + 2*level, ch->max_hit)` cap uses the RAW max_hit, not the guarded divisor (ROM `src/fight.c`). |
| ARITH-012 | `mud/commands/combat.py` do_flee hp_percent | `max_hit` | NPC-reachable. Mob protos with degenerate `hit_dice` can spawn with `max_hit <= 0`. Any fighting NPC can call do_flee. |
| ARITH-208 | `mud/spawning/templates.py` `_roll_dice` (source) + the divisors above | — | **FIXED 2026-06-19.** Source floor `max(0, dice+bonus)` removed so `max_hit = dice()+bonus` is stored raw (ROM `src/db.c:2074-2077`, can be negative); coupled divisor floors narrowed from `max(1,…)` to `divisor or 1` + `c_div` (combat.py do_berserk, combat/messages.py dam_message, mobprog.py hpcnt/HPCT, combat/engine.py max_hit/4 threshold). The mobprog sites also moved from bare `//` to `c_div` (latent floor-vs-trunc bug on negative `current`/`max_hit`). Test: `tests/test_arith_208_dice_no_floor.py`. |

Future closures of ARITH-001/002/003/005/006/007/008/014 should be
evaluated against this same policy: reachability probe → keep the
floor → ROM-cite + reclass N/A → regression test.

## Anti-Goal

This divergence is **not** an excuse to add new `max(1, ...)` floors
to ROM-parity code. Every floor is a divergence that must be
justified by an audit row and documented here. The default for new
parity code is **raw ROM math via `c_div` / `c_mod`** (see
`AGENTS.md` "ROM Parity Rules"). Existing floors get documented;
new code should not need them.
