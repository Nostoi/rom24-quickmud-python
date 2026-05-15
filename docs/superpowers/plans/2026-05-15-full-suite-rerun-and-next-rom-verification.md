# Full Suite Rerun And Next ROM Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the full suite after the `NANNY-010` reconnect closure, then choose and execute the next ROM-source-first verification target based on concrete evidence instead of stale tracker text.

**Architecture:** This plan treats the full-suite rerun as the gate. If the rerun fails, the first failure becomes the next task and is traced directly to ROM C before any fix. If the rerun passes, the next task is a bounded fresh ROM verification pass selected from still-risky surfaces that are not clearly covered by the current tracker narrative.

**Tech Stack:** Python 3.12, pytest, ROM C reference in `src/`, parity audits in `docs/parity/`, session tracking in `docs/sessions/`.

---

### Task 1: Re-run the full suite as the validation gate

**Files:**
- Modify: `docs/sessions/SESSION_STATUS.md`
- Test: full suite via `./venv/bin/python -m pytest -q --maxfail=1`

- [ ] **Step 1: Run the full suite fail-fast**

Run:
```bash
./venv/bin/python -m pytest -q --maxfail=1
```

Expected:
- If green: suite completes with `passed/skipped` summary
- If red: stop on first failure and capture exact failing test path and assertion

- [ ] **Step 2: Record the result in session status scratch notes**

Document in `docs/sessions/SESSION_STATUS.md`:
- command run
- pass/fail result
- if failed, exact first failing test
- whether the next task is regression triage or fresh verification

- [ ] **Step 3: Do not broaden scope before classifying the result**

Classification rule:
- full suite fails → next task is the first failing test only
- full suite passes → next task is a new ROM verification slice only

- [ ] **Step 4: Commit checkpoint if code changed during rerun triage**

```bash
git add <touched-files>
git commit -m "test: recertify full suite after nanny reconnect sweep"
```

If no code or docs changed yet, skip commit.

### Task 2: Select the next ROM verification target from evidence

**Files:**
- Read: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Read: `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`
- Read: the selected ROM source file under `src/`
- Modify: `docs/sessions/SESSION_STATUS.md`

- [ ] **Step 1: If the suite failed, bind the next target to that failure**

Selection rule:
- failing test file becomes the verification surface
- corresponding ROM file is identified before any code change
- no alternate target is allowed until the failure is explained

Example command pattern:
```bash
rg -n "<failing symbol>|<failing command>|<failing behavior>" src/ mud/ tests/
```

Expected:
- exact ROM function path
- exact Python implementation path
- exact regression test path

- [ ] **Step 2: If the suite passed, choose one bounded fresh verification slice**

Selection priority:
1. a cross-file invariant with weaker confidence than current code warrants
2. a deferred architectural note with user-visible behavior at the edge
3. a combat or networking-adjacent flow where Python architecture may still hide drift

Primary candidate order for this repo:
```text
1. docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md
2. src/comm.c descriptor and reconnect-adjacent behavior not already locked by tests
3. src/fight.c sequencing edges not covered by current parity slices
```

Expected output:
- one target only
- why it was chosen
- which ROM function(s) are authoritative

- [ ] **Step 3: Write the target decision into session status**

Update `docs/sessions/SESSION_STATUS.md` with:
- target name
- reason for choosing it
- whether it came from a real failure or proactive verification

### Task 3: Execute the selected verification slice

**Files:**
- Read: exact ROM source in `src/`
- Read/Modify: matching Python files under `mud/`
- Modify: matching tests under `tests/`
- Modify: relevant audit doc under `docs/parity/`

- [ ] **Step 1: Read the ROM function before touching Python**

Run:
```bash
sed -n '<start>,<end>p' src/<target-file>.c
```

Expected:
- exact ROM control flow in hand
- no guesswork from tracker prose alone

- [ ] **Step 2: Write or tighten one focused failing test if a gap exists**

Test rule:
- prefer one focused regression first
- integration test if the behavior crosses modules
- unit test only when the surface is truly local

Template:
```python
def test_rom_behavior_name():
    result = behavior_under_test()
    assert result == expected_from_rom
```

- [ ] **Step 3: Run the focused test to confirm the gap**

Run:
```bash
./venv/bin/python -m pytest -q tests/<target-test>.py::<test_name>
```

Expected:
- FAIL if a real gap exists
- PASS if the tracker or suspicion was stale, in which case update docs instead of code

- [ ] **Step 4: Implement the minimal ROM-faithful change or doc reconciliation**

Implementation rule:
- if ROM and Python differ, change Python to ROM
- if behavior already matches ROM, change docs/tests only
- keep the patch minimal and cite ROM in parity-sensitive code

- [ ] **Step 5: Re-run the focused slice and one adjacent verification slice**

Run:
```bash
./venv/bin/python -m pytest -q tests/<target-test>.py::<test_name>
./venv/bin/python -m pytest -q <adjacent-tests>
```

Expected:
- target test passes
- adjacent tests stay green

### Task 4: Close the loop in docs and suite state

**Files:**
- Modify: `docs/parity/<TARGET>_AUDIT.md`
- Modify: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `docs/sessions/SESSION_STATUS.md`
- Create: `docs/sessions/SESSION_SUMMARY_2026-05-15_<topic>.md`

- [ ] **Step 1: Update the parity audit with the exact closure or verification result**

Document:
- ROM references used
- Python files changed
- tests added or run
- whether the issue was real code drift or stale documentation

- [ ] **Step 2: Update the tracker row only if the evidence supports it**

Rule:
- never advance tracker status without test-backed verification
- if nothing changed behaviorally, describe the reconciliation precisely

- [ ] **Step 3: Update session status with the new current state and next task**

Include:
- commands run
- result summary
- remaining open work, if any

- [ ] **Step 4: Create the dated session summary**

Filename pattern:
```text
docs/sessions/SESSION_SUMMARY_2026-05-15_<short-topic>.md
```

- [ ] **Step 5: Commit if this task changed repo contents**

```bash
git add docs/sessions/SESSION_STATUS.md docs/sessions/SESSION_SUMMARY_2026-05-15_<short-topic>.md docs/parity/<TARGET>_AUDIT.md docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md <code-files> <test-files>
git commit -m "fix: close <target-gap>"
```

---

## Self-Review

- Spec coverage: this plan covers both requested actions — full-suite rerun first, then selecting and executing the next ROM verification target from the observed result.
- Placeholder scan: no `TODO` or deferred implementation placeholders remain; each task has exact files, commands, and branch rules.
- Type consistency: the plan consistently uses the existing repo surfaces (`src/`, `mud/`, `tests/`, `docs/parity/`, `docs/sessions/`) and the current virtualenv test command.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-15-full-suite-rerun-and-next-rom-verification.md`.

Per your instruction, I am proceeding with inline execution now rather than stopping for an execution-mode choice.
