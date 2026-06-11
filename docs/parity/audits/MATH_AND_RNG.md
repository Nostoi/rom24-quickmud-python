# META Audit: MATH_AND_RNG_CHANNEL (Class 8)

> **Parent**: `docs/parity/META_AUDIT_TAXONOMY.md` § Class 8.
> **Format template**: `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`.

## Scope

Two channels of ROM-parity-sensitive primitive divergence:

1. **RNG channel** — Python production code using `random.*` or
   `numpy.random.*` for behavior ROM C decides via its Mitchell-Moore RNG
   (`mud.math.rng_mm.number_*`). Any production-path hit is a ❌. Test
   scaffolding (`tests/`) is out of scope.

2. **Integer math channel** — Python code using `//` or `%` on signed
   integers where either operand can be negative, while the ROM C
   equivalent uses C's truncate-toward-zero `/` and `%`. Python's `//`
   floors toward negative infinity, so `-1 // 2 == -1` in Python but
   `-1 / 2 == 0` in C. Forbidden in combat/affect/damage paths unless
   both operands are guaranteed `>= 0`. The wrapper is
   `mud.math.c_compat.c_div` / `c_mod`.

Out of scope: pure-Python indexing/slicing `//`, percentage display, and
all `tests/` code.

## Method

```bash
grep -rn "import random\|from random" mud/ --include="*.py"
grep -rn " // \| % " mud/ --include="*.py"
```

For each hit, read the surrounding 10 lines, determine operand
signedness from context (`level`, `hp`, skill percentage, etc.), locate
the ROM C reference where applicable, and classify ✅/⚠️/❌. RNG channel
scan returned zero hits in `mud/` (clean). Integer math channel narrowed
to 32 hits in parity-sensitive subtrees (`mud/combat/`, `mud/skills/`,
`mud/magic/`, `mud/affects/`); the remaining ~118 hits across `mud/` are
in OLC, persistence, formatters, and loaders where operands are widths,
counts, or vnums (non-negative by construction) — catalogued en bloc
below.

## Findings

### RNG channel violations

| ID | Python site | ROM C reference | Severity | Status | Notes |
|----|-------------|-----------------|----------|--------|-------|
| — | (none) | — | — | ✅ CLEAN | `grep -rn "import random\|from random" mud/` returns zero hits. All production RNG flows through `mud.utils.rng_mm` (re-exported as `mud.math.rng_mm`). |

### Integer math channel violations

| ID | Python site | ROM C reference | Severity | Status | Notes |
|----|-------------|-----------------|----------|--------|-------|
| MATH-001 | `mud/combat/engine.py:1290` — now `dam += c_div(get_damroll(attacker) * min(100, skill_total), 100)` | `src/fight.c` one_hit damroll bonus: `dam += GET_DAMROLL(ch) * UMIN(100,skill) / 100;` | HIGH | ✅ FIXED (2.9.53) | Closed by `c_div` substitution. Regression pinned by `tests/integration/test_weapon_damage_damroll_c_div.py::test_damroll_uses_c_truncation_not_python_floor` — damroll=-1, skill=99 → product -99 → c_div = 0 (ROM), Python // gave -1. |
| MATH-002 | `mud/combat/engine.py` — `attacker.hit += c_div(dam, 2)` (vampiric weapon flag) | `src/fight.c` weapon_flag VAMPIRIC: heal half of damage | LOW | ✅ FIXED (2.13.86) | `dam` is non-negative (`rng_mm.number_range(1, ...)` lower bound 1). Swapped `dam // 2` → `c_div(dam, 2)` for hygiene and future PARITY008 lint compatibility. |
| MATH-003 | `mud/combat/engine.py` — `c_div(weapon_level, {2,4,5,6})` in weapon-flag effect dispatch | `src/fight.c` weapon flag handlers (VAMPIRIC / FLAMING / FROST / SHOCKING) | LOW | ✅ FIXED (2.13.86) | `weapon_level` is `obj.level` (`>= 0` by construction). All 7 `weapon_level //` sites swapped to `c_div` — vampiric×1, flaming×2, frost×2, shocking×2. No observable bug; hygiene parity with PARITY008 intent. |
| MATH-004 | `mud/skills/handlers.py` — `c_div(fail, {5,3,2})` in enchant_armor / enchant_weapon fizzle branches | `src/magic.c` enchant_armor / enchant_weapon fizzle thresholds | LOW | ✅ FIXED (2.13.86) | `fail` is a percentage in `[0, 100]`, non-negative. All 4 `fail //` sites swapped to `c_div`. No observable bug; hygiene. |
| MATH-005 | `mud/skills/handlers.py:1985` — `new_sex = (current_sex + 1) % 3` | `src/magic.c` change_sex spell | NONE | ✅ MATCH | `current_sex` is `int(Sex)` in `[0, 2]`. `%` on non-negative operands matches C exactly. No action. |
| MATH-006 | `mud/combat/engine.py:260` — `(40 + (5 * level)) // 2` (second-hit base chance) | `src/fight.c` second_attack | NONE | ✅ MATCH | `level >= 1`, so the numerator is `> 0`. Non-negative; `//` matches C `/`. No action. |
| MATH-007 | `mud/combat/engine.py:334, 350` — `second_attack_skill // 2`, `third_attack_skill // 4` | `src/fight.c` second/third attack | NONE | ✅ MATCH | Skill values in `[0, 100]`. Non-negative. No action. |
| MATH-008 | `mud/combat/engine.py:1034-1035` — `share = silver_reward // member_count; remainder = silver_reward % member_count` | `src/fight.c` group_gain silver split | NONE | ✅ MATCH | `silver_reward >= 0`, `member_count >= 1`. Non-negative. No action. |
| MATH-009 | `mud/combat/engine.py:1238-1276` — weapon damage scaling by `skill_total` (`* skill // 100`, `* level // 3`, `* 3 // 2`, etc.) | `src/fight.c` one_hit damage compute | NONE | ✅ MATCH | All operands are level/skill/dice — non-negative. The HIGH-severity gap is specifically at line 1290 where `get_damroll` admits negatives. The lines above stay clean. No action. |
| MATH-010 | `mud/skills/registry.py:343` — `learned // 2` (improve chance) | `src/skills.c` check_improve | NONE | ✅ MATCH | `learned` is a skill percentage in `[0, 100]`. Non-negative. No action. |
| MATH-011 | `mud/skills/handlers.py:6634` — `80 * skill_pct // 100` | `src/magic.c` success-rate scale | NONE | ✅ MATCH | `skill_pct` in `[0, 100]`. Non-negative. No action. |
| MATH-012 | `mud/magic/effects.py:101` — `chance += item_type_modifier;  // varies by effect type` | n/a | NONE | ✅ FALSE POSITIVE | `//` here is a Python end-of-line comment (the source line was hand-translated from ROM C and kept the `//` token). Not integer division. No action. |

### Acceptable use (catalogued, not gaps)

The remaining ~118 `//` / `%` hits across `mud/` (full grep returns 150
total, 32 in parity-sensitive subtrees above) fall into these buckets,
all of which are non-negative by construction and therefore safe:

- **Loaders** (`mud/loaders/`, `mud/spawning/`) — `//` on file offsets,
  vnum ranges, dice counts; operands always `>= 0`.
- **OLC** (`mud/commands/build.py`, `mud/olc/`) — `//` on widths,
  column counts for `string_grid` displays.
- **Persistence** (`mud/persistence.py`, `mud/db/`) — `//` on byte
  counts and array indexes during serialization.
- **Format helpers** (`mud/utils/format.py`, `mud/net/ansi.py`) — `//`
  on string lengths and ANSI column widths.
- **Time/tick math** (`mud/time.py`, `mud/game_loop.py`) — `//` on
  tick counts and hour-of-day; both `>= 0`.

Cataloguing each one would inflate this audit without surfacing
divergences. The proposed PARITY008 lint rule (below) would allowlist
these paths so the audit focuses on combat/skills/magic/affects.

## Summary

| Metric | Count |
|--------|-------|
| RNG channel candidates scanned | 0 (clean) |
| Integer math channel candidates scanned (parity-sensitive subtrees) | 32 |
| ❌ HIGH | 0 (MATH-001 closed 2.9.53) |
| ⚠️ LOW | 0 (MATH-002/003/004 closed 2.13.86) |
| ✅ MATCH / FALSE POSITIVE / FIXED | 11 (MATH-001 … MATH-012) |
| Acceptable use (out-of-subtree) | ~118 |

All findings are now closed. MATH-001 (HIGH — negative damroll truncation) was
fixed in 2.9.53. MATH-002/003/004 (LOW — hygiene swaps) were fixed in 2.13.86
by replacing `//` with `c_div` in `process_weapon_special_attacks` (weapon flag
damage/heal divisors) and `enchant_armor`/`enchant_weapon` (fizzle thresholds).
Operands were non-negative by construction in all three cases; the swaps make
the intent explicit and remove the only `//` smells the PARITY008 lint rule
would flag in parity-sensitive subtrees.

## Suggested ruff rule sketch

A custom flake8/ruff plugin rule **PARITY008** would catch these
mechanically:

```text
PARITY008  use-c_div-on-signed-ints
  Forbid `//` and `%` operators in parity-sensitive modules unless
  both operands are statically provable non-negative. Use
  `mud.math.c_compat.c_div` / `c_mod` instead.

  Allowlist (by path):
    - mud/loaders/**         # non-negative file/vnum math
    - mud/spawning/**        # vnum math
    - mud/olc/**             # column widths
    - mud/db/**              # byte counts
    - mud/persistence.py     # byte counts
    - mud/time.py            # tick counts
    - mud/utils/format.py    # string widths
    - mud/net/ansi.py        # column widths
    - mud/utils/rng_mm.py    # RNG internals; mirrors ROM C exactly

  Enforced paths:
    - mud/combat/**
    - mud/skills/**
    - mud/magic/**
    - mud/affects/**
    - mud/characters/**

  Per-line override: `# noqa: PARITY008  (reason)` with a required
  reason string citing the ROM C line where C-truncation either
  doesn't matter or is deliberately matched by `//`.
```

The same plugin should ship **PARITY009** for the RNG channel:

```text
PARITY009  use-rng_mm-not-random
  Forbid `import random`, `from random`, and `random.*` attribute
  access anywhere under `mud/` except `mud/utils/rng_mm.py`. Use
  `mud.utils.rng_mm.number_*` instead.

  Allowlist: tests/**
```

PARITY008 is the higher-value rule (1 real bug found, will catch
regressions). PARITY009 is preventative — currently clean, but cheap to
add and lock in.
