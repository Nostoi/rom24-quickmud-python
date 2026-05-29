# Session Status — 2026-05-29 — affect_armor differential; FINDING-015 / MAGIC-002 (armor) resolved

## Current State

- **Active mode**: differential-harness-driven parity verification. A new
  `affect_armor` scenario joins `movement_get_drop`, `combat_melee_rounds`, and
  `spell_combat`; **all four converge end-to-end** and `KNOWN_DIVERGENCES` is empty
  (zero known divergences).
- **Last completed** (this session):
  - **Harness instrument fix** (diff-harness `d296b434`) — `pysnap._affect_names`
    read `aff.spell_name`/`aff.name`, but the real affect model (`AffectData`)
    stores the spell identity in `.type` (lowercase ROM skill name, or int SN). So
    `affects` was silently always `[]` on the Python side. Now reads `.type`,
    mapping int SNs through `ROM_SKILL_NAMES_BY_INDEX`. Locked by 2 unit tests.
  - **`affect_armor` scenario** (diff-harness `d296b434`) + committed golden — an
    L10 mage `__learn`s and self-casts `armor`. Surfaced FINDING-015.
  - **`FINDING-015` / `MAGIC-002`** ✅ FIXED (armor) (master 2.11.20, `a3476e33`) —
    ROM `spell_armor` (`src/magic.c:753`) sends "You feel someone protecting you."
    on success; the Python `armor` handler was silent (and `do_cast` is silent since
    FINDING-013), so the line was dropped. `armor` now mirrors ROM messaging.
    affects/eff_ac/mana all converged — only `output` diverged. The broader
    bless/shield/… sweep remains OPEN under MAGIC-002.
  - **`affect_armor` converged** (diff-harness `3a5a5379`) — master fix merged;
    replay clean; `KNOWN_DIVERGENCES` self-cleared.
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-05-29_AFFECT_ARMOR_FINDING_015.md](SESSION_SUMMARY_2026-05-29_AFFECT_ARMOR_FINDING_015.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.11.20 |
| Tests | 4957 passed, 4 skipped (full suite, parallel, ~98s) |
| Differential | 12 passed, 0 xfail — 4 scenarios converge end-to-end |
| ROM C files audited | 43 / 43 (per-file pass complete; differential + cross-file invariants active) |
| Active focus | differential scenarios — zero known divergences |

## Next Intended Task

The differential harness is back at zero known divergences across four scenarios.
The cheapest high-value next move is the **MAGIC-002 sweep**: port the ROM success
message for `bless` (`handlers.py:1465`), `shield` (`handlers.py:7094`), and the
other affect-only spells — each is a confirmed silent-on-success instance that
`do_cast` drops (the `affect_armor` pattern + `__learn` make per-spell verification
cheap). Alternatively:

1. **First flag-setting affect scenario** (sanctuary/haste/detect-invis) — surfaces
   the deferred `affect_flags` case-normalization (C lowercase vs Python
   `AffectFlag.<NAME>.name`) and probes the still-un-exercised `affect_flags`
   snapshot field.
2. **`SHOP-PET-002`** (`FIGHT_C_AUDIT.md`) — pet purchase should
   `create_mobile(pIndexData)` (fresh re-roll), not clone the kennel template. A
   concrete RNG-parity gap (breaks existing pet-shop gold assertions — needs care).
3. **Optional async project** (`FINDINGS.md` FINDING-014) — enforce wait-state at
   the Python input loop like ROM `comm.c`.

Also pending (test-infra, not a parity gap): seed RNG in the `test_combat_death.py`
unit death tests to kill the xdist ordering flake.
