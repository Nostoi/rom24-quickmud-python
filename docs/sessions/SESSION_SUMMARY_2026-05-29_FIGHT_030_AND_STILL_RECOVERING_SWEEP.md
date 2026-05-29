# Session Summary — 2026-05-29 — FIGHT-030 + INV-001 (d) (SINGLE-DELIVERY family)

## Scope

Continued from the FIGHT-029 handoff. `SESSION_STATUS.md` named **FIGHT-030**
as the single next task and **INV-001 (d)** as the documented follow-on. Closed
both via the standard gap-closer TDD flow (failing test → fix → tracker /
changelog / version → single commit each). Both gaps are in the INV-001
SINGLE-DELIVERY family surfaced by the `do_rescue` read during FIGHT-029; with
them closed, **INV-001 is now fully ✅ ENFORCED** (no open violations).

## Outcomes

### `FIGHT-030` — ✅ FIXED (2.11.26, `095e268a`)

- **Python**: `mud/skills/handlers.py:rescue`
- **ROM C**: `src/fight.c:3097` (the `check_killer(ch, fch)` call), `:3094-3099`
  (ordering), `:1226-1287` (`check_killer` itself)
- **Gap**: `do_rescue` omitted the rescuer's PK (KILLER) flagging. ROM
  `do_rescue` calls `check_killer(ch, fch)` between the two `stop_fighting` and
  the two `set_fighting` calls. When the rescued ally is fighting **another PC**
  (`fch` is not an NPC), the rescuer joins that PvP fight and ROM flags it
  `PLR_KILLER` (+ killer timer + wiznet) exactly as `do_kill`/`do_murder` would.
  `do_rescue`'s only kill-stealing guard (`src/fight.c:3075`) is NPC-gated, so a
  PC-vs-PC rescue proceeds — the exact case `check_killer` exists to flag. The
  Python `rescue()` handler did the `stop_fighting`/`set_fighting` swap but
  skipped `check_killer`, so the rescuer escaped the PK consequences.
- **Fix**: `rescue()` now calls `check_killer(caster, foe)` in the ROM-faithful
  position. Placement is **load-bearing** — `check_killer` early-returns once
  `attacker.fighting is foe` (`mud/combat/engine.py:1291`), so it must run
  **before** `set_fighting(caster, foe)` or the flag would silently never fire.
  The common ally-vs-mob rescue is unaffected (`check_killer` early-returns on
  an NPC foe).
- **Tests**: `tests/integration/test_rescue_killer_flag.py` (2 cases) — PC foe →
  clan rescuer flagged `PlayerFlag.KILLER` (anchored on the **state bit**, and
  asserting the tank swap actually ran so a missing flag can't masquerade as a
  bailed rescue, per the advisor catch); NPC foe → rescuer NOT flagged (the
  common case the PvP-only placement protects). Fail-first verified: the flag
  assertion failed `0 & KILLER` *after* the swap assertions passed (rescue ran,
  flag absent — the right reason). Built on the proven `check_killer`-firing
  recipe (`test_combat.py::test_kill_flags_player_as_killer`: `initialize_world`
  + `create_test_character` + `clan=1` + `desc`), because `check_killer` calls
  `save_character(attacker)` on the flag path.

### `INV-001 (d)` — ✅ FIXED (2.11.27, `0956f8cf`)

- **Python**: `mud/commands/combat.py` — `do_kick`, `do_rescue`, `do_backstab`,
  `do_bash`, `do_berserk`, `do_flee`, `do_cast` (the wait-state guards)
- **ROM C**: none — the message is not a ROM line (ROM gates wait at the
  interpreter level, silent). INV-001 (d) is delivery-channel only.
- **Gap**: each of the 7 commands did
  `char.messages.append("You are still recovering.")` **and**
  `return "You are still recovering."`. The connection loop
  (`mud/net/connection.py:1980-2000`) sends a command's return value AND drains
  `char.messages`, so a connected PC saw the line **twice** — the FIGHT-029
  fail-path / `do_kill` (FIGHT-020) / `do_surrender` shape.
- **Fix**: dropped the mailbox append at all 7 sites; kept the return (the
  single canonical delivery). **`mud/skills/registry.py:163` was deliberately
  EXCLUDED** (advisor-confirmed): it `raise`s `ValueError("still recovering")`
  rather than returning the line, has **no production callers** (only tests call
  `SkillRegistry.use`), and the loop sends a generic error string on exceptions
  (never the exception text) — so its append is a single mailbox delivery in a
  test-only path, not a double, and the "drop append, keep return" fix
  structurally doesn't apply (there is no return). The exclusion rationale is
  documented in the tracker so a future `grep "still recovering"` won't re-flag it.
- **Tests**: `tests/integration/test_still_recovering_single_delivery.py` —
  a **grep-guard** locking all 7 combat.py sites against any future re-addition
  (the AGENTS.md `test_rng_determinism.py` / `test_equipment_key_convention.py`
  idiom) plus a **behavioral** connected-PC single-delivery test through
  `do_kick`. Fail-first verified: behavioral test showed
  `['You are still recovering.', 'You are still recovering.']` (2×); grep-guard
  found all 7 offenders.

## Files Modified

- `mud/skills/handlers.py` — `rescue` adds `check_killer(caster, foe)` + import (FIGHT-030)
- `mud/commands/combat.py` — 7 wait-state guards drop the mailbox append (INV-001 (d))
- `tests/integration/test_rescue_killer_flag.py` — new (2 tests, FIGHT-030)
- `tests/integration/test_still_recovering_single_delivery.py` — new (2 tests, INV-001 (d))
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-030 row → ✅ FIXED
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 (d) → ✅ FIXED + registry.py exclusion documented; INV-001 status cell → ✅ ENFORCED (all known violations closed)
- `CHANGELOG.md` — `[2.11.26]` (FIGHT-030) + `[2.11.27]` (INV-001 (d)) Fixed entries
- `pyproject.toml` — 2.11.25 → 2.11.27 (two patch bumps)

Commits: `095e268a` (FIGHT-030), `0956f8cf` (INV-001 (d)).

## Test Status

- `tests/integration/test_rescue_killer_flag.py` — 2/2 (FIGHT-030).
- `tests/integration/test_still_recovering_single_delivery.py` — 2/2 (INV-001 (d)).
- Broad combat/skills area suite (7 files incl. the untouched `registry.use`
  test) — 183 passed, 1 skipped.
- **Full suite**: **4978 passed, 4 skipped** (+4 vs prior 4974 = 2 new tests per
  gap). No regressions; none of the carried flakes (`test_backstab_uses_position_and_weapon`,
  `test_combat_death.py`) surfaced this run.
- `ruff check` on touched files: handlers.py (5) and combat.py (1) errors are
  all **pre-existing** — verified byte-identical to `HEAD` before each commit;
  none in edited regions, 0 new.
- `gitnexus_detect_changes`: both commits LOW risk, 0 affected processes; scope
  = exactly the edited symbols (`rescue`; the 7 combat commands). `sanctuary` /
  `auto_success` flagged are diff-adjacency artifacts. Reindexed after each
  commit (exit 0).

## Outstanding

(Carried from the FIGHT-029 summary; FIGHT-030 and INV-001 (d) now closed.)

- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template.
- **Object targeting in `do_cast`** — `TAR_OBJ_CHAR_*` object-target legs
  (`src/magic.c:502-506`, `:525-529`) and `TAR_OBJ_INV` fall back to the caster;
  named-not-found returns `"They aren't here."` not ROM's
  `"You don't see that here."` (deferred, MAGIC_C_AUDIT Scope Notes).
- **Converter hardening** — `convert_skills_to_json.py` is lossy (drops
  hand-added `cancellation`/`harm`); make it merge-not-replace (interim guard in
  the script docstring, `86eee6ef`).
- **`test_backstab_uses_position_and_weapon` parallel flake** (carried) — passes
  serial; root-cause the leaking sibling if it recurs, don't just re-run.
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- Stray uncommitted 1-line doc tweak to
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present across sessions;
  unrelated to parity — left uncommitted).

## Next Steps

The INV-001 SINGLE-DELIVERY family is now fully ✅ ENFORCED, so the highest-yield
INV-001 sibling vein is exhausted. The per-file audit tracker remains exhausted;
**cross-file invariants is the standing pass**. Concrete next candidates: close
**`SHOP-PET-002`** (`rom-gap-closer`, local single-function divergence), or probe
a fresh cross-file invariant area not yet covered by an INV row (affect ticks,
position transitions, mob script triggers, group/follower chain — the
probe-then-scope method in AGENTS.md "Cross-File Invariants").
