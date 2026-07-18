# Session Status — 2026-07-18 — Autonomous loop (OLC setters + combat recall-oracle)

## Current State

- **9 genuine iterations complete** (user asked for a 15-session loop; paced for
  quality over count per the advisor — "iterations, not padded commits"). 5
  parity closures + 1 test fixup + 4 verified clean probes. Full retrospective:
  [SESSION_SUMMARY_2026-07-18_AUTONOMOUS_LOOP_OLC_FIGHT.md](SESSION_SUMMARY_2026-07-18_AUTONOMOUS_LOOP_OLC_FIGHT.md)
- **Highest-value find:** FIGHT-104 (recall-oracle) — invisible attacker's
  inviso-strip ran AFTER parry/dodge in `apply_damage`; ROM strips it BEFORE
  (`src/fight.c:763` before `:790`), so a parried/dodged attacker still fades.
  Was hidden behind an incorrect FIGHT-092 comment.
- **Active focus** (unchanged): cross-file invariants / divergence-class probe
  mode, plus the un-audited OLC per-field setter vein (redit/oedit/medit now
  swept; aedit next).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.336 |
| Tests | **6258 passed, 4 skipped, 0 failed** (159s parallel) |
| ROM C files audited | 43 / 43 |
| Differential harness | 102/102 across 69 scenarios; diffshim C binary builds clean (re-verified 2026-07-18) |
| Push status | **Local only — operator review still pending**: prior ~19 commits + this session's 6 (`3eb836fc`…`1d1cce52`). Do NOT push without operator sign-off. |
| Active focus | Cross-file invariants / divergence-class + OLC setter sweep |

## Next Intended Task — concrete queue for iterations 10-15

1. **OLC_ACT-019 — aedit setters** (`aedit_security`/`aedit_vnum`/`aedit_lvnum`/
   `aedit_builder`, ⚠️ PARTIAL). Verify each vs `src/olc_act.c:825-978` first;
   likely the same value-leak/placeholder/guard class as OLC_ACT-015..018.
2. **Remaining oedit/redit inline setters** (oedit type/short, redit_clan/format/
   owner). Skip the `string_append`-dependent ones (redit_desc/oedit_long).
3. **FIGHT-098 dedicated C-oracle scenario** (diffshim binary builds; needs an
   OFF_AREA_ATTACK mob directive + fled-still-fighting char — multi-commit
   harness extension).
4. **Recall-oracle on non-combat surfaces** — affect ticks (char_update affect
   expiry / "wears off" ordering), message delivery (INV-001). The combat
   `damage()` pipeline is now swept clean (iterations 4/6/8/9) — pivot away.

## Outstanding — deferred by design (unchanged)

- **DESC-001** — OPEN by design (latent, unreachable in ROM's input range).
- **OLC spell-name lookup** — gated on a skill-by-index registry.
- **OLC_ACT-010b** — medit dice/AC stored as strings pending model split.
- **DB2-004/005** — theoretical multi-line `fread` (canonical areas never hit).
