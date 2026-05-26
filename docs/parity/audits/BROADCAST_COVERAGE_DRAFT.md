# Command Broadcast Coverage Audit — DRAFT SKETCH

> **Status**: schema sketch + 5 worked rows. The full scan has not been
> run. Once approved, a dedicated session populates every `do_*` in
> `mud/commands/`. Each row that comes back ❌ or ⚠️ becomes a single
> gap-closer commit in the burn-down pass that follows.

## Why this audit exists

The per-file `/rom-parity-audit` walks one ROM C file at a time and
confirms each function has a Python equivalent. But ROM commands
emit 1–4 `act()` calls per outcome (TO_CHAR, TO_VICT, TO_NOTVICT,
TO_ROOM), and Python's `def do_X(...) -> str` returns ONLY the
TO_CHAR equivalent. The TO_VICT/TO_NOTVICT/TO_ROOM broadcasts have
to be made via explicit `broadcast_room()` / `room.broadcast()` /
`messages.append()` calls — which are easy to omit silently.

The 2.9.17 → 2.9.20 cluster found four of these in a row
(`do_say`/`do_tell` SPEECH gate, `do_buy`, `do_follow`, `do_group`).
Each was the same architectural bug in a different command. The
audit below catches the rest *systematically* instead of one
probe-and-pray at a time.

## Rubric

For each `do_X`:

1. Locate the ROM C function. Citation comments already exist for
   most commands; otherwise `grep -n "^void do_X " src/`.
2. Count `act(...)` and `act_new(...)` calls in the ROM function,
   bucketed by terminal arg: TO_CHAR, TO_VICT, TO_NOTVICT, TO_ROOM,
   TO_ALL. Ignore TO_CHAR (that's the Python return value).
3. In the Python function, count distinct broadcast destinations
   for non-`char` recipients. Sources:
   - `broadcast_room(room, msg, exclude=char)` → TO_ROOM
   - `room.broadcast(msg, exclude=char)` → TO_ROOM
   - `victim.messages.append(msg)` (or via `send_to_char(victim, …)`) → TO_VICT
   - iterating `room.people` to append to non-char/non-victim → TO_NOTVICT
   - `act_format(...)` followed by one of the above
4. Compare counts per bucket. Set status:
   - **✅ MATCH** — every ROM non-TO_CHAR `act()` has a Python
     counterpart with the right destination on every success path.
   - **⚠️ PARTIAL** — counts match on the happy path but at least
     one error branch / quirky outcome is silent.
   - **❌ MISSING** — the Python function emits zero broadcasts on
     a path where ROM emits one or more.
   - **N/A** — Python intentionally diverges (rare; must cite
     `docs/divergences/`).
5. If ❌ or ⚠️, assign a `BCAST-NNN` gap ID. Add a row to the
   per-command audit doc if one exists; otherwise the audit row
   itself is the spec.

## Schema

| # | Command | Python entry | ROM C ref | TO_VICT | TO_NOTVICT | TO_ROOM | Status | Gap ID | Notes |
|---|---------|--------------|-----------|---------|------------|---------|--------|--------|-------|

- Counts are `ROM / Python`. `1/1` = parity; `1/0` = missing one;
  `2/1` = partial coverage.
- "TO_VICT" means the second-person target (a victim, a recipient).
- A ✅ row stays in the table — it's a pinning regression record
  and tells future maintainers "this contract is checked."

## Worked examples (5 rows)

| # | Command | Python entry | ROM C ref | TO_VICT | TO_NOTVICT | TO_ROOM | Status | Gap ID | Notes |
|---|---------|--------------|-----------|---------|------------|---------|--------|--------|-------|
| 1 | `buy` | `mud/commands/shop.py:727 do_buy` | `src/act_obj.c:2531-2769` | 0/0 | 0/0 | 1/1 | ✅ MATCH | (was BCAST-001, fixed in 2.9.18) | TO_ROOM `$n buys $p[N].` / `$n buys $p.` added via `room.broadcast` in 2.9.18. Pet-shop branch separate. |
| 2 | `follow` | `mud/commands/group_commands.py:71 do_follow → add_follower` | `src/act_comm.c:1591-1607` | 1/1 | 0/0 | 0/0 | ✅ MATCH | (was BCAST-002, fixed in 2.9.19) | TO_VICT `$n now follows you.` (gated on `can_see(master, ch)`) added 2.9.19. Symmetric `stop_follower` also fixed. |
| 3 | `group` | `mud/commands/group_commands.py:165 do_group` | `src/act_comm.c:1838-1854` | 1/1 | 1/1 | 0/0 | ✅ MATCH | (was BCAST-003, fixed in 2.9.20) | Both add and remove branches now emit TO_VICT + TO_NOTVICT. |
| 4 | `give` | `mud/commands/give.py:20 do_give` | `src/act_obj.c:659-180` | 1/1 | 1/1 | 0/0 | ✅ MATCH | — | Both coin path (`$n gives $N some coins.`) and object path (`$n gives $p to $N.`) emit TO_VICT + TO_NOTVICT via `act_format` + `messages.append`. |
| 5 | `quaff` | `mud/commands/obj_manipulation.py:470 do_quaff` | `src/act_obj.c:1865-1906` | 0/0 | 0/0 | 1/1 | ✅ MATCH | — | TO_ROOM `$n quaffs $p.` at line 504-506 fires before spells, matching ROM ordering at `:1897-1898`. |

## Reading the worked rows

- Three of the five (`buy`, `follow`, `group`) needed the most recent
  cluster of fixes. The audit row is now a *pinning regression* — the
  next time someone refactors `do_buy` and accidentally drops the
  broadcast, this row's "1/1" claim becomes false and the gap is
  visible without anyone having to remember the 2.9.18 fix.
- The remaining two (`give`, `quaff`) were already correct. They
  should appear in the table anyway — green rows are evidence the
  scan worked, and they cost nothing to maintain.

## What the full scan would look like

The `mud/commands/` tree currently has approximately 130+ `do_*`
functions (movement, communication, magic, combat, inventory, shop,
misc, immortal). A full scan session:

1. Enumerate every `do_*` by `grep -rn "^def do_" mud/commands/`.
2. For each, locate the ROM C ref from the function's docstring or
   citation comment. Where missing, `grep -n "^void do_X " src/`.
3. Apply the rubric. Add a row.
4. End of session: the table has N rows, M ❌/⚠️. File `M` as
   `BCAST-001` … `BCAST-M` ready for burn-down.

Estimated session length: 4–6 hours of focused mechanical work,
single agent. Output is one markdown table — no code changes, no
tests, no commits to behavior. The burn-down pass that follows runs
the existing `rom-gap-closer` skill once per ❌/⚠️ row.

## Open questions before approving the full scan

1. **Scope cap.** Cap at top-N by traffic (look, score, who, get,
   drop, wear, remove, kill, cast, say, tell, fl, n/s/e/w) for a
   first pass? Or do all 130 in one shot? My recommendation: all
   130 — the bookkeeping cost is small once you're in the rhythm,
   and partial-coverage tables rot.
2. **Mixed-shape commands.** Some commands have many outcome paths
   (e.g. `do_drink` differs for FOUNTAIN vs DRINK_CON vs ground
   liquid). Should the table use one row per command with the
   *worst* status, or expand to one row per outcome? My
   recommendation: one row per command, with a "Notes" column line
   per non-trivial outcome.
3. **`act()` helpers.** Some Python files use a wrapper (`_broadcast`,
   `act_to_room`, `act_to_others`) — should the rubric count those?
   Yes, treat any function that ultimately reaches `broadcast_room`
   / `room.broadcast` / `send_to_char(non_ch, ...)` as a broadcast.
4. **Position floors.** ROM `act_new(..., POS_RESTING)` only delivers
   if recipient position ≥ RESTING. Most Python broadcasts ignore
   position. Track in a separate sub-audit, not this one — distinct
   bug class.

If the schema and worked rows look right, the next session can
populate this doc end-to-end.
