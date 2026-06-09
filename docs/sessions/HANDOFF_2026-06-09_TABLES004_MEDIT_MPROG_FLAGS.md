# Handoff — 2026-06-09 — TABLES-004 MEdit mobprog flags

Read first:

1. `docs/sessions/SESSION_STATUS.md`
2. `docs/sessions/SESSION_SUMMARY_2026-06-09_TABLES004_MEDIT_MPROG_FLAGS.md`
3. `docs/parity/DIVERGENCE_CLASS_ROSTER.md`

What just landed:

- `TABLES-004` fixed OLC MEdit `addmprog` trigger values. The local builder
  trigger table now derives all 16 ROM `mprog_flags[]` values from
  `mud.mobprog.Trigger`, so builder-created mobprogs set the same bits runtime
  movement/greet/act checks read.
- Full suite result: `PYTHONPATH=. pytest -q` — 5466 passed, 5 skipped.
- Lint result: `ruff check .` — clean.
- GitNexus change detection: low risk, no affected execution flows.

Recommended next task:

Continue Class 11 / dynamic differential widening. A good next probe is to take
an OLC-created mobprog through a runtime trigger path now that builder
`mprog_flags` values are aligned, or pick another deterministic non-combat
lifecycle contract from ROM source before editing.
