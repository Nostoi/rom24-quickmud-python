# Session Summary — 2026-05-26 — META audits Classes 1, 7, 8 (2.9.52)

## Scope

Continuation of the 2026-05-26 series. After the immortal-command cluster
(2.9.48–2.9.51) brought load/purge/slay/restore to parity, the per-file
audit's "next candidate" list (position-transition adjacency,
group-leader-on-logout vs persistence) probed clean. Pivoted to the
density-first META class burn-down per
`docs/parity/META_AUDIT_TAXONOMY.md`. Three audits ran in parallel
sub-agents, each producing one audit doc.

## Outcomes

### `BROADCAST_COVERAGE.md` — ✅ AUDITED (Class 1)

- **File**: `docs/parity/audits/BROADCAST_COVERAGE.md` (347 lines)
- **Commands audited**: 283 of ~284 dispatcher slots (`clan`/`clantalk`
  share one handler row).
- **Counts**: 209 ✅ COVERED / 10 ⚠️ PARTIAL / 29 ❌ MISSING / 35 N/A.
- **Method**: regex-counted ROM `act()`/`act_new()` call sites per
  `do_X` (bucketed by TO_ROOM / TO_VICT / TO_NOTVICT / TO_ALL),
  compared to 10 Python broadcast indicators inside each Python `do_*`
  body. Shallow, body-only — no helper transitivity, so the ❌ count
  is inflated by known helper-hidden cases (door commands almost
  certainly covered by `mud/world/movement.py`; combat skills routed
  through `damage()`).
- **Stable IDs**: `BCAST-001` … `BCAST-039` on the 39 ⚠️/❌ rows.
- **Top 3 gap candidates** (per agent priority ranking):
  1. `do_disarm` / `do_trip` / `do_dirt` / `do_surrender` (`src/fight.c`)
     — TO_VICT + TO_NOTVICT hit-feedback for victim and bystanders;
     if not delegated through `damage()` these are visible parity gaps.
  2. `do_goto` / `@goto` (`src/act_wiz.c:905`, V=4) — ROM emits
     poofout TO_ROOM at origin and poofin TO_VICT at destination;
     bystanders see no immortal-transition narration.
  3. `do_invis` / `do_incognito` (`src/act_wiz.c:4252/4298`, R=3)
     — ROM emits "X slowly fades into thin air." TO_ROOM on
     visibility transitions; Python body has zero broadcast hits.
- **Next session work** (when burning down): walk ❌/⚠️ list in
  priority order; before promoting any row to a `/rom-gap-closer`
  commit, verify whether a helper (`world/movement.py`,
  `combat/engine.py:damage`) already issues the broadcast. Helper
  hits collapse the row to ✅; misses get promoted to gap-closers.

### `PARALLEL_REPRESENTATIONS.md` — ✅ AUDITED (Class 7)

- **File**: `docs/parity/audits/PARALLEL_REPRESENTATIONS.md`
- **Counts**: 1 ❌ ACTIVE-BUG / 8 ⚠️ DRIFT-RISK / 6 ✅ ENFORCED.
- **Hypothesis** "mostly closed by INV-012/INV-013/INV-014" —
  **HELD**. All object-shape / registry / equipment / inventory /
  room-people parallel reps are enforced via existing invariants or
  fully retired.
- **Single ❌ `PARALLEL-010`** (concrete gap-closer candidate):
  - **Python**: `mud/commands/combat.py:683-688` `do_flee` writes to
    `room.characters` and `new_room.characters` — neither attribute
    exists (Room has `people`).
  - **Symptom**: the `hasattr(room, "characters")` gate at line 684
    hides the remove silently (always False → no remove). Line 688
    `new_room.characters.append(char)` raises `AttributeError` caught
    by broad `try/except` at line 695-696, surfacing a misleading
    "Flee failed: 'Room' object has no attribute 'characters'" while
    `char.move` is still decremented at line 699.
  - **Net effect**: character pays the move cost but doesn't actually
    move; `room.people` is never updated. The flee SUCCESS path
    (combat-stop, exp loss, room broadcast) ran but the actual room
    transition didn't.
  - **Fix shape**: use the canonical `room.remove_character(char)` /
    `new_room.add_character(char)` helpers (defined at
    `mud/models/room.py:140, 157`).
- **8 ⚠️ DRIFT-RISK** (mechanical cleanup batch, same class as
  the previously-fixed SAC-004 `autosplit` bug): inline hex flag
  aliases in `misc_player.py`, `player_config.py`, `remaining_rom.py`,
  `obj_manipulation.py`, `imm_load.py`, plus a dead `.carrying`
  fallback in `consumption.py:308-316` and a stale docstring at
  `handler.py:694`.

### `MATH_AND_RNG.md` — ✅ AUDITED (Class 8)

- **File**: `docs/parity/audits/MATH_AND_RNG.md`
- **Counts**: 1 ❌ HIGH / 3 ⚠️ LOW / ~110 ✅ MATCH.
- **RNG channel**: **completely clean** — zero `import random` or
  `random.*` hits anywhere in `mud/`. Years of "use `rng_mm`"
  enforcement actually held.
- **Single ❌ `MATH-001`** (concrete gap-closer candidate):
  - **Python**: `mud/combat/engine.py:1290`
    `dam += get_damroll(attacker) * min(100, skill_total) // 100`
  - **ROM C**: `src/fight.c` `one_hit` —
    `GET_DAMROLL(ch) * UMIN(100, skill) / 100` (C truncate-toward-zero).
  - **Divergence**: with cursed gear or debuffs, `get_damroll` can be
    negative; the product `(get_damroll * min(100, skill_total))` is
    then negative; Python `// 100` floor-divs toward negative infinity
    where ROM's `/` truncates toward zero. So Python over-debits
    damroll by 1 in the negative range.
  - **Fix shape**: replace `// 100` with `c_div(..., 100)` from
    `mud.math.c_compat`.
  - **Why this didn't surface earlier**: integration tests likely
    don't cover combat with a negative-damroll character.
- **3 ⚠️ LOW** (currently safe via upstream `max(0, ...)` clamps but
  fragile under refactor): `MATH-002` vampiric `dam // 2`,
  `MATH-003` weapon-flag `weapon_level // N`, `MATH-004`
  `magic.c` `fail // N`.
- **Doc includes**: PARITY008 (RNG-channel lint) + PARITY009
  (signed-divide lint) ruff rule sketches with allowlist mechanism.

### Sub-agent infrastructure note

Three `general-purpose` agents ran in parallel — Class 1 with
`isolation: "worktree"`, Classes 7/8 re-run without isolation after the
first run's worktrees were auto-cleaned and the audit docs lost. **Use
no-isolation for audit-only deliverables** going forward — worktree
isolation cleans up uncommitted files when the agent exits without a
commit, which silently destroys the deliverable. The Class 1 worktree
survived only because its worktree was locked (lock reason: "claude
agent agent-a1b07201d504ce97b"). The Class 1 file content was rescued
by `cp` from the locked worktree path. The locked Class 1 worktree
remains at `.claude/worktrees/agent-a1b07201d504ce97b` — non-blocking,
can be unlocked + removed in a separate hygiene pass.

## Files Modified

- `docs/parity/audits/BROADCAST_COVERAGE.md` — NEW (347 lines, Class 1)
- `docs/parity/audits/PARALLEL_REPRESENTATIONS.md` — NEW (Class 7)
- `docs/parity/audits/MATH_AND_RNG.md` — NEW (Class 8)
- `CHANGELOG.md` — 2.9.52 section
- `pyproject.toml` — 2.9.51 → 2.9.52
- `docs/sessions/SESSION_STATUS.md` — points at this summary

## Test Status

- **No tests run.** This is an audits-only commit; no runtime behavior
  changed.
- Pre-existing suite state from 2.9.51: integration 2239 passed + 3
  skipped (72s).

## Next Steps

The audits are landed. Burn-down begins next session.

1. **Push approval** required for 2.9.52. Per standing rule, no push
   without explicit per-cluster approval ("yes push v2.9.52 to
   origin/master").
2. **Burn-down order** (smallest-first to bank fast wins):
   - **`MATH-001`** (Class 8): one-line `//` → `c_div` change at
     `mud/combat/engine.py:1290`; failing test = combat with
     negative-damroll victim; ROM ref `src/fight.c` `one_hit`.
   - **`PARALLEL-010`** (Class 7): rewrite `do_flee` move
     code at `mud/commands/combat.py:683-688` to use
     `room.remove_character` / `new_room.add_character`; failing
     test = flee from room with multiple exits, assert char is in
     new room's `people` after success.
   - **`BCAST-001`…`BCAST-039`** (Class 1): walk in agent's priority
     order; verify helper coverage before promoting each row to a
     gap-closer commit.
3. **Drift-risk cleanup batch** (8 PARALLEL ⚠️ rows + 3 MATH ⚠️
   rows): a separate mechanical-cleanup commit cycle once the ❌s are
   closed. Not blocking.
4. **GitNexus refresh** — index still stale. Run
   `npx gitnexus analyze --skip-agents-md` before the next code-edit
   probe.
