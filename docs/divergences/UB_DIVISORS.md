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

The port therefore applies a `max(1, divisor)` (or analogous) floor
on these specific divisions. The result is a deliberate, documented
divergence: when the divisor would have been 0, Python returns a
sane value (typically `100` for `hp_percent`) instead of crashing.

## Policy

For each ROM raw-division where the divisor depends on character or
object state:

1. **Verify reachability.** Probe initialization paths to confirm
   whether the divisor can actually be 0 at the call site (e.g.
   degenerate area data, save corruption, equipment-affect math
   ordering). Cite the init paths (`mud/spawning/templates.py`,
   `mud/models/character.py`, `mud/handler.py`) in the audit row.

2. **Keep the Python floor.** Do not remove it to replicate ROM's
   SIGFPE — the cost is asymmetric (see above).

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

| Gap ID | Site | Divisor | Reachable in Python? |
|--------|------|---------|----------------------|
| ARITH-011 | `mud/commands/combat.py:512` do_berserk hp_percent | `max_hit` | PC-only path; PC `max_hit` initializes to ≥ 20 (`mud/models/character.py:951-976`). Unreachable in steady-state PC play, but kept consistent with ARITH-012. |
| ARITH-012 | `mud/commands/combat.py:636` do_flee hp_percent | `max_hit` | NPC-reachable. Mob protos with degenerate `hit_dice` (e.g. `(0,0,0)`) spawn with `max_hit == 0` (`mud/spawning/templates.py:170-172` floors `_roll_dice` at 0, not 1). Any fighting NPC can call do_flee. |

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
