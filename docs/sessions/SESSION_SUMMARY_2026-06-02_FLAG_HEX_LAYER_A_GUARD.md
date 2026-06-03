# Session Summary — 2026-06-02 — Flag-hex divergence class locked as Layer-A guard

## Scope

Picked up from the prior session's handoff (2.12.75, divergence-class
completeness lens), whose documented next task was the cheap **Layer-A to-do**:
investigate divergence class 5 (flag-hex) and class 6 (pointer-identity) via
`/rom-divergence-sweep`, each yielding either a committed guard or an honest
reclassification.

This session ran the sweep on **class 5 (flag-hex)** — the AGENTS.md "never
hardcode hex bit values; use the IntEnum" rule. Unlike async-delivery (class 4,
which reclassified A→C last session when its bypass-grep false-positived),
flag-hex came back the **other** way: a tight prefix-anchored grep had exactly
one legitimate hit, so the class proved Layer-A **feasible**. Closing it required
resolving four offender sites (2 mechanical enum migrations + 2 dead-code
deletions), then committing the guard green. **No live parity bug existed** — the
two live offenders carried correct values; the two wrong-valued ones were dead.

## Outcomes

### Divergence class 5 (flag-hex) — ✅ LOCKED as Layer-A guard

- **Guard**: `tests/test_flag_hex_convention.py` — the **fourth** static
  bypass-guard, same `rglob → forbid-pattern → assert` shape as
  `test_rng_determinism` / `test_equipment_key_convention` /
  `test_attribute_convention`.
- **Pattern**: forbids `FLAGPREFIX_X = 0x…` (PLR_/OFF_/ASSIST_/COMM_/IMM_/…)
  outside the enum modules. **Sole legitimate hit**: `mud/wiznet.py`'s
  `WiznetFlag` enum body (the canonical chokepoint — allowlisted).
- **Recall validated** (Phase 3): the grep correctly does *not* flag the two
  past instances of this class — PARALLEL-005 (`0x0010`→ExtraFlag.EVIL) and
  ACT_TRAIN (`0x200`) — which now appear only as comments documenting their
  fixes, proving the query would have caught them when live.
- **Honest limit** (recorded in the roster row): locks "no flag-prefixed *hex*
  constant redefined outside the enum modules" — does **not** catch a
  *decimal*-literal bypass (`if act & 32768:`), indistinguishable from arithmetic.

### `HANDLER-DEAD-001` — `is_friend` dead duplicate, wrong assist bits — ✅ REMOVED

- **Python**: `mud/handler.py` `is_friend` (deleted).
- **ROM C**: `src/handler.c:50-93`; assist flags are letter macros
  `ASSIST_ALL = (P)` = bit 15, `ASSIST_PLAYERS = (S)` = bit 18.
- **Gap**: hardcoded `ASSIST_PLAYERS = 0x1` (bit 0), `ASSIST_ALL = 0x2` (bit 1),
  … bits 0–4 — **all wrong** vs canonical `OffFlag` bits 15–20. Dead (no callers;
  live mob-assist path is `mud/combat/assist.py`, which uses `OffFlag`).
- **Fix**: deleted; left a note citing the live path.

### `HANDLER-DEAD-002` — `check_immune` dead duplicate, wrong RIV bits — ✅ REMOVED

- **Python**: `mud/handler.py` `check_immune` (deleted).
- **ROM C**: `src/handler.c:213-304`; `IMM_MAGIC = (C)` = bit 2,
  `IMM_WEAPON = (D)` = bit 3.
- **Gap**: hardcoded `IMM_WEAPON = 0x1` (bit 0), `IMM_MAGIC = 0x2` (bit 1) —
  wrong vs canonical `DefenseBit.WEAPON = 1<<3` / `MAGIC = 1<<2`; only a
  WEAPON/MAGIC TODO stub. Dead (no callers; live RIV path is
  `mud/affects/saves.py::_check_immune`, tested by `test_saves_rom_parity.py`).
- **Fix**: deleted; left a note citing the live path.

### Live offenders migrated to canonical enums (no behavior change)

- `mud/commands/player_config.py`: `PLR_CANLOOT/NOSUMMON/NOFOLLOW` →
  `int(PlayerFlag.X)`. Values already correct (`CANLOOT = 1<<15 = 0x8000`, …).
- `mud/commands/remaining_rom.py`: `COMM_DEAF = 0x2` → `int(CommFlag.DEAF)` (the
  pattern the very next line already used for `COMM_QUIET`). Value already correct.

## Files Modified

- `mud/handler.py` — deleted dead `is_friend` + `check_immune` (notes left)
- `mud/commands/player_config.py` — PLR_* derive from `PlayerFlag`
- `mud/commands/remaining_rom.py` — `COMM_DEAF` derives from `CommFlag`
- `tests/test_flag_hex_convention.py` — **new** Layer-A bypass-guard
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 5 row → ✅ guarded; Layer-A 4/5; to-do item 3 closed
- `docs/parity/HANDLER_C_AUDIT.md` — HANDLER-DEAD-001/002 filed
- `CHANGELOG.md` — Added (guard) + Fixed (offender resolution) entries
- `pyproject.toml` — 2.12.75 → 2.12.76

## Test Status

- `tests/test_flag_hex_convention.py` — RED (4 offender sites) → GREEN after fixes.
- Targeted regression (combat/saves/resistance/affects/combat): **114 passed**.
- Full suite: **5356 passed, 4 skipped** in 201.91s — the +1 vs the 2.12.75
  baseline (5355) is the new guard test; **zero regressions**.
- `gitnexus_detect_changes`: **low risk, 0 affected processes** — confirms the
  deleted functions had no upstream callers (validates deadness).
- `ruff`: touched code lines clean; the two "would reformat" hits on
  player_config/remaining_rom are **pre-existing** docstring-whitespace / long-line
  drift, not from this session's edits (repo carries 1762 pre-existing ruff issues).

## Commits

- `568639b7` — `fix(parity): flag-hex class — drop dead wrong-bit handler dupes, route PLR_/COMM_DEAF through enums`
- `6ce23769` — `test(parity): lock flag-hex divergence class as Layer-A bypass-guard (2.12.76)`

## Addendum — class 6 (pointer-identity) probe → INV-034 filed (2.12.77)

Continued into the next Layer-A to-do, class 6 (pointer-identity), as a probe
("classify + grep, stop at the verdict if behavioral"). It went deeper than
flag-hex:

- **Verdict: Layer-A infeasible → reclassified A→C** (like async-delivery). A
  static bypass-guard can't work — `==`/`!=` can't be type-discriminated by
  line-grep (most `==` in the codebase is int/str/enum).
- **Discovery (not just classification):** the root cause is *live*.
  `Character`/`Object` are plain `@dataclass` (`eq=True`) → **value-based
  `__eq__`** (`Character.__eq__ is object.__eq__` → False; `__hash__` → None).
  The live spawn path sets `instance_id=None` (`obj_spawner.py:35`) and leaves
  `Character.id` default, so two freshly-spawned same-proto entities compare
  `==`-equal. **Empirically verified**: `spawn_object(v) == spawn_object(v)` is
  True; `a in [b]` is True for distinct a,b. This poisons ~91 production
  `obj in <list>` / `list.remove(obj)` / `.index(obj)` sites.
- **Recall oracle:** INV-031(c) had already fixed one site of this exact class
  (`is_same_group` → `is`, "the `==` version could silently produce wrong
  results if duplicate Character objects existed"). The sweep independently
  re-derived the class → recall confirmed, scope broadened.
- **Advisor caught an over-claim mid-probe:** my first empirical test used bare
  `Character(name='Alice')` constructors (both `id=0`) — that's *why* they were
  equal. The advisor flagged that `id`/`instance_id` are in the compare set and
  the real question is whether the *spawn path* assigns them. It doesn't
  (verified) — so the divergence genuinely manifests, not just in constructors.

### Artifacts (probe → file, NOT fix — per the probe-only mandate)

- `tests/test_inv034_pointer_identity_divergence.py` — **new**, strict-xfail
  demonstration (flips to xpass when the root fix lands).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — **INV-034** (Layer C, ⚠️ OPEN).
- `docs/parity/DIVERGENCE_CLASS_ROSTER.md` — class 6 row A→C; Layer C row 12;
  Layer-A "feasible ceiling" note; to-do items 4/5.
- `AGENTS.md` — new ROM Parity Rule "**Entity identity:** use `is`/`is not`,
  never `==`/`!=`" (method; status stays in INV-034 per roster guardrail 1).
- `CHANGELOG.md` — Added entry; `pyproject.toml` 2.12.76 → 2.12.77.

### Why not fixed this session

The root fix (`@dataclass(eq=False)`, restoring identity `==` + identity
`__hash__`) has ~91-site blast radius and must be gated on a sweep of tests
relying on value-equality (`grep -rn "assert .*(obj|char|victim|item).*==" tests/`).
That is a deliberate scoped session, not a probe tail — fixing it reactively is
the exact trap the probe-only mandate guards against.

## Next Steps

1. **Root-fix INV-034 (scoped session)** — convert `Character`/`Object` to
   identity equality (`@dataclass(eq=False)`), gated on
   `grep -rn "assert .*(obj|char|victim|item).*==" tests/` to find/repair
   value-equality reliance first. Promotes divergence class 6 to ✅ and flips the
   strict-xfail `test_inv034_*` to xpass. (The class-6 *probe* is done — see the
   addendum above; Layer A is now at its feasible ceiling, 4/4 feasible classes
   guarded.)
2. **Highest-ceiling (deliberate project):** `diff_harness` Hypothesis widening
   (`tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`) — the only
   enumeration-independent path to *unknown* divergences.
3. **Standing cross-INV candidate:** mob-trigger ordering
   (bribe/exit/fight/kill/hpcnt); INV tracker consolidation (26 rows, past the
   ~20 soft cap).
4. **Do NOT** mistake Layer-A completeness for parity — guardrail 3.

> **Push note:** 2.12.76 (`568639b7`, `6ce23769`) + this handoff are on local
> `master`, **not pushed** — on top of the unpushed 2.12.72–2.12.75 from prior
> sessions.
