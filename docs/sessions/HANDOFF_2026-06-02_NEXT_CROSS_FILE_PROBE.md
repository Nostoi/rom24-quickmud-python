# Handoff — 2026-06-02 → next agent — cross-file probe continuation

This session is **complete and fully pushed** (`origin/master` @ `5f3aed4d`,
2.12.82). Nothing is mid-stream — this handoff exists to point you at the next
pass, not to resume unfinished work.

## Where we are (read these first)

1. `docs/sessions/SESSION_STATUS.md` — canonical current-state pointer (already
   refreshed to 2.12.82).
2. `docs/sessions/SESSION_SUMMARY_2026-06-02_MOVE005_EXIT_TRIGGER_ORDERING.md`
   — full narrative of this session (MOVE-005 + MOVE-006).

## What just landed (all pushed)

| Gap | What | Version | Commit |
|-----|------|---------|--------|
| **MOVE-005** | mob `TRIG_EXIT` now fires **first** in `move_char` (before exit-existence/encumbrance gates), matching ROM `src/act_move.c:78-82`. Cross-file ordering miss the per-file audit had marked ✅ PARITY by checking *called* not *order*. | 2.12.81 | `8681630c` |
| **MOVE-006** | Removed the non-ROM `"You are too encumbered to move."` movement gate. ROM has **no** carry-weight movement gate anywhere in `src/`; caps are enforced at *pickup* time (`do_get`). Kept all carry-cap machinery; corrected 5 tests. User-confirmed behavior change. | 2.12.82 | `0c890d57` |

- Full suite: **5364 passed, 4 skipped**. `ruff` clean on edited lines.
- `docs/parity/ACT_MOVE_C_AUDIT.md`: MOVE-005 & MOVE-006 rows are ✅ FIXED;
  line-by-line items 2 & 3 corrected.

## Active mode

Cross-file invariants via **probe-then-scope** (the per-file audit tracker has no
⚠️/❌ rows — all 43 files at 100%). Method: pick a candidate contract → read ROM C
→ read Python equivalent → write one failing test → close as a single gap or file
as the next free INV-NNN. See AGENTS.md "Cross-File Invariants".

## Next intended task — pick one

1. **Mob-trigger ordering is now exhausted** — do NOT re-probe it. Status:
   FIGHT/HPCNT (INV-026), ACT (INV-025), KILL/DEATH (combat engine) enforced;
   EXIT closed (MOVE-005); BRIBE/GIVE verified at call-site ordering. The only
   untouched trigger family is **`TRIG_RANDOM` / `TRIG_DELAY`** (`src/update.c:452-458`,
   fired from the area/mobile update loop) — a fresh probe candidate.
2. **Position-transition edges** — ROM `update_pos` / `stop_fighting` /
   `raw_kill` ordering vs the Python equivalents (a standing candidate; some of
   this is covered by PROMPT-CLAMP INV but the full transition table is not).
3. **Highest-ceiling (deliberate multi-day):** `diff_harness` Hypothesis
   widening — `tools/diff_harness/PROPOSAL_HYPOTHESIS_WIDENING.md`. The only
   *enumeration-independent* path to unknown divergences (the roster + INV
   trackers are enumeration-dependent — "close on the known surface" ≠ "close to
   parity").
4. **Housekeeping:** INV tracker consolidation — `CROSS_FILE_INVARIANTS_TRACKER.md`
   is at 27 rows, past the ~20 soft cap AGENTS.md sets.

## Watch-outs (learned this session)

- **Per-file ✅ PARITY rows can be false on *ordering*.** MOVE-005 was marked
  PARITY because the trigger was *called*; the bug was *when*. When a probe
  touches a cross-module call, check call-**order**, not just call-presence.
- **Re-verify ✅/citation claims against ROM source before relaying them.**
  MOVE-006's tests cited `act_move.c:204` to look ROM-backed; :204 is the
  arrival broadcast and the actual gate was uncited. (My own first-draft summary
  mis-framed this and was corrected via an advisor recall check — the lesson is
  durable in AGENTS.md's "re-verify ✅" rule.)
- **Removing a feature with a parity-claiming test is a user decision.** MOVE-006
  was surfaced via `AskUserQuestion` before deletion because it changed
  player-facing behavior. Do the same for any divergence whose fix removes
  gameplay behavior that existing tests assert.

## Repo state

- `origin/master` @ `5f3aed4d` (2.12.82) — clean working tree, nothing unpushed.
- GitNexus index current as of `0c890d57` (the last code commit; the trailing
  doc-only commits change no symbols).
