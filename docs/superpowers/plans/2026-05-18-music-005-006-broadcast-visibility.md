# Music Broadcast Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining user-visible `music.c` parity gaps so global and jukebox music broadcasts respect ROM-style visibility and active-connection semantics.

**Architecture:** Keep the existing `mud/music/__init__.py` queueing logic intact and add the missing delivery semantics around it. For the global channel, add a descriptor-aware recipient filter so only effectively playing characters hear music, mirroring ROM `d->connected == CON_PLAYING` with switched-player resolution. For jukebox room output, route messages through ROM-style per-viewer formatting so `$p` visibility fallback behaves correctly.

**Tech Stack:** Python 3.12, pytest, existing QuickMUD telnet/session model, `mud.music`, `mud.net.protocol`, `mud.utils.act`, ROM `src/music.c`.

---

### Task 1: Lock down the ROM behavior in tests

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_music.py` (or create if the current unit coverage has no good fit)
- Reference: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/music.c`

- [ ] **Step 1: Add a failing integration test for global-channel recipient gating**

Write a test that seeds `mud.music.channel_songs` and a song, then asserts:
- a connected playing PC hears the `Music:` output
- a linkless/menu-state PC does not
- if the project models switched characters, the original player identity is the recipient basis rather than the puppet

Use the current test fixtures or small in-test doubles that match the fields `song_update()` and the broadcaster actually read.

- [ ] **Step 2: Run the new test and verify it fails for the right reason**

Run: `./venv/bin/python -m pytest -q tests/integration/test_music_play.py -k 'global_music_recipient_gating'`

Expected: failure showing the current broadcaster still sends to an entity ROM would skip.

- [ ] **Step 3: Add a failing integration test for jukebox per-viewer visibility**

Write a test that places a jukebox object in a room with at least two viewers:
- one who can see the jukebox and should receive its short description
- one who cannot and should receive the ROM-equivalent fallback (effectively `something` through `$p` resolution)

The assertion should verify per-viewer divergence, not a single shared room string.

- [ ] **Step 4: Run the jukebox visibility test and verify it fails**

Run: `./venv/bin/python -m pytest -q tests/integration/test_music_play.py -k 'jukebox_visibility'`

Expected: failure because the current implementation broadcasts one preformatted string to everyone.

- [ ] **Step 5: Commit the red tests**

```bash
git add /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_music.py
git commit -m "test: add ROM music broadcast parity regressions"
```

### Task 2: Implement `MUSIC-005` global-channel connection semantics

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/protocol.py`
- Inspect: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/connection.py`
- Inspect: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/commands/imm_admin.py`
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py`

- [ ] **Step 1: Identify the minimal descriptor/session signal available at broadcast time**

Confirm which runtime fields cleanly answer the ROM question “is this descriptor in `CON_PLAYING`, and if switched, who is the real recipient?” Do not invent a second session model; reuse the existing connection/session object already attached to characters.

- [ ] **Step 2: Implement a descriptor-aware global music recipient filter**

Adjust the global music send path so it:
- still respects `COMM_NOMUSIC` and `COMM_QUIET`
- additionally skips characters not effectively in the playing state
- resolves switched-player delivery against the original player object if that concept exists in the current runtime

Keep the queue and line-advance logic unchanged.

- [ ] **Step 3: Run the focused global gating tests**

Run: `./venv/bin/python -m pytest -q tests/integration/test_music_play.py -k 'global_music_recipient_gating or loud'`

Expected: pass.

- [ ] **Step 4: Commit the global gating fix**

```bash
git add /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/protocol.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py
git commit -m "fix(parity): close MUSIC-005 global music recipient gating"
```

### Task 3: Implement `MUSIC-006` per-viewer jukebox formatting

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py`
- Inspect: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/utils/act.py`
- Inspect: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/protocol.py`
- Test: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py`

- [ ] **Step 1: Replace one-string room broadcasting for jukebox lines with per-viewer formatting**

Route the “starts playing …” and “bops: '…'” messages through the existing ROM-style act formatter or an equivalent per-viewer helper that can resolve `$p` against recipient visibility.

Constraint:
- do not rewrite generic room broadcasting for unrelated systems
- keep this slice local to the music subsystem unless a tiny shared helper extraction is clearly warranted

- [ ] **Step 2: Preserve current room-recipient behavior while changing only the formatting semantics**

The same people in the room should receive the message; only the object-name rendering should become ROM-correct on a per-recipient basis.

- [ ] **Step 3: Run the jukebox-focused tests**

Run: `./venv/bin/python -m pytest -q tests/integration/test_music_play.py -k 'jukebox_visibility or starts_playing or bops'`

Expected: pass.

- [ ] **Step 4: Commit the jukebox visibility fix**

```bash
git add /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py
git commit -m "fix(parity): close MUSIC-006 jukebox per-viewer visibility"
```

### Task 4: Audit docs, changelog, and verification

**Files:**
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/MUSIC_C_AUDIT.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md`
- Add: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-18_MUSIC_005_006_BROADCAST_VISIBILITY.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/CHANGELOG.md`
- Modify: `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/pyproject.toml`

- [ ] **Step 1: Mark `MUSIC-005` and `MUSIC-006` closed in the audit docs**

Update the gap table, closure summary, and tracker row so `music.c` moves from `95%` deferred to fully closed if both gaps land without leaving a new documented divergence behind.

- [ ] **Step 2: Add the release metadata**

Bump patch version and add a changelog entry describing:
- global music recipient gating parity
- per-viewer jukebox object visibility parity

- [ ] **Step 3: Run the subsystem verification band**

Run:
```bash
./venv/bin/python -m pytest -q tests/integration/test_music_play.py tests/integration/test_music_load_songs.py tests/test_music.py
./venv/bin/ruff check /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/music/__init__.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/net/protocol.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/integration/test_music_play.py /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/tests/test_music.py
```

Expected: all green.

- [ ] **Step 4: Run the full suite recertification**

Run: `./venv/bin/python -m pytest -q --maxfail=1`

Expected: full green baseline with the current pass/skip count updated in the session summary.

- [ ] **Step 5: Run GitNexus change detection and commit the documentation/release sweep**

Run change detection first, then commit:

```bash
git add /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/MUSIC_C_AUDIT.md /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_STATUS.md /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/docs/sessions/SESSION_SUMMARY_2026-05-18_MUSIC_005_006_BROADCAST_VISIBILITY.md /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/CHANGELOG.md /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/pyproject.toml
git commit -m "docs: close deferred music broadcast visibility gaps"
```
