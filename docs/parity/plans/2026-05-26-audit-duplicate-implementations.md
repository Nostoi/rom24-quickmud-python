# DUPLICATE_IMPLEMENTATIONS Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` — a complete, status-bucketed table of every same-name same-primitive duplicate `def` in `mud/`, with gap IDs assigned for ❌/⚠️ rows and a consolidation plan note per row.

**Architecture:** This is a doc-producing audit session, not a code change. The audit walks `mud/`, identifies parallel implementations of the same primitive (the failure mode that surfaced in 2.9.8 / 2.9.19 / 2.9.20), buckets them by divergence severity, and produces a markdown table. The audit's output is the input to a future *burn-down* session (separate plan) that closes ❌ rows by consolidation. No production code changes in this plan.

**Tech Stack:** bash (grep / awk / sort / uniq), Python read-only inspection, git.

**Scope boundary:** This plan produces the audit doc only. Closing the ❌/⚠️ rows is out of scope — each one becomes its own gap-closer commit under the existing `rom-gap-closer` skill in follow-up sessions. The plan also does NOT change production code; if a quick fix is obvious during analysis, it's recorded as a row, not applied.

**Spec reference:** `docs/parity/META_AUDIT_TAXONOMY.md` § Class 6: DUPLICATE_IMPLEMENTATIONS.

---

## File Structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` | Create | The audit deliverable (table + meta) |
| `docs/parity/audits/` | Create (directory) | Houses all class audits going forward |
| `docs/parity/META_AUDIT_TAXONOMY.md` | Modify | Flip queue row #6 from probe to measured; link the audit doc |
| `docs/sessions/SESSION_STATUS.md` | Modify | Reflect the new audit completion |
| `CHANGELOG.md` | Modify | `[Unreleased]` Added entry |

No production source touched. No tests added.

---

## Task 1: Discovery — enumerate every multi-def name in `mud/`

**Files:**
- Create: `docs/parity/audits/_workdir/dup-defs-raw.txt` (working file, deleted at end)

- [ ] **Step 1: Verify working directory and tooling**

```bash
test -d mud && command -v grep && command -v awk && command -v sort
```

Expected: exit 0, no output.

- [ ] **Step 2: Create the workdir**

```bash
mkdir -p docs/parity/audits/_workdir
```

Expected: silent success.

- [ ] **Step 3: Run the discovery grep**

```bash
grep -rn "^def " mud/ \
  | awk -F: '{print $1 ":" $2 ":" $3}' \
  | awk '{print $0, $NF}' \
  | sed 's/(.*//' \
  | awk '{name=$NF; sub(/^def /, "", name); print name, $1}' \
  | sort -k1,1 \
  > docs/parity/audits/_workdir/dup-defs-raw.txt
```

Expected: file created. Inspect first 20 lines:

```bash
head -20 docs/parity/audits/_workdir/dup-defs-raw.txt
```

Expected: lines of the form `name path:line:colno`.

- [ ] **Step 4: Filter to names with >1 occurrence**

```bash
awk '{print $1}' docs/parity/audits/_workdir/dup-defs-raw.txt \
  | sort | uniq -c | awk '$1 > 1 {print $2}' \
  > docs/parity/audits/_workdir/dup-names.txt
wc -l docs/parity/audits/_workdir/dup-names.txt
```

Expected: a count between ~50 and ~300 (includes a lot of dunder methods that we'll filter next).

- [ ] **Step 5: Snapshot the raw set**

```bash
cat docs/parity/audits/_workdir/dup-names.txt
```

Expected: alphabetized list of names. Eyeball for sanity — should include `add_follower`, `stop_follower`, `is_same_group` (the known cases) plus many dunder noise.

---

## Task 2: Filter — drop dunders, generic helpers, and unrelated overloads

**Files:**
- Modify: `docs/parity/audits/_workdir/dup-names.txt` (filtered in place)

- [ ] **Step 1: Drop dunder methods**

```bash
grep -v "^__" docs/parity/audits/_workdir/dup-names.txt \
  > docs/parity/audits/_workdir/dup-names-stage1.txt
wc -l docs/parity/audits/_workdir/dup-names-stage1.txt
```

Expected: count drops significantly (likely 30–70% reduction).

- [ ] **Step 2: Drop common generic helper names that are commonly overloaded per-module on purpose**

The exclusion list: `__init__`, `__repr__`, `__str__`, `__eq__`, `__hash__`, `__iter__`, `__len__`, `__post_init__`, `to_dict`, `from_dict`, `validate`, `serialize`, `deserialize`, `setup`, `teardown`, `_setup`, `_teardown`, `process`.

```bash
grep -vE "^(to_dict|from_dict|validate|serialize|deserialize|setup|teardown|_setup|_teardown|process)$" \
  docs/parity/audits/_workdir/dup-names-stage1.txt \
  > docs/parity/audits/_workdir/dup-names-stage2.txt
wc -l docs/parity/audits/_workdir/dup-names-stage2.txt
```

Expected: count drops further. Note: if a per-module `to_dict` actually IS a parity-sensitive primitive (unlikely), it can be re-added in Task 3 manual review.

- [ ] **Step 3: Review the survivors manually**

```bash
cat docs/parity/audits/_workdir/dup-names-stage2.txt
```

Inspect: the list should be small enough (target: 10–30 names) to skim. For each name that is *obviously* not a parity-sensitive primitive (e.g. `_helper`, `_format_x` that's name-shadowed across utilities), drop it. Add a one-line note per dropped name to a scratch file:

```bash
touch docs/parity/audits/_workdir/dropped-reasons.txt
```

Then manually edit `dup-names-stage2.txt` to remove rows, and for each removed row, append a line to `dropped-reasons.txt`:

```
<name>: <one-sentence reason>
```

Expected output: `dup-names-stage2.txt` reduced to the genuine-candidate set; `dropped-reasons.txt` documenting every drop.

- [ ] **Step 4: Sanity check — known cases must survive**

```bash
grep -E "^(add_follower|stop_follower|is_same_group|affect_remove)$" docs/parity/audits/_workdir/dup-names-stage2.txt
```

Expected: all four names present. If any are missing, the filter is too aggressive — go back to Step 2 and revise. (`affect_remove` may be absent if it was fully removed in 2.9.8; if so, document in dropped-reasons.txt.)

---

## Task 3: Per-candidate analysis

**Files:**
- Create: `docs/parity/audits/_workdir/per-candidate-notes.md` (working notes, folded into the final doc)

For each name in `dup-names-stage2.txt`, gather the following data points. This task has many sub-steps; do one candidate end-to-end before moving to the next.

- [ ] **Step 1: For each candidate, list every `def` site**

For a candidate `NAME`, run:

```bash
NAME=add_follower  # example
grep -rn "^def $NAME" mud/
```

Expected: 2+ lines like `mud/X.py:NN:def add_follower(...):`.

- [ ] **Step 2: Identify which copy the dispatcher / high-traffic call sites use**

```bash
grep -rn "from .*import.*$NAME\|from .*import.*\\bNAME\\b" mud/commands/dispatcher.py mud/handler.py mud/world/ mud/combat/ 2>/dev/null
```

Also check the command dispatcher's command-registration block:

```bash
grep -n "$NAME\|Command(" mud/commands/dispatcher.py | head -20
```

Record which file's copy reaches production code paths.

- [ ] **Step 3: Diff the copies**

For two sites `mud/A.py:NA` and `mud/B.py:NB`, view both function bodies (use Read tool or `sed -n 'NA,/^def\|^class/p' mud/A.py | head -50`). Note:

- Are they byte-identical?
- Same args / same return type?
- Same broadcasts?
- Same error handling?
- Same edge-case behavior (e.g. `add_follower` no-op when `master == follower` vs `add_follower` bug-and-return)?

- [ ] **Step 4: Classify divergence severity**

Bucket per the spec's rubric:

- **✅ MATCH** — copies byte-identical, or one delegates to the other.
- **⚠️ PARTIAL** — copies agree on happy path; differ on at least one error / edge branch.
- **❌ MISSING** — copies diverge meaningfully on a parity-sensitive path (broadcasts, gates, state mutations).

- [ ] **Step 5: Record findings**

Append to `docs/parity/audits/_workdir/per-candidate-notes.md` a block:

```markdown
### NAME

- Sites: `mud/A.py:NA`, `mud/B.py:NB`
- Dispatcher-wired: B (via `mud/commands/dispatcher.py:LINE`)
- Divergence: <one-paragraph summary, mention ROM contract if known>
- Status: ❌ MISSING
- Gap ID: DUPL-001 (assigned next)
- Consolidation plan: <one or two sentences>
```

Repeat for every candidate. Numbering: DUPL-001, DUPL-002, ... in order.

- [ ] **Step 6: Cross-check known cases against existing fixes**

For `add_follower` / `stop_follower` / `is_same_group`, the 2.9.19 / 2.9.20 commits added broadcasts to the silent (dispatcher-wired) copies. Verify in your notes:

- Status should be ⚠️ PARTIAL (now), not ❌ — the broadcasts match, but two parallel implementations still exist, which is the consolidation deferral.
- Consolidation plan: "Remove duplicate from `mud/commands/group_commands.py`; route `do_follow` / `do_group` through `mud/characters/follow.py`."

---

## Task 4: Write the audit doc

**Files:**
- Create: `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`

- [ ] **Step 1: Draft the doc header and table schema**

Create `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` with this exact opening:

```markdown
# DUPLICATE_IMPLEMENTATIONS Audit

> **Parent**: `docs/parity/META_AUDIT_TAXONOMY.md` § Class 6.

**Status**: complete as of YYYY-MM-DD. N rows, M ❌, K ⚠️, R ✅.

## Rubric

Each row in the table represents a same-name same-primitive `def`
that exists at 2+ file:line sites under `mud/`. Status:

- **✅ MATCH** — copies are byte-identical or one delegates to the other.
- **⚠️ PARTIAL** — copies agree on happy path; differ on at least one error / edge branch.
- **❌ MISSING** — copies diverge meaningfully on a parity-sensitive path.

Gap IDs use the form `DUPL-NNN` and feed the burn-down plan
(`docs/parity/plans/<date>-burn-down-duplicate-implementations.md`,
authored when this audit completes).

## Table

| # | Primitive | Sites | Dispatcher-wired? | Divergence summary | Status | Gap ID | Consolidation plan |
|---|-----------|-------|-------------------|--------------------|--------|--------|--------------------|
```

Replace `N`, `M`, `K`, `R`, and `YYYY-MM-DD` with actual values after Task 5.

- [ ] **Step 2: Populate the table from `per-candidate-notes.md`**

For each candidate block in `per-candidate-notes.md`, append one row to the table:

```markdown
| 1 | `add_follower` | `mud/characters/follow.py:23`, `mud/commands/group_commands.py:14` | group_commands.py | Both now emit broadcasts (2.9.19), but two implementations persist. Risk: future drift. | ⚠️ PARTIAL | DUPL-001 | Delete group_commands copy; route do_follow through follow.py. |
```

Repeat for every candidate. Keep ordering: ❌ first (highest priority), then ⚠️, then ✅.

- [ ] **Step 3: Append meta sections**

After the table:

```markdown
## Methodology

1. Discovery: `grep -rn "^def " mud/`, name-bucket, filter to >1 occurrence.
2. Filter: drop dunders, generic helpers (see workdir/dropped-reasons.txt).
3. Per-candidate: locate `def` sites, identify dispatcher-wired copy, diff bodies, classify.
4. Bucket: ✅ / ⚠️ / ❌.
5. Assign DUPL-NNN gap IDs in failure-severity order.

## Drops (not audited)

The following multi-def names were filtered as not parity-sensitive
or expected-to-be-overloaded:

<paste contents of dropped-reasons.txt here>

## Open follow-ups

- Burn-down plan: `docs/parity/plans/<date>-burn-down-duplicate-implementations.md` (to be authored).
- Re-scan cadence: re-run discovery after every major refactor session under `mud/`.
```

- [ ] **Step 4: Update the status line at the top**

Count rows, count statuses, set `N`, `M`, `K`, `R`, and today's date.

- [ ] **Step 5: Read the doc end-to-end**

Verify: every row has a status; every ❌/⚠️ has a gap ID; the consolidation-plan column is populated. Fix any gaps inline.

---

## Task 5: Update parent docs

**Files:**
- Modify: `docs/parity/META_AUDIT_TAXONOMY.md`
- Modify: `docs/sessions/SESSION_STATUS.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Flip the queue row in `META_AUDIT_TAXONOMY.md`**

In the TL;DR queue, change row #6's "Suspected density" cell:

From: `~5–15 duplicates *(probe)*`
To: `<actual count> duplicates, <M> ❌, <K> ⚠️, <R> ✅ *(measured)*`

And change the "Next-session deliverable" cell:

From: `audits/DUPLICATE_IMPLEMENTATIONS.md (5–15 rows)`
To: `audits/DUPLICATE_IMPLEMENTATIONS.md ✅ (linked) — N rows`

Add a citation in Class 6's detail section, after the "Deliverable" line:

```markdown
**Status**: ✅ AUDITED YYYY-MM-DD — see `audits/DUPLICATE_IMPLEMENTATIONS.md`.
```

- [ ] **Step 2: Update `SESSION_STATUS.md`**

Overwrite with the current state. Use the existing format (see prior `SESSION_STATUS.md` for shape). Required sections:

- Current state: "DUPLICATE_IMPLEMENTATIONS audit complete; <N> rows, <M> ❌ to burn down."
- Project Status snapshot (version unchanged; tests unchanged; audit-tracker columns updated).
- Next intended task: "Author burn-down plan for DUPLICATE_IMPLEMENTATIONS or run next audit (BROADCAST_COVERAGE / ARITHMETIC_BOUNDARY)."

- [ ] **Step 3: Update `CHANGELOG.md`**

Under `## [Unreleased]`, add:

```markdown
### Added
- `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` — first class audit
  under the META_AUDIT_TAXONOMY plan. N rows enumerating same-name
  same-primitive duplicate defs in `mud/`. M ❌, K ⚠️, R ✅. Burn-down
  plan to follow.
```

Replace `N`, `M`, `K`, `R` with actual values.

---

## Task 6: Clean up and commit

**Files:**
- Delete: `docs/parity/audits/_workdir/` (working directory)
- Commit: all changes from Tasks 4 and 5

- [ ] **Step 1: Remove the workdir**

```bash
rm -rf docs/parity/audits/_workdir
ls docs/parity/audits/
```

Expected: only `DUPLICATE_IMPLEMENTATIONS.md` in `docs/parity/audits/`.

- [ ] **Step 2: Verify git status**

```bash
git status
```

Expected: modified `docs/parity/META_AUDIT_TAXONOMY.md`, `docs/sessions/SESSION_STATUS.md`, `CHANGELOG.md`; new `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`. No production source touched.

- [ ] **Step 3: Stage and commit**

```bash
git add docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md \
        docs/parity/META_AUDIT_TAXONOMY.md \
        docs/sessions/SESSION_STATUS.md \
        CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(parity): audit DUPLICATE_IMPLEMENTATIONS — N rows, M open

First audit under the META_AUDIT_TAXONOMY plan. Enumerates every
same-name same-primitive duplicate def in mud/. Status bucketed:
M ❌ MISSING, K ⚠️ PARTIAL, R ✅ MATCH.

Burn-down plan follows in a separate session.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Replace `N`, `M`, `K`, `R` with actual values before running.

- [ ] **Step 4: Do NOT push automatically**

Per project standing instruction: pushes require explicit per-cluster user approval. Surface the commit hash to the user and ask.

---

## Task 7: Surface result and decide next step

- [ ] **Step 1: Report to user**

Plain-text summary, ~3 sentences:
- Audit complete; N rows total; M ❌, K ⚠️, R ✅.
- Highlight: the 3 most surprising / highest-severity rows.
- Ask: (a) push the doc commit, (b) author burn-down plan for this class now or defer, (c) move to next audit class (BROADCAST_COVERAGE or ARITHMETIC_BOUNDARY).

Do not auto-proceed. Wait for direction.

---

## Acceptance criteria (whole plan)

The plan is complete when:

1. `docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md` exists and is committed.
2. Every row in its table has: primitive name, sites (file:line for each), dispatcher-wired column populated, divergence summary, status (✅/⚠️/❌), gap ID (for ❌/⚠️), consolidation plan note.
3. `META_AUDIT_TAXONOMY.md` queue row #6 reflects measured numbers.
4. `SESSION_STATUS.md` points at the new audit.
5. `CHANGELOG.md` has an `[Unreleased]` entry.
6. The `_workdir/` directory is removed.
7. Known cases (`add_follower`, `stop_follower`, `is_same_group`) are present in the table with correct status (⚠️ PARTIAL with consolidation plan referencing `mud/characters/follow.py`).
8. No production source under `mud/` is modified.
9. No test file under `tests/` is added or modified.
10. The commit is local-only; pushing waits for user authorization.
