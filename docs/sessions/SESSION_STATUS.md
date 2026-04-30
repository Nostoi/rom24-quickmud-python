# Session Status — 2026-04-29 — `olc_act.c` MINORs closed + `olc_save.c` audit filed

## Current State

- **Active audit**: `olc_save.c` (Phase 1–3 filed; Phase 4 closures
  pending, starting with the OLC_SAVE-001..008 round-trip data-loss block)
- **Last completed**: OLC_ACT-013/014 (both MINOR structural gaps
  closed); `olc_save.c` audit doc filed with stable gap IDs
  OLC_SAVE-001..020
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-04-29_OLC_ACT_FINAL_AND_OLC_SAVE_AUDIT.md](SESSION_SUMMARY_2026-04-29_OLC_ACT_FINAL_AND_OLC_SAVE_AUDIT.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.87 |
| OLC integration tests | 158 passing (9 new this session: 3 OLC_ACT-013, 6 OLC_ACT-014) |
| ROM C files audited | ~22 / 43 (`olc_act.c` ⚠️ Partial, TIER A/B 100% closed; `olc_save.c` ⚠️ Partial, Phase 1–3 filed) |
| Active focus | `olc_save.c` — Phase 4 closures begin with OLC_SAVE-001..008 |

## Next Intended Task

Begin `olc_save.c` Phase 4 closures, **CRITICAL block first**
(OLC_SAVE-001..008 — round-trip data loss). Recommended starting gap:
**OLC_SAVE-001** (mob `off_flags`/`imm_flags`/`res_flags`/`vuln_flags`
not persisted on JSON save). Use `rom-gap-closer` per gap. Each closure
must include a round-trip integration test (load .are → save JSON →
load JSON → assert proto equals original) and may include a paired
change in `mud/loaders/json_loader.py` to read the new field back —
both sides land in one commit per the audit's locked closure rule.

Alternative paths:
- **OLC_SAVE-009..013** (IMPORTANT) if the loader-side data-model work
  for OLC_SAVE-001..008 turns out blocking.
- **`olc_mpcode.c` audit** — the last unaudited OLC editor file
  (~300 lines), would close out the OLC editor cluster's audit phase.

`olc_act.c` cannot flip to ✅ AUDITED until the ~78 TIER C functions
receive a deep-audit pass and the three OLC_ACT-010 sub-gaps
(10b/c/d — dice/AC byte format, shop/mprogs/spec_fun rendering, mob
flag-table names) are addressed. Those depend on data-model alignment;
defer until in scope.

## Subagent reliability note

Sonnet subagents continue to terminate mid-investigation in this
codebase (now four sessions reproduced). For multi-step parity work
(audits, multi-step closures), prefer inline execution. Haiku subagents
remain reliable for small string-drift / single-keyword gap closures.
The `olc_save.c` audit was run inline per the session brief.
