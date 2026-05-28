# Session Status — 2026-05-28 — harness soundness reconciled + MOVE-003 / LOOK-004 (harness's 2nd & 3rd catches)

## Current State

- **Active mode**: differential-harness-driven parity verification. The harness
  was made **sound** (start-state + output-capture fairness), and the now-trustworthy
  diffs caught two real ROM parity bugs in files the per-file audit had marked
  "100% parity" — both fixed on `master` and merged back to clear the differential.
- **Loop demonstrated a 2nd time (end-to-end):** harness made sound → caught
  FINDING-003/004 → fixed on `master` (MOVE-003, LOOK-004) → pushed → merged into
  `diff-harness` → re-ran → **`movement_get_drop` diff matches the C reference
  exactly**, xfail removed.
- **Last completed**:
  - **Harness soundness** (branch `diff-harness`, `67eb0609`) — 4 comparison-fairness
    asymmetries reconciled (FINDING-002 hp/level, snapshot people-key, output
    channel). Golden recaptured. Harness-only; no `mud/`/`src/` edits.
  - **`MOVE-003`** ✅ FIXED (master 2.10.4, `ab8f9bd9`) — directional movement
    returns the destination room view (ROM `act_move.c:204` do_look "auto"), not a
    non-ROM "You walk <dir> to <room>." line. ~25 assertions across 14 files
    re-asserted ROM-faithfully.
  - **`LOOK-004`** ✅ FIXED (master 2.10.5, `2e5ebf3f`) — room object listing shows
    the ROM ground `description` (ROM `format_obj_to_char` fShort=FALSE), skipping
    description-less objects, not `short_descr`.
  - **Loop closure** (branch `diff-harness`, `91608b0f`) — merged master, removed
    the `KNOWN_DIVERGENCES` xfail, marked FINDING-003/004 RESOLVED.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-28_HARNESS_SOUNDNESS_AND_MOVE_LOOK_FIXES.md](SESSION_SUMMARY_2026-05-28_HARNESS_SOUNDNESS_AND_MOVE_LOOK_FIXES.md)
  (predecessor:
  [SESSION_SUMMARY_2026-05-28_LOOK_GAPS_AND_CHECKER_OPT_IN.md](SESSION_SUMMARY_2026-05-28_LOOK_GAPS_AND_CHECKER_OPT_IN.md))

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version (master) | **2.10.5** (branch `diff-harness`: 2.11.0, unmerged) |
| Tests (master) | **4915 passed, 4 skipped, 0 failed** (full suite, post-MOVE-003/LOOK-004). |
| ROM C files audited | 40 / 43 ✅ (3 N/A). `act_move.c` `move_char` + `act_info.c` `format_obj_to_char` rows corrected from false "100% parity" to MOVE-003 / LOOK-004 FIXED. |
| Differential harness | **Sound** (start-state + output-capture fairness reconciled). `movement_get_drop` diff matches the C reference exactly; xfail cleared. Has now caught **4 issues** (FINDING-001→004); all resolved. v1 on `diff-harness`, unmerged. |
| Branch | `master` — pushed to `origin` (`2e5ebf3f`), in sync, +MOVE-003/LOOK-004. `diff-harness` — local-only (`91608b0f`), master merged in, **1 open soundness follow-up** (`.are`/JSON input-source asymmetry). |

## Next Intended Task

1. **Reconcile the harness input-source asymmetry** (the last soundness item
   before `diff-harness` can merge): the C side reads `.are` files (repaired
   midgaard overlay), the Python side reads `data/areas/*.json`. Regenerate the
   JSON from the repaired `.are`, repair the malformed `area/midgaard.are`, or
   point both engines at the same data. See `tools/diff_harness/FINDINGS.md`.
2. **Extend the harness** — combat/RNG scenario slice (OLD_RAND bit-match already
   in place), generated scenarios; each as its own spec→plan.
3. **`format_obj_to_char` aura/stat prefixes** — latent gap surfaced alongside
   LOOK-004 (`(Glowing)`/`(Humming)`/`(Invis)`/detect auras on room object lines).
   Its own gap-closer.
4. **Merge `diff-harness` to master** once #1 is closed and the harness is extended.
5. **INV-025 non-combat narration sweep** — still open from earlier.
6. **GitNexus** — on-disk graph stale (`2272b2e`), MCP DB read-only all session;
   re-run `npx gitnexus analyze --skip-agents-md` once the lock clears.
