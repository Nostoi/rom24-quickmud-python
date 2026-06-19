# Session Status — 2026-06-19 — /loop gap-closer: WEAR-012 + LOOK-008 + LOOK-009

## Current State

- **Active focus**: Cross-file / divergence-class sweep, **Layer C** (per-file
  audit tracker exhausted). Differential harness (`tools/diff_harness/`) vs. the
  live ROM C oracle is the enumeration-independent finder. This `/loop`
  gap-closer session surfaced-and-closed 3 genuine divergences on the
  look/examine/wear surfaces.
- **Last completed** (this session, 4 commits incl. handoff, master, **not
  pushed**):
  - `25e1829c` v2.14.139 — **WEAR-012**: `wear all` equips lights/weapons/hold
    via a shared `_wear_obj(ch, obj, fReplace)` (FINDING-034).
  - `f748a821` v2.14.140 — **LOOK-008**: `look`/`examine` on an object shows the
    description XOR a keyword-matching extra-description, not both (FINDING-035).
  - `10327a59` v2.14.141 — **LOOK-009**: looking at a description-less character
    renders the objective pronoun ($M), not the name (FINDING-036). Also
    corrected a `pytest | tail` exit-masking flaw from gap 2 (see summary).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_WEAR012_LOOK008_LOOK009.md](SESSION_SUMMARY_2026-06-19_LOOP_GAPCLOSER_WEAR012_LOOK008_LOOK009.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.141 |
| Tests | 5852 passed, 4 skipped (full suite, exit verified directly) |
| ROM C files audited | 43 / 43 (P0/P1/P2 100%, P3 75% + 3 N/A) |
| Active focus | Cross-file invariants / divergence-class sweep (Layer C) |
| Open findings | none (FINDING-034/035/036 all RESOLVED this session) |

## Next Intended Task

The `/loop` (target 5 gaps) stopped at **3/5** by deliberate choice — genuine
harness-findable divergences on the probed surfaces (look/examine/wear/get/drop/
sacrifice/container/money) are largely closed; most new probes converge clean,
and guardrail 3 forbids manufacturing gaps. To resume hunting gaps 4–5, probe
**fresh, unexamined command surfaces** — `score`/`who`/`where`/`weather`/`time`,
social commands, combat/death output, group/follow messaging, `give`/`put`-to-mob
edge cases — with a throwaway C-oracle-vs-pyreplay probe per surface; close any
real divergence via `/rom-gap-closer`, file cross-file root causes as the next
INV-NNN. **Verification note (durable lesson): never read a `pytest | tail` exit
code as the result — capture pytest's exit directly.** 6 commits v2.14.139-141 on
master, not pushed; `git push` if sharing (versions/CHANGELOG current).
